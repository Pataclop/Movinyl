"""Movinyl film database (SQLite): what was processed, what the film is, and
the mean color of every sampled frame.

Two tables:

``films``
    One row per film. ``id`` is the stable internal key; ``tmdb_id`` is the
    film's universal identifier on TMDB (unique, NULL until a lookup succeeds).
    ``name`` is the sanitized stem shared by the disk PNG and the page PNG, which
    is how the pipeline finds a film. The row also stores the TMDB metadata
    (title, year, director, runtime) and the processing state of each stage.

``mean_color``
    One row per sampled frame: ``(film_id, frame, r, g, b)``, frame 1 being the
    start of the movie. That is enough to redraw the film as a barcode or as a
    disk of flat rings without the video (see :mod:`movinyl.barcode`).

The database lives in ``data/movinyl.db`` at the project root (tracked in git);
set ``MOVINYL_DB`` to put it elsewhere. Every call opens its own short-lived
connection, so the module is safe to use from the page worker pool.
"""
from __future__ import annotations

import os
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from . import platforminfo as pf

RGB = Tuple[int, int, int]

SCHEMA_VERSION = 2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS films (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tmdb_id         INTEGER UNIQUE,
    name            TEXT NOT NULL UNIQUE,
    title           TEXT,
    original_title  TEXT,
    year            INTEGER,
    director        TEXT,
    runtime         INTEGER,
    video           TEXT,
    video_size      INTEGER,
    frames          INTEGER,
    max_height      INTEGER,
    disk_path       TEXT,
    disk_at         REAL,
    page_path       TEXT,
    page_at         REAL
);
CREATE TABLE IF NOT EXISTS mean_color (
    film_id  INTEGER NOT NULL REFERENCES films(id) ON DELETE CASCADE,
    frame    INTEGER NOT NULL,
    r        INTEGER NOT NULL,
    g        INTEGER NOT NULL,
    b        INTEGER NOT NULL,
    PRIMARY KEY (film_id, frame)
) WITHOUT ROWID;
"""

_FILM_COLUMNS = ("id", "tmdb_id", "name", "title", "original_title", "year",
                 "director", "runtime", "video", "video_size", "frames",
                 "max_height", "disk_path", "disk_at", "page_path", "page_at")


@dataclass
class Film:
    id: int
    tmdb_id: Optional[int]
    name: str
    title: Optional[str]
    original_title: Optional[str]
    year: Optional[int]
    director: Optional[str]
    runtime: Optional[int]
    video: Optional[str]
    video_size: Optional[int]
    frames: Optional[int]
    max_height: Optional[int]
    disk_path: Optional[str]
    disk_at: Optional[float]
    page_path: Optional[str]
    page_at: Optional[float]


@dataclass
class MovieInfo:
    """Film metadata, as returned by a TMDB lookup."""
    tmdb_id: Optional[int] = None
    title: Optional[str] = None
    original_title: Optional[str] = None
    year: Optional[int] = None
    director: Optional[str] = None
    runtime: Optional[int] = None


def db_path() -> Path:
    env = os.environ.get("MOVINYL_DB")
    return Path(env) if env else pf.PROJECT_ROOT / "data" / "movinyl.db"


def _create_tables(conn: sqlite3.Connection) -> None:
    for stmt in _SCHEMA.split(";"):
        if stmt.strip():
            conn.execute(stmt)


def _migrate_v1(conn: sqlite3.Connection) -> None:
    """v1 had a single ``films`` table keyed by ``name``: keep its rows."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(films)")}
    if not cols or "id" in cols:
        return
    conn.execute("ALTER TABLE films RENAME TO films_v1")
    _create_tables(conn)
    conn.execute(
        """INSERT INTO films (name, video, video_size, frames, max_height,
                              disk_path, disk_at, page_path, page_at)
           SELECT name, video, video_size, frames, max_height,
                  disk_path, disk_at, page_path, page_at
           FROM films_v1 ORDER BY name""")
    conn.execute("DROP TABLE films_v1")


