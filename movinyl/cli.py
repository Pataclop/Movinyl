"""Command-line interface for Movinyl.

Built on the standard-library ``argparse`` so ``doctor`` and ``setup`` work on a
fresh machine with nothing but Python installed; Rich (progress bars) and Textual
(the dashboard) are imported lazily, only once they are needed.

    python -m movinyl doctor
    python -m movinyl setup [--install-system]
    python -m movinyl disk   [DIR] [--n 2000]
    python -m movinyl page   [DIR] [--out DIR] [--jobs N]
    python -m movinyl planche[DIR] [--cols 4 --rows 4]
    python -m movinyl history [--forget NAME | --clear]
    python -m movinyl redraw NAME [--style barcode|disk] [--out FILE]
    python -m movinyl tui
"""
from __future__ import annotations

import argparse
import contextlib
import sys
from pathlib import Path
from typing import List, Optional

from . import bootstrap, engine, history
from . import platforminfo as pf
from .progress import Reporter

DEFAULT_INPUT = pf.PROJECT_ROOT / "PROCESSING_ZONE"
DEFAULT_PAGE = pf.PROJECT_ROOT / "PAGE_ZONE"


# ---------------------------------------------------------------------------
# Reporter selection (Rich if available, otherwise a quiet fallback)
# ---------------------------------------------------------------------------

def _make_reporter():
    """Return ``(reporter, live_context)``. Falls back gracefully without Rich."""
    try:
        from .progress import RichReporter
        reporter = RichReporter()
        return reporter, reporter.live()
    except Exception:  # noqa: BLE001 - rich not installed yet
        print("(install 'rich' for progress bars:  pip install rich)")
        return Reporter(), contextlib.nullcontext()


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------

_SYMBOL = {"ok": "[ OK ]", "warn": "[ ?? ]", "missing": "[ XX ]"}


def cmd_doctor(args: argparse.Namespace) -> int:
    checks = bootstrap.doctor()
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title=f"Movinyl doctor  ({pf.system()}, {pf.cpu_count()} cores)")
        table.add_column("Check")
        table.add_column("Status")
        table.add_column("Detail / fix", overflow="fold")
        style = {"ok": "green", "warn": "yellow", "missing": "red"}
        for c in checks:
            detail = c.detail + (f"\n→ {c.fix}" if c.fix else "")
            table.add_row(c.name, f"[{style[c.status]}]{c.status}[/]", detail)
        console.print(table)
    except Exception:  # noqa: BLE001 - plain fallback
        for c in checks:
            line = f"{_SYMBOL[c.status]} {c.name}: {c.detail}"
            if c.fix:
                line += f"  -> {c.fix}"
            print(line)

    missing = [c for c in checks if c.status == "missing"]
    if missing:
        print(f"\n{len(missing)} required item(s) missing. See fixes above.")
        return 1
    print("\nAll required checks passed.")
    return 0


# ---------------------------------------------------------------------------
# setup
# ---------------------------------------------------------------------------

def cmd_setup(args: argparse.Namespace) -> int:
    try:
        bootstrap.setup(
            install_system=args.install_system,
            install_python=not args.no_python,
        )
    except Exception as exc:  # noqa: BLE001 - surface a clean message
        print(f"setup failed: {exc}", file=sys.stderr)
        return 1
    print("\nSetup complete. Try:  python -m movinyl tui")
    return 0


# ---------------------------------------------------------------------------
# disk / page / planche
# ---------------------------------------------------------------------------

def _resolve_jobs(args: argparse.Namespace) -> int:
    if getattr(args, "jobs", None):
        return max(1, args.jobs)
    return pf.default_jobs(leave_cores=getattr(args, "leave_cores", 0))


