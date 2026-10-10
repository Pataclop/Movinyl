"""History database and the skip / re-process rules built on it.

No ffmpeg, C++ renderer or network needed: the heavy stages are monkeypatched.
"""
import sqlite3
from pathlib import Path

import pytest

from PIL import Image

from movinyl import barcode, engine, history, palette, tmdb
from movinyl.history import MovieInfo
from movinyl.progress import Reporter

INCEPTION = MovieInfo(tmdb_id=27205, title="Inception", original_title="Inception",
                      year=2010, director="Christopher Nolan", runtime=148)


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("MOVINYL_DB", str(tmp_path / "test.db"))


@pytest.fixture(autouse=True)
def fake_tmdb(monkeypatch):
    """No network: only Inception is "on TMDB"."""
    calls = []

    def lookup(title, year, key=None):
        calls.append(title)
        return INCEPTION if title == "Inception" else None

    monkeypatch.setattr(tmdb, "lookup", lookup)
    return calls


@pytest.fixture
def video(tmp_path):
    v = tmp_path / "videos" / "Inception_2010.mp4"
    v.parent.mkdir()
    v.write_bytes(b"x" * 100)
    return v


@pytest.fixture
def fake_render(monkeypatch):
    """Replace extraction + rendering; returns the list of rendered names."""
    rendered = []

    def extract(video, n, images_dir, *args, **kwargs):
        images_dir.mkdir(parents=True, exist_ok=True)

    def render(work_dir, *args, **kwargs):
        rendered.append(work_dir.name.split(".")[0])
        save = work_dir / "save.png"
        save.write_bytes(b"png")
        return save

    monkeypatch.setattr(engine, "extract_frames", extract)
    monkeypatch.setattr(engine, "normalize_frame_count", lambda *a, **k: None)
    monkeypatch.setattr(engine, "_mean_colors",
                        lambda d, n: [(i, i, i) for i in range(n)])
    monkeypatch.setattr(engine, "render_disk", render)
    return rendered


@pytest.fixture
def fake_page(monkeypatch):
    """Replace page composition; returns the list of disks composed."""
    composed = []

    def page(disk, output_dir, *args, **kwargs):
        composed.append(disk.stem)
        out = output_dir / f"{disk.stem}_page.png"
        out.write_bytes(b"page")
        history.record_page(disk.stem, out)
        return out

    monkeypatch.setattr(engine, "generate_page_for_disk", page)
    return composed


def disk(video, out_dir, overwrite=False):
    return engine.generate_disk_for_video(video, 10, out_dir, Reporter(),
                                          overwrite=overwrite)


# -- history module ---------------------------------------------------------

def test_record_and_query(video, tmp_path):
    assert not history.disk_done("Inception_2010")
    history.record_disk("Inception_2010", video, 2000, 1080, tmp_path / "a.png")
    film = history.get("Inception_2010")
    assert history.disk_done("Inception_2010")
    assert not history.page_done("Inception_2010")
    assert (film.video, film.video_size, film.frames) == ("Inception_2010.mp4", 100, 2000)

    history.record_page("Inception_2010", tmp_path / "a_page.png")
    assert history.page_done("Inception_2010")
    assert [f.name for f in history.all_films()] == ["Inception_2010"]


def test_new_disk_invalidates_page(video, tmp_path):
    history.record_disk("Inception_2010", video, 2000, 1080, tmp_path / "a.png")
    history.record_page("Inception_2010", tmp_path / "a_page.png")
    history.record_disk("Inception_2010", video, 3000, 1080, tmp_path / "a.png")
    assert not history.page_done("Inception_2010")


def test_adopting_a_disk_keeps_page(video, tmp_path):
    history.record_page("Inception_2010", tmp_path / "a_page.png")
    history.record_disk("Inception_2010", video, None, None, tmp_path / "a.png",
                        reset_page=False)
    assert history.page_done("Inception_2010")


def test_video_changed(video, tmp_path):
    assert not history.video_changed("Inception_2010", video)  # unknown film
    history.record_disk("Inception_2010", video, 2000, 1080, tmp_path / "a.png")
    assert not history.video_changed("Inception_2010", video)
    video.write_bytes(b"x" * 200)
    assert history.video_changed("Inception_2010", video)


def test_forget_and_clear(video, tmp_path):
    for name in ("A", "B"):
        history.record_disk(name, video, 10, 0, tmp_path / f"{name}.png")
    assert history.forget("A")
    assert not history.forget("A")
    assert history.clear() == 1
    assert history.all_films() == []


# -- disk stage -------------------------------------------------------------

def test_disk_is_rendered_once(video, tmp_path, fake_render):
    out_dir = video.parent
    assert disk(video, out_dir) == out_dir / "Inception_2010.png"
    assert disk(video, out_dir) == out_dir / "Inception_2010.png"  # exists
    assert fake_render == ["Inception_2010"]


def test_moved_disk_is_still_skipped(video, fake_render):
    out = disk(video, video.parent)
    out.rename(video.parent / "moved.png")
    assert disk(video, video.parent) is None
    assert fake_render == ["Inception_2010"]


