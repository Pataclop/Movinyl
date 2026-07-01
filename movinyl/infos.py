"""Generate the per-movie page assets: title/year/director/duration + palette.

Refactored from the old ``generate_infos.py``:
  * the TMDB API key is read from ``$TMDB_API_KEY`` (the historical key remains the
    out-of-the-box default so nothing breaks),
  * network lookups never crash the pipeline -- on any failure we fall back to the
    filename-derived title/year and leave the rest blank,
  * asset filenames are ASCII (``title.png`` ...) for cross-platform reliability,
  * asset sizes are derived from the actual disk image so page composition lines up.
"""
from __future__ import annotations

import os
import textwrap
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from . import platforminfo as pf
from .palette import RGB, extract_palette

# Historical default key; override with the TMDB_API_KEY environment variable.
_DEFAULT_TMDB_KEY = "38b045cf5307eaa109b937ba5047d015"

ASSET_HEIGHT = 600  # page.cpp copies title/year/... into fixed-height 600px slots


def _font(filename: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a bundled TrueType font, falling back to Pillow's default."""
    path = pf.PROJECT_ROOT / filename
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


def _parse_name(name: str) -> Tuple[str, str]:
    """Split a sanitized ``Title_Words_YEAR`` stem into (title, year)."""
    words = name.replace("_", " ").replace("-", " ").split()
    if len(words) >= 2 and words[-1].isdigit():
        return " ".join(words[:-1]), words[-1]
    return " ".join(words) or name, ""


def _lookup_tmdb(title: str, year: str, api_key: str) -> Tuple[str, str, str]:
    """Return (display_title, director, duration). Never raises."""
    display_title, director, duration = title, "", ""
    try:
        import tmdbsimple as tmdb  # optional dependency

        tmdb.API_KEY = api_key
        tmdb.REQUESTS_TIMEOUT = 5
        search = tmdb.Search()
        search.movie(query=title)
        for result in search.results or []:
            release = (result.get("release_date") or "")[:4]
            if year and release != year:
                continue
            movie = tmdb.Movies(result["id"])
            info = movie.info()
            display_title = info.get("original_title") or info.get("title") or title
            if info.get("runtime"):
                duration = f"{info['runtime']}'"
            movie.credits()
            for credit in movie.crew or []:
                if credit.get("job") == "Director":
                    director = credit.get("name", "")
                    break
            break
    except Exception:  # noqa: BLE001 - network/key/parse issues must not be fatal
        pass
    return display_title, director, duration


def generate_assets(
    name: str,
    disk_png: Path,
    out_dir: Path,
    tmdb_key: Optional[str] = None,
) -> None:
    """Write title/year/director/duration/palette PNGs into ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    api_key = tmdb_key or os.environ.get("TMDB_API_KEY") or _DEFAULT_TMDB_KEY

    title, year = _parse_name(name)
    display_title, director, duration = _lookup_tmdb(title, year, api_key)

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