def cmd_disk(args: argparse.Namespace) -> int:
    reporter, live = _make_reporter()
    try:
        with live:
            outputs = engine.run_disk_batch(
                Path(args.dir), n=args.n, reporter=reporter,
                overwrite=args.overwrite, keep_frames=args.keep_frames,
                low_priority=not args.no_low_priority,
                max_height=args.max_height, tmdb_key=args.tmdb_key,
            )
        print(f"\nGenerated {len(outputs)} disk(s) in {args.dir}")
        return 0
    except engine.MovinylError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def cmd_page(args: argparse.Namespace) -> int:
    reporter, live = _make_reporter()
    out_dir = Path(args.out) if args.out else Path(args.dir)
    try:
        with live:
            outputs = engine.run_page_batch(
                Path(args.dir), output_dir=out_dir, jobs=_resolve_jobs(args),
                reporter=reporter, tmdb_key=args.tmdb_key,
                low_priority=not args.no_low_priority,
                overwrite=args.overwrite,
            )
        print(f"\nGenerated {len(outputs)} page(s) in {out_dir}")
        return 0
    except engine.MovinylError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def cmd_planche(args: argparse.Namespace) -> int:
    from .planche import make_contact_sheets
    reporter, live = _make_reporter()
    in_dir = Path(args.dir)
    out_dir = Path(args.out) if args.out else in_dir
    disks = engine.discover_disks(in_dir)
    if not disks:
        print(f"No disk PNGs found in {in_dir}", file=sys.stderr)
        return 1
    with live:
        sheets = make_contact_sheets(
            disks, out_dir, cols=args.cols, rows=args.rows,
            cell=args.cell, reporter=reporter,
        )
    print(f"\nGenerated {len(sheets)} contact sheet(s) in {out_dir}")
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    if args.clear:
        print(f"Forgot {history.clear()} film(s).")
        return 0
    if args.forget:
        for name in args.forget:
            name = engine.sanitize_name(name)
            print(f"{'forgot' if history.forget(name) else 'not found'}: {name}")
        return 0

    import time
    films = history.all_films()
    if not films:
        print(f"No processed films yet ({history.db_path()}).")
        return 0
    fmt = lambda t: time.strftime("%Y-%m-%d %H:%M", time.localtime(t)) if t else "-"
    width = max(len(f.name) for f in films)
    print(f"{'film':<{width}}  {'tmdb':>8}  {'disk':<16}  {'page':<16}  colors")
    for f in films:
        colors = len(history.mean_colors(f.name))
        print(f"{f.name:<{width}}  {f.tmdb_id or '-':>8}  {fmt(f.disk_at):<16}  "
              f"{fmt(f.page_at):<16}  {colors or '-'}")
    print(f"\n{len(films)} film(s) in {history.db_path()}")
    return 0


def cmd_redraw(args: argparse.Namespace) -> int:
    from .barcode import render_film
    name = engine.sanitize_name(args.name)
    size = {"size": args.size} if args.style == "disk" else {
        "width": args.width, "height": args.height}
    try:
        out = render_film(name, args.style, Path(args.out) if args.out else None,
                          **size)
    except LookupError as exc:
        print(f"error: {exc} (render its disk first)", file=sys.stderr)
        return 1
    print(f"{args.style} written to {out}")
    return 0


def cmd_tui(args: argparse.Namespace) -> int:
    try:
        from .tui import run
    except Exception as exc:  # noqa: BLE001
        print(f"Textual is required for the TUI: pip install textual  ({exc})",
              file=sys.stderr)
        return 1
    run()
    return 0


def cmd_gui(args: argparse.Namespace) -> int:
    try:
        from .gui import run
    except Exception as exc:  # noqa: BLE001
        print(f"PyQt6 is required for the GUI: pip install PyQt6  ({exc})",
              file=sys.stderr)
        return 1
    return run([sys.argv[0]])


