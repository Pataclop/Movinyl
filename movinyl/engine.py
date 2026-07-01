"""UI-agnostic Movinyl engine: frame extraction, disk rendering, page assembly.

This module never imports a UI toolkit. It talks to the outside world through a
:class:`movinyl.progress.Reporter` and an optional ``threading.Event`` used for
cooperative cancellation. The same code therefore powers the CLI, the TUI and any
test harness.

Concurrency model (the answer to the old fork-bomb):
  * Videos are rendered **sequentially** -- each ``disk`` run already saturates
    every CPU core through OpenMP, so running several at once only thrashes RAM.
  * Pages are rendered through a **bounded** thread pool (``jobs`` workers) instead
    of the historical ``for f in *; do ./assist "$f" & done`` that spawned one
    process per file with no limit.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, List, Optional

from . import platforminfo as pf
from .progress import Reporter

DEFAULT_FRAME_COUNT = 2000

# Each frame only colors a single 1px-wide ring, so full-resolution frames are
# wasted decode + disk I/O. We cap the frame height (never upscaling) with a
# fixed, deterministic scaler so output stays reproducible across machines.
DEFAULT_MAX_HEIGHT = 1080


class MovinylError(RuntimeError):
    """Raised for any recoverable, user-facing engine failure."""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def sanitize_name(stem: str) -> str:
    """Normalize a video basename into a safe, ASCII-ish disk/page name.

    Mirrors the historical ``rename`` cleanup (drop parentheses, turn spaces and
    a few punctuation characters into underscores) so existing naming habits keep
    working across platforms.
    """
    s = stem
    for ch in "()":
        s = s.replace(ch, "")
    for ch in " :!-":
        s = s.replace(ch, "_")
    return s


def is_video(path: Path) -> bool:
    return path.is_file() and path.suffix.lower().lstrip(".") in pf.VIDEO_EXTENSIONS


def discover_videos(directory: Path) -> List[Path]:
    """Return video files in ``directory`` in a deterministic order."""
    if not directory.is_dir():
        raise MovinylError(f"Directory not found: {directory}")
    return sorted((p for p in directory.iterdir() if is_video(p)), key=lambda p: p.name)


def discover_disks(directory: Path) -> List[Path]:
    """Return generated disk PNGs (excluding already-composed ``*_page.png``)."""
    if not directory.is_dir():
        raise MovinylError(f"Directory not found: {directory}")
    return sorted(
        p for p in directory.glob("*.png")
        if p.is_file() and not p.stem.endswith("_page")
    )


def _require_tool(name: str) -> str:
    path = pf.which(name)
    if path is None:
        cmd = pf.system_install_command() or "your package manager"
        raise MovinylError(
            f"'{name}' was not found on PATH. Install it with:\n    {cmd}"
        )
    return path


def ffprobe_duration(video: Path) -> float:
    """Video duration in seconds (raises if it cannot be determined)."""
    ffprobe = _require_tool("ffprobe")
    try:
        out = subprocess.check_output(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
            stderr=subprocess.STDOUT,
        )
        return float(out.strip())
    except (subprocess.CalledProcessError, ValueError) as exc:
        raise MovinylError(f"Could not read duration of {video.name}: {exc}")


def _low_priority_kwargs() -> dict:
    """subprocess kwargs that run children at a lower scheduling priority."""
    if pf.is_windows():
        # 0x00004000 == BELOW_NORMAL_PRIORITY_CLASS
        return {"creationflags": 0x00004000}
    return {"preexec_fn": lambda: os.nice(10)}  # POSIX only


def _stream_process(
    proc: subprocess.Popen,
    on_line: Callable[[str], None],
    cancel: Optional[threading.Event],
) -> int:
    """Pump a process's stdout line by line, honoring cooperative cancellation."""
    assert proc.stdout is not None
    try:
        for raw in proc.stdout:
            if cancel is not None and cancel.is_set():
                proc.terminate()
                break
            on_line(raw.rstrip("\n"))
    finally:
        proc.stdout.close()
    return proc.wait()


# ---------------------------------------------------------------------------
# Stage 1 - frame extraction (single ffmpeg pass)
# ---------------------------------------------------------------------------

