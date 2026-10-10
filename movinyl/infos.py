"""Generate the per-movie page assets: title/year/director/duration + palette.

Refactored from the old ``generate_infos.py``:
  * film metadata comes from the database (filled by the disk stage); TMDB is
    only queried (see :mod:`movinyl.tmdb`) when the film is not known yet,
  * network lookups never crash the pipeline -- on any failure we fall back to the
    filename-derived title/year and leave the rest blank,
  * asset filenames are ASCII (``title.png`` ...) for cross-platform reliability,
  * asset sizes are derived from the actual disk image so page composition lines up.
"""
from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Callable, List, Optional

from PIL import Image, ImageDraw, ImageFont

from . import history, tmdb
from . import platforminfo as pf
from .palette import RGB, extract_palette

ASSET_HEIGHT = 600  # page.cpp copies title/year/... into fixed-height 600px slots


def _font(filename: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a bundled TrueType font, falling back to Pillow's default."""
    path = pf.RESOURCE_ROOT / filename
    try:
        return ImageFont.truetype(str(path), size)
    except (OSError, IOError):
        try:
            return ImageFont.load_default(size=size)  # Pillow >= 10.1
        except TypeError:
            return ImageFont.load_default()


def _draw_centered_text(text: str, font_file: str, size: int, width: int,
                        out_path: Path) -> None:
    """Black slot with centered, wrapped white text (matches page.cpp slots)."""
    font = _font(font_file, size)
    img = Image.new("RGB", (width, ASSET_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    lines = textwrap.wrap(text, width=50) or [""]
    y, pad = 40, 10
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((width - w) / 2, y), line, font=font, fill="white")
        y += h + pad
    img.save(out_path)


def _draw_palette(colors: List[RGB], width: int, out_path: Path) -> None:
    """Row of up to 7 grey-bordered color discs (matches the historical layout)."""
    height = width // 7
    img = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    slots = 7
    cell = width // (2 * slots)          # historical geometry used W//14
    pad = width // (4 * slots)           # historical geometry used W//28
    disc = width // (2 * slots)
    for s in range(slots):
        x0 = (2 * s * cell) + pad
        x1 = ((2 * s + 1) * cell) + pad
        draw.ellipse((x0, 50, x1, disc + 50), fill=(127, 127, 127))
        if s < len(colors):
            draw.ellipse((x0 + 5, 55, x1 - 5, disc + 45), fill=tuple(colors[s]))
    img.save(out_path)


def film_info(
    name: str,
    tmdb_key: Optional[str] = None,
    resolve: Optional[Callable[[str], Optional[history.MovieInfo]]] = None,
) -> history.MovieInfo:
    """Metadata for ``name``: from the database, else TMDB (then stored).

    ``resolve`` is asked for the film when the automatic lookup finds nothing
    (the GUI opens its TMDB search window there).
    """
    film = history.get(name)
    if film is not None and film.tmdb_id is not None:
        return history.MovieInfo(film.tmdb_id, film.title, film.original_title,
                                 film.year, film.director, film.runtime)
    info = tmdb.lookup_name(name, tmdb_key)
    if info is None and resolve is not None:
        info = resolve(name)
    if info is not None:
        history.record_info(name, info)
        return info
    title, year = tmdb.parse_name(name)
    return history.MovieInfo(title=title, year=int(year) if year else None)


def generate_assets(
    name: str,
    disk_png: Path,
    out_dir: Path,
    tmdb_key: Optional[str] = None,
    resolve: Optional[Callable[[str], Optional[history.MovieInfo]]] = None,
) -> None:
    """Write title/year/director/duration/palette PNGs into ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    info = film_info(name, tmdb_key, resolve)
    display_title = info.original_title or info.title or name
    year = str(info.year) if info.year else ""
    director = info.director or ""
    duration = f"{info.runtime}'" if info.runtime else ""

    with Image.open(disk_png) as disk:
        disk_w = disk.size[0]
    width = disk_w + disk_w // 4  # == page.cpp outputWidth

    _draw_centered_text(display_title, "futura medium bt.ttf", 200, width,
                        out_dir / "title.png")
    _draw_centered_text(f"({year})" if year else "", "futura light bt.ttf", 200,
                        width, out_dir / "year.png")
    _draw_centered_text(director, "futura medium bt.ttf", 170, width,
                        out_dir / "director.png")
    _draw_centered_text(duration, "futura light bt.ttf", 150, width,
                        out_dir / "duration.png")

    colors = extract_palette(disk_png, k=7)
    _draw_palette(colors, width, out_dir / "palette.png")