def _upgrade(conn: sqlite3.Connection) -> None:
    """Create or migrate the schema once, under a write lock (workers race)."""
    conn.isolation_level = None
    conn.execute("BEGIN IMMEDIATE")
    try:
        if conn.execute("PRAGMA user_version").fetchone()[0] < SCHEMA_VERSION:
            _migrate_v1(conn)
            _create_tables(conn)
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.isolation_level = ""


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30)
    conn.execute("PRAGMA foreign_keys = ON")
    if conn.execute("PRAGMA user_version").fetchone()[0] < SCHEMA_VERSION:
        _upgrade(conn)
    return conn


_SELECT = f"SELECT {', '.join(_FILM_COLUMNS)} FROM films"


def get(name: str) -> Optional[Film]:
    with closing(_connect()) as conn:
        row = conn.execute(f"{_SELECT} WHERE name = ?", (name,)).fetchone()
    return Film(*row) if row else None


def get_by_tmdb(tmdb_id: int) -> Optional[Film]:
    with closing(_connect()) as conn:
        row = conn.execute(f"{_SELECT} WHERE tmdb_id = ?", (tmdb_id,)).fetchone()
    return Film(*row) if row else None


def all_films() -> List[Film]:
    with closing(_connect()) as conn:
        rows = conn.execute(f"{_SELECT} ORDER BY name").fetchall()
    return [Film(*r) for r in rows]


# Processing-state filters for :func:`search` (key -> SQL condition).
STATUS_FILTERS = {
    "all": "1",
    "disk": "disk_at IS NOT NULL",
    "page": "page_at IS NOT NULL",
    "no_page": "disk_at IS NOT NULL AND page_at IS NULL",
    "colors": "EXISTS (SELECT 1 FROM mean_color WHERE film_id = films.id)",
    "no_tmdb": "tmdb_id IS NULL",
}


def search(text: str = "", director: Optional[str] = None,
           year_from: Optional[int] = None, year_to: Optional[int] = None,
           status: str = "all") -> List[Film]:
    """Films matching every given filter, ordered by title.

    ``text`` is a case-insensitive substring of the name, title, original title
    or director. Films with an unknown year are dropped by any year bound.
    """
    where, args = [STATUS_FILTERS[status]], []
    if text.strip():
        where.append("(name LIKE ? OR title LIKE ? OR original_title LIKE ?"
                     " OR director LIKE ?)")
        args += [f"%{text.strip()}%"] * 4
    if director:
        where.append("director = ?")
        args.append(director)
    if year_from is not None:
        where.append("year >= ?")
        args.append(year_from)
    if year_to is not None:
        where.append("year <= ?")
        args.append(year_to)
    with closing(_connect()) as conn:
        rows = conn.execute(
            f"{_SELECT} WHERE {' AND '.join(where)}"
            " ORDER BY COALESCE(title, name) COLLATE NOCASE", args).fetchall()
    return [Film(*r) for r in rows]