def extract_frames(
    video: Path,
    n: int,
    images_dir: Path,
    reporter: Reporter,
    key: str,
    cancel: Optional[threading.Event] = None,
    low_priority: bool = True,
    max_height: int = DEFAULT_MAX_HEIGHT,
) -> None:
    """Extract ``n`` evenly spaced frames from ``video`` into ``images_dir``.

    A single ffmpeg pass (``-vf fps=n/duration``) replaces the historical ~2000
    separate ffmpeg invocations that each re-opened and re-seeked the whole file.

    Frames are capped to ``max_height`` pixels tall (never upscaled) because each
    frame only paints a 1px ring: keeping full 1080p/4K detail just wastes encode,
    disk I/O and the renderer's re-decode. ``flags=lanczos`` is fixed so the
    downscale stays bit-identical across machines.
    """
    ffmpeg = _require_tool("ffmpeg")
    duration = ffprobe_duration(video)
    if duration <= 0:
        raise MovinylError(f"{video.name} has a non-positive duration.")

    images_dir.mkdir(parents=True, exist_ok=True)
    for old in images_dir.glob("*.jpg"):
        old.unlink()

    fps = n / duration
    vf = f"fps={fps:.10f}"
    if max_height and max_height > 0:
        # -2 keeps the aspect ratio with an even width; min(h,ih) never upscales.
        vf += f",scale=-2:'min({int(max_height)},ih)':flags=lanczos"
    cmd = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(video),
        "-vf", vf,
        "-qscale:v", "2",
        "-frames:v", str(n),
        "-progress", "pipe:1", "-nostats",
        str(images_dir / "%d.jpg"),
    ]
    reporter.task(key, f"Extracting frames · {video.name}", total=n)

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        **_low_priority_kwargs() if low_priority else {},
    )

    def handle(line: str) -> None:
        if line.startswith("frame="):
            try:
                reporter.update(key, completed=min(n, int(line[6:])))
            except ValueError:
                pass

    rc = _stream_process(proc, handle, cancel)
    stderr = proc.stderr.read() if proc.stderr else ""
    if cancel is not None and cancel.is_set():
        return
    if rc != 0:
        raise MovinylError(f"ffmpeg failed on {video.name}:\n{stderr.strip()}")
    reporter.update(key, completed=n)


def normalize_frame_count(images_dir: Path, n: int) -> None:
    """Guarantee exactly frames ``1.jpg .. n.jpg`` exist (deterministic padding).

    ffmpeg may emit one frame too few near the tail; the disk renderer expects a
    dense ``1..n`` sequence, so we fill any gap by copying the nearest neighbor.
    """
    present = sorted(
        int(p.stem) for p in images_dir.glob("*.jpg") if p.stem.isdigit()
    )
    if not present:
        raise MovinylError(f"No frames were extracted into {images_dir}")
    present_set = set(present)

    for i in range(1, n + 1):
        if i in present_set:
            continue
        # nearest existing index (prefer the closest lower one, then higher)
        nearest = min(present, key=lambda j: (abs(j - i), j))
        shutil.copyfile(images_dir / f"{nearest}.jpg", images_dir / f"{i}.jpg")
        present.append(i)
        present_set.add(i)


# ---------------------------------------------------------------------------
# Stage 2 - disk rendering (C++ binary)
# ---------------------------------------------------------------------------

def render_disk(
    work_dir: Path,
    n: int,
    reporter: Reporter,
    key: str,
    cancel: Optional[threading.Event] = None,
    low_priority: bool = True,
) -> Path:
    """Run the ``disk`` binary in ``work_dir`` (which contains ``images/``)."""
    binary = pf.disk_binary()
    if binary is None:
        raise MovinylError(
            "The 'disk' binary is not built yet. Run:  movinyl setup"
        )

    reporter.task(key, "Rendering disk", total=n)
    proc = subprocess.Popen(
        [str(binary), str(n)], cwd=str(work_dir),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        **_low_priority_kwargs() if low_priority else {},
    )

    missing = 0

    def handle(line: str) -> None:
        nonlocal missing
        if line == "PROGRESS":
            reporter.advance(key, 1)
        elif line.startswith("MISSING "):
            missing += 1

    rc = _stream_process(proc, handle, cancel)
    if missing:
        reporter.log(f"[warn] {missing} frame(s) were unreadable and left blank rings.")
    if cancel is not None and cancel.is_set():
        raise MovinylError("Cancelled")
    if rc != 0:
        raise MovinylError(f"disk renderer failed (exit {rc}) in {work_dir}")

    save = work_dir / "save.png"
    if not save.is_file():
        raise MovinylError(f"disk renderer produced no output in {work_dir}")
    return save


def generate_disk_for_video(
    video: Path,
    n: int,
    output_dir: Path,
    reporter: Reporter,
    cancel: Optional[threading.Event] = None,
    overwrite: bool = False,
    keep_frames: bool = False,
    low_priority: bool = True,
    max_height: int = DEFAULT_MAX_HEIGHT,
) -> Optional[Path]:
    """Full per-video pipeline: extract -> normalize -> render -> place PNG."""
    name = sanitize_name(video.stem)
    output = output_dir / f"{name}.png"
    if output.exists() and not overwrite:
        reporter.log(f"skip (exists): {output.name}")
        return output

    work_dir = output_dir / f"{name}.movinyl_work"
    images_dir = work_dir / "images"
    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)

    try:
        extract_frames(video, n, images_dir, reporter, "extract", cancel,
                       low_priority, max_height)
        if cancel is not None and cancel.is_set():
            return None
        normalize_frame_count(images_dir, n)
        save = render_disk(work_dir, n, reporter, "disk", cancel, low_priority)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(save), str(output))
        reporter.log(f"disk ready: {output.name}")
        return output
    finally:
        reporter.remove("extract")
        reporter.remove("disk")
        if not keep_frames:
            shutil.rmtree(work_dir, ignore_errors=True)


