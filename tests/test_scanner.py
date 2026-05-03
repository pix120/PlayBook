import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from playbook.db.connection import override_db_path_for_testing
from playbook.db.database import initialize_db, get_all_books, add_book
from playbook.models.book import Book, BookStatus
from playbook.scanner import scan_and_update_library


@pytest.fixture(autouse=True)
def setup_test_db():
    """Перед каждым тестом создаём временную БД и инициализируем таблицы."""
    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp_db_path = Path(tmp_db.name)
    tmp_db.close()

    override_db_path_for_testing(tmp_db_path)
    initialize_db()
    yield
    override_db_path_for_testing(None)
    tmp_db_path.unlink()


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

    # Последнее событие должно быть finished с 2 добавленными
    assert events[-1]["type"] == "finished"
    assert events[-1]["added"] == 2
    assert events[-1]["updated"] == 0

    books = get_all_books()
    assert len(books) == 2
    titles = {b.title for b in books}
    assert titles == {"Book1", "Book2"}


def test_scan_updates_existing_book():
    # Добавляем книгу вручную
    existing = add_book(
        Book(
            title="Old Title",
            author="Old Author",
            duration=50.0,
            file_path="/fake/existing.mp3",
            status=BookStatus.STARTED,
            progress=10.0,
        )
    )

    fake_paths = [Path("/fake/existing.mp3")]
    with (
        patch("playbook.scanner.find_audio_files", return_value=fake_paths),
        patch("playbook.scanner.extract_metadata") as mock_extract,
    ):
        mock_extract.return_value = {
            "title": "New Title",
            "author": "New Author",
            "duration": 200.0,
            "cover_data": b"fake",
        }
        events = list(scan_and_update_library([Path("/fake")]))

    assert events[-1]["added"] == 0
    assert events[-1]["updated"] == 1

    book = get_all_books()[0]
    assert book.title == "New Title"
    assert book.author == "New Author"
    assert book.duration == 200.0
    assert book.status == BookStatus.STARTED
    assert book.progress == 10.0
    assert book.cover_path == "embedded"


def test_scan_handles_missing_folder():
    events = list(scan_and_update_library([Path("/nonexistent")]))
    # Если реальная папка не существует, find_audio_files ничего не вернёт
    # Ожидаем только финальное событие
    assert len(events) == 1
    assert events[0]["type"] == "finished"
    assert events[0]["added"] == 0
    assert events[0]["updated"] == 0


def test_scan_updates_existing_book(monkeypatch):
    # monkeypatch уже есть в импортах; если нет, добавь 'import monkeypatch' не нужно,
    # monkeypatch передаётся как аргумент фикстуры.
    # Но в текущем файле тестов monkeypatch не используется как фикстура.
    # Лучше сделаем так:
    import playbook.scanner as scanner_module

    # Добавим книгу в БД заранее
    from playbook.db.database import add_book

    existing = add_book(
        Book(
            title="Old Title",
            author="Old Author",
            duration=50.0,
            file_path="/fake/existing.mp3",
            status=BookStatus.STARTED,
            progress=10.0,
        )
    )

    fake_paths = [Path("/fake/existing.mp3")]
    with (
        patch.object(scanner_module, "find_audio_files", return_value=fake_paths),
        patch.object(scanner_module, "extract_metadata") as mock_extract,
        patch.object(scanner_module, "save_cover") as mock_save,
    ):
        mock_extract.return_value = {
            "title": "New Title",
            "author": "New Author",
            "duration": 200.0,
            "cover_data": b"fake",
        }
        mock_save.return_value = Path("/fake/cover/saved.jpg")

        events = list(scan_and_update_library([Path("/fake")]))

    assert events[-1]["added"] == 0
    assert events[-1]["updated"] == 1

    # Проверим, что статус и прогресс сохранились, а метаданные обновились
    book = get_all_books()[0]
    assert book.title == "New Title"
    assert book.author == "New Author"
    assert book.duration == 200.0
    assert book.status == BookStatus.STARTED
    assert book.progress == 10.0
    # Обложка должна быть путём, который вернул save_cover
    assert book.cover_path == "/fake/cover/saved.jpg"
    mock_save.assert_called_once_with("/fake/existing.mp3", b"fake")