def directors() -> List[str]:
    """Every known director, alphabetically."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT DISTINCT director FROM films WHERE director IS NOT NULL"
            " ORDER BY director COLLATE NOCASE").fetchall()
    return [r[0] for r in rows]


def disk_done(name: str) -> bool:
    film = get(name)
    return film is not None and film.disk_at is not None


def page_done(name: str) -> bool:
    film = get(name)
    return film is not None and film.page_at is not None


def video_changed(name: str, video: Path) -> bool:
    """True if ``video`` differs (by size) from the file the disk was made from.

    Lets a better copy of a film saved under the same name get re-processed.
    Unknown sizes never count as a change.
    """
    film = get(name)
    if film is None or film.video_size is None:
        return False
    try:
        return video.stat().st_size != film.video_size
    except OSError:
        return False


def _ensure(conn: sqlite3.Connection, name: str) -> int:
    """Return the ``films.id`` of ``name``, creating an empty row if needed."""
    conn.execute("INSERT OR IGNORE INTO films (name) VALUES (?)", (name,))
    return conn.execute("SELECT id FROM films WHERE name = ?", (name,)).fetchone()[0]


def record_disk(name: str, video: Path, frames: Optional[int],
                max_height: Optional[int], disk_path: Path,
                reset_page: bool = True,
                colors: Optional[Sequence[RGB]] = None) -> None:
    """Record a disk, and the mean color of each of its frames if given.

    A freshly rendered disk (``reset_page``) invalidates the film's page so the
    next ``page`` run rebuilds it from the new disk.
    """
    try:
        size = video.stat().st_size
    except OSError:
        size = None
    page_reset = (", page_path = NULL, page_at = NULL" if reset_page else "")
    with closing(_connect()) as conn, conn:
        film_id = _ensure(conn, name)
        conn.execute(
            f"""UPDATE films SET video = ?, video_size = ?, frames = ?,
                    max_height = ?, disk_path = ?, disk_at = ? {page_reset}
                WHERE id = ?""",
            (video.name, size, frames, max_height, str(disk_path), time.time(),
             film_id),
        )
        if colors is not None:
            _write_colors(conn, film_id, colors)


def record_page(name: str, page_path: Path) -> None:
    with closing(_connect()) as conn, conn:
        film_id = _ensure(conn, name)
        conn.execute("UPDATE films SET page_path = ?, page_at = ? WHERE id = ?",
                     (str(page_path), time.time(), film_id))


def record_info(name: str, info: MovieInfo) -> None:
    """Store TMDB metadata for ``name``.

    If another row already owns that ``tmdb_id`` (same film under another file
    name), the id is left unset here rather than breaking its uniqueness.
    """
    with closing(_connect()) as conn, conn:
        film_id = _ensure(conn, name)
        tmdb_id = info.tmdb_id
        if tmdb_id is not None:
            owner = conn.execute("SELECT id FROM films WHERE tmdb_id = ?",
                                 (tmdb_id,)).fetchone()
            if owner is not None and owner[0] != film_id:
                tmdb_id = None
        conn.execute(
            """UPDATE films SET tmdb_id = COALESCE(?, tmdb_id), title = ?,
                   original_title = ?, year = ?, director = ?, runtime = ?
               WHERE id = ?""",
            (tmdb_id, info.title, info.original_title, info.year, info.director,
             info.runtime, film_id),
        )


def _write_colors(conn: sqlite3.Connection, film_id: int,
                  colors: Sequence[RGB]) -> None:
    conn.execute("DELETE FROM mean_color WHERE film_id = ?", (film_id,))
    conn.executemany(
        "INSERT INTO mean_color (film_id, frame, r, g, b) VALUES (?, ?, ?, ?, ?)",
        ((film_id, i, r, g, b) for i, (r, g, b) in enumerate(colors, start=1)),
    )


def record_colors(name: str, colors: Sequence[RGB]) -> None:
    """Replace the per-frame mean colors of ``name`` (frame 1 first)."""
    with closing(_connect()) as conn, conn:
        _write_colors(conn, _ensure(conn, name), colors)


def mean_colors(name: str) -> List[RGB]:
    """Per-frame mean colors of ``name`` in movie order (empty if unknown)."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            """SELECT r, g, b FROM mean_color
               JOIN films ON films.id = mean_color.film_id
               WHERE films.name = ? ORDER BY frame""", (name,)).fetchall()
    return [tuple(r) for r in rows]


def forget(name: str) -> bool:
    """Drop a film (and its colors) from the database. True if it was there."""
    with closing(_connect()) as conn, conn:
        cur = conn.execute("DELETE FROM films WHERE name = ?", (name,))
    return cur.rowcount > 0


def clear() -> int:
    """Drop every film from the database. Returns how many rows were removed."""
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM mean_color")
        cur = conn.execute("DELETE FROM films")
    return cur.rowcount
