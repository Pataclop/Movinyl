"""Deterministic color-palette extraction from a finished disk image.

Replaces the old ``convert`` (ImageMagick) crop + ``extcolors`` pipeline with a
single, dependency-light, fully reproducible Pillow median-cut quantization.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from PIL import Image

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
