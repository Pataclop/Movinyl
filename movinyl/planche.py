"""Assemble several disks into printable contact sheets ("planches").

A clean, deterministic rewrite of the old ``planche.py`` (which was broken on
modern Pillow: ``draw.textsize`` was removed, ``new()`` was undefined and the
call signature was wrong).
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont

from . import platforminfo as pf
from .progress import Reporter


def _font(size: int) -> ImageFont.ImageFont:
    path = pf.PROJECT_ROOT / "futura medium bt.ttf"
    try:
        return ImageFont.truetype(str(path), size)
    except (OSError, IOError):
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()


def _caption_for(disk: Path) -> str:
    stem = disk.stem
    if stem.endswith("_page"):
        stem = stem[: -len("_page")]
    return stem.replace("_", " ")


def make_contact_sheets(
    disks: List[Path],
    output_dir: Path,
    cols: int = 4,
    rows: int = 4,
    cell: int = 1000,
    captions: Optional[List[str]] = None,
    reporter: Optional[Reporter] = None,
) -> List[Path]:
    """Lay ``disks`` out on ``cols`` x ``rows`` grids and save one PNG per sheet."""
    reporter = reporter or Reporter()
    if not disks:
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    per_sheet = cols * rows
    disc_size = int(cell * 0.85)
    caption_h = max(40, cell // 12)
    font = _font(caption_h - 12)

    sheet_w = cols * cell
    sheet_h = rows * cell
    n_sheets = (len(disks) + per_sheet - 1) // per_sheet

    reporter.task("planche", "Contact sheets", total=len(disks))
    outputs: List[Path] = []

    for sheet_idx in range(n_sheets):
        sheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 255))
        draw = ImageDraw.Draw(sheet)

        for slot in range(per_sheet):
            i = sheet_idx * per_sheet + slot
            if i >= len(disks):
                break
            col, row = slot % cols, slot // cols
            cx = col * cell + cell // 2
            cy = row * cell + (cell - caption_h) // 2

            with Image.open(disks[i]) as raw:
                disc = raw.convert("RGBA").resize((disc_size, disc_size), Image.LANCZOS)
            sheet.paste(disc, (cx - disc_size // 2, cy - disc_size // 2), disc)

            caption = captions[i] if captions and i < len(captions) else _caption_for(disks[i])
            bbox = draw.textbbox((0, 0), caption, font=font)
            tw = bbox[2] - bbox[0]
            draw.text((cx - tw / 2, row * cell + cell - caption_h),
                      caption, font=font, fill=(255, 255, 255, 255))
            reporter.advance("planche", 1)

        out = output_dir / f"planche{sheet_idx}.png"
        sheet.save(out)
        outputs.append(out)
        reporter.log(f"planche ready: {out.name}")

    reporter.remove("planche")
    return outputs
