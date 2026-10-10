"""PyQt6 desktop window: pick your folders, click, watch progress.

Same engine as the CLI/TUI. Heavy work runs in a background thread; the
:class:`QtReporter` forwards progress callbacks through Qt signals, which are
queued onto the UI thread automatically.
"""
from __future__ import annotations

import hashlib
import html
import os
import subprocess
import sys
import tempfile
import threading
import time
from collections import deque
from pathlib import Path
from typing import Callable, List, Optional, Sequence

from PyQt6.QtCore import (
    QEvent,
    QFileSystemWatcher,
    QItemSelectionModel,
    QObject,
    QPoint,
    QPointF,
    QRectF,
    QSettings,
    QSize,
    QStandardPaths,
    Qt,
    QTimer,
    QUrl,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QConicalGradient,
    QDesktopServices,
    QFont,
    QFontDatabase,
    QIcon,
    QImage,
    QImageReader,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QRadialGradient,
    QShortcut,
    QValidator,
)
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import bootstrap, engine, history, tmdb
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

# -- theme --------------------------------------------------------------------
# A dark "record sleeve" base with a sunset-to-ocean rainbow for accents.
BG = "#12111a"
SURFACE = "#1c1a29"
SURFACE_2 = "#262338"
FIELD = "#15131f"
BORDER = "#34304d"
TEXT = "#ece9ff"
MUTED = "#9a95b8"
DIM = "#5d5878"
PINK = "#ff4f9a"
ORANGE = "#ff9f43"
YELLOW = "#ffd93d"
TEAL = "#2ee6c5"
BLUE = "#4d9bff"
VIOLET = "#9b6bff"
RED = "#ff5c6c"
RAINBOW = (PINK, ORANGE, YELLOW, TEAL, BLUE, VIOLET)


def _grad(a: str, b: str) -> str:
    return f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {a}, stop:1 {b})"


STYLESHEET = f"""
* {{ color: {TEXT}; font-size: 10pt; }}
QMainWindow, QWidget#central {{ background: {BG}; }}
QToolTip {{
    background: {SURFACE_2}; color: {TEXT};
    border: 1px solid {VIOLET}; border-radius: 6px; padding: 4px 8px;
}}

QGroupBox {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 14px;
    margin-top: 16px;
    padding: 16px 12px 12px 12px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin; subcontrol-position: top left;
    left: 16px; padding: 2px 10px;
    border-radius: 8px;
    color: {BG}; background: {VIOLET};
}}
QGroupBox#folders::title  {{ background: {_grad(PINK, ORANGE)}; }}
QGroupBox#options::title  {{ background: {_grad(ORANGE, YELLOW)}; }}
QGroupBox#videos::title   {{ background: {_grad(TEAL, BLUE)}; }}
QGroupBox#disks::title    {{ background: {_grad(BLUE, VIOLET)}; }}
QGroupBox#progress::title {{ background: {_grad(VIOLET, PINK)}; }}
QGroupBox#log::title      {{ background: {_grad(YELLOW, TEAL)}; }}

QLabel {{ background: transparent; }}
QLabel#formLabel {{ color: {MUTED}; }}

QLineEdit, QSpinBox {{
    background: {FIELD}; border: 1px solid {BORDER}; border-radius: 8px;
    padding: 6px 8px; selection-background-color: {VIOLET};
}}
QLineEdit:focus, QSpinBox:focus {{ border: 1px solid {TEAL}; }}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 18px; background: {SURFACE_2}; border: none; border-radius: 4px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background: {BORDER}; }}

QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border-radius: 5px;
    border: 2px solid {BORDER}; background: {FIELD};
}}
QCheckBox::indicator:hover {{ border-color: {TEAL}; }}
QCheckBox::indicator:checked {{ background: {_grad(TEAL, BLUE)}; border-color: {TEAL}; }}

QListWidget, QPlainTextEdit {{
    background: {FIELD}; border: 1px solid {BORDER}; border-radius: 10px;
    padding: 6px; outline: none;
}}
QListWidget::item {{ padding: 5px 8px; border-radius: 6px; }}
QListWidget::item:hover {{ background: {SURFACE_2}; }}
QListWidget::item:selected {{ background: {_grad("#3a2a5e", "#22365e")}; }}

QPushButton {{
    background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: 10px;
    padding: 8px 18px; font-weight: 700;
}}
QPushButton:hover {{ border-color: {MUTED}; }}
QPushButton:pressed {{ background: {BORDER}; }}
QPushButton:disabled {{ color: {DIM}; background: #1a1826; border-color: #24212f; }}
QPushButton#small {{ padding: 6px 12px; font-weight: 600; border-radius: 8px; }}

QPushButton#disks   {{ background: {_grad(PINK, ORANGE)}; border: none; color: {BG}; }}
QPushButton#pages   {{ background: {_grad(TEAL, BLUE)};   border: none; color: {BG}; }}
QPushButton#planche {{ background: {_grad(VIOLET, PINK)}; border: none; color: {BG}; }}
QPushButton#disks:hover   {{ background: {_grad("#ff6fae", "#ffb469")}; }}
QPushButton#pages:hover   {{ background: {_grad("#5cf0d5", "#73b2ff")}; }}
QPushButton#planche:hover {{ background: {_grad("#b28cff", "#ff72b0")}; }}
QPushButton#disks:disabled, QPushButton#pages:disabled, QPushButton#planche:disabled {{
    background: #1a1826; color: {DIM}; border: 1px solid #24212f;
}}
QPushButton#setup {{ color: {YELLOW}; }}
QPushButton#setup:hover {{ border-color: {YELLOW}; }}
QPushButton#refresh {{ color: {TEAL}; }}
QPushButton#refresh:hover {{ border-color: {TEAL}; }}
QPushButton#cancel {{ color: {RED}; border-color: #5a2a36; }}
QPushButton#cancel:hover {{ background: #3a1c26; border-color: {RED}; }}
QPushButton#cancel:disabled {{ color: {DIM}; border-color: #24212f; }}

QProgressBar {{
    background: {FIELD}; border: 1px solid {BORDER}; border-radius: 9px;
    min-height: 18px; text-align: center; font-weight: 600;
}}
QProgressBar::chunk {{ border-radius: 8px; }}
QProgressBar#overall::chunk {{ background: {_grad(PINK, ORANGE)}; }}
QProgressBar#extract::chunk {{ background: {_grad(TEAL, BLUE)}; }}
QProgressBar#render::chunk  {{ background: {_grad(VIOLET, PINK)}; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {VIOLET}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {BORDER}; border-radius: 3px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: {VIOLET}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

QTabWidget::pane {{ border: none; top: 4px; }}
QTabBar::tab {{
    background: {SURFACE}; color: {MUTED}; border: 1px solid {BORDER};
    border-radius: 9px; padding: 6px 18px; margin-right: 6px; font-weight: 600;
}}
QTabBar::tab:hover {{ color: {TEXT}; border-color: {MUTED}; }}
QTabBar::tab:selected {{ background: {_grad(TEAL, BLUE)}; color: {BG}; border: none; }}

QComboBox {{
    background: {FIELD}; border: 1px solid {BORDER}; border-radius: 8px;
    padding: 6px 8px;
}}
QComboBox:focus {{ border: 1px solid {TEAL}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE_2}; border: 1px solid {BORDER};
    selection-background-color: {VIOLET}; outline: none;
}}

QTableWidget {{
    background: {FIELD}; border: 1px solid {BORDER}; border-radius: 10px;
    gridline-color: transparent; outline: none;
    alternate-background-color: #191725;
}}
QTableWidget::item {{ padding: 3px 6px; background: transparent; }}
/* Solid: a gradient would restart in every cell of the selected row. */
QTableWidget::item:selected {{ background: #2e305e; color: {TEXT}; }}
QHeaderView::section {{
    background: {SURFACE_2}; color: {MUTED}; border: none;
    border-right: 1px solid {BORDER}; padding: 5px 8px; font-weight: 600;
}}
QTableCornerButton::section {{ background: {SURFACE_2}; border: none; }}
QPushButton#danger {{ color: {RED}; }}
QPushButton#danger:hover {{ border-color: {RED}; }}
QPushButton#danger:disabled {{ color: {DIM}; }}

QStatusBar {{ background: {SURFACE}; color: {MUTED}; border-top: 1px solid {BORDER}; }}
QMessageBox {{ background: {SURFACE}; }}
QDialog {{ background: {BG}; }}
QLabel#poster {{
    background: {FIELD}; border: 1px solid {BORDER}; border-radius: 10px; color: {DIM};
}}
QLabel#matchTitle {{ font-size: 13pt; font-weight: 700; }}
QPushButton#use {{ background: {_grad(TEAL, BLUE)}; border: none; color: {BG}; }}
QPushButton#use:hover {{ background: {_grad("#5cf0d5", "#73b2ff")}; }}
QPushButton#use:disabled {{ background: #1a1826; color: {DIM}; border: 1px solid #24212f; }}

QMenu {{
    background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{ padding: 6px 26px 6px 14px; border-radius: 6px; }}
QMenu::item:selected {{ background: {_grad("#3a2a5e", "#22365e")}; }}
QMenu::item:disabled {{ color: {DIM}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 5px 8px; }}

QSplitter::handle {{ background: transparent; border-radius: 3px; }}
QSplitter::handle:hover {{ background: {BORDER}; }}

QPushButton#toggle {{ padding: 6px 12px; font-weight: 600; border-radius: 8px; }}
QPushButton#toggle:checked {{ background: {_grad(TEAL, BLUE)}; color: {BG}; border: none; }}

QListWidget#grid {{ padding: 10px; }}
QListWidget#grid::item {{ padding: 6px; border-radius: 12px; }}
QWidget#detailsBody {{ background: transparent; }}
QLabel#detailTitle {{ font-size: 14pt; font-weight: 700; }}
QLabel#hint {{ color: {DIM}; }}
"""

# Log lines are tinted by what they announce (first match wins).
_LOG_COLORS = (
    ("[error]", RED),
    ("Cancel", ORANGE),
    ("Done", TEAL),
    ("Setup complete", TEAL),
    ("✓", TEAL),
)


def _log_color(message: str) -> str:
    for needle, color in _LOG_COLORS:
        if needle in message:
            return color
    if message.rstrip().endswith("…"):
        return YELLOW
    return TEXT


def _arrow_qss() -> str:
    """Spin-box arrows as tiny painted PNGs (QSS can't draw triangles itself)."""
    out = Path(tempfile.gettempdir()) / "movinyl-ui"
    out.mkdir(parents=True, exist_ok=True)
    rules = []
    for name, pts in (("up", ((1, 7), (5, 2), (9, 7))),
                      ("down", ((1, 3), (5, 8), (9, 3)))):
        pix = QPixmap(10, 10)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(TEAL))
        p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in pts]))
        p.end()
        path = out / f"arrow-{name}.png"
        pix.save(str(path))
        rules.append(f"QSpinBox::{name}-arrow {{ image: url({path.as_posix()}); "
                     f"width: 10px; height: 10px; }}")
    rules.append(f"QComboBox::down-arrow {{ image: url({(out / 'arrow-down.png').as_posix()}); "
                 f"width: 10px; height: 10px; }}")
    return "\n".join(rules)


