"""Movinyl - capture the colors of your favorite movie as a vinyl-like disk.

This package is the cross-platform orchestration layer. It drives the optimized
C++ renderers (``disk`` / ``page``) and ``ffmpeg`` from a single Python code base
that runs identically on Linux, macOS and Windows, with progress reporting and
bounded concurrency (no more fork-bombing the machine).

Public entry points live in :mod:`movinyl.cli` (command line) and
:mod:`movinyl.tui` (Textual dashboard). The UI-agnostic logic is in
:mod:`movinyl.engine`.
"""

__version__ = "2.0.0"