def run_disk_batch(
    input_dir: Path,
    n: int = DEFAULT_FRAME_COUNT,
    reporter: Optional[Reporter] = None,
    cancel: Optional[threading.Event] = None,
    overwrite: bool = False,
    keep_frames: bool = False,
    low_priority: bool = True,
    max_height: int = DEFAULT_MAX_HEIGHT,
) -> List[Path]:
    """Render disks for every video in ``input_dir`` (sequentially)."""
    reporter = reporter or Reporter()
    videos = discover_videos(input_dir)
    if not videos:
        raise MovinylError(f"No video files found in {input_dir}")

    reporter.task("overall", "Disks", total=len(videos))
    outputs: List[Path] = []
    for video in videos:
        if cancel is not None and cancel.is_set():
            break
        try:
            result = generate_disk_for_video(
                video, n, input_dir, reporter, cancel,
                overwrite, keep_frames, low_priority, max_height,
            )
            if result is not None:
                outputs.append(result)
        except MovinylError as exc:
            reporter.log(f"[error] {video.name}: {exc}")
        reporter.advance("overall", 1)
    reporter.remove("overall")
    return outputs


# ---------------------------------------------------------------------------
# Stage 3 - page assembly (palette + TMDB info + C++ page), bounded pool
# ---------------------------------------------------------------------------

def generate_page_for_disk(
    disk_png: Path,
    output_dir: Path,
    reporter: Reporter,
    cancel: Optional[threading.Event] = None,
    tmdb_key: Optional[str] = None,
    low_priority: bool = True,
) -> Path:
    """Compose the final movie page for a single disk PNG."""
    from . import infos  # local import: keeps Pillow optional until needed

    binary = pf.page_binary()
    if binary is None:
        raise MovinylError("The 'page' binary is not built yet. Run:  movinyl setup")

    name = disk_png.stem
    work_dir = Path(tempfile.mkdtemp(prefix="movinyl_page_"))
    try:
        shutil.copyfile(disk_png, work_dir / f"{name}.png")
        infos.generate_assets(name, disk_png, work_dir, tmdb_key=tmdb_key)
        if cancel is not None and cancel.is_set():
            raise MovinylError("Cancelled")

        proc = subprocess.Popen(
            [str(binary), name], cwd=str(work_dir),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            **_low_priority_kwargs() if low_priority else {},
        )
        out, _ = proc.communicate()
        if proc.returncode != 0:
            raise MovinylError(f"page renderer failed for {name}:\n{out.strip()}")

        produced = work_dir / f"{name}_page.png"
        if not produced.is_file():
            raise MovinylError(f"page renderer produced no output for {name}")
        output_dir.mkdir(parents=True, exist_ok=True)
        final = output_dir / f"{name}_page.png"
        shutil.move(str(produced), str(final))
        return final
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def run_page_batch(
    input_dir: Path,
    output_dir: Optional[Path] = None,
    jobs: Optional[int] = None,
    reporter: Optional[Reporter] = None,
    cancel: Optional[threading.Event] = None,
    tmdb_key: Optional[str] = None,
    low_priority: bool = True,
) -> List[Path]:
    """Compose pages for every disk PNG, using a *bounded* worker pool."""
    reporter = reporter or Reporter()
    output_dir = output_dir or input_dir
    disks = discover_disks(input_dir)
    if not disks:
        raise MovinylError(f"No disk PNGs found in {input_dir}")

    jobs = max(1, jobs or pf.default_jobs())
    reporter.task("overall", f"Pages (x{jobs})", total=len(disks))
    outputs: List[Path] = []

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {
            pool.submit(
                generate_page_for_disk, disk, output_dir, reporter,
                cancel, tmdb_key, low_priority,
            ): disk
            for disk in disks
        }
        for fut in as_completed(futures):
            disk = futures[fut]
            try:
                outputs.append(fut.result())
                reporter.log(f"page ready: {disk.stem}_page.png")
            except MovinylError as exc:
                reporter.log(f"[error] {disk.name}: {exc}")
            except Exception as exc:  # noqa: BLE001 - surface unexpected failures
                reporter.log(f"[error] {disk.name}: {exc}")
            reporter.advance("overall", 1)

    reporter.remove("overall")
    return outputs
