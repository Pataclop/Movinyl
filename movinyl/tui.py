"""Textual dashboard: manage everything and watch progress in one screen.

Layout is intentionally simple and "calm": two text panels listing the videos
and the generated disks, three progress bars (overall / extraction / rendering),
and a log. All heavy work runs in a background worker thread so the UI stays
responsive and cancellable.
"""
from __future__ import annotations

import threading
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, ProgressBar, Static

try:  # widget was renamed across Textual versions
    from textual.widgets import RichLog as _LogWidget
except ImportError:  # pragma: no cover
    from textual.widgets import TextLog as _LogWidget  # type: ignore

from . import bootstrap, engine
from . import platforminfo as pf
from .progress import Reporter

INPUT_DIR = pf.PROJECT_ROOT / "PROCESSING_ZONE"
PAGE_DIR = pf.PROJECT_ROOT / "PAGE_ZONE"

# Map engine task keys onto the three fixed progress bars.
_BAR_FOR = {
    "overall": "overall",
    "extract": "sub1",
    "disk": "sub2",
    "planche": "overall",
}


class TextualReporter(Reporter):
    """Bridges the engine's progress callbacks onto the Textual app (thread-safe)."""

    def __init__(self, app: "MovinylApp") -> None:
        self.app = app

    def _call(self, fn, *args) -> None:
        try:
            self.app.call_from_thread(fn, *args)
        except Exception:  # noqa: BLE001 - app may be shutting down
            pass

    def task(self, key, description, total):
        self._call(self.app.bar_task, key, description, total)

    def advance(self, key, amount=1):
        self._call(self.app.bar_advance, key, amount)

    def update(self, key, *, description=None, total=None, completed=None):
        self._call(self.app.bar_update, key, description, total, completed)

    def remove(self, key):
        self._call(self.app.bar_remove, key)

    def log(self, message):
        self._call(self.app.write_log, message)


