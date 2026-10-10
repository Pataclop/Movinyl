"""PyQt6 desktop window: pick your folders, click, watch progress.

Same engine as the CLI/TUI. Heavy work runs in a background thread; the
:class:`QtReporter` forwards progress callbacks through Qt signals, which are
queued onto the UI thread automatically.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import bootstrap, engine, history
from . import platforminfo as pf
from .progress import Reporter

DEFAULT_INPUT = pf.PROJECT_ROOT / "PROCESSING_ZONE"
DEFAULT_PAGE = pf.PROJECT_ROOT / "PAGE_ZONE"

# Map engine task keys onto the three fixed progress bars (same as the TUI).
_BAR_FOR = {
    "overall": "overall",
    "extract": "extract",
    "disk": "render",
    "planche": "overall",
}


class QtReporter(QObject, Reporter):
    """Engine progress -> Qt signals (safe to call from any thread)."""

    sig_task = pyqtSignal(str, str, object)
    sig_advance = pyqtSignal(str, int)
    sig_update = pyqtSignal(str, object, object, object)
    sig_remove = pyqtSignal(str)
    sig_log = pyqtSignal(str)

    def task(self, key, description, total):
        self.sig_task.emit(key, description, total)

    def advance(self, key, amount=1):
        self.sig_advance.emit(key, amount)

    def update(self, key, *, description=None, total=None, completed=None):
        self.sig_update.emit(key, description, total, completed)

    def remove(self, key):
        self.sig_remove.emit(key)

    def log(self, message):
        self.sig_log.emit(str(message))


class FolderPicker(QWidget):
    """A line edit + "Browse…" + "Open" button row."""

    changed = pyqtSignal()

    def __init__(self, initial: Path, title: str) -> None:
        super().__init__()
        self._title = title
        self.edit = QLineEdit(str(initial))
        self.edit.editingFinished.connect(self.changed.emit)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        open_btn = QPushButton("Open")
        open_btn.clicked.connect(lambda: _open_in_explorer(self.path()))
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.edit, 1)
        row.addWidget(browse)
        row.addWidget(open_btn)

    def path(self) -> Path:
        return Path(self.edit.text().strip() or ".")

    def _browse(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, self._title, str(self.path()))
        if chosen:
            self.edit.setText(chosen)
            self.changed.emit()


def _open_in_explorer(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class MainWindow(QMainWindow):
    sig_done = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Movinyl")
        self.resize(900, 720)

        self.reporter = QtReporter()
        self.reporter.sig_task.connect(self._bar_task)
        self.reporter.sig_advance.connect(self._bar_advance)
        self.reporter.sig_update.connect(self._bar_update)
        self.reporter.sig_remove.connect(self._bar_remove)
        self.reporter.sig_log.connect(self.write_log)
        self.sig_done.connect(self._finish)

        self._cancel = threading.Event()
        self._busy = False

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        banner = QLabel("◉  M O V I N Y L  ◉")
        banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        banner.setFont(font)
        root.addWidget(banner)

        # -- folders + options ------------------------------------------------
        folders = QGroupBox("Folders")
        form = QFormLayout(folders)
        self.video_dir = FolderPicker(DEFAULT_INPUT, "Choose the video folder")
        self.disk_dir = FolderPicker(DEFAULT_PAGE, "Choose the disk folder")
        self.video_dir.changed.connect(self.refresh_lists)
        self.disk_dir.changed.connect(self.refresh_lists)
        form.addRow("Videos (→ disks written here):", self.video_dir)
        form.addRow("Disks (→ pages / planches):", self.disk_dir)
        root.addWidget(folders)

        opts = QGroupBox("Options")
        opt_row = QHBoxLayout(opts)
        opt_row.addWidget(QLabel("Frames:"))
        self.frames = QSpinBox()
        self.frames.setRange(10, 20000)
        self.frames.setValue(engine.DEFAULT_FRAME_COUNT)
        opt_row.addWidget(self.frames)
        opt_row.addSpacing(16)
        opt_row.addWidget(QLabel("Max height:"))
        self.max_height = QSpinBox()
        self.max_height.setRange(0, 4320)
        self.max_height.setValue(engine.DEFAULT_MAX_HEIGHT)
        self.max_height.setSpecialValueText("full")
        opt_row.addWidget(self.max_height)
        opt_row.addSpacing(16)
        self.overwrite = QCheckBox("Re-process films already done")
        self.overwrite.setToolTip(
            "Re-render disks and pages even if they exist or are recorded "
            "in the history (✓ in the lists).")
        opt_row.addWidget(self.overwrite)
        opt_row.addStretch(1)
        root.addWidget(opts)

        # -- file lists -------------------------------------------------------
        lists = QHBoxLayout()
        self.videos_box = QGroupBox()
        self.videos_list = QListWidget()
        QVBoxLayout(self.videos_box).addWidget(self.videos_list)
        self.disks_box = QGroupBox()
        self.disks_list = QListWidget()
        QVBoxLayout(self.disks_box).addWidget(self.disks_list)
        lists.addWidget(self.videos_box)
        lists.addWidget(self.disks_box)
        root.addLayout(lists, 2)

        # -- actions ----------------------------------------------------------
        buttons = QHBoxLayout()
        self.btn_disks = QPushButton("▶  Disks")
        self.btn_pages = QPushButton("▤  Pages")
        self.btn_planche = QPushButton("▦  Planche")
        self.btn_setup = QPushButton("⚙  Setup")
        self.btn_refresh = QPushButton("⟳  Refresh")
        self.btn_cancel = QPushButton("✕  Cancel")
        self.btn_disks.clicked.connect(self.action_disks)
        self.btn_pages.clicked.connect(self.action_pages)
        self.btn_planche.clicked.connect(self.action_planche)
        self.btn_setup.clicked.connect(self.action_setup)
        self.btn_refresh.clicked.connect(self.refresh_lists)
        self.btn_cancel.clicked.connect(self.action_cancel)
        self.btn_cancel.setEnabled(False)
        # The .exe ships prebuilt renderers and has no compiler/sources to rebuild.
        self.btn_setup.setVisible(not pf.FROZEN)
        self._job_buttons = (self.btn_disks, self.btn_pages,
                             self.btn_planche, self.btn_setup)
        for b in (*self._job_buttons, self.btn_refresh, self.btn_cancel):
            b.setMinimumHeight(34)
            buttons.addWidget(b)
        root.addLayout(buttons)

        # -- progress ---------------------------------------------------------
        progress = QGroupBox("Progress")
        pform = QFormLayout(progress)
        self._bars = {}
        self._labels = {}
        for key, label in (("overall", "Overall"), ("extract", "Extract"),
                           ("render", "Render")):
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setFormat("%v / %m  (%p%)")
            lab = QLabel(label)
            lab.setMinimumWidth(140)
            self._bars[key] = bar
            self._labels[key] = lab
            pform.addRow(lab, bar)
        root.addWidget(progress)

        # -- log --------------------------------------------------------------
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        mono = QFont("Consolas" if sys.platform.startswith("win") else "Monospace")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.log.setFont(mono)
        root.addWidget(self.log, 2)

        self.statusBar().showMessage(
            f"{pf.system()} · {pf.cpu_count()} cores")
        self.refresh_lists()
        self.write_log("Welcome. Pick a video folder, then click Disks.")
        self.write_log("✓ = already processed (skipped unless “Re-process” is checked).")
        if pf.disk_binary() is None:
            self.write_log("disk/page renderers not built yet — click Setup first.")

    # -- progress bars (UI thread) ------------------------------------------
    def _bar(self, key: str):
        k = _BAR_FOR.get(key, "extract")
        return self._bars[k], self._labels[k]

    def _bar_task(self, key, description, total) -> None:
        bar, label = self._bar(key)
        label.setText(str(description)[:28])
        if total:
            bar.setRange(0, int(total))
        else:
            bar.setRange(0, 0)  # unknown total -> busy indicator
        bar.setValue(0)

    def _bar_advance(self, key, amount) -> None:
        bar, _ = self._bar(key)
        bar.setValue(bar.value() + int(amount))

    def _bar_update(self, key, description, total, completed) -> None:
        bar, label = self._bar(key)
        if description is not None:
            label.setText(str(description)[:28])
        if total is not None:
            bar.setRange(0, int(total))
        if completed is not None:
            bar.setValue(int(completed))

    def _bar_remove(self, key) -> None:
        bar, label = self._bar(key)
        bar.setRange(0, 100)
        bar.setValue(0)
        label.setText("idle")

    def write_log(self, message: str) -> None:
        self.log.appendPlainText(message)

    # -- lists ---------------------------------------------------------------
    def refresh_lists(self) -> None:
        vdir, ddir = self.video_dir.path(), self.disk_dir.path()
        videos = engine.discover_videos(vdir) if vdir.is_dir() else []
        disks = engine.discover_disks(ddir) if ddir.is_dir() else []
        self.videos_box.setTitle(f"Videos ({len(videos)})")
        self.disks_box.setTitle(f"Disks ({len(disks)})")
        films = {f.name: f for f in history.all_films()}

        def mark(name: str, done_at) -> str:
            return f"✓  {name}" if done_at else f"    {name}"

        self.videos_list.clear()
        self.videos_list.addItems([
            mark(p.name, getattr(films.get(engine.sanitize_name(p.stem)), "disk_at", None))
            for p in videos])
        self.disks_list.clear()
        self.disks_list.addItems([
            mark(p.name, getattr(films.get(p.stem), "page_at", None))
            for p in disks])

    # -- job plumbing --------------------------------------------------------
    def _start(self, label: str, fn: Callable[[], str]) -> None:
        if self._busy:
            return
        self._busy = True
        self._cancel = threading.Event()
        for b in self._job_buttons:
            b.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.write_log(label)

        def run():
            try:
                msg = fn()
            except Exception as exc:  # noqa: BLE001
                msg = f"[error] {exc}"
            self.sig_done.emit(msg)

        threading.Thread(target=run, daemon=True).start()

    def _finish(self, summary: str) -> None:
        self._busy = False
        for b in self._job_buttons:
            b.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.write_log(summary)
        self.refresh_lists()

    # -- actions -------------------------------------------------------------
    def action_disks(self) -> None:
        vdir = self.video_dir.path()
        n, max_h, overwrite = (self.frames.value(), self.max_height.value(),
                               self.overwrite.isChecked())

        def job() -> str:
            outs = engine.run_disk_batch(
                vdir, n=n, reporter=self.reporter, cancel=self._cancel,
                overwrite=overwrite, max_height=max_h)
            return f"Done: {len(outs)} disk(s) in {vdir}"

        self._start(f"Generating disks from {vdir} (n={n}) …", job)

    def action_pages(self) -> None:
        ddir = self.disk_dir.path()
        overwrite = self.overwrite.isChecked()

        def job() -> str:
            outs = engine.run_page_batch(ddir, reporter=self.reporter,
                                         cancel=self._cancel, overwrite=overwrite)
            return f"Done: {len(outs)} page(s) in {ddir}"

        self._start(f"Generating pages from {ddir} …", job)

    def action_planche(self) -> None:
        from .planche import make_contact_sheets
        ddir = self.disk_dir.path()

        def job() -> str:
            disks = engine.discover_disks(ddir)
            if not disks:
                return f"[error] No disk PNGs found in {ddir}"
            sheets = make_contact_sheets(disks, ddir, reporter=self.reporter)
            return f"Done: {len(sheets)} contact sheet(s) in {ddir}"

        self._start("Assembling contact sheets …", job)

    def action_setup(self) -> None:
        def job() -> str:
            bootstrap.setup(install_system=False, install_python=False,
                            log=self.reporter.log)
            return "Setup complete."

        self._start("Building C++ renderers …", job)

    def action_cancel(self) -> None:
        if self._busy:
            self._cancel.set()
            self.write_log("Cancelling …")

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if self._busy:
            answer = QMessageBox.question(
                self, "Movinyl", "A job is running. Cancel it and quit?")
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._cancel.set()
        event.accept()


def run(argv: Optional[list] = None) -> int:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("Movinyl")
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    return app.exec()
