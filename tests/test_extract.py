"""Frame extraction: long films are decoded in parallel chunks, and chunking
never changes which frames are kept.

The chunk test needs ffmpeg/ffprobe on PATH and is skipped without them.
"""
import filecmp
import subprocess
from pathlib import Path

import pytest

from movinyl import engine
from movinyl import platforminfo as pf
from movinyl.progress import Reporter

needs_ffmpeg = pytest.mark.skipif(
    pf.which("ffmpeg") is None or pf.which("ffprobe") is None,
    reason="needs ffmpeg and ffprobe")


def test_how_many_decoders(monkeypatch):
    film = Path("District_9_2009.mkv")
    monkeypatch.setattr(pf, "cpu_count", lambda: 24)
    assert engine.extraction_workers(film, 6736, 2000) == 4
    assert engine.extraction_workers(Path("Film.MP4"), 6736, 2000) == 4
    assert engine.extraction_workers(Path("Film.ts"), 6736, 2000) == 1  # ts may jump
    assert engine.extraction_workers(film, 300, 2000) == 1              # short clip
    assert engine.extraction_workers(film, 3000, 20000) == 1            # dense samples
    monkeypatch.setattr(pf, "cpu_count", lambda: 12)
    assert engine.extraction_workers(film, 6736, 2000) == 2
    monkeypatch.setattr(pf, "cpu_count", lambda: 8)
    assert engine.extraction_workers(film, 6736, 2000) == 1


@needs_ffmpeg
def test_chunks_keep_exactly_the_same_frames(tmp_path):
    # B-frames, a keyframe every 2 s and a non-zero start time (like many rips).
    video = tmp_path / "Clip_2001.mkv"
    subprocess.run(
        [pf.which("ffmpeg"), "-v", "error", "-f", "lavfi",
         "-i", "testsrc2=size=320x180:rate=25:duration=120",
         "-c:v", "mpeg4", "-bf", "2", "-g", "50", "-q:v", "5",
         "-output_ts_offset", "0.088", str(video)],
        check=True)
    n = 40
    for workers in (1, 3):
        engine.extract_frames(video, n, tmp_path / str(workers), Reporter(), "x",
                              workers=workers)

    one, chunked = tmp_path / "1", tmp_path / "3"
    assert (one / "1.jpg").read_bytes() != (one / "2.jpg").read_bytes()
    names = [f"{i}.jpg" for i in range(1, n + 1)]
    match, mismatch, errors = filecmp.cmpfiles(one, chunked, names, shallow=False)
    assert (len(match), mismatch, errors) == (n, [], [])
