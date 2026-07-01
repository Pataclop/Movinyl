"""Progress-reporting abstraction shared by the CLI and the TUI.

The :class:`Reporter` API is intentionally tiny so the engine never has to know
whether it is talking to a Rich progress display, a Textual dashboard, or nothing
at all (headless / tests). Tasks are addressed by an opaque string ``key``.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Dict, Optional


class Reporter:
    """No-op reporter. Subclass and override to render progress somewhere."""

    def task(self, key: str, description: str, total: Optional[int]) -> None:
        """Create (or reset) a task identified by ``key``."""

    def advance(self, key: str, amount: int = 1) -> None:
        """Advance a task by ``amount`` units."""

    def update(
        self,
        key: str,
        *,
        description: Optional[str] = None,
        total: Optional[int] = None,
        completed: Optional[int] = None,
    ) -> None:
        """Update a task's label / total / absolute position."""

    def remove(self, key: str) -> None:
        """Drop a finished task from the display."""

    def log(self, message: str) -> None:
        """Emit a human-readable log line."""


class RichReporter(Reporter):
    """Renders progress with ``rich.progress`` (used by the command line)."""

    def __init__(self) -> None:
        # Imported lazily so the package works even if rich is missing until setup.
        from rich.console import Console
        from rich.progress import (
            BarColumn,
            MofNCompleteColumn,
            Progress,
            SpinnerColumn,
            TextColumn,
            TimeRemainingColumn,
        )

        self.console = Console()
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=False,
        )
        self._tasks: Dict[str, int] = {}

    @contextmanager
    def live(self):
        with self._progress:
            yield self

    def task(self, key: str, description: str, total: Optional[int]) -> None:
        if key in self._tasks:
            self._progress.reset(
                self._tasks[key], total=total, description=description
            )
        else:
            self._tasks[key] = self._progress.add_task(description, total=total)

    def advance(self, key: str, amount: int = 1) -> None:
        if key in self._tasks:
            self._progress.advance(self._tasks[key], amount)

    def update(
        self,
        key: str,
        *,
        description: Optional[str] = None,
        total: Optional[int] = None,
        completed: Optional[int] = None,
    ) -> None:
        if key not in self._tasks:
            self.task(key, description or key, total)
            return
        kwargs = {}
        if description is not None:
            kwargs["description"] = description
        if total is not None:
            kwargs["total"] = total
        if completed is not None:
            kwargs["completed"] = completed
        self._progress.update(self._tasks[key], **kwargs)

    def remove(self, key: str) -> None:
        task_id = self._tasks.pop(key, None)
        if task_id is not None:
            self._progress.remove_task(task_id)

    def log(self, message: str) -> None:
        self.console.log(message)