# ---------------------------------------------------------------------------
# argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="movinyl",
                                description="Capture the colors of your favorite movie.")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("doctor", help="Check the environment").set_defaults(func=cmd_doctor)

    sp = sub.add_parser("setup", help="Build the C++ renderers and prepare the project")
    sp.add_argument("--install-system", action="store_true",
                    help="Also run the system package manager (sudo/admin).")
    sp.add_argument("--no-python", action="store_true",
                    help="Skip 'pip install -r requirements.txt'.")
    sp.set_defaults(func=cmd_setup)

    sp = sub.add_parser("disk", help="Generate disks from videos")
    sp.add_argument("dir", nargs="?", default=str(DEFAULT_INPUT))
    sp.add_argument("--n", type=int, default=engine.DEFAULT_FRAME_COUNT,
                    help="Frames per video (default: 2000).")
    sp.add_argument("--max-height", type=int, default=engine.DEFAULT_MAX_HEIGHT,
                    help="Cap frame height in pixels; sources are never upscaled "
                         "(default: 1080). Use 0 to keep full resolution.")
    sp.add_argument("--overwrite", action="store_true",
                    help="Re-render disks that exist or are recorded in the history "
                         "(a changed video file is always re-rendered).")
    sp.add_argument("--keep-frames", action="store_true",
                    help="Keep extracted frames instead of cleaning them up.")
    sp.add_argument("--no-low-priority", action="store_true",
                    help="Do not lower child-process scheduling priority.")
    sp.add_argument("--tmdb-key", default=None, help="Override the TMDB API key.")
    sp.set_defaults(func=cmd_disk)

    sp = sub.add_parser("page", help="Generate pages from disks")
    sp.add_argument("dir", nargs="?", default=str(DEFAULT_PAGE))
    sp.add_argument("--out", default=None, help="Output directory (default: DIR).")
    sp.add_argument("--jobs", type=int, default=None,
                    help="Parallel page workers (default: CPU count).")
    sp.add_argument("--leave-cores", type=int, default=0,
                    help="Keep N cores free so the machine stays responsive.")
    sp.add_argument("--tmdb-key", default=None, help="Override the TMDB API key.")
    sp.add_argument("--overwrite", action="store_true",
                    help="Re-render pages already recorded in the history.")
    sp.add_argument("--no-low-priority", action="store_true")
    sp.set_defaults(func=cmd_page)

    sp = sub.add_parser("planche", help="Assemble disks into contact sheets")
    sp.add_argument("dir", nargs="?", default=str(DEFAULT_PAGE))
    sp.add_argument("--out", default=None)
    sp.add_argument("--cols", type=int, default=4)
    sp.add_argument("--rows", type=int, default=4)
    sp.add_argument("--cell", type=int, default=1000, help="Cell size in pixels.")
    sp.set_defaults(func=cmd_planche)

    sp = sub.add_parser("history", help="List or edit the processed-films database")
    sp.add_argument("--forget", nargs="+", metavar="NAME",
                    help="Forget these films so they get processed again.")
    sp.add_argument("--clear", action="store_true", help="Forget every film.")
    sp.set_defaults(func=cmd_history)

    sp = sub.add_parser("redraw", help="Redraw a film from its stored mean colors")
    sp.add_argument("name", help="Film name (disk PNG stem), e.g. Inception_2010")
    sp.add_argument("--style", choices=("barcode", "disk"), default="barcode")
    sp.add_argument("--out", default=None, help="Output PNG (default: NAME_STYLE.png).")
    sp.add_argument("--width", type=int, default=None,
                    help="Barcode width (default: one pixel per frame).")
    sp.add_argument("--height", type=int, default=600, help="Barcode height.")
    sp.add_argument("--size", type=int, default=None,
                    help="Disk side in pixels (default: 2 x frames).")
    sp.set_defaults(func=cmd_redraw)

    sub.add_parser("tui", help="Launch the interactive dashboard").set_defaults(func=cmd_tui)
    sub.add_parser("gui", help="Launch the desktop window (PyQt6)").set_defaults(func=cmd_gui)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        # No subcommand -> launch the dashboard (the friendliest default).
        return cmd_tui(args)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