class MovinylApp(App):
    CSS = """
    Screen { background: $surface; }

    #banner {
        height: 3;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        background: $panel;
        border: round $accent;
        margin: 0 0 1 0;
    }

    #panels { height: 11; }
    #panels Static {
        border: round $primary;
        padding: 0 1;
        width: 1fr;
    }

    #controls {
        height: 3;
        align: center middle;
        padding: 0 1;
    }
    #controls Button { margin: 0 1; }

    #bars { height: auto; padding: 1 1; border: round $primary; }
    .barrow { height: 1; margin: 0 0 1 0; }
    .barrow.overall { text-style: bold; }
    .barlabel { width: 12; content-align: left middle; color: $text-muted; }
    .barrow.overall .barlabel { color: $accent; }
    ProgressBar Bar > .bar--bar { color: $accent; }
    ProgressBar Bar > .bar--complete { color: $success; }

    #log {
        height: 1fr;
        border: round $primary;
        border-title-color: $accent;
        padding: 0 1;
    }
    """

    BINDINGS = [
        ("d", "disks", "Disks"),
        ("p", "pages", "Pages"),
        ("a", "planche", "Planche"),
        ("s", "setup", "Setup"),
        ("r", "refresh", "Refresh"),
        ("c", "cancel", "Cancel"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.reporter = TextualReporter(self)
        self._cancel = threading.Event()
        self._busy = False

    # -- composition --------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("◉  M O V I N Y L  ◉", id="banner")
        with Horizontal(id="panels"):
            yield Static(id="videos")
            yield Static(id="disks")
        with Horizontal(id="controls"):
            yield Button("▶ Disks (d)", id="btn-disks", variant="primary")
            yield Button("▤ Pages (p)", id="btn-pages", variant="success")
            yield Button("▦ Planche (a)", id="btn-planche")
            yield Button("⚙ Setup (s)", id="btn-setup")
            yield Button("✕ Cancel (c)", id="btn-cancel", variant="error")
        with Vertical(id="bars"):
            for key, label in (("overall", "Overall"), ("sub1", "Extract"),
                               ("sub2", "Render")):
                cls = "barrow overall" if key == "overall" else "barrow"
                with Horizontal(classes=cls):
                    yield Static(label, id=f"label-{key}", classes="barlabel")
                    yield ProgressBar(total=100, id=f"bar-{key}", show_eta=True)
        yield _LogWidget(id="log", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Movinyl"
        self.sub_title = f"{pf.system()} · {pf.cpu_count()} cores · {engine.DEFAULT_FRAME_COUNT} frames"
        self.query_one("#bars").border_title = "Progress"
        self.query_one("#log").border_title = "Log"
        self.refresh_lists()
        self.write_log("Welcome. Put videos in PROCESSING_ZONE, then press [b]d[/] to generate disks.")
        if pf.disk_binary() is None:
            self.write_log("[yellow]disk/page not built yet — press 's' (Setup) first.[/]")

    # -- progress-bar helpers (always called on the UI thread) --------------
    def _bar(self, key: str):
        bar_key = _BAR_FOR.get(key, "sub1")
        return (self.query_one(f"#bar-{bar_key}", ProgressBar),
                self.query_one(f"#label-{bar_key}", Static))

    def bar_task(self, key, description, total) -> None:
        bar, label = self._bar(key)
        label.update(description[:22])
        bar.update(total=total, progress=0)

    def bar_advance(self, key, amount) -> None:
        bar, _ = self._bar(key)
        bar.advance(amount)

    def bar_update(self, key, description, total, completed) -> None:
        bar, label = self._bar(key)
        if description is not None:
            label.update(description[:22])
        kwargs = {}
        if total is not None:
            kwargs["total"] = total
        if completed is not None:
            kwargs["progress"] = completed
        if kwargs:
            bar.update(**kwargs)

    def bar_remove(self, key) -> None:
        bar, label = self._bar(key)
        bar.update(total=100, progress=0)
        label.update("idle")

    def write_log(self, message: str) -> None:
        self.query_one("#log", _LogWidget).write(message)

    def refresh_lists(self) -> None:
        videos = engine.discover_videos(INPUT_DIR) if INPUT_DIR.is_dir() else []
        disks = engine.discover_disks(PAGE_DIR) if PAGE_DIR.is_dir() else []
        self.query_one("#videos", Static).update(
            self._panel("Videos · PROCESSING_ZONE", videos))
        self.query_one("#disks", Static).update(
            self._panel("Disks · PAGE_ZONE", disks))

    @staticmethod
    def _panel(title: str, items) -> str:
        if items:
            body = "\n".join(f"[dim]·[/] {p.name}" for p in items[:8])
        else:
            body = "[dim](empty)[/]"
        more = f"\n[dim]… +{len(items) - 8} more[/]" if len(items) > 8 else ""
        return f"[b]{title}[/]  [dim]({len(items)})[/]\n{body}{more}"

    # -- worker plumbing ----------------------------------------------------
    def _start(self, fn) -> None:
        if self._busy:
            self.write_log("[yellow]A job is already running (press 'c' to cancel).[/]")
            return
        self._busy = True
        self._cancel = threading.Event()
        self.run_worker(fn, thread=True, exclusive=True)

    def _finish(self, summary: str) -> None:
        self._busy = False
        self.write_log(summary)
        self.refresh_lists()

    # -- actions ------------------------------------------------------------
    def action_disks(self) -> None:
        n = engine.DEFAULT_FRAME_COUNT

        def job():
            try:
                outs = engine.run_disk_batch(INPUT_DIR, n=n, reporter=self.reporter,
                                             cancel=self._cancel)
                msg = f"[green]Done: {len(outs)} disk(s).[/]"
            except Exception as exc:  # noqa: BLE001
                msg = f"[red]disk error: {exc}[/]"
            self.call_from_thread(self._finish, msg)

        self.write_log(f"Generating disks (n={n}) …")
        self._start(job)

    def action_pages(self) -> None:
        def job():
            try:
                outs = engine.run_page_batch(PAGE_DIR, reporter=self.reporter,
                                             cancel=self._cancel)
                msg = f"[green]Done: {len(outs)} page(s).[/]"
            except Exception as exc:  # noqa: BLE001
                msg = f"[red]page error: {exc}[/]"
            self.call_from_thread(self._finish, msg)

        self.write_log("Generating pages …")
        self._start(job)

    def action_planche(self) -> None:
        from .planche import make_contact_sheets

        def job():
            try:
                disks = engine.discover_disks(PAGE_DIR)
                sheets = make_contact_sheets(disks, PAGE_DIR, reporter=self.reporter)
                msg = f"[green]Done: {len(sheets)} contact sheet(s).[/]"
            except Exception as exc:  # noqa: BLE001
                msg = f"[red]planche error: {exc}[/]"
            self.call_from_thread(self._finish, msg)

        self.write_log("Assembling contact sheets …")
        self._start(job)

    def action_setup(self) -> None:
        def job():
            try:
                bootstrap.setup(install_system=False, install_python=False,
                                log=lambda m: self.call_from_thread(self.write_log, m))
                msg = "[green]Setup complete.[/]"
            except Exception as exc:  # noqa: BLE001
                msg = f"[red]setup error: {exc}[/]"
            self.call_from_thread(self._finish, msg)

        self.write_log("Building C++ renderers …")
        self._start(job)

    def action_refresh(self) -> None:
        self.refresh_lists()

    def action_cancel(self) -> None:
        if self._busy:
            self._cancel.set()
            self.write_log("[yellow]Cancelling …[/]")
        else:
            self.write_log("Nothing to cancel.")

    # -- buttons ------------------------------------------------------------
    @on(Button.Pressed, "#btn-disks")
    def _b_disks(self) -> None:
        self.action_disks()

    @on(Button.Pressed, "#btn-pages")
    def _b_pages(self) -> None:
        self.action_pages()

    @on(Button.Pressed, "#btn-planche")
    def _b_planche(self) -> None:
        self.action_planche()

    @on(Button.Pressed, "#btn-setup")
    def _b_setup(self) -> None:
        self.action_setup()

    @on(Button.Pressed, "#btn-cancel")
    def _b_cancel(self) -> None:
        self.action_cancel()


def run() -> None:
    MovinylApp().run()
