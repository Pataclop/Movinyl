"""Desktop window: settings, library views, jobs and helpers.

Runs Qt offscreen and is skipped without PyQt6. No ffmpeg, C++ renderer or
network needed: the engine is monkeypatched where a job would run.
"""
import os
import time

import pytest

pytest.importorskip("PyQt6.QtWidgets")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QCoreApplication, QEvent, QMimeData, QPointF, Qt, QUrl  # noqa: E402
from PyQt6.QtGui import QColor, QDropEvent, QImage  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from movinyl import engine, gui, history  # noqa: E402
from movinyl.history import MovieInfo  # noqa: E402

INCEPTION = MovieInfo(tmdb_id=27205, title="Inception", original_title="Inception",
                      year=2010, director="Christopher Nolan", runtime=148)


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("MOVINYL_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("MOVINYL_SETTINGS", str(tmp_path / "settings.ini"))
    monkeypatch.setenv("MOVINYL_CACHE", str(tmp_path / "cache"))
    return tmp_path


@pytest.fixture
def window(qapp, env):
    win = gui.MainWindow()
    yield win
    win._busy = False
    win.close()


def wait_until(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < deadline, "timed out"
        QCoreApplication.processEvents()
        time.sleep(0.01)


def add_film(env, name="Inception_2010", info=INCEPTION, colors=None, disk=False):
    video = env / f"{name}.mkv"
    video.write_bytes(b"x")
    disk_path = env / f"{name}.png"
    if disk:
        QImage(40, 40, QImage.Format.Format_RGB32).save(str(disk_path))
    history.record_disk(name, video, 3, 1080, disk_path,
                        colors=colors or [(200, 0, 0), (0, 200, 0), (0, 0, 200)])
    if info is not None:
        history.record_info(name, info)
    return history.get(name)


# -- helpers ---------------------------------------------------------------

def test_durations():
    assert gui._human_duration(42) == "42 s"
    assert gui._human_duration(185) == "3 min 05 s"
    assert gui._human_duration(4020) == "1 h 07 min"
    assert gui._eta_text(42) == "40 s"
    assert gui._eta_text(250) == "4 min"


def test_ring_and_round_images(qapp):
    rings = gui._ring_image([(255, 0, 0), (0, 0, 255)], 40)
    assert rings.pixelColor(2, 20) == QColor(255, 0, 0)      # frame 1 outermost
    assert rings.pixelColor(20, 20) == QColor(0, 0, 255)     # last frame at the hub
    assert rings.pixelColor(0, 0).alpha() == 0               # round, not square

    square = QImage(40, 40, QImage.Format.Format_ARGB32_Premultiplied)
    square.fill(QColor(0, 255, 0))
    disk = gui._round_image(square, 0.5)
    assert disk.pixelColor(20, 20) == QColor(0, 255, 0)
    assert disk.pixelColor(3, 20).alpha() == 0                # outside the disk


# -- settings --------------------------------------------------------------

def test_settings_are_remembered(qapp, env):
    videos = env / "videos"
    videos.mkdir()
    win = gui.MainWindow()
    win.video_dir.edit.setText(str(videos))
    win.frames.setValue(500)
    win.mean_colors.setChecked(True)
    win.then_pages.setChecked(True)
    win.library.set_gallery(True)
    win.tabs.setCurrentIndex(1)
    win.close()                                                # saves

    again = gui.MainWindow()
    assert again.video_dir.path() == videos
    assert again.disk_dir.path() == gui.DEFAULT_PAGE
    assert again.frames.value() == 500
    assert again.mean_colors.isChecked() and again.then_pages.isChecked()
    assert again.ask_tmdb.isChecked() and not again.overwrite.isChecked()
    assert again.library.is_gallery() and again.tabs.currentIndex() == 1
    again.close()
    # Default folders are not pinned: a moved install keeps working.
    assert "disks" not in (env / "settings.ini").read_text()


# -- library ---------------------------------------------------------------

def test_details_follow_the_selection(window, env):
    film = add_film(env)
    add_film(env, "Home_Movie", info=None)
    window.refresh_lists()
    lib = window.library
    assert lib.shown() == 2

    lib.table.selectRow(0)                                     # sorted by title
    assert [f.name for f in lib.selected()] == ["Home_Movie"]
    lib.table.selectRow(1)
    assert [f.name for f in lib.selected()] == ["Inception_2010"]
    assert lib.details.title.text() == "Inception"
    assert "Christopher Nolan" in lib.details.meta.text()
    assert "27205" in lib.details.meta.text()                  # TMDB link

    lib.table.selectAll()
    assert lib.details.title.text() == "2 films"
    assert "2 h 28 min of cinema" in lib.details.meta.text()

    # No disk file: the thumbnail is drawn from the stored mean colors.
    wait_until(lambda: window.thumbs.get(film) is not None)
    assert not window.thumbs.get(film).isNull()


def test_gallery_keeps_the_selection(window, env):
    add_film(env)
    add_film(env, "Amelie_2001", MovieInfo(194, "Amélie", year=2001))
    window.refresh_lists()
    lib = window.library
    lib.table.selectRow(1)                                     # Inception
    lib.set_gallery(True)
    assert lib.is_gallery() and lib.grid.count() == 2
    assert [f.name for f in lib.selected()] == ["Inception_2010"]
    assert lib.grid.item(0).text() == "Amélie (2001)"

    lib.grid.item(0).setSelected(True)
    lib.set_gallery(False)
    assert [f.name for f in lib.selected()] == ["Amelie_2001", "Inception_2010"]


def test_thumbnail_of_a_disk_png_is_cached(window, env):
    film = add_film(env, disk=True)
    wait_until(lambda: window.thumbs.get(film) is not None)
    pix = window.thumbs.get(film)
    assert pix.width() == gui.Thumbnails.SIZE
    assert list((env / "cache" / "thumbs").glob("*.png"))


def test_open_film_without_files_logs(window, env):
    film = add_film(env)
    window.open_film(film)
    assert "no disk or page file" in window.log.toPlainText()


# -- jobs ------------------------------------------------------------------

def test_disks_then_pages(window, env, monkeypatch):
    disks = [env / "A.png", env / "B.png"]
    calls = {}

    def disk_batch(vdir, **kwargs):
        calls["batch"] = kwargs
        history.record_page("B", env / "B_page.png")           # B already has a page
        return disks

    def pages(todo, out, **kwargs):
        calls["pages"] = (todo, out)
        return todo

    monkeypatch.setattr(engine, "run_disk_batch", disk_batch)
    monkeypatch.setattr(engine, "run_pages", pages)
    window.then_pages.setChecked(True)
    window.action_disks()
    wait_until(lambda: not window._busy)
    assert calls["pages"] == ([env / "A.png"], window.disk_dir.path())
    assert "1 page(s)" in window.log.toPlainText()
    assert calls["batch"]["overwrite"] is False


def test_selected_videos_are_rendered_again(window, env, monkeypatch):
    seen = {}

    def run_disks(videos, out, **kwargs):
        seen.update(videos=videos, overwrite=kwargs["overwrite"])
        return []

    monkeypatch.setattr(engine, "run_disks", run_disks)
    video = env / "Inception_2010.mkv"
    window.action_selected_disks([video])
    wait_until(lambda: not window._busy)
    assert seen == {"videos": [video], "overwrite": True}


def test_progress_shows_eta_and_title(window):
    window._busy = True
    reporter = window.reporter
    reporter.task("overall", "Disks", 4)
    reporter.advance("overall", 1)
    assert window.windowTitle() == "25% · Movinyl"
    reporter.task("extract", "Extracting frames", 100)
    window._bar_started["extract"] -= 60                      # a minute in
    reporter.update("extract", completed=50)
    assert window.windowTitle() == "31% · Movinyl"            # (1 + 0.5 / 2) / 4
    assert window._bars["extract"].format().endswith("1 min left")
    reporter.remove("extract")
    assert window._bars["extract"].format() == ""


# -- folders ---------------------------------------------------------------

def test_dropping_a_file_uses_its_folder(window, env):
    video = env / "drop" / "Film_2001.mkv"
    video.parent.mkdir()
    video.write_bytes(b"x")
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(video))])
    target = window.videos_list.viewport()
    for kind in (QEvent.Type.DragEnter, QEvent.Type.Drop):
        event = QDropEvent(QPointF(5, 5), Qt.DropAction.CopyAction, mime,
                           Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                           kind)
        QApplication.sendEvent(target, event)
        assert event.isAccepted()
    assert window.video_dir.path() == video.parent
    assert window.videos_list.count() == 1


def test_file_lists_refresh_by_themselves(window, env):
    folder = env / "watched"
    folder.mkdir()
    window._use_folder(window.video_dir, folder)
    assert window.videos_list.count() == 0
    (folder / "New_Film_2024.mp4").write_bytes(b"x")
    wait_until(lambda: window.videos_list.count() == 1)
