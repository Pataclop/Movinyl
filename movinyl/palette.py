"""Deterministic color-palette extraction from a finished disk image.

Replaces the old ``convert`` (ImageMagick) crop + ``extcolors`` pipeline with a
single, dependency-light, fully reproducible Pillow median-cut quantization.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageStat

RGB = Tuple[int, int, int]


def _center_strip(img: Image.Image) -> Image.Image:
    """Crop a thin vertical strip through the disk center.

    The strip crosses every concentric ring, so it samples the movie's whole
    color timeline while avoiding the black background in the corners and the
    black hub-region bias of using the full square.
    """
    w, h = img.size
    half = max(2, int(w * 0.02))
    cx = w // 2
    left, right = cx - half, cx + half
    top, bottom = int(h * 0.012), int(h * 0.988)
    return img.crop((left, top, right, bottom))


def extract_palette(image_path: Path, k: int = 7) -> List[RGB]:
    """Return up to ``k`` dominant colors (most frequent first), deterministically."""
    with Image.open(image_path) as raw:
        img = raw.convert("RGB")
        strip = _center_strip(img)
        # Downscale for speed; LANCZOS is deterministic.
        strip.thumbnail((64, 1600), Image.LANCZOS)
        quantized = strip.quantize(colors=max(1, k), method=Image.MEDIANCUT)

    palette = quantized.getpalette() or []
    counts = quantized.getcolors() or []  # list of (count, palette_index)

    colors: List[Tuple[int, RGB]] = []
    for count, index in counts:
        base = index * 3
        rgb = (palette[base], palette[base + 1], palette[base + 2])
        colors.append((count, rgb))

    # Most frequent first; tie-break on the color value for a stable order.
    colors.sort(key=lambda c: (-c[0], c[1]))
    return [rgb for _, rgb in colors[:k]]


def frame_mean_color(path: Path) -> RGB:
    """Mean color of one extracted frame.

    JPEG ``draft`` mode lets libjpeg decode at 1/8 scale straight from the DCT
    coefficients, which is several times faster and averages to the same color
    (to within rounding) as the full-resolution frame. An unreadable frame is
    black, like the blank ring the disk renderer leaves for it.
    """
    try:
        with Image.open(path) as raw:
            raw.draft("RGB", (max(1, raw.width // 8), max(1, raw.height // 8)))
            mean = ImageStat.Stat(raw.convert("RGB")).mean
    except OSError:
        return (0, 0, 0)
    return (round(mean[0]), round(mean[1]), round(mean[2]))


def frame_mean_colors(images_dir: Path, n: int, jobs: int = 0) -> List[RGB]:
    """Mean colors of frames ``1.jpg .. n.jpg`` in movie order.

    Decoding releases the GIL, so a thread pool scales across cores.
    """
    paths = [images_dir / f"{i}.jpg" for i in range(1, n + 1)]
    with ThreadPoolExecutor(max_workers=jobs or None) as pool:
        return list(pool.map(frame_mean_color, paths))


def _write_flat_frame(item: Tuple[Path, RGB]) -> None:
    path, rgb = item
    # A uniform block is pure DC in JPEG: at quality 100 with no chroma
    # subsampling it decodes back to the same color (to within rounding).
    Image.new("RGB", (16, 16), rgb).save(path, "JPEG", quality=100, subsampling=0)


def write_flat_frames(images_dir: Path, colors: List[RGB], jobs: int = 0) -> None:
    """Replace frames ``1.jpg .. n.jpg`` with solid blocks of their mean color.

    The disk renderer then paints each ring in a single color, unchanged.
    """
    items = [(images_dir / f"{i}.jpg", rgb) for i, rgb in enumerate(colors, 1)]
    with ThreadPoolExecutor(max_workers=jobs or None) as pool:
        list(pool.map(_write_flat_frame, items))
