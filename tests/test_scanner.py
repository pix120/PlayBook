import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from playbook.db.connection import override_db_path_for_testing
from playbook.db.database import initialize_db, get_all_books, add_book
from playbook.models.book import Book, BookStatus
from playbook.scanner import (
    find_audio_files,
    extract_metadata,
    scan_and_update_library,
)


@pytest.fixture(autouse=True)
def setup_test_db():
    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp_db_path = Path(tmp_db.name)
    tmp_db.close()

    override_db_path_for_testing(tmp_db_path)
    initialize_db()
    yield
    override_db_path_for_testing(None)
    tmp_db_path.unlink()


def test_find_audio_files_skips_missing_and_collects(tmp_path):
    missing = tmp_path / "nope"
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "a.mp3").write_bytes(b"\x00")
    (lib / "readme.txt").write_text("x")
    sub = lib / "sub"
    sub.mkdir()
    (sub / "b.flac").write_bytes(b"\x00")

    found = sorted(find_audio_files([missing, lib]))
    assert {p.name for p in found} == {"a.mp3", "b.flac"}


def test_extract_metadata_mutagen_errors():
    with patch("playbook.scanner.mutagen.File", side_effect=OSError("x")):
        meta = extract_metadata(Path("/some/book.mp3"))
    assert meta["title"] == "book"
    assert meta["duration"] == 0.0


def test_extract_metadata_none_audio():
    with patch("playbook.scanner.mutagen.File", return_value=None):
        meta = extract_metadata(Path("/x/named_file.m4a"))
    assert meta["title"] == "named_file"


def test_scan_adds_new_books():
    fake_paths = [Path("/fake/book1.mp3"), Path("/fake/book2.m4b")]
    with (
        patch("playbook.scanner.find_audio_files", return_value=fake_paths),
        patch("playbook.scanner.extract_metadata") as mock_extract,
    ):
        mock_extract.side_effect = lambda p: {
            "title": p.stem.capitalize(),
            "author": "Test Author",
            "duration": 100.0,
            "cover_data": None,
        }

        events = list(scan_and_update_library([Path("/fake")]))

    assert events[-1]["type"] == "finished"
    assert events[-1]["added"] == 1
    assert events[-1]["updated"] == 0

    books = get_all_books()
    assert len(books) == 1
    assert books[0].title == "fake"
    assert books[0].duration == 200.0


def test_scan_updates_existing_book_with_cover(tmp_path):
    # Создаём существующую книгу в БД с file_path = папка tmp_path
    add_book(
        Book(
            title="Old Title",
            author="Old Author",
            duration=50.0,
            file_path=str(tmp_path),  # используем реальную папку
            status=BookStatus.STARTED,
            progress=10.0,
        )
    )

    # В папке создаём реальный файл, чтобы find_audio_files его нашёл
    test_file = tmp_path / "existing.mp3"
    test_file.write_bytes(b"dummy audio")

    # Мокаем только extract_metadata и save_cover
    with (
        patch("playbook.scanner.extract_metadata") as mock_extract,
        patch("playbook.scanner.save_cover") as mock_save,
    ):
        mock_extract.return_value = {
            "title": "New Title",
            "author": "New Author",
            "duration": 200.0,
            "cover_data": b"fake",
        }
        mock_save.return_value = tmp_path / "cover/saved.jpg"

        events = list(scan_and_update_library([tmp_path]))

    assert events[-1]["added"] == 0
    assert events[-1]["updated"] == 1

    book = get_all_books()[0]
    assert book.title == tmp_path.name  # имя папки tmp_path (случайное)
    assert book.author == "New Author"
    assert book.duration == 200.0
    assert book.status == BookStatus.STARTED
    assert book.progress == 10.0
    assert book.cover_path == str(tmp_path / "cover/saved.jpg")
    mock_save.assert_called_once_with(str(test_file), b"fake")


def test_scan_save_cover_failure_still_updates(monkeypatch, tmp_path):
    add_book(
        Book(
            title="T",
            author="A",
            duration=1.0,
            file_path=str(tmp_path),
            status=BookStatus.NEW,
        )
    )
    fp = tmp_path / "t.mp3"
    fp.write_bytes(b"\x00")

    with (
        patch("playbook.scanner.extract_metadata") as mock_extract,
        patch("playbook.scanner.save_cover", side_effect=RuntimeError("disk full")),
    ):
        mock_extract.return_value = {
            "title": "T2",
            "author": "A2",
            "duration": 2.0,
            "cover_data": b"x",
        }
        list(scan_and_update_library([tmp_path]))

    book = get_all_books()[0]
    assert book.title == tmp_path.name
    assert book.cover_path is None


def test_scan_handles_missing_folder():
    events = list(scan_and_update_library([Path("/nonexistent")]))
    assert len(events) == 1
    assert events[0]["type"] == "finished"
    assert events[0]["added"] == 0
    assert events[0]["updated"] == 0
