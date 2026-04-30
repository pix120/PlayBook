import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from playbook.db.connection import override_db_path_for_testing
from playbook.db.database import (
    initialize_db,
    add_book,
    get_book_by_id,
    get_book_by_path,
    get_all_books,
    update_book,
    delete_book,
    update_progress,
)
from playbook.models.book import Book, BookStatus


@pytest.fixture(autouse=True)
def setup_test_db():
    """Перед каждым тестом создаём временную БД и инициализируем таблицы."""
    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp_db_path = Path(tmp_db.name)
    tmp_db.close()  # закрываем, чтобы SQLite мог открыть

    override_db_path_for_testing(tmp_db_path)
    initialize_db()
    yield
    override_db_path_for_testing(None)
    # Удаляем временный файл после теста
    tmp_db_path.unlink()


@pytest.fixture
def sample_book():
    return Book(
        title="Тестовая книга",
        author="Автор",
        duration=3600.0,
        file_path="/path/to/book.mp3",
        cover_path="/path/to/cover.jpg",
        status=BookStatus.NEW,
        progress=0.0,
        date_added=datetime.now(),
    )


def test_add_and_get_book(sample_book):
    """Добавляем книгу и проверяем, что её можно получить по id."""
    added = add_book(sample_book)
    assert added.id is not None

    fetched = get_book_by_id(added.id)
    assert fetched is not None
    assert fetched.title == sample_book.title
    assert fetched.file_path == sample_book.file_path
    assert fetched.status == BookStatus.NEW


def test_get_book_by_path(sample_book):
    add_book(sample_book)
    fetched = get_book_by_path(sample_book.file_path)
    assert fetched is not None
    assert fetched.author == "Автор"


def test_get_all_books_filtered(sample_book):
    add_book(sample_book)
    # Добавим ещё одну книгу со статусом FINISHED
    finished_book = Book(
        title="Завершённая",
        author="Другой",
        duration=1800.0,
        file_path="/path/to/finished.mp3",
        status=BookStatus.FINISHED,
        date_added=datetime.now(),
    )
    add_book(finished_book)

    new_books = get_all_books(status=BookStatus.NEW)
    assert len(new_books) == 1
    assert new_books[0].status == BookStatus.NEW

    all_books = get_all_books()
    assert len(all_books) == 2


def test_update_book(sample_book):
    added = add_book(sample_book)
    added.title = "Обновлённое название"
    added.status = BookStatus.STARTED
    update_book(added)

    fetched = get_book_by_id(added.id)
    assert fetched.title == "Обновлённое название"
    assert fetched.status == BookStatus.STARTED


def test_delete_book(sample_book):
    added = add_book(sample_book)
    assert delete_book(added.id) is True
    assert get_book_by_id(added.id) is None
    # Повторное удаление должно вернуть False
    assert delete_book(added.id) is False


def test_update_progress(sample_book):
    added = add_book(sample_book)
    update_progress(added.id, 125.5)

    fetched = get_book_by_id(added.id)
    assert fetched.progress == 125.5
    assert fetched.last_played is not None
    # Проверим, что last_played примерно сейчас (разница не более 2 секунд)
    assert (datetime.now() - fetched.last_played) < timedelta(seconds=2)


def test_unique_file_path_constraint(sample_book):
    add_book(sample_book)
    duplicate = Book(
        title="Дубликат",
        author="Кто-то",
        duration=100.0,
        file_path=sample_book.file_path,  # тот же путь!
        status=BookStatus.NEW,
        date_added=datetime.now(),
    )
    with pytest.raises(Exception):  # SQLite выбросит IntegrityError
        add_book(duplicate)