def test_overwrite_rerenders(video, fake_render):
    disk(video, video.parent)
    disk(video, video.parent, overwrite=True)
    assert fake_render == ["Inception_2010", "Inception_2010"]


def test_changed_video_rerenders(video, fake_render):
    disk(video, video.parent)
    video.write_bytes(b"x" * 500)
    disk(video, video.parent)
    assert fake_render == ["Inception_2010", "Inception_2010"]


def test_existing_disk_is_adopted(video, fake_render):
    (video.parent / "Inception_2010.png").write_bytes(b"png")
    disk(video, video.parent)
    film = history.get("Inception_2010")
    assert fake_render == []
    assert film.disk_at and film.frames is None


# -- page stage -------------------------------------------------------------

def test_pages_skip_done_films(tmp_path, fake_page):
    for name in ("A", "B"):
        (tmp_path / f"{name}.png").write_bytes(b"png")
    engine.run_page_batch(tmp_path, jobs=1)
    assert sorted(fake_page) == ["A", "B"]

    assert engine.run_page_batch(tmp_path, jobs=1) == []
    assert sorted(fake_page) == ["A", "B"]

    engine.run_page_batch(tmp_path, jobs=1, overwrite=True)
    assert sorted(fake_page) == ["A", "A", "B", "B"]


def test_rerendered_disk_gets_a_new_page(video, fake_render, fake_page):
    out_dir: Path = video.parent
    disk(video, out_dir)
    engine.run_page_batch(out_dir, jobs=1)
    disk(video, out_dir, overwrite=True)
    engine.run_page_batch(out_dir, jobs=1)
    assert fake_page == ["Inception_2010", "Inception_2010"]


# -- film info, mean colors, schema -----------------------------------------

def test_disk_stores_info_and_colors(video, fake_render, fake_tmdb):
    disk(video, video.parent)
    film = history.get("Inception_2010")
    assert (film.tmdb_id, film.director, film.runtime) == (27205, "Christopher Nolan", 148)
    assert history.mean_colors("Inception_2010") == [(i, i, i) for i in range(10)]
    assert history.get_by_tmdb(27205).name == "Inception_2010"

    disk(video, video.parent, overwrite=True)  # known film: no second lookup
    assert fake_tmdb == ["Inception"]


def test_unknown_film_has_no_tmdb_id(tmp_path, fake_render):
    v = tmp_path / "Home_Movie.mp4"
    v.write_bytes(b"x")
    disk(v, tmp_path)
    film = history.get("Home_Movie")
    assert film.tmdb_id is None and film.disk_at
    assert len(history.mean_colors("Home_Movie")) == 10


def test_tmdb_id_stays_unique(video, tmp_path):
    history.record_info("Inception_2010", INCEPTION)
    history.record_info("Inception_2010_remux", INCEPTION)
    assert history.get("Inception_2010").tmdb_id == 27205
    assert history.get("Inception_2010_remux").tmdb_id is None


def test_forget_drops_colors(video, tmp_path):
    history.record_disk("A", video, 3, 0, tmp_path / "A.png",
                        colors=[(1, 2, 3)] * 3)
    assert history.forget("A")
    with sqlite3.connect(history.db_path()) as conn:
        assert conn.execute("SELECT COUNT(*) FROM mean_color").fetchone()[0] == 0


def test_v1_database_is_migrated(tmp_path):
    with sqlite3.connect(history.db_path()) as conn:
        conn.execute("""CREATE TABLE films (name TEXT PRIMARY KEY, video TEXT,
            video_size INTEGER, frames INTEGER, max_height INTEGER,
            disk_path TEXT, disk_at REAL, page_path TEXT, page_at REAL)""")
        conn.execute("INSERT INTO films VALUES ('Old_1999', 'o.mkv', 5, 2000, 1080,"
                     " 'o.png', 1.0, NULL, NULL)")
    film = history.get("Old_1999")
    assert (film.frames, film.disk_at, film.tmdb_id) == (2000, 1.0, None)
    history.record_colors("Old_1999", [(9, 9, 9)])
    assert history.mean_colors("Old_1999") == [(9, 9, 9)]


def test_frame_mean_color(tmp_path):
    Image.new("RGB", (64, 32), (200, 100, 50)).save(tmp_path / "1.jpg", quality=100)
    r, g, b = palette.frame_mean_colors(tmp_path, 1)[0]
    assert abs(r - 200) <= 2 and abs(g - 100) <= 2 and abs(b - 50) <= 2
    assert palette.frame_mean_color(tmp_path / "missing.jpg") == (0, 0, 0)


def test_redraw_from_colors(video, tmp_path):
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    history.record_colors("Inception_2010", colors)
    out = barcode.render_film("Inception_2010", "barcode", tmp_path / "b.png", height=4)
    with Image.open(out) as img:
        assert img.size == (3, 4) and img.getpixel((2, 0)) == (0, 0, 255)
    disc = barcode.render_disk(colors, size=60)
    assert disc.getpixel((1, 30)) == (255, 0, 0)    # outer ring = frame 1
    assert disc.getpixel((30, 30)) == (0, 0, 255)   # hub = last frame
    with pytest.raises(LookupError):
        barcode.render_film("Nope", out=tmp_path / "n.png")
