import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

DEFAULT_DB_PATH = Path("data/playbook.db")


def set_db_path(path: Path) -> None:
    """установить глобальный путь к файлу БД."""
    global DEFAULT_DB_PATH
    DEFAULT_DB_PATH = path


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Контекстный менеджер для получения соединения с БД.
    Автоматически создает родительские директории для файла.
    """

    db_path = DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # улучшение производительности
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