def _load_fonts() -> str:
    """Register the bundled Futura faces; return the family to use for titles."""
    family = ""
    for name in ("futura medium bt.ttf", "futura light bt.ttf"):
        path = pf.RESOURCE_ROOT / name
        if not path.is_file():
            continue
        fid = QFontDatabase.addApplicationFont(str(path))
        families = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
        if families and not family:
            family = families[0]
    return family


class VinylBanner(QWidget):
    """Header: a rainbow record (spins while a job runs) + gradient title."""

    def __init__(self, title_family: str = "") -> None:
        super().__init__()
        self.setFixedHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._family = title_family
        self._angle = 90.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def set_spinning(self, on: bool) -> None:
        if on:
            self._timer.start()
        else:
            self._timer.stop()

    def _tick(self) -> None:
        self._angle = (self._angle - 3.0) % 360
        self.update()

    def _font(self, size: int, spacing: float, bold: bool) -> QFont:
        font = QFont(self._family) if self._family else QFont()
        font.setPointSize(size)
        font.setBold(bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
        return font

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Card with a faint rainbow wash.
        card = QPainterPath()
        card.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 18, 18)
        wash = QLinearGradient(0, 0, w, 0)
        for i, col in enumerate(RAINBOW):
            c = QColor(col)
            c.setAlpha(34)
            wash.setColorAt(i / (len(RAINBOW) - 1), c)
        p.fillPath(card, QColor(SURFACE))
        p.fillPath(card, QBrush(wash))
        p.setPen(QPen(QColor(BORDER), 1))
        p.drawPath(card)

        # The record: a rotating conical rainbow, grooves, sheen, label.
        r = (h - 22) / 2
        center = QPointF(22 + r, h / 2)
        cone = QConicalGradient(center, self._angle)
        stops = (*RAINBOW, RAINBOW[0])
        for i, col in enumerate(stops):
            cone.setColorAt(i / (len(stops) - 1), QColor(col))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(cone))
        p.drawEllipse(center, r, r)

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(0, 0, 0, 70), 1.1))
        k = r * 0.95
        while k > r * 0.36:
            p.drawEllipse(center, k, k)
            k -= 3.0

        sheen = QRadialGradient(QPointF(center.x() - r * 0.4, center.y() - r * 0.5), r * 1.2)
        sheen.setColorAt(0, QColor(255, 255, 255, 80))
        sheen.setColorAt(1, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(sheen))
        p.drawEllipse(center, r, r)

        p.setBrush(QColor(BG))
        p.drawEllipse(center, r * 0.33, r * 0.33)
        p.setBrush(QColor(YELLOW))
        p.drawEllipse(center, r * 0.27, r * 0.27)
        p.setBrush(QColor(BG))
        p.drawEllipse(center, r * 0.06, r * 0.06)

        # Title with a rainbow fill, subtitle underneath.
        x0 = center.x() + r + 28
        title = QPainterPath()
        title.addText(x0, h / 2 + 6, self._font(30, 8, True), "MOVINYL")
        tb = title.boundingRect()
        fill = QLinearGradient(tb.left(), 0, tb.right(), 0)
        for i, col in enumerate(RAINBOW):
            fill.setColorAt(i / (len(RAINBOW) - 1), QColor(col))
        p.fillPath(title, QBrush(fill))

        p.setFont(self._font(10, 2, False))
        p.setPen(QColor(MUTED))
        p.drawText(QPointF(x0 + 2, h / 2 + 30), "every film, pressed into colour")
        p.end()


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

    # Asked from a worker thread: the UI thread opens the TMDB match window and
    # the worker waits for its answer (one window at a time).
    sig_resolve = pyqtSignal(str, object)
    ask_tmdb = True

    def __init__(self) -> None:
        super().__init__()
        self._resolve_lock = threading.Lock()

    def resolve_film(self, name):
        if not self.ask_tmdb:
            return None
        with self._resolve_lock:
            if not self.ask_tmdb:  # "Skip all" while we were queued
                return None
            reply = {"done": threading.Event(), "info": None}
            self.sig_resolve.emit(name, reply)
            reply["done"].wait()
            return reply["info"]


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
        for b in (browse, open_btn):
            b.setObjectName("small")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            row.addWidget(b)

    def path(self) -> Path:
        return Path(self.edit.text().strip() or ".")

    def _browse(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, self._title, str(self.path()))
        if chosen:
            self.edit.setText(chosen)
            self.changed.emit()


class _FolderDrop(QObject):
    """Event filter: a folder (or a file, meaning its folder) dropped on the
    watched widgets is handed to ``on_drop``."""

    def __init__(self, on_drop: Callable[[Path], None], *widgets: QWidget) -> None:
        super().__init__(widgets[0])
        self._on_drop = on_drop
        for w in widgets:
            w.setAcceptDrops(True)
            w.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 - Qt naming
        kind = event.type()
        if kind not in (QEvent.Type.DragEnter, QEvent.Type.DragMove, QEvent.Type.Drop):
            return False
        mime = event.mimeData()
        paths = [Path(u.toLocalFile()) for u in (mime.urls() if mime.hasUrls() else ())
                 if u.isLocalFile()]
        if not paths:
            return False
        event.acceptProposedAction()
        if kind == QEvent.Type.Drop:
            self._on_drop(paths[0] if paths[0].is_dir() else paths[0].parent)
        return True


def _open_in_explorer(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def _muted(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("formLabel")
    return lab


def _open_file(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def _reveal(path: Path) -> None:
    """Show ``path`` selected in the system file manager."""
    if sys.platform.startswith("win"):
        subprocess.Popen(["explorer", "/select,", str(path)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path.parent)])


def _human_duration(seconds: float) -> str:
    """``42 s``, ``3 min 05 s``, ``1 h 07 min``."""
    s = int(round(seconds))
    if s < 60:
        return f"{s} s"
    if s < 3600:
        return f"{s // 60} min {s % 60:02d} s"
    return f"{s // 3600} h {s % 3600 // 60:02d} min"


def _eta_text(seconds: float) -> str:
    """A remaining time coarse enough not to flicker: ``45 s``, ``4 min``."""
    if seconds < 60:
        return f"{max(5, int(round(seconds / 5)) * 5)} s"
    if seconds < 3600:
        return f"{int(round(seconds / 60))} min"
    return _human_duration(seconds)


def _settings() -> QSettings:
    """What the window remembers (folders, options, layout): an INI file in
    the user's config folder, or ``$MOVINYL_SETTINGS``."""
    path = os.environ.get("MOVINYL_SETTINGS")
    if path:
        return QSettings(path, QSettings.Format.IniFormat)
    return QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                     "Movinyl", "Movinyl")


def _cache_dir() -> Path:
    """Disposable files (disk thumbnails): ``$MOVINYL_CACHE`` or the user cache."""
    env = os.environ.get("MOVINYL_CACHE")
    if env:
        return Path(env)
    location = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.CacheLocation)
    return Path(location or Path(tempfile.gettempdir()) / "movinyl-cache")


def _barcode_pixmap(colors: Sequence, width: int = 150, height: int = 16) -> QPixmap:
    """Tiny movie barcode of a film's per-frame mean colors."""
    data = bytes(c for rgb in colors for c in rgb)
    img = QImage(data, len(colors), 1, 3 * len(colors), QImage.Format.Format_RGB888)
    return QPixmap.fromImage(img.scaled(
        width, height, Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation))


