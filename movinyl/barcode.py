"""Redraw a film from the per-frame mean colors stored in the database.

No video and no frames needed: the ``mean_color`` table holds one RGB triplet
per sampled frame, which is all a movie barcode or a flat-ring disk needs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from PIL import Image, ImageDraw

from . import history
from .palette import RGB


def _strip(colors: Sequence[RGB]) -> Image.Image:
    """The colors as a 1px-tall image, frame 1 on the left."""
    img = Image.new("RGB", (len(colors), 1))
    img.putdata(list(colors))
    return img


def render_barcode(colors: Sequence[RGB], width: Optional[int] = None,
                   height: int = 600) -> Image.Image:
    """Classic movie barcode: one vertical stripe per frame, left to right."""
    if not colors:
        raise ValueError("no colors to draw")
    width = width or len(colors)
    # NEAREST keeps each frame a crisp stripe (no blending between frames).
    return _strip(colors).resize((width, height), Image.NEAREST)


def render_disk(colors: Sequence[RGB], size: Optional[int] = None) -> Image.Image:
    """Disk of flat concentric rings: frame 1 outermost, the last frame at the hub.

    Same layout as the photographic disk, with each ring painted in its frame's
    mean color.
    """
    if not colors:
        raise ValueError("no colors to draw")
    n = len(colors)
    size = size or 2 * n
    img = Image.new("RGB", (size, size), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Outermost first: each smaller disc covers the previous one but its ring.
    for i, color in enumerate(colors):
        inset = i * size / (2.0 * n)
        draw.ellipse((inset, inset, size - 1 - inset, size - 1 - inset),
                     fill=tuple(color))
    return img


def render_film(name: str, style: str = "barcode", out: Optional[Path] = None,
                **size) -> Path:
    """Render ``name`` from the database into a PNG and return its path."""
    colors = history.mean_colors(name)
    if not colors:
        raise LookupError(f"no mean colors stored for {name!r}")
    img = render_disk(colors, **size) if style == "disk" else render_barcode(colors, **size)
    out = out or Path(f"{name}_{style}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out
