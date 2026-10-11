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

from . import history
from . import platforminfo as pf
from .progress import Reporter

DEFAULT_FRAME_COUNT = 2000

# Each frame only colors a single 1px-wide ring, so full-resolution frames are
# wasted decode + disk I/O. We cap the frame height (never upscaling) with a
# fixed, deterministic scaler so output stays reproducible across machines.
FRAME_HEIGHT = 1080

# In mean-color mode a frame is reduced to its average color, so a tiny
# area-averaged frame is enough (and much cheaper to encode and decode).
MEAN_FRAME_WIDTH = 64


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
            stderr=subprocess.STDOUT, **_child_kwargs(False),
        )
        return float(out.strip())
    except (subprocess.CalledProcessError, ValueError) as exc:
        raise MovinylError(f"Could not read duration of {video.name}: {exc}")


def _child_kwargs(low_priority: bool) -> dict:
    """subprocess kwargs: optionally lower priority; never pop a console window."""
    if pf.is_windows():
        # 0x08000000 == CREATE_NO_WINDOW (no console flash from the GUI / .exe)
        flags = 0x08000000
        if low_priority:
            flags |= 0x00004000  # BELOW_NORMAL_PRIORITY_CLASS
        return {"creationflags": flags}
    return {"preexec_fn": lambda: os.nice(10)} if low_priority else {}  # POSIX only


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


class _AnyOf:
    """Set as soon as one of ``events`` is (an Event look-alike)."""

    def __init__(self, *events: Optional[threading.Event]) -> None:
        self._events = [e for e in events if e is not None]

    def is_set(self) -> bool:
        return any(e.is_set() for e in self._events)


def _run_ffmpeg_parts(
    cmds: List[List[str]],
    workers: int,
    on_frames: Callable[[int], None],
    cancel: Optional[threading.Event],
    low_priority: bool,
) -> Optional[str]:
    """Run ffmpeg commands (each with ``-progress pipe:1``), ``workers`` at a
    time and in order, reporting the frames written by all of them together.

    Returns the error output of the first part that failed (the other parts
    are then stopped), or None.
    """
    counts = [0] * len(cmds)
    pending = list(range(len(cmds)))
    lock = threading.Lock()
    errors: List[str] = []
    failed = threading.Event()
    stop = _AnyOf(cancel, failed)

    def run_part(i: int) -> None:
        def handle(line: str) -> None:
            if line.startswith("frame="):
                try:
                    value = int(line[6:])
                except ValueError:
                    return
                with lock:
                    counts[i] = value
                    done = sum(counts)
                on_frames(done)

        # stderr goes to a file: a chatty decoder can never fill a pipe and
        # stall ffmpeg while we read its progress.
        with tempfile.TemporaryFile() as log:
            proc = subprocess.Popen(
                cmds[i], stdout=subprocess.PIPE, stderr=log, text=True,
                **_child_kwargs(low_priority),
            )
            rc = _stream_process(proc, handle, stop)
            if rc != 0 and not stop.is_set():
                log.seek(0)
                errors.append(log.read().decode("utf-8", "replace").strip()
                              or f"exit code {rc}")
                failed.set()

    def worker() -> None:
        try:
            while not stop.is_set():
                with lock:
                    if not pending:
                        return
                    i = pending.pop(0)
                run_part(i)
        except BaseException:
            failed.set()
            raise

    if workers <= 1:
        worker()
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for fut in [pool.submit(worker) for _ in range(workers)]:
                fut.result()
    return errors[0] if errors else None


# ---------------------------------------------------------------------------
# Stage 1 - frame extraction (ffmpeg; long films decoded in parallel)
# ---------------------------------------------------------------------------

# One ffmpeg process decodes a film on ~6 hardware threads at best, so long
# films are cut into consecutive chunks decoded side by side. Measured on a
# 1h52 HEVC 1080p film with a 12-core/24-thread CPU: 230 s in one pass, x1.7
# with 2 decoders, x2.0 with 3, x2.2 with 4 (~0.6 GB of RAM each).
MAX_EXTRACT_WORKERS = 4
MIN_SPLIT_DURATION = 600.0  # seconds: shorter videos are quick in one pass
# Containers with steady timestamps. MPEG-TS/PS timestamps may jump, so those
# files are always read in one pass.
_SPLITTABLE = {"mkv", "mp4", "mov", "m4v", "webm"}