def _ring_image(colors: Sequence, size: int) -> QImage:
    """Flat rings of the per-frame mean colors, frame 1 outermost (the
    ``redraw --style disk`` look): stands in for a disk whose PNG is gone."""
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    # Thinner rings than a pixel would only overdraw each other.
    rings = max(1, min(len(colors), size // 2))
    for k in range(rings):
        p.setBrush(QColor(*colors[k * len(colors) // rings]))
        r = size / 2 * (rings - k) / rings
        p.drawEllipse(QPointF(size / 2, size / 2), r, r)
    p.end()
    return image


def _round_image(image: QImage, ratio: float = 1.0) -> QImage:
    """The centered disk of a square ``image`` (radius ``ratio`` x half its
    side) on transparency, with anti-aliased edges."""
    size = image.width()
    out = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(image))  # texture anchored at (0, 0), like the image
    r = size / 2 * ratio
    p.drawEllipse(QPointF(size / 2, size / 2), r, r)
    p.end()
    return out


# The disk renderer keeps its outermost ring SAFE_DIST px inside the square
# (see src/disk/disk.cpp); everything outside it is black background.
_SAFE_DIST = 15


class Thumbnails(QObject):
    """Round disk thumbnails for the Library, made off the UI thread.

    A thumbnail is the film's disk PNG scaled down and clipped to the disk or,
    when the PNG is gone, flat rings drawn from the stored mean colors. They
    are kept in memory and as small PNGs in the user cache folder, so a large
    library opens instantly the next time.
    """

    SIZE = 240
    ready = pyqtSignal(str)              # key of a thumbnail that just arrived
    _made = pyqtSignal(str, object)      # worker -> UI thread (QImage or None)

    def __init__(self, workers: int = 2) -> None:
        super().__init__()
        self._pixmaps: dict = {}
        self._queue: deque = deque()
        self._queued: set = set()
        self._cond = threading.Condition()
        self._dir = _cache_dir() / "thumbs"
        self._made.connect(self._store)
        for _ in range(workers):
            threading.Thread(target=self._work, daemon=True).start()

    @staticmethod
    def key(film: history.Film) -> str:
        return f"{film.id}:{film.disk_at}:{film.disk_path}"

    def get(self, film: history.Film, urgent: bool = False) -> Optional[QPixmap]:
        """The film's thumbnail (a null pixmap if it has neither disk nor
        colors), or None while it is being made: ``ready`` follows."""
        key = self.key(film)
        if key in self._pixmaps:
            return self._pixmaps[key]
        job = (key, film.name, film.disk_path, film.frames)
        with self._cond:
            if key in self._queued:
                if urgent and job in self._queue:  # jump the queue
                    self._queue.remove(job)
                    self._queue.appendleft(job)
            else:
                self._queued.add(key)
                if urgent:
                    self._queue.appendleft(job)
                else:
                    self._queue.append(job)
                self._cond.notify()
        return None

    def _work(self) -> None:
        while True:
            with self._cond:
                while not self._queue:
                    self._cond.wait()
                key, name, path, frames = self._queue.popleft()
            try:
                image = self._make(name, path, frames)
            except Exception:  # noqa: BLE001 - a broken file just has no thumbnail
                image = None
            try:
                self._made.emit(key, image)
            except RuntimeError:  # the window is gone (app quitting)
                return

    def _make(self, name: str, path: Optional[str],
              frames: Optional[int]) -> Optional[QImage]:
        if path and os.path.isfile(path):
            st = os.stat(path)
            digest = hashlib.sha1(
                f"{os.path.abspath(path)}|{st.st_size}|{st.st_mtime_ns}|{self.SIZE}"
                .encode()).hexdigest()
            cached = self._dir / f"{digest}.png"
            image = QImage(str(cached)) if cached.is_file() else QImage()
            if not image.isNull():
                return image
            reader = QImageReader(path)
            reader.setScaledSize(QSize(self.SIZE, self.SIZE))  # disks are square
            image = reader.read()
            if not image.isNull():
                ratio = ((frames - _SAFE_DIST - 0.5) / frames
                         if frames and frames > 2 * _SAFE_DIST else 0.99)
                image = _round_image(image, ratio)
                try:
                    self._dir.mkdir(parents=True, exist_ok=True)
                    image.save(str(cached))
                except OSError:
                    pass
                return image
        colors = history.mean_colors(name)
        return _ring_image(colors, self.SIZE) if colors else None

    def _store(self, key: str, image) -> None:
        with self._cond:
            self._queued.discard(key)
        self._pixmaps[key] = QPixmap.fromImage(image) if image is not None else QPixmap()
        self.ready.emit(key)


_SORT_KEY = Qt.ItemDataRole.UserRole + 1


class _Cell(QTableWidgetItem):
    """Table cell that sorts by a hidden key (numbers sort as numbers)."""

    def __init__(self, text: str, key) -> None:
        super().__init__(text)
        self.setData(_SORT_KEY, key)

    def __lt__(self, other) -> bool:
        return self.data(_SORT_KEY) < other.data(_SORT_KEY)


class YearSpin(QSpinBox):
    """Year bound; its far end (``unbounded``) reads "any" and means no bound."""

    def __init__(self, unbounded: int) -> None:
        super().__init__()
        self.unbounded = unbounded
        self.setRange(min(1880, unbounded), max(2100, unbounded))
        self.setValue(unbounded)
        self.setMinimumWidth(80)

    def textFromValue(self, value: int) -> str:  # noqa: N802 - Qt naming
        return "any" if value == self.unbounded else str(value)

    def valueFromText(self, text: str) -> int:  # noqa: N802 - Qt naming
        return int(text) if text.isdigit() else self.unbounded

    def validate(self, text: str, pos: int):
        if text == "any" or (text.isdigit() and len(text) == 4):
            state = QValidator.State.Acceptable
        elif "any".startswith(text) or (text.isdigit() and len(text) < 4):
            state = QValidator.State.Intermediate
        else:
            state = QValidator.State.Invalid
        return state, text, pos

    def bound(self) -> Optional[int]:
        return None if self.value() == self.unbounded else self.value()


class DiskView(QWidget):
    """A film's disk, round on a soft shadow, or a dashed placeholder.

    ``side`` px when there is room, shrinking to ``minimum`` in a short window.
    """

    def __init__(self, side: int = 216, minimum: int = 110) -> None:
        super().__init__()
        self._side = side
        self.setMinimumSize(minimum, minimum)
        self._pixmap: Optional[QPixmap] = None
        self._text = ""

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt naming
        return QSize(self._side, self._side)

    def show_disk(self, pixmap: Optional[QPixmap], text: str = "") -> None:
        self._pixmap = pixmap if pixmap is not None and not pixmap.isNull() else None
        self._text = text
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        side = min(self.width(), self.height(), self._side) - 12
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        center = rect.center()
        if self._pixmap is None:
            p.setPen(QPen(QColor(BORDER), 2, Qt.PenStyle.DashLine))
            p.setBrush(QColor(FIELD))
            p.drawEllipse(rect)
            p.setPen(QColor(DIM))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                       self._text)
            return
        shadow = QRadialGradient(center, side / 2 + 6)
        shadow.setColorAt(0.9, QColor(0, 0, 0, 150))
        shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(shadow))
        p.drawEllipse(center, side / 2 + 6, side / 2 + 6)
        p.drawPixmap(rect.toRect(), self._pixmap)


class FilmDetails(QWidget):
    """Library side pane: the selected film's disk, facts and files."""

    def __init__(self, thumbs: Thumbnails) -> None:
        super().__init__()
        self.setObjectName("detailsBody")
        self._thumbs = thumbs
        self._film: Optional[history.Film] = None
        thumbs.ready.connect(self._thumb_ready)

        self.disk = DiskView()
        self.title = QLabel()
        self.title.setObjectName("detailTitle")
        self.title.setWordWrap(True)
        self.title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.meta = _muted("")
        self.meta.setWordWrap(True)
        self.meta.setOpenExternalLinks(True)
        self.barcode = QLabel()
        self.barcode.setFixedHeight(22)
        self.barcode.setScaledContents(True)  # the strip spans the pane
        self.barcode.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.files = _muted("")

        self.btn_page = QPushButton("Page")
        self.btn_disk = QPushButton("Disk")
        self.btn_folder = QPushButton("Folder")
        self.btn_page.setToolTip("Open the page")
        self.btn_disk.setToolTip("Open the disk")
        self.btn_folder.setToolTip("Show the disk (or page) in its folder")
        self.btn_page.clicked.connect(lambda: self._open("page_path"))
        self.btn_disk.clicked.connect(lambda: self._open("disk_path"))
        self.btn_folder.clicked.connect(self._show_in_folder)
        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        for b in (self.btn_page, self.btn_disk, self.btn_folder):
            b.setObjectName("small")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            buttons.addWidget(b)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)
        layout.addWidget(self.disk)
        layout.addWidget(self.title)
        layout.addWidget(self.meta)
        layout.addWidget(self.barcode)
        layout.addWidget(self.files)
        layout.addLayout(buttons)
        layout.addStretch(1)
        self.show_films([])

    def show_films(self, films: List[history.Film]) -> None:
        self._film = films[0] if len(films) == 1 else None
        film = self._film
        for w in (self.barcode, self.files, self.btn_page, self.btn_disk,
                  self.btn_folder):
            w.setVisible(film is not None)
        if film is None:
            self._show_summary(films)
            return

        self.title.setText(film.title or film.name.replace("_", " "))
        lines = []
        if film.original_title and film.original_title != film.title:
            lines.append(f"<i>{html.escape(film.original_title)}</i>")
        facts = [str(film.year) if film.year else "",
                 html.escape(film.director or ""),
                 f"{film.runtime} min" if film.runtime else ""]
        if any(facts):
            lines.append(" · ".join(f for f in facts if f))
        if film.tmdb_id:
            url = f"https://www.themoviedb.org/movie/{film.tmdb_id}"
            lines.append(f'<a style="color:{TEAL}" href="{url}">Open on TMDB ↗</a>')
        else:
            lines.append("Not matched on TMDB yet")
        self.meta.setText("<br>".join(lines))

        colors = history.mean_colors(film.name)
        if colors:
            self.barcode.setPixmap(_barcode_pixmap(colors, 480, 22))
            self.barcode.setToolTip(f"{len(colors)} frames, start → end")
        self.barcode.setVisible(bool(colors))

        parts, tips = [], []
        for label, path in (("Disk", film.disk_path), ("Page", film.page_path)):
            ok = self._exists(path)
            parts.append(f'<span style="color:{TEAL if ok else DIM}">'
                         f'{"✓" if ok else "✗"} {label}</span>')
            tips.append(f"{label}: {path}" + ("" if ok else "  (moved or deleted)")
                        if path else f"{label}: not rendered yet")
        if film.frames:
            parts.append(f"{film.frames} rings")
        self.files.setText(" · ".join(parts))
        self.files.setToolTip("\n".join(tips))
        self.btn_page.setEnabled(self._exists(film.page_path))
        self.btn_disk.setEnabled(self._exists(film.disk_path))
        self.btn_folder.setEnabled(self._exists(film.disk_path)
                                   or self._exists(film.page_path))
        self._show_thumb()

    def _show_summary(self, films: List[history.Film]) -> None:
        if not films:
            self.title.setText("")
            self.meta.setText("Select a film to see its disk — or several to "
                              "act on them together.")
            self.disk.show_disk(None, "no film\nselected")
            return
        self.title.setText(f"{len(films)} films")
        runtime = sum(f.runtime or 0 for f in films)
        facts = [f"{sum(1 for f in films if f.disk_at)} disks",
                 f"{sum(1 for f in films if f.page_at)} pages"]
        if runtime:
            facts.append(_human_duration(runtime * 60) + " of cinema")
        self.meta.setText(" · ".join(facts))
        self.disk.show_disk(None, f"{len(films)} films\nselected")

    @staticmethod
    def _exists(path: Optional[str]) -> bool:
        return bool(path) and Path(path).is_file()

    def _show_thumb(self) -> None:
        pix = self._thumbs.get(self._film, urgent=True)
        if pix is None:
            self.disk.show_disk(None, "loading…")
        else:
            self.disk.show_disk(pix, "no disk\nyet")

    def _thumb_ready(self, key: str) -> None:
        if self._film is not None and Thumbnails.key(self._film) == key:
            self._show_thumb()

    def _open(self, attr: str) -> None:
        if self._film is not None and self._exists(getattr(self._film, attr)):
            _open_file(Path(getattr(self._film, attr)))

    def _show_in_folder(self) -> None:
        film = self._film
        if film is None:
            return
        for path in (film.disk_path, film.page_path):
            if self._exists(path):
                _reveal(Path(path))
                return


def _placeholder_pixmap(size: int = Thumbnails.SIZE) -> QPixmap:
    """Dashed empty disk, shown while a thumbnail loads (or if there is none)."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(BORDER), 3, Qt.PenStyle.DashLine))
    p.setBrush(QColor(FIELD))
    p.drawEllipse(QRectF(8, 8, size - 16, size - 16))
    p.end()
    return pix


class LibraryPanel(QWidget):
    """The film database: filters over a sortable table or a gallery of disks,
    with the selected film's details alongside. Multi-select in both views."""

    _STATUSES = (("all", "Any state"), ("disk", "Disk rendered"),
                 ("page", "Page rendered"), ("no_page", "Disk without page"),
                 ("colors", "Has mean colors"), ("no_tmdb", "Missing TMDB info"))
    _COLUMNS = ("Film", "Year", "Director", "Runtime", "Disk", "Page", "Colors")

    selection_changed = pyqtSignal()
    film_activated = pyqtSignal(object)     # Film: double-clicked
    menu_requested = pyqtSignal(QPoint)     # global position of a right-click

    def __init__(self, thumbs: Thumbnails) -> None:
        super().__init__()
        self._films: dict = {}
        self._barcodes: dict = {}
        self._thumbs = thumbs
        self._grid_items: dict = {}         # thumbnail key -> gallery item
        self._placeholder = QIcon(_placeholder_pixmap())
        thumbs.ready.connect(self._thumb_ready)

        # -- filters ----------------------------------------------------------
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search title, file name, director…")
        self.search.setClearButtonEnabled(True)
        self.director = QComboBox()
        self.director.setMinimumWidth(160)
        self.status = QComboBox()
        for key, label in self._STATUSES:
            self.status.addItem(label, key)
        self.year_from = YearSpin(1879)
        self.year_to = YearSpin(2101)
        reset = QPushButton("Reset")
        reset.setObjectName("small")
        reset.setCursor(Qt.CursorShape.PointingHandCursor)
        reset.clicked.connect(self.reset_filters)

        filters = QHBoxLayout()
        filters.setSpacing(8)
        filters.addWidget(self.search, 3)
        filters.addWidget(self.director, 2)
        filters.addWidget(_muted("Years"))
        filters.addWidget(self.year_from)
        filters.addWidget(_muted("→"))
        filters.addWidget(self.year_to)
        filters.addWidget(self.status, 2)
        filters.addWidget(reset)

        self.btn_list = QPushButton("☰  List")
        self.btn_gallery = QPushButton("◉  Gallery")
        self.btn_list.setToolTip("Films as a sortable table")
        self.btn_gallery.setToolTip("Films as a wall of disks")
        views = QButtonGroup(self)
        for b in (self.btn_list, self.btn_gallery):
            b.setObjectName("toggle")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            views.addButton(b)
            filters.addWidget(b)
        self.btn_list.setChecked(True)
        self.btn_gallery.toggled.connect(self._switch_view)

        # -- table ------------------------------------------------------------
        t = self.table = QTableWidget(0, len(self._COLUMNS))
        t.setHorizontalHeaderLabels(self._COLUMNS)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setAlternatingRowColors(True)
        t.setShowGrid(False)
        t.setWordWrap(False)
        t.setIconSize(QSize(150, 16))
        t.verticalHeader().setVisible(False)
        t.verticalHeader().setDefaultSectionSize(28)
        t.setMinimumHeight(170)
        header = t.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setHighlightSections(False)
        t.setSortingEnabled(True)
        t.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        # The gallery follows the table's order (once the table has re-sorted).
        header.sortIndicatorChanged.connect(
            lambda *_: QTimer.singleShot(0, self._fill_grid))

        # -- gallery ----------------------------------------------------------
        g = self.grid = QListWidget()
        g.setObjectName("grid")
        g.setViewMode(QListView.ViewMode.IconMode)
        g.setIconSize(QSize(150, 150))
        g.setGridSize(QSize(178, 204))
        g.setResizeMode(QListView.ResizeMode.Adjust)
        g.setMovement(QListView.Movement.Static)
        g.setUniformItemSizes(True)
        g.setWordWrap(True)
        g.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        g.verticalScrollBar().setSingleStep(24)

        tip = ("Ctrl/Shift-click to pick several films (Ctrl+A: all shown) · "
               "double-click to open the page, or the disk · right-click for more")
        for view in (t, g):
            view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
            view.setToolTip(tip)
            view.itemSelectionChanged.connect(self._selection_changed)
            view.itemDoubleClicked.connect(self._activate)
            view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            view.customContextMenuRequested.connect(
                lambda pos, v=view: self._context_menu(v, pos))
        self.views = QStackedWidget()
        self.views.addWidget(t)
        self.views.addWidget(g)

        # -- details (its disk shrinks to fit a short window) -----------------
        self.details = FilmDetails(thumbs)
        self.details.setMinimumWidth(250)

        self.split = QSplitter(Qt.Orientation.Horizontal)
        self.split.addWidget(self.views)
        self.split.addWidget(self.details)
        self.split.setStretchFactor(0, 1)
        self.split.setCollapsible(0, False)
        self.split.setSizes([720, 270])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addLayout(filters)
        layout.addWidget(self.split, 1)

        self.search.textChanged.connect(self._apply_filters)
        for combo in (self.director, self.status):
            combo.currentIndexChanged.connect(self._apply_filters)
        for spin in (self.year_from, self.year_to):
            spin.valueChanged.connect(self._apply_filters)

    # -- data ----------------------------------------------------------------
    def reset_filters(self) -> None:
        widgets = (self.search, self.director, self.status, self.year_from, self.year_to)
        for w in widgets:
            w.blockSignals(True)
        self.search.clear()
        self.director.setCurrentIndex(0)
        self.status.setCurrentIndex(0)
        self.year_from.setValue(self.year_from.unbounded)
        self.year_to.setValue(self.year_to.unbounded)
        for w in widgets:
            w.blockSignals(False)
        self._apply_filters()

    def refresh(self) -> None:
        """Reload everything from the database (directors list included)."""
        current = self.director.currentData()
        self.director.blockSignals(True)
        self.director.clear()
        self.director.addItem("Any director", None)
        for name in history.directors():
            self.director.addItem(name, name)
        self.director.setCurrentIndex(max(self.director.findData(current), 0))
        self.director.blockSignals(False)
        self._apply_filters()

    def _apply_filters(self) -> None:
        films = history.search(
            self.search.text(), self.director.currentData(),
            self.year_from.bound(), self.year_to.bound(), self.status.currentData())
        keep = {f.id for f in self.selected()}
        self._films = {f.id: f for f in films}

        t = self.table
        t.blockSignals(True)
        t.setSortingEnabled(False)
        t.clearContents()
        t.setRowCount(len(films))
        for row, f in enumerate(films):
            title = f.title or f.name.replace("_", " ")
            cells = (
                _Cell(title, title.lower()),
                _Cell(str(f.year) if f.year else "–", f.year or 0),
                _Cell(f.director or "–", (f.director or "").lower()),
                _Cell(f"{f.runtime} min" if f.runtime else "–", f.runtime or 0),
                _Cell("✓" if f.disk_at else "", f.disk_at or 0),
                _Cell("✓" if f.page_at else "", f.page_at or 0),
                _Cell("", 0),
            )
            for col, cell in enumerate(cells):
                if col in (4, 5):
                    cell.setForeground(QColor(TEAL))
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                t.setItem(row, col, cell)
            cells[0].setData(Qt.ItemDataRole.UserRole, f.id)
            tip = f.name
            if f.original_title and f.original_title != f.title:
                tip += f"\n{f.original_title}"
            cells[0].setToolTip(tip)
            pix = self._barcode(f)
            if pix is not None:
                cells[6].setData(Qt.ItemDataRole.DecorationRole, pix)
                cells[6].setData(_SORT_KEY, 1)
        t.setSortingEnabled(True)
        t.blockSignals(False)

        self._fill_grid()
        # Filtering keeps whatever was selected and is still shown.
        self._select_ids(keep)
        self._selection_changed()

    def _fill_grid(self) -> None:
        """One disk per shown film, in the table's order."""
        g = self.grid
        g.blockSignals(True)
        g.clear()
        self._grid_items = {}
        load = self.is_gallery()
        for row in range(self.table.rowCount()):
            film = self._films[self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)]
            title = film.title or film.name.replace("_", " ")
            caption = f"{title} ({film.year})" if film.year else title
            if len(caption) > 44:  # two lines under the disk at most
                caption = caption[:42].rstrip() + "…"
            item = QListWidgetItem(caption)
            item.setData(Qt.ItemDataRole.UserRole, film.id)
            item.setToolTip(" · ".join(str(x) for x in (
                film.original_title or title, film.year, film.director) if x))
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter
                                  | Qt.AlignmentFlag.AlignTop)
            g.addItem(item)
            self._grid_items[Thumbnails.key(film)] = item
            self._set_icon(item, self._thumbs.get(film) if load else None)
        g.blockSignals(False)

    def _set_icon(self, item: QListWidgetItem, pix: Optional[QPixmap]) -> None:
        item.setIcon(QIcon(pix) if pix is not None and not pix.isNull()
                     else self._placeholder)

    def _thumb_ready(self, key: str) -> None:
        item = self._grid_items.get(key)
        if item is not None:
            film = self._films.get(item.data(Qt.ItemDataRole.UserRole))
            if film is not None:
                self._set_icon(item, self._thumbs.get(film))

    def _select_ids(self, ids) -> None:
        """Select the shown films whose id is in ``ids``, in both views."""
        t, g = self.table, self.grid
        for view in (t, g):
            view.blockSignals(True)
        model, selection = t.model(), t.selectionModel()
        selection.clearSelection()
        flags = (QItemSelectionModel.SelectionFlag.Select
                 | QItemSelectionModel.SelectionFlag.Rows)
        for row in range(t.rowCount()):
            if t.item(row, 0).data(Qt.ItemDataRole.UserRole) in ids:
                selection.select(model.index(row, 0), flags)
        for i in range(g.count()):
            g.item(i).setSelected(g.item(i).data(Qt.ItemDataRole.UserRole) in ids)
        for view in (t, g):
            view.blockSignals(False)

    # -- views ---------------------------------------------------------------
    def is_gallery(self) -> bool:
        return self.views.currentWidget() is self.grid

    def set_gallery(self, on: bool) -> None:
        (self.btn_gallery if on else self.btn_list).setChecked(True)

    def _switch_view(self) -> None:
        on = self.btn_gallery.isChecked()
        if on == self.is_gallery():
            return
        ids = {f.id for f in self.selected()}
        self.views.setCurrentWidget(self.grid if on else self.table)
        self._select_ids(ids)
        if on:
            for item in self._grid_items.values():
                film = self._films[item.data(Qt.ItemDataRole.UserRole)]
                self._set_icon(item, self._thumbs.get(film))
            selected = self.grid.selectedItems()
            if selected:
                self.grid.scrollToItem(selected[0])
        self._selection_changed()

    def _selection_changed(self) -> None:
        self.details.show_films(self.selected())
        self.selection_changed.emit()

    def _activate(self, item) -> None:
        if isinstance(item, QTableWidgetItem):
            item = self.table.item(item.row(), 0)  # the id lives in column 0
        film = self._films.get(item.data(Qt.ItemDataRole.UserRole))
        if film is not None:
            self.film_activated.emit(film)

    def _context_menu(self, view, pos: QPoint) -> None:
        """Right-click: act on the film under the cursor (and keep a
        multi-selection that includes it)."""
        if view is self.table:
            index = view.indexAt(pos)
            if index.isValid() and not view.selectionModel().isRowSelected(index.row()):
                view.selectRow(index.row())
        else:
            item = view.itemAt(pos)
            if item is not None and not item.isSelected():
                view.clearSelection()
                item.setSelected(True)
        if self.selected():
            self.menu_requested.emit(view.viewport().mapToGlobal(pos))

    def _barcode(self, film: history.Film) -> Optional[QPixmap]:
        key = (film.id, film.disk_at)
        if key not in self._barcodes:
            colors = history.mean_colors(film.name)
            self._barcodes[key] = _barcode_pixmap(colors) if colors else None
        return self._barcodes[key]

    def shown(self) -> int:
        return self.table.rowCount()

    def selected(self) -> List[history.Film]:
        if self.is_gallery():
            rows = sorted(self.grid.row(i) for i in self.grid.selectedItems())
            ids = [self.grid.item(r).data(Qt.ItemDataRole.UserRole) for r in rows]
        else:
            rows = sorted(i.row() for i in self.table.selectionModel().selectedRows())
            ids = [self.table.item(r, 0).data(Qt.ItemDataRole.UserRole) for r in rows]
        return [self._films[i] for i in ids if i in self._films]


