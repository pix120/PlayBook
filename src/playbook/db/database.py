from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import List, Optional

from .connection import get_connection
from ..models.book import Book, BookStatus

# ------------------------------------------------------------
# Миграции (создание/обновление таблиц)
# ------------------------------------------------------------

SCHEMA_VERSION = 1

INITIAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT 'Неизвестный автор',
    duration REAL NOT NULL DEFAULT 0.0,
    file_path TEXT NOT NULL UNIQUE,
    cover_path TEXT,
    status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new', 'started', 'finished')),
    progress REAL NOT NULL DEFAULT 0.0,
    last_played TEXT,
    date_added TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_books_status ON books(status);
CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
"""


def initialize_db() -> None:
    """
    создать таблицы если их нет.
    обновить при необходимости
    """
    with get_connection() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)"
        )
        current_version = conn.execute(
            "SELECT COALESCE(MAX(version), 0) FROM schema_version"
        ).fetchone()[0]
        if current_version < 1:
            conn.executescript(INITIAL_SCHEMA)
            conn.execute(
                "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )
            print("База данных создана/обновлена до версии 1.")


def _row_to_book(row: sqlite3.Row) -> Book:
    """Преобразовать строку БД в объект Book."""
    return Book(
        id=row["id"],
        title=row["title"],
        author=row["author"],
        duration=row["duration"],
        file_path=row["file_path"],
        cover_path=row["cover_path"],
        status=BookStatus(row["status"]),
        progress=row["progress"],
        last_played=(
            datetime.fromisoformat(row["last_played"]) if row["last_played"] else None
        ),
        date_added=datetime.fromisoformat(row["date_added"]),
    )


def add_book(book: Book) -> Book:
    """
    Добавить новую книгу в библиотеку.
    Возвращает объект Book с присвоенным id.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO books (
                title, author, duration, file_path, cover_path,
                status, progress, last_played, date_added
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                book.title,
                book.author,
                book.duration,
                book.file_path,
                book.cover_path,
                book.status.value,
                book.progress,
                book.last_played.isoformat() if book.last_played else None,
                book.date_added.isoformat(),
            ),
        )
        book.id = cursor.lastrowid
        return book


def get_book_by_id(book_id: int) -> Optional[Book]:
    """Найти книгу по id."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if row:
            return _row_to_book(row)
        return None


def get_book_by_path(file_path: str) -> Optional[Book]:
    """Найти книгу по пути к аудиофайлу."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM books WHERE file_path = ?", (file_path,)
        ).fetchone()
        if row:
            return _row_to_book(row)
        return None


def get_all_books(status: Optional[BookStatus] = None) -> List[Book]:
    """
    Получить список всех книг, опционально отфильтрованных по статусу.
    """
    with get_connection() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM books WHERE status = ? ORDER BY date_added DESC",
                (status.value,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM books ORDER BY date_added DESC"
            ).fetchall()
        return [_row_to_book(r) for r in rows]


def update_book(book: Book) -> None:
    """Обновить данные книги (по id)."""
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE books
            SET title = ?, author = ?, duration = ?, file_path = ?, cover_path = ?,
                status = ?, progress = ?, last_played = ?, date_added = ?
            WHERE id = ?
            """,
            (
                book.title,
                book.author,
                book.duration,
                book.file_path,
                book.cover_path,
                book.status.value,
                book.progress,
                book.last_played.isoformat() if book.last_played else None,
                book.date_added.isoformat(),
                book.id,
            ),
        )


def delete_book(book_id: int) -> bool:
    """Удалить книгу по id. Возвращает True, если удалено."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        return cursor.rowcount > 0


def update_progress(book_id: int, progress: float) -> None:
    """
    Обновить только прогресс и время последнего прослушивания.
    Это часто вызываемая операция, поэтому выделена отдельно для лёгкой оптимизации.
    """
    with get_connection() as conn:
        conn.execute(
            "UPDATE books SET progress = ?, last_played = ? WHERE id = ?",
            (progress, datetime.now().isoformat(), book_id),
        )