def extraction_workers(video: Path, duration: float, n: int) -> int:
    """How many ffmpeg processes share the extraction of ``video``."""
    if (video.suffix.lower().lstrip(".") not in _SPLITTABLE
            or duration < MIN_SPLIT_DURATION
            # A chunk seeks to the start of its first sample interval; the
            # first half of that interval must hold frames (>= 10 fps video).
            or duration / n < 0.2):
        return 1
    return max(1, min(MAX_EXTRACT_WORKERS, pf.cpu_count() // 6, n // 2))


def extract_frames(
    video: Path,
    n: int,
    images_dir: Path,
    reporter: Reporter,
    key: str,
    cancel: Optional[threading.Event] = None,
    low_priority: bool = True,
    mean_colors: bool = False,
    workers: Optional[int] = None,
) -> None:
    """Extract ``n`` evenly spaced frames from ``video`` into ``images_dir``.

    A single ffmpeg pass (``-vf fps=n/duration``) replaces the historical ~2000
    separate ffmpeg invocations that each re-opened and re-seeked the whole file.
    Long films are cut into consecutive chunks that ``workers`` ffmpeg
    processes decode side by side (default: :func:`extraction_workers`).

    Output frame ``j`` is the last frame shown before ``(j + 0.5) * duration / n``.
    A chunk seeks to the start of its first sample interval and keeps the
    film's own timeline (``-copyts -start_at_zero``), so chunking never changes
    which frames are kept: the disk is the same whatever the core count.

    Frames are capped to ``FRAME_HEIGHT`` pixels tall (never upscaled) because
    each frame only paints a 1px ring: keeping full 1080p/4K detail just wastes
    encode, disk I/O and the renderer's re-decode. ``flags=lanczos`` is fixed so
    the downscale stays bit-identical across machines. With ``mean_colors`` the
    frames are area-averaged down to ``MEAN_FRAME_WIDTH`` pixels wide instead,
    since only their average color is kept.
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
    if mean_colors:
        # area scaling averages whole pixel blocks, so the mean color is kept.
        vf += f",scale={MEAN_FRAME_WIDTH}:-2:flags=area"
    else:
        # -2 keeps the aspect ratio with an even width; min(h,ih) never upscales.
        vf += f",scale=-2:'min({FRAME_HEIGHT},ih)':flags=lanczos"

    workers = max(1, min(workers or extraction_workers(video, duration, n), n))
    # A decoder done early takes the next chunk: a few chunks per decoder even
    # out the uneven decoding cost of the film's scenes.
    chunks = 1 if workers == 1 else min(n, 4 * workers)
    bounds = [n * i // chunks for i in range(chunks + 1)]  # frames [j0, j1)
    cmds = []
    for j0, j1 in zip(bounds, bounds[1:]):
        timeline = []
        if chunks > 1:
            timeline = ["-copyts", "-start_at_zero"]
            if j0:
                timeline += ["-ss", f"{j0 / fps:.6f}"]
        cmds.append([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y", *timeline,
            "-i", str(video),
            "-vf", vf,
            "-qscale:v", "2",
            "-frames:v", str(j1 - j0),
            "-start_number", str(j0 + 1),
            "-progress", "pipe:1", "-nostats",
            str(images_dir / "%d.jpg"),
        ])
    label = f"Extracting frames ×{workers}" if workers > 1 else "Extracting frames"
    reporter.task(key, f"{label} · {video.name}", total=n)

    error = _run_ffmpeg_parts(
        cmds, workers, lambda done: reporter.update(key, completed=min(n, done)),
        cancel, low_priority)
    if cancel is not None and cancel.is_set():
        return
    if error is not None:
        raise MovinylError(f"ffmpeg failed on {video.name}:\n{error}")
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
        **_child_kwargs(low_priority),
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
    mean_colors: bool = False,
    tmdb_key: Optional[str] = None,
) -> Optional[Path]:
    """Full per-video pipeline: extract -> normalize -> mean colors -> render
    -> place PNG, then record the film (TMDB metadata + colors) in the database.

    With ``mean_colors`` every ring is painted with its frame's average color
    instead of the frame itself.
    """
    name = sanitize_name(video.stem)
    output = output_dir / f"{name}.png"
    if not overwrite and history.video_changed(name, video):
        reporter.log(f"video changed since last run, re-processing: {name}")
        overwrite = True
    if output.exists() and not overwrite:
        reporter.log(f"skip (exists): {output.name}")
        if not history.disk_done(name):
            # Adopt a disk made outside Movinyl's history: its settings are
            # unknown and any recorded page still matches it.
            history.record_disk(name, video, None, None, output, reset_page=False)
        return output
    if history.disk_done(name) and not overwrite:
        # The PNG may have been moved (e.g. to PAGE_ZONE): trust the history.
        reporter.log(f"skip (already processed): {name}")
        return None

    work_dir = output_dir / f"{name}.movinyl_work"
    images_dir = work_dir / "images"
    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)

    try:
        extract_frames(video, n, images_dir, reporter, "extract", cancel,
                       low_priority, mean_colors)
        if cancel is not None and cancel.is_set():
            return None
        normalize_frame_count(images_dir, n)
        colors = _mean_colors(images_dir, n)
        if mean_colors:
            _flatten_frames(images_dir, colors)
        save = render_disk(work_dir, n, reporter, "disk", cancel, low_priority)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(save), str(output))
        history.record_disk(name, video, n, None if mean_colors else FRAME_HEIGHT,
                            output, colors=colors)
        _record_info(name, tmdb_key, reporter)
        reporter.log(f"disk ready: {output.name}")
        return output
    finally:
        reporter.remove("extract")
        reporter.remove("disk")
        if not keep_frames:
            shutil.rmtree(work_dir, ignore_errors=True)


def _mean_colors(images_dir: Path, n: int) -> list:
    from .palette import frame_mean_colors  # local import: Pillow
    return frame_mean_colors(images_dir, n)


def _flatten_frames(images_dir: Path, colors: list) -> None:
    from .palette import write_flat_frames  # local import: Pillow
    write_flat_frames(images_dir, colors)


def _record_info(name: str, tmdb_key: Optional[str], reporter: Reporter) -> None:
    """Store the film's TMDB metadata and id, unless it is already known."""
    from . import tmdb
    film = history.get(name)
    if film is not None and film.tmdb_id is not None:
        return
    info = tmdb.lookup_name(name, tmdb_key) or reporter.resolve_film(name)
    if info is None:
        reporter.log(f"[warn] {name}: not found on TMDB (no metadata stored)")
    else:
        history.record_info(name, info)


def run_disk_batch(
    input_dir: Path,
    n: int = DEFAULT_FRAME_COUNT,
    reporter: Optional[Reporter] = None,
    cancel: Optional[threading.Event] = None,
    overwrite: bool = False,
    keep_frames: bool = False,
    low_priority: bool = True,
    mean_colors: bool = False,
    tmdb_key: Optional[str] = None,
) -> List[Path]:
    """Render disks for every video in ``input_dir`` (sequentially)."""
    videos = discover_videos(input_dir)
    if not videos:
        raise MovinylError(f"No video files found in {input_dir}")
    return run_disks(videos, input_dir, n, reporter, cancel, overwrite,
                     keep_frames, low_priority, mean_colors, tmdb_key)


def run_disks(
    videos: List[Path],
    output_dir: Path,
    n: int = DEFAULT_FRAME_COUNT,
    reporter: Optional[Reporter] = None,
    cancel: Optional[threading.Event] = None,
    overwrite: bool = False,
    keep_frames: bool = False,
    low_priority: bool = True,
    mean_colors: bool = False,
    tmdb_key: Optional[str] = None,
) -> List[Path]:
    """Render a disk for each of ``videos`` into ``output_dir`` (sequentially).

    Films already processed are skipped unless ``overwrite`` is set, exactly as
    in :func:`run_disk_batch`.
    """
    reporter = reporter or Reporter()
    reporter.task("overall", "Disks", total=len(videos))
    outputs: List[Path] = []
    for video in videos:
        if cancel is not None and cancel.is_set():
            break
        try:
            result = generate_disk_for_video(
                video, n, output_dir, reporter, cancel,
                overwrite, keep_frames, low_priority, mean_colors, tmdb_key,
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
        infos.generate_assets(name, disk_png, work_dir, tmdb_key=tmdb_key,
                              resolve=reporter.resolve_film)
        if cancel is not None and cancel.is_set():
            raise MovinylError("Cancelled")

        proc = subprocess.Popen(
            [str(binary), name], cwd=str(work_dir),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            **_child_kwargs(low_priority),
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
        history.record_page(name, final)
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
    overwrite: bool = False,
) -> List[Path]:
    """Compose pages for every disk PNG, using a *bounded* worker pool.

    Films whose page is already recorded in the history are skipped unless
    ``overwrite`` is set.
    """
    reporter = reporter or Reporter()
    output_dir = output_dir or input_dir
    disks = discover_disks(input_dir)
    if not disks:
        raise MovinylError(f"No disk PNGs found in {input_dir}")
    if not overwrite:
        done = [d for d in disks if history.page_done(d.stem)]
        for d in done:
            reporter.log(f"skip (already processed): {d.stem}")
        disks = [d for d in disks if d not in done]
        if not disks:
            return []
    return run_pages(disks, output_dir, jobs, reporter, cancel, tmdb_key,
                     low_priority)


def run_pages(
    disks: List[Path],
    output_dir: Path,
    jobs: Optional[int] = None,
    reporter: Optional[Reporter] = None,
    cancel: Optional[threading.Event] = None,
    tmdb_key: Optional[str] = None,
    low_priority: bool = True,
) -> List[Path]:
    """Compose a page for each of ``disks`` (no skipping), bounded pool."""
    reporter = reporter or Reporter()
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