class TmdbMatchDialog(QDialog):
    """Find a film on TMDB by hand: search, filter the hits, pick one.

    Opened when the automatic lookup found nothing (during a job) or from the
    Library. ``info`` holds the chosen film's metadata after ``accept()``;
    ``skip_all`` is set when the user asks not to be prompted again.
    """

    _LANGUAGES = (("en-US", "English titles"), ("fr-FR", "Titres français"),
                  ("de-DE", "Deutsche Titel"), ("es-ES", "Títulos en español"),
                  ("it-IT", "Titoli italiani"))
    _SORTS = (("relevance", "Relevance"), ("popularity", "Popularity"),
              ("votes", "Most votes"), ("rating", "Best rated"),
              ("newest", "Newest"), ("oldest", "Oldest"))
    _COLUMNS = ("Title", "Original title", "Year", "Lang", "Votes", "Rating")

    _sig_results = pyqtSignal(int, object, str)
    _sig_poster = pyqtSignal(str, bytes)

    def __init__(self, name: str, title: str = "", year: Optional[int] = None,
                 parent: Optional[QWidget] = None, in_job: bool = False) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Find on TMDB — {name}")
        self.resize(1040, 680)
        self.setMinimumHeight(560)
        self.info: Optional[history.MovieInfo] = None
        self.skip_all = False
        self._hits: List[tmdb.Candidate] = []
        self._shown: List[tmdb.Candidate] = []
        self._token = 0
        self._posters: dict = {}
        self._sig_results.connect(self._on_results)
        self._sig_poster.connect(self._on_poster)

        if not title:
            title, parsed = tmdb.parse_name(name)
            year = year or (int(parsed) if parsed else None)

        intro = _muted(f"No automatic TMDB match for “{name}”. Search by title, "
                       "or paste an IMDb id/link (tt0062622) or a TMDB link."
                       if in_job else f"Pick the TMDB film for “{name}”.")
        intro.setWordWrap(True)

        # -- query + filters --------------------------------------------------
        self.query = QLineEdit(title)
        self.query.setPlaceholderText("Title, IMDb id (tt…) or TMDB link")
        self.query.setClearButtonEnabled(True)
        self.query.returnPressed.connect(self.run_search)
        self.lang = QComboBox()
        for code, label in self._LANGUAGES:
            self.lang.addItem(label, code)
        self.lang.currentIndexChanged.connect(self.run_search)
        search_btn = QPushButton("⌕  Search")
        search_btn.setObjectName("small")
        search_btn.clicked.connect(self.run_search)
        top = QHBoxLayout()
        top.addWidget(self.query, 1)
        top.addWidget(self.lang)
        top.addWidget(search_btn)

        self.year_from = YearSpin(1879)
        self.year_to = YearSpin(2101)
        for spin in (self.year_from, self.year_to):
            spin.setMinimumWidth(92)
        if year:
            self.year_from.setValue(year - 1)
            self.year_to.setValue(year + 1)
        self.orig_lang = QComboBox()
        self.orig_lang.setMinimumWidth(130)
        self.min_votes = QSpinBox()
        self.min_votes.setRange(0, 100000)
        self.min_votes.setSingleStep(10)
        self.min_votes.setSpecialValueText("any")
        self.sort = QComboBox()
        for key, label in self._SORTS:
            self.sort.addItem(label, key)
        clear = QPushButton("Clear filters")
        clear.setObjectName("small")
        clear.clicked.connect(self.clear_filters)
        filters = QHBoxLayout()
        filters.setSpacing(8)
        filters.addWidget(_muted("Years"))
        filters.addWidget(self.year_from)
        filters.addWidget(_muted("→"))
        filters.addWidget(self.year_to)
        filters.addWidget(_muted("Language"))
        filters.addWidget(self.orig_lang)
        filters.addWidget(_muted("Min votes"))
        filters.addWidget(self.min_votes)
        filters.addWidget(_muted("Sort"))
        filters.addWidget(self.sort)
        filters.addStretch(1)
        filters.addWidget(clear)
        for spin in (self.year_from, self.year_to, self.min_votes):
            spin.valueChanged.connect(self._apply_filters)
        for combo in (self.orig_lang, self.sort):
            combo.currentIndexChanged.connect(self._apply_filters)

        # -- results + details ------------------------------------------------
        t = self.table = QTableWidget(0, len(self._COLUMNS))
        t.setHorizontalHeaderLabels(self._COLUMNS)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setAlternatingRowColors(True)
        t.setShowGrid(False)
        t.setWordWrap(False)
        t.verticalHeader().setVisible(False)
        t.verticalHeader().setDefaultSectionSize(28)
        header = t.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setHighlightSections(False)
        t.itemSelectionChanged.connect(self._show_details)
        t.itemDoubleClicked.connect(lambda _item: self._use())

        self.poster = QLabel("no poster")
        self.poster.setObjectName("poster")
        self.poster.setFixedSize(185, 278)
        self.poster.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_title = QLabel()
        self.detail_title.setObjectName("matchTitle")
        self.detail_title.setWordWrap(True)
        self.detail_meta = _muted("")
        self.detail_meta.setWordWrap(True)
        self.detail_meta.setOpenExternalLinks(True)
        self.overview = QLabel()
        self.overview.setWordWrap(True)
        self.overview.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.overview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        details = QVBoxLayout()
        details.setSpacing(6)
        details.addWidget(self.poster, 0, Qt.AlignmentFlag.AlignHCenter)
        details.addWidget(self.detail_title)
        details.addWidget(self.detail_meta)
        scroll = QScrollArea()
        scroll.setWidget(self.overview)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        details.addWidget(scroll, 1)
        details_box = QWidget()
        details_box.setFixedWidth(280)
        details_box.setLayout(details)
        middle = QHBoxLayout()
        middle.addWidget(t, 1)
        middle.addWidget(details_box)

        # -- buttons ----------------------------------------------------------
        self.status = _muted("")
        self.btn_use = QPushButton("✓  Use this film")
        self.btn_use.setObjectName("use")
        self.btn_use.setEnabled(False)
        self.btn_use.clicked.connect(self._use)
        skip = QPushButton("Skip")
        skip.clicked.connect(self.reject)
        buttons = QHBoxLayout()
        buttons.addWidget(self.status, 1)
        if in_job:
            skip_all = QPushButton("Skip all")
            skip_all.setToolTip("Don't ask again during this job.")
            skip_all.clicked.connect(self._skip_all)
            buttons.addWidget(skip_all)
        buttons.addWidget(skip)
        buttons.addWidget(self.btn_use)
        for b in self.findChildren(QPushButton):
            b.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.addWidget(intro)
        layout.addLayout(top)
        layout.addLayout(filters)
        layout.addLayout(middle, 1)
        layout.addLayout(buttons)

        self._fill_languages()
        if title:
            QTimer.singleShot(0, self.run_search)

    # -- search (network in a thread, results back through a signal) ---------
    def run_search(self) -> None:
        query = self.query.text().strip()
        if not query:
            return
        self._token += 1
        token, language = self._token, self.lang.currentData()
        self.status.setText("Searching TMDB …")

        def work() -> None:
            try:
                hits, error = tmdb.search(query, language=language), ""
            except Exception as exc:  # noqa: BLE001 - shown in the window
                hits, error = [], str(exc) or exc.__class__.__name__
            self._sig_results.emit(token, hits, error)

        threading.Thread(target=work, daemon=True).start()

    def _on_results(self, token: int, hits, error: str) -> None:
        if token != self._token:
            return  # a newer search is on its way
        self._hits = list(hits)
        self._fill_languages()
        self._apply_filters()
        if error:
            self.status.setText(f"TMDB search failed: {error}")

    def _fill_languages(self) -> None:
        current = self.orig_lang.currentData()
        self.orig_lang.blockSignals(True)
        self.orig_lang.clear()
        self.orig_lang.addItem("Any", None)
        for code in sorted({h.language for h in self._hits if h.language}):
            self.orig_lang.addItem(code, code)
        self.orig_lang.setCurrentIndex(max(self.orig_lang.findData(current), 0))
        self.orig_lang.blockSignals(False)

    def clear_filters(self) -> None:
        for w in (self.year_from, self.year_to, self.min_votes,
                  self.orig_lang, self.sort):
            w.blockSignals(True)
        self.year_from.setValue(self.year_from.unbounded)
        self.year_to.setValue(self.year_to.unbounded)
        self.min_votes.setValue(0)
        self.orig_lang.setCurrentIndex(0)
        self.sort.setCurrentIndex(0)
        for w in (self.year_from, self.year_to, self.min_votes,
                  self.orig_lang, self.sort):
            w.blockSignals(False)
        self._apply_filters()

    def _apply_filters(self) -> None:
        lo, hi = self.year_from.bound(), self.year_to.bound()
        lang, votes = self.orig_lang.currentData(), self.min_votes.value()

        def keep(h: tmdb.Candidate) -> bool:
            if (lo or hi) and h.year is None:
                return False
            if lo and h.year < lo or hi and h.year > hi:
                return False
            return (not lang or h.language == lang) and h.votes >= votes

        shown = [h for h in self._hits if keep(h)]
        order = {
            "popularity": lambda h: -h.popularity,
            "votes": lambda h: -h.votes,
            "rating": lambda h: -h.rating,
            "newest": lambda h: -(h.year or 0),
            "oldest": lambda h: h.year or 9999,
        }.get(self.sort.currentData())
        if order is not None:
            shown.sort(key=order)
        self._shown = shown

        t = self.table
        t.blockSignals(True)
        t.clearContents()
        t.setRowCount(len(shown))
        for row, h in enumerate(shown):
            cells = (h.title,
                     h.original_title if h.original_title != h.title else "",
                     str(h.year or "–"), h.language, str(h.votes),
                     f"{h.rating:.1f}" if h.votes else "–")
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if col >= 2:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                t.setItem(row, col, item)
        t.blockSignals(False)
        hidden = len(self._hits) - len(shown)
        self.status.setText(
            f"{len(shown)} result(s)" + (f" · {hidden} hidden by filters" if hidden else "")
            if self._hits else "No result — try another title, or clear the filters.")
        if shown:
            t.selectRow(0)
        else:
            self._show_details()

    # -- details pane ----------------------------------------------------------
    def _current(self) -> Optional[tmdb.Candidate]:
        rows = self.table.selectionModel().selectedRows()
        return self._shown[rows[0].row()] if rows else None

    def _show_details(self) -> None:
        h = self._current()
        self.btn_use.setEnabled(h is not None)
        if h is None:
            self.detail_title.setText("")
            self.detail_meta.setText("")
            self.overview.setText("")
            self.poster.setPixmap(QPixmap())
            self.poster.setText("no poster")
            return
        self.detail_title.setText(f"{h.title} ({h.year})" if h.year else h.title)
        meta = []
        if h.original_title and h.original_title != h.title:
            meta.append(html.escape(h.original_title))
        if h.votes:
            meta.append(f"★ {h.rating:.1f} · {h.votes} votes")
        url = f"https://www.themoviedb.org/movie/{h.tmdb_id}"
        meta.append(f'<a style="color:{TEAL}" href="{url}">Open on TMDB</a>')
        self.detail_meta.setText("<br>".join(meta))
        self.overview.setText(h.overview or "No overview.")
        self._load_poster(h.poster_path)

    def _load_poster(self, path: Optional[str]) -> None:
        self.poster.setPixmap(QPixmap())
        self.poster.setText("no poster" if not path else "…")
        self._poster_wanted = path
        if not path:
            return
        if path in self._posters:
            self._on_poster(path, self._posters[path])
            return

        def work() -> None:
            import urllib.request
            try:
                with urllib.request.urlopen(tmdb.poster_url(path), timeout=8) as r:
                    data = r.read()
            except Exception:  # noqa: BLE001 - a missing poster is fine
                data = b""
            self._sig_poster.emit(path, data)

        threading.Thread(target=work, daemon=True).start()

    def _on_poster(self, path: str, data: bytes) -> None:
        self._posters[path] = data
        if path != getattr(self, "_poster_wanted", None):
            return
        pix = QPixmap()
        if data and pix.loadFromData(data):
            self.poster.setPixmap(pix.scaled(
                self.poster.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        else:
            self.poster.setText("no poster")

    # -- answer ----------------------------------------------------------------
    def _use(self) -> None:
        h = self._current()
        if h is None:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.info = tmdb.details(h.tmdb_id, self.lang.currentData())
        except Exception as exc:  # noqa: BLE001
            self.status.setText(f"Could not fetch the film's details: {exc}")
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.accept()

    def _skip_all(self) -> None:
        self.skip_all = True
        self.reject()


def _popup_menu(parent: QWidget) -> QMenu:
    menu = QMenu(parent)
    # The QSS rounded corners need a see-through window behind them.
    menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint
                        | Qt.WindowType.NoDropShadowWindowHint)
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    return menu


def _add(menu: QMenu, text: str, slot: Callable[[], None],
         enabled: bool = True) -> QAction:
    action = menu.addAction(text)
    action.triggered.connect(lambda _checked=False: slot())
    action.setEnabled(enabled)
    return action


def _existing(path: Optional[str]) -> Optional[Path]:
    return Path(path) if path and Path(path).is_file() else None


class MainWindow(QMainWindow):
    sig_done = pyqtSignal(str)

    _BAR_FORMAT = "%v / %m  (%p%)"

    def __init__(self, title_family: str = "") -> None:
        super().__init__()
        self.setWindowTitle("Movinyl")
        screen = QApplication.primaryScreen()
        room = screen.availableGeometry() if screen is not None else None
        self.resize(min(1120, room.width() - 40) if room else 1120,
                    min(960, room.height() - 40) if room else 960)
        icon = pf.RESOURCE_ROOT / "logos" / "movinyl_logo_square_bold.png"
        if icon.is_file():
            self.setWindowIcon(QIcon(str(icon)))

        self.reporter = QtReporter()
        self.reporter.sig_task.connect(self._bar_task)
        self.reporter.sig_advance.connect(self._bar_advance)
        self.reporter.sig_update.connect(self._bar_update)
        self.reporter.sig_remove.connect(self._bar_remove)
        self.reporter.sig_log.connect(self.write_log)
        self.reporter.sig_resolve.connect(self._resolve_film)
        self.sig_done.connect(self._finish)

        self._cancel = threading.Event()
        self._busy = False
        self._job_started = 0.0
        self._bar_started: dict = {}     # bar -> start time of its current task
        self._settings = _settings()
        self.thumbs = Thumbnails()

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 14, 16, 10)
        root.setSpacing(10)

        self.banner = VinylBanner(title_family)
        root.addWidget(self.banner)

        # -- folders + options ------------------------------------------------
        top = QHBoxLayout()
        top.setSpacing(10)
        folders = QGroupBox("Folders")
        folders.setObjectName("folders")
        form = QFormLayout(folders)
        form.setVerticalSpacing(8)
        self.video_dir = FolderPicker(DEFAULT_INPUT, "Choose the video folder")
        self.disk_dir = FolderPicker(DEFAULT_PAGE, "Choose the disk folder")
        self.video_dir.changed.connect(self.refresh_lists)
        self.disk_dir.changed.connect(self.refresh_lists)
        form.addRow(_muted("Videos  →  disks"), self.video_dir)
        form.addRow(_muted("Disks  →  pages"), self.disk_dir)
        drop_tip = QLabel("Tip: drop a folder on a path, or on its list below.")
        drop_tip.setObjectName("hint")
        form.addRow(drop_tip)
        top.addWidget(folders, 5)

        opts = QGroupBox("Options")
        opts.setObjectName("options")
        grid = QGridLayout(opts)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)
        self.frames = QSpinBox()
        self.frames.setRange(10, 20000)
        self.frames.setMinimumWidth(110)
        self.frames.setToolTip("Frames sampled per film: each one becomes a ring "
                               "of the disk, so the disk is 2 × frames pixels wide.")
        self.frames_hint = QLabel()
        self.frames_hint.setObjectName("hint")
        self.frames.valueChanged.connect(self._frames_changed)
        self.frames.setValue(engine.DEFAULT_FRAME_COUNT)
        frames_row = QHBoxLayout()
        frames_row.addWidget(_muted("Frames"))
        frames_row.addWidget(self.frames)
        frames_row.addWidget(self.frames_hint)
        frames_row.addStretch(1)
        grid.addLayout(frames_row, 0, 0, 1, 2)
        self.mean_colors = QCheckBox("Mean-color rings")
        self.mean_colors.setToolTip(
            "Paint each ring with its frame's average color instead of the "
            "frame itself, for a smoother disk.")
        self.overwrite = QCheckBox("Re-process done films")
        self.overwrite.setToolTip(
            "Re-render disks and pages even if they exist or are recorded "
            "in the history (✓ in the lists).")
        self.then_pages = QCheckBox("Pages right after disks")
        self.then_pages.setToolTip(
            "When a Disks job ends, compose the page of each new disk straight "
            "away, into the disk folder (no need to move the disks first).")
        self.ask_tmdb = QCheckBox("Ask when TMDB is unsure")
        self.ask_tmdb.setChecked(True)
        self.ask_tmdb.setToolTip(
            "Open a search window when the automatic TMDB lookup finds nothing, "
            "so you can pick the right film (otherwise it is left without info).")
        for i, box in enumerate((self.mean_colors, self.overwrite,
                                 self.then_pages, self.ask_tmdb)):
            grid.addWidget(box, 1 + i // 2, i % 2)
        top.addWidget(opts, 4)
        root.addLayout(top)

        # -- file lists -------------------------------------------------------
        lists = QHBoxLayout()
        lists.setSpacing(10)
        self.videos_box = QGroupBox()
        self.videos_box.setObjectName("videos")
        self.videos_list = self._file_list(self._video_menu)
        QVBoxLayout(self.videos_box).addWidget(self.videos_list)
        self.disks_box = QGroupBox()
        self.disks_box.setObjectName("disks")
        self.disks_list = self._file_list(self._disk_menu)
        QVBoxLayout(self.disks_box).addWidget(self.disks_list)
        lists.addWidget(self.videos_box)
        lists.addWidget(self.disks_box)
        files_tab = QWidget()
        files_tab.setLayout(lists)
        lists.setContentsMargins(0, 0, 0, 0)
        _FolderDrop(lambda p: self._use_folder(self.video_dir, p),
                    self.video_dir.edit, self.videos_list.viewport())
        _FolderDrop(lambda p: self._use_folder(self.disk_dir, p),
                    self.disk_dir.edit, self.disks_list.viewport())

        # -- library (film database) -----------------------------------------
        self.library = LibraryPanel(self.thumbs)
        self.library.selection_changed.connect(self._library_selection)
        self.library.film_activated.connect(self.open_film)
        self.library.menu_requested.connect(self._library_menu)
        self.lib_count = _muted("")
        self.btn_lib_pages = QPushButton("▤  Pages")
        self.btn_lib_planche = QPushButton("▦  Planche")
        self.btn_lib_barcodes = QPushButton("▮  Barcodes")
        self.btn_lib_match = QPushButton("⌕  TMDB match")
        self.btn_lib_forget = QPushButton("✕  Forget")
        self.btn_lib_pages.setToolTip(
            "Compose the page of each selected film from its disk "
            "(re-rendered even if already done), into the disk folder.")
        self.btn_lib_planche.setToolTip(
            "Contact sheet(s) of the selected films' disks, into the disk folder.")
        self.btn_lib_barcodes.setToolTip(
            "Redraw each selected film as a movie barcode from its stored mean "
            "colors, into <disk folder>/barcodes.")
        self.btn_lib_match.setToolTip(
            "Search TMDB by hand for the selected film(s) and store the chosen "
            "match (re-render the page afterwards to update it).")
        self.btn_lib_forget.setToolTip(
            "Remove the selected films from the database; their files are "
            "kept (Del).")
        self.btn_lib_pages.clicked.connect(self.action_lib_pages)
        self.btn_lib_planche.clicked.connect(self.action_lib_planche)
        self.btn_lib_barcodes.clicked.connect(self.action_lib_barcodes)
        self.btn_lib_match.clicked.connect(self.action_lib_match)
        self.btn_lib_forget.clicked.connect(self.action_lib_forget)
        lib_actions = QHBoxLayout()
        lib_actions.setSpacing(8)
        lib_actions.addWidget(self.lib_count, 1)
        for b, name in ((self.btn_lib_pages, "pages"),
                        (self.btn_lib_planche, "planche"),
                        (self.btn_lib_barcodes, "small"),
                        (self.btn_lib_match, "small"),
                        (self.btn_lib_forget, "danger")):
            b.setObjectName(name)
            b.setMinimumHeight(34)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            lib_actions.addWidget(b)
        library_tab = QWidget()
        lib_layout = QVBoxLayout(library_tab)
        lib_layout.setContentsMargins(0, 0, 0, 0)
        lib_layout.setSpacing(8)
        lib_layout.addWidget(self.library, 1)
        lib_layout.addLayout(lib_actions)

        self.tabs = QTabWidget()
        self.tabs.addTab(files_tab, "Files")
        self.tabs.addTab(library_tab, "Library")

        # -- actions ----------------------------------------------------------
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
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
        for b, name, stretch in ((self.btn_disks, "disks", 2),
                                 (self.btn_pages, "pages", 2),
                                 (self.btn_planche, "planche", 2),
                                 (self.btn_setup, "setup", 1),
                                 (self.btn_refresh, "refresh", 1),
                                 (self.btn_cancel, "cancel", 1)):
            b.setObjectName(name)
            b.setMinimumHeight(42)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            buttons.addWidget(b, stretch)
        for b, keys, tip in (
                (self.btn_disks, "Ctrl+D", "Render a disk for every video of the video folder"),
                (self.btn_pages, "Ctrl+P", "Compose a page for every disk of the disk folder"),
                (self.btn_planche, "Ctrl+L", "Contact sheets of every disk of the disk folder"),
                (self.btn_refresh, "F5", "Re-read the folders and the film database")):
            b.setShortcut(QKeySequence(keys))
            b.setToolTip(f"{tip}  ({keys})")
        self.btn_setup.setToolTip("Build the C++ disk and page renderers")
        self.btn_cancel.setToolTip("Stop the running job (the film in progress is dropped)")

        # -- progress + log, side by side ------------------------------------
        progress = QGroupBox("Progress")
        progress.setObjectName("progress")
        pform = QFormLayout(progress)
        pform.setVerticalSpacing(8)
        self._bars = {}
        self._labels = {}
        self._bar_names = {"overall": "Overall", "extract": "Extract",
                           "render": "Render"}
        for key, label in self._bar_names.items():
            bar = QProgressBar()
            bar.setObjectName(key)
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setFormat("")  # idle
            lab = _muted(label)
            lab.setMinimumWidth(170)
            self._bars[key] = bar
            self._labels[key] = lab
            pform.addRow(lab, bar)

        log_box = QGroupBox("Log")
        log_box.setObjectName("log")
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        mono = QFont("Consolas" if sys.platform.startswith("win") else "Monospace")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.log.setFont(mono)
        QVBoxLayout(log_box).addWidget(self.log)

        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        bottom.addWidget(progress, 1)
        bottom.addWidget(log_box, 1)
        lower = QWidget()
        lower_layout = QVBoxLayout(lower)
        lower_layout.setContentsMargins(0, 0, 0, 0)
        lower_layout.setSpacing(10)
        lower_layout.addLayout(buttons)
        lower_layout.addLayout(bottom, 1)

        # Drag the gap between the tabs and the buttons to share the height.
        self.split = QSplitter(Qt.Orientation.Vertical)
        self.split.setChildrenCollapsible(False)
        self.split.setHandleWidth(10)
        self.split.addWidget(self.tabs)
        self.split.addWidget(lower)
        self.split.setStretchFactor(0, 1)
        self.split.setSizes([700, 180])
        root.addWidget(self.split, 1)

        self.statusBar().showMessage(
            f"{pf.system()} · {pf.cpu_count()} cores")

        # -- shortcuts --------------------------------------------------------
        def shortcut(keys, slot, parent=None, context=Qt.ShortcutContext.WindowShortcut):
            sc = QShortcut(QKeySequence(keys), parent or self)
            sc.setContext(context)
            sc.activated.connect(slot)

        shortcut(QKeySequence.StandardKey.Find, self._focus_search)
        for i in range(self.tabs.count()):
            shortcut(f"Ctrl+{i + 1}", lambda i=i: self.tabs.setCurrentIndex(i))
        for view in (self.library.table, self.library.grid):
            for keys in ("Return", "Enter"):
                shortcut(keys, self._open_selected, view, Qt.ShortcutContext.WidgetShortcut)
            shortcut(QKeySequence.StandardKey.Delete, self.action_lib_forget, view,
                     Qt.ShortcutContext.WidgetShortcut)

        # -- notifications + folder watching ---------------------------------
        self.tray = None
        if QSystemTrayIcon.isSystemTrayAvailable() and not self.windowIcon().isNull():
            self.tray = QSystemTrayIcon(self.windowIcon(), self)
            self.tray.setToolTip("Movinyl")
            self.tray.messageClicked.connect(self._bring_to_front)
            self.tray.activated.connect(lambda _reason: self._bring_to_front())
        self._tray_timer = QTimer(self)
        self._tray_timer.setSingleShot(True)
        self._tray_timer.timeout.connect(self._hide_tray)

        self._watched: List[str] = []
        self._watcher = QFileSystemWatcher(self)
        self._watch_timer = QTimer(self)
        self._watch_timer.setSingleShot(True)
        self._watch_timer.setInterval(800)  # one refresh per burst of changes
        self._watch_timer.timeout.connect(self.refresh_files)
        self._watcher.directoryChanged.connect(lambda _path: self._watch_timer.start())

        self._restore_settings()
        self.refresh_lists()
        self.write_log("Welcome. Pick a video folder, then click Disks.")
        self.write_log("✓ = already processed (skipped unless “Re-process” is checked).")
        if pf.disk_binary() is None:
            self.write_log("disk/page renderers not built yet — click Setup first.")

    # -- settings ------------------------------------------------------------
    def _option_boxes(self):
        return (("options/mean_colors", self.mean_colors),
                ("options/overwrite", self.overwrite),
                ("options/then_pages", self.then_pages),
                ("options/ask_tmdb", self.ask_tmdb))

    def _restore_settings(self) -> None:
        s = self._settings
        geometry = s.value("window/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        for splitter, key in ((self.split, "window/split"),
                              (self.library.split, "library/split")):
            state = s.value(key)
            if state is not None:
                splitter.restoreState(state)
        self.video_dir.edit.setText(s.value("folders/videos", str(DEFAULT_INPUT)))
        self.disk_dir.edit.setText(s.value("folders/disks", str(DEFAULT_PAGE)))
        self.frames.setValue(s.value("options/frames", engine.DEFAULT_FRAME_COUNT, type=int))
        for key, box in self._option_boxes():
            box.setChecked(s.value(key, box.isChecked(), type=bool))
        self.library.set_gallery(s.value("library/gallery", False, type=bool))
        self.tabs.setCurrentIndex(s.value("window/tab", 0, type=int))

    def save_settings(self) -> None:
        s = self._settings
        s.setValue("window/geometry", self.saveGeometry())
        s.setValue("window/split", self.split.saveState())
        s.setValue("library/split", self.library.split.saveState())
        s.setValue("window/tab", self.tabs.currentIndex())
        s.setValue("library/gallery", self.library.is_gallery())
        # Default folders are not pinned, so a moved install keeps working.
        for key, picker, default in (("folders/videos", self.video_dir, DEFAULT_INPUT),
                                     ("folders/disks", self.disk_dir, DEFAULT_PAGE)):
            if picker.path() == default:
                s.remove(key)
            else:
                s.setValue(key, str(picker.path()))
        s.setValue("options/frames", self.frames.value())
        for key, box in self._option_boxes():
            s.setValue(key, box.isChecked())
        s.sync()

    def _frames_changed(self, n: int) -> None:
        self.frames_hint.setText(f"→ {2 * n} px disk")

    # -- progress bars (UI thread) ------------------------------------------
    def _bar(self, key: str):
        k = _BAR_FOR.get(key, "extract")
        return k, self._bars[k], self._labels[k]

    def _bar_task(self, key, description, total) -> None:
        k, bar, label = self._bar(key)
        label.setText(str(description)[:28])
        if total:
            bar.setRange(0, int(total))
        else:
            bar.setRange(0, 0)  # unknown total -> busy indicator
        bar.setValue(0)
        self._bar_started[k] = time.monotonic()
        self._show_progress(k)

    def _bar_advance(self, key, amount) -> None:
        k, bar, _ = self._bar(key)
        bar.setValue(bar.value() + int(amount))
        self._show_progress(k)

    def _bar_update(self, key, description, total, completed) -> None:
        k, bar, label = self._bar(key)
        if description is not None:
            label.setText(str(description)[:28])
        if total is not None:
            bar.setRange(0, int(total))
        if completed is not None:
            bar.setValue(int(completed))
        self._show_progress(k)

    def _bar_remove(self, key) -> None:
        k, bar, label = self._bar(key)
        bar.setRange(0, 100)
        bar.setValue(0)
        label.setText(self._bar_names[k])
        self._bar_started.pop(k, None)
        self._show_progress(k)

    def _show_progress(self, k: str) -> None:
        """Bar text with the time left once it can be estimated, and the job's
        percentage in the window title (so in the taskbar too)."""
        bar = self._bars[k]
        started, done, total = self._bar_started.get(k), bar.value(), bar.maximum()
        text = self._BAR_FORMAT if started is not None else ""
        if started is not None and 0 < done < total:
            elapsed = time.monotonic() - started
            if elapsed >= 5:
                text += f"  ·  {_eta_text(elapsed * (total - done) / done)} left"
        if bar.format() != text:
            bar.setFormat(text)
        self._update_title()

    def job_percent(self) -> Optional[int]:
        """Progress of the running job: the finished items of the overall bar
        plus the current item's share (half extraction, half rendering)."""
        overall = self._bars["overall"]
        if not self._busy or "overall" not in self._bar_started or overall.maximum() <= 0:
            return None
        part = 0.0
        for k in ("extract", "render"):
            bar = self._bars[k]
            if k in self._bar_started and bar.maximum() > 0:
                part += bar.value() / bar.maximum() / 2
        return int(100 * min(1.0, (overall.value() + part) / overall.maximum()))

    def _update_title(self) -> None:
        pct = self.job_percent()
        title = f"{pct}% · Movinyl" if pct is not None else "Movinyl"
        if self.windowTitle() != title:
            self.setWindowTitle(title)
            if self.tray is not None:
                self.tray.setToolTip(title)

    def write_log(self, message: str) -> None:
        text = html.escape(message).replace("  ", "&nbsp; ")
        self.log.appendHtml(
            f'<span style="color:{DIM}">{time.strftime("%H:%M:%S")}</span> '
            f'<span style="color:{_log_color(message)}">{text}</span>')

    # -- notifications -------------------------------------------------------
    def _notify(self, message: str) -> None:
        """Flash the taskbar entry and pop a desktop notification, unless the
        window is already in front of the user."""
        if self.isActiveWindow():
            return
        QApplication.alert(self)
        if self.tray is not None:
            self.tray.show()
            self.tray.showMessage("Movinyl", message, self.windowIcon(), 10000)
            self._tray_timer.start(20000)

    def _hide_tray(self) -> None:
        if self.tray is not None:
            self.tray.hide()

    def _bring_to_front(self) -> None:
        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()

    # -- lists ---------------------------------------------------------------
    def refresh_lists(self) -> None:
        """Re-read both folders and the film database."""
        self.refresh_files()
        self.library.refresh()

    def refresh_files(self) -> None:
        vdir, ddir = self.video_dir.path(), self.disk_dir.path()
        videos = self._listing(engine.discover_videos, vdir)
        disks = self._listing(engine.discover_disks, ddir)
        self.videos_box.setTitle(f"Videos ({len(videos)})")
        self.disks_box.setTitle(f"Disks ({len(disks)})")
        films = {f.name: f for f in history.all_films()}
        self._fill_list(self.videos_list, [
            (p, getattr(films.get(engine.sanitize_name(p.stem)), "disk_at", None))
            for p in videos])
        self._fill_list(self.disks_list, [
            (p, getattr(films.get(p.stem), "page_at", None)) for p in disks])
        self._watch_folders((vdir, ddir))

    @staticmethod
    def _listing(discover, folder: Path) -> List[Path]:
        try:
            return discover(folder) if folder.is_dir() else []
        except OSError:
            return []

    @staticmethod
    def _fill_list(widget: QListWidget, rows) -> None:
        """Refill a file list, keeping its selection and scroll position."""
        keep = {i.data(Qt.ItemDataRole.UserRole) for i in widget.selectedItems()}
        scroll = widget.verticalScrollBar().value()
        widget.blockSignals(True)
        widget.clear()
        for path, done_at in rows:
            item = QListWidgetItem(f"✓  {path.name}" if done_at else f"●  {path.name}")
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setForeground(QColor(TEAL if done_at else TEXT))
            if done_at:
                item.setToolTip("Already processed")
            widget.addItem(item)
            item.setSelected(path in keep)
        widget.blockSignals(False)
        widget.verticalScrollBar().setValue(scroll)

    def _file_list(self, on_menu: Callable[[QListWidget, QPoint], None]) -> QListWidget:
        lst = QListWidget()
        lst.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        lst.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        lst.customContextMenuRequested.connect(lambda pos: on_menu(lst, pos))
        lst.itemDoubleClicked.connect(
            lambda item: _open_file(item.data(Qt.ItemDataRole.UserRole)))
        return lst

    @staticmethod
    def _picked(lst: QListWidget, pos: QPoint) -> List[Path]:
        """The files a right-click acts on: the selection, or the file under
        the cursor if it is not part of it."""
        item = lst.itemAt(pos)
        if item is not None and not item.isSelected():
            lst.clearSelection()
            item.setSelected(True)
        rows = sorted(lst.row(i) for i in lst.selectedItems())
        return [lst.item(r).data(Qt.ItemDataRole.UserRole) for r in rows]

    def _video_menu(self, lst: QListWidget, pos: QPoint) -> None:
        videos = self._picked(lst, pos)
        if not videos:
            return
        menu = _popup_menu(self)
        n = len(videos)
        _add(menu, "▶  Render disk" if n == 1 else f"▶  Render {n} disks",
             lambda: self.action_selected_disks(videos), not self._busy)
        if n == 1:
            menu.addSeparator()
            _add(menu, "Open video", lambda: _open_file(videos[0]))
            _add(menu, "Show in folder", lambda: _reveal(videos[0]))
        menu.exec(lst.viewport().mapToGlobal(pos))

    def _disk_menu(self, lst: QListWidget, pos: QPoint) -> None:
        disks = self._picked(lst, pos)
        if not disks:
            return
        menu = _popup_menu(self)
        n = len(disks)
        _add(menu, "▤  Compose page" if n == 1 else f"▤  Compose {n} pages",
             lambda: self.action_selected_pages(disks), not self._busy)
        if n == 1:
            film = history.get(disks[0].stem)
            page = _existing(film.page_path if film else None)
            menu.addSeparator()
            _add(menu, "Open disk", lambda: _open_file(disks[0]))
            _add(menu, "Open page", lambda: _open_file(page), page is not None)
            _add(menu, "Show in folder", lambda: _reveal(disks[0]))
        menu.exec(lst.viewport().mapToGlobal(pos))

    def _use_folder(self, picker: FolderPicker, folder: Path) -> None:
        """A folder was dropped onto ``picker`` or its list."""
        picker.edit.setText(str(folder))
        picker.changed.emit()

    def _watch_folders(self, folders) -> None:
        """Refresh the lists by themselves when files come and go."""
        wanted = sorted({str(p) for p in folders if p.is_dir()})
        if wanted == self._watched and len(self._watcher.directories()) == len(wanted):
            return
        if self._watcher.directories():
            self._watcher.removePaths(self._watcher.directories())
        if wanted:
            self._watcher.addPaths(wanted)
        self._watched = wanted

    def _focus_search(self) -> None:
        self.tabs.setCurrentIndex(1)
        self.library.search.setFocus()
        self.library.search.selectAll()

    # -- library -------------------------------------------------------------
    def _library_selection(self) -> None:
        n = len(self.library.selected())
        self.lib_count.setText(f"{n} selected · {self.library.shown()} shown")
        for b in (self.btn_lib_pages, self.btn_lib_planche,
                  self.btn_lib_barcodes, self.btn_lib_match,
                  self.btn_lib_forget):
            b.setEnabled(bool(n) and not self._busy)

    def open_film(self, film: history.Film) -> None:
        """Open the film's page, or its disk when it has no page."""
        path = _existing(film.page_path) or _existing(film.disk_path)
        if path is not None:
            _open_file(path)
        else:
            self.write_log(f"[warn] {film.name}: no disk or page file to open")

    def _open_selected(self) -> None:
        films = self.library.selected()
        if len(films) == 1:
            self.open_film(films[0])

    def _library_menu(self, pos: QPoint) -> None:
        films = self.library.selected()
        if not films:
            return
        menu = _popup_menu(self)
        if len(films) == 1:
            film = films[0]
            page, disk = _existing(film.page_path), _existing(film.disk_path)
            _add(menu, "Open page", lambda: _open_file(page), page is not None)
            _add(menu, "Open disk", lambda: _open_file(disk), disk is not None)
            _add(menu, "Show in folder", lambda: _reveal(disk or page),
                 bool(disk or page))
            if film.tmdb_id:
                url = f"https://www.themoviedb.org/movie/{film.tmdb_id}"
                _add(menu, "Open on TMDB ↗", lambda: QDesktopServices.openUrl(QUrl(url)))
            menu.addSeparator()
        n, free = len(films), not self._busy
        _add(menu, "▤  Compose page" if n == 1 else f"▤  Compose {n} pages",
             self.action_lib_pages, free)
        _add(menu, "▦  Contact sheet", self.action_lib_planche, free)
        _add(menu, "▮  Barcode" if n == 1 else f"▮  {n} barcodes",
             self.action_lib_barcodes, free)
        _add(menu, "⌕  Find on TMDB…", self.action_lib_match, free)
        menu.addSeparator()
        _add(menu, "✕  Forget…", self.action_lib_forget, free)
        menu.exec(pos)

    # -- job plumbing --------------------------------------------------------
    def _start(self, label: str, fn: Callable[[], str]) -> None:
        if self._busy:
            return
        self._busy = True
        self._cancel = threading.Event()
        self._job_started = time.monotonic()
        self.reporter.ask_tmdb = self.ask_tmdb.isChecked()
        for b in self._job_buttons:
            b.setEnabled(False)
        self._library_selection()
        self.btn_cancel.setEnabled(True)
        self.banner.set_spinning(True)
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
        self.banner.set_spinning(False)
        elapsed = time.monotonic() - self._job_started
        if elapsed >= 1:
            summary += f"  ({_human_duration(elapsed)})"
        self.write_log(summary)
        self._update_title()
        self.refresh_lists()
        if elapsed >= 20:  # long enough for the user to have looked away
            self._notify(summary)

    # -- actions -------------------------------------------------------------
    def action_disks(self) -> None:
        self._run_disks(None)

    def action_selected_disks(self, videos: List[Path]) -> None:
        self._run_disks(videos)

    def _run_disks(self, videos: Optional[List[Path]]) -> None:
        """Disks of ``videos`` (every video of the folder when None), then
        their pages when "Compose pages right after" is on. A hand-picked
        selection is rendered even if it was done before."""
        vdir, ddir = self.video_dir.path(), self.disk_dir.path()
        n, mean = self.frames.value(), self.mean_colors.isChecked()
        overwrite = self.overwrite.isChecked() or videos is not None
        then_pages = self.then_pages.isChecked()

        def job() -> str:
            if videos is None:
                outs = engine.run_disk_batch(
                    vdir, n=n, reporter=self.reporter, cancel=self._cancel,
                    overwrite=overwrite, mean_colors=mean)
            else:
                outs = engine.run_disks(
                    videos, vdir, n=n, reporter=self.reporter, cancel=self._cancel,
                    overwrite=overwrite, mean_colors=mean)
            msg = f"Done: {len(outs)} disk(s) in {vdir}"
            todo = [d for d in outs if overwrite or not history.page_done(d.stem)]
            if then_pages and todo and not self._cancel.is_set():
                pages = engine.run_pages(todo, ddir, reporter=self.reporter,
                                         cancel=self._cancel)
                msg += f", {len(pages)} page(s) in {ddir}"
            return msg

        what = f"{len(videos)} video(s)" if videos is not None else str(vdir)
        self._start(f"Generating disks from {what} (n={n}) …", job)

    def action_pages(self) -> None:
        ddir = self.disk_dir.path()
        overwrite = self.overwrite.isChecked()

        def job() -> str:
            outs = engine.run_page_batch(ddir, reporter=self.reporter,
                                         cancel=self._cancel, overwrite=overwrite)
            return f"Done: {len(outs)} page(s) in {ddir}"

        self._start(f"Generating pages from {ddir} …", job)

    def action_selected_pages(self, disks: List[Path]) -> None:
        out = self.disk_dir.path()

        def job() -> str:
            outs = engine.run_pages(disks, out, reporter=self.reporter,
                                    cancel=self._cancel)
            return f"Done: {len(outs)} page(s) in {out}"

        self._start(f"Generating {len(disks)} page(s) …", job)

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

    # -- library actions (selected films) -----------------------------------
    def _selected_disks(self):
        """Selected films whose disk PNG is on disk, as (films, disk paths)."""
        films, disks = [], []
        for f in self.library.selected():
            if f.disk_path and Path(f.disk_path).is_file():
                films.append(f)
                disks.append(Path(f.disk_path))
            else:
                self.write_log(f"[warn] {f.name}: disk PNG not found "
                               f"({f.disk_path or 'never rendered'}), skipped")
        return films, disks

    def action_lib_pages(self) -> None:
        _, disks = self._selected_disks()
        if not disks:
            return
        out = self.disk_dir.path()

        def job() -> str:
            outs = engine.run_pages(disks, out, reporter=self.reporter,
                                    cancel=self._cancel)
            return f"Done: {len(outs)} page(s) in {out}"

        self._start(f"Generating {len(disks)} page(s) from the library …", job)

    def action_lib_planche(self) -> None:
        from .planche import make_contact_sheets
        films, disks = self._selected_disks()
        if not disks:
            return
        out = self.disk_dir.path()
        captions = [f"{f.title} ({f.year})" if f.title and f.year
                    else f.title or f.name.replace("_", " ") for f in films]

        def job() -> str:
            sheets = make_contact_sheets(disks, out, captions=captions,
                                         reporter=self.reporter)
            return f"Done: {len(sheets)} contact sheet(s) in {out}"

        self._start(f"Assembling contact sheets of {len(disks)} film(s) …", job)

    def action_lib_barcodes(self) -> None:
        from .barcode import render_film
        films = self.library.selected()
        out = self.disk_dir.path() / "barcodes"

        def job() -> str:
            done = 0
            self.reporter.task("overall", "Barcodes", total=len(films))
            for f in films:
                if self._cancel.is_set():
                    break
                try:
                    render_film(f.name, "barcode", out / f"{f.name}_barcode.png")
                    done += 1
                except LookupError:
                    self.reporter.log(f"[warn] {f.name}: no mean colors stored, skipped")
                self.reporter.advance("overall", 1)
            self.reporter.remove("overall")
            return f"Done: {done} barcode(s) in {out}"

        self._start(f"Drawing {len(films)} barcode(s) from the database …", job)

    def _resolve_film(self, name: str, reply: dict) -> None:
        """A job found no TMDB match for ``name``: let the user search."""
        try:
            if self._cancel.is_set():
                return
            # The job waits for this answer: make sure the user notices.
            self._notify(f"{name}: no TMDB match, pick the film to continue.")
            dialog = TmdbMatchDialog(name, parent=self, in_job=True)
            dialog.exec()
            if dialog.skip_all:
                self.reporter.ask_tmdb = False
            reply["info"] = dialog.info
            if dialog.info is not None:
                self.write_log(f"✓ {name}: matched by hand to "
                               f"{dialog.info.title} ({dialog.info.year or '?'})")
        finally:
            reply["done"].set()

    def action_lib_match(self) -> None:
        films = self.library.selected()
        if not films or self._busy:
            return
        matched = 0
        for f in films:
            dialog = TmdbMatchDialog(f.name, f.title or "", f.year, parent=self,
                                     in_job=len(films) > 1)
            if dialog.exec() == QDialog.DialogCode.Accepted and dialog.info:
                info = dialog.info
                owner = history.get_by_tmdb(info.tmdb_id)
                if owner is not None and owner.name != f.name:
                    self.write_log(f"[warn] {f.name}: TMDB film {info.tmdb_id} is "
                                   f"already linked to {owner.name}; metadata "
                                   "copied without the id")
                history.record_info(f.name, info)
                self.write_log(f"✓ {f.name}: {info.title} ({info.year or '?'})")
                matched += 1
            if dialog.skip_all:
                break
        if matched:
            self.refresh_lists()

    def action_lib_forget(self) -> None:
        films = self.library.selected()
        if not films or self._busy:
            return
        answer = QMessageBox.question(
            self, "Movinyl",
            f"Remove {len(films)} film(s) from the database?\n"
            "Their disks and pages stay on disk, but they will be processed "
            "again next time.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        for f in films:
            history.forget(f.name)
        self.write_log(f"Forgot {len(films)} film(s).")
        self.refresh_lists()

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
        self.save_settings()
        self._hide_tray()
        event.accept()


def run(argv: Optional[list] = None) -> int:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("Movinyl")
    app.setStyle("Fusion")
    hints = app.styleHints()
    if hasattr(hints, "setColorScheme"):  # Qt >= 6.8: dark title bars and popups
        hints.setColorScheme(Qt.ColorScheme.Dark)
    app.setStyleSheet(STYLESHEET + _arrow_qss())
    win = MainWindow(_load_fonts())
    win.show()
    return app.exec()
