import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator, Optional

DEFAULT_DB_PATH = Path("data/playbook.db")
_override_db_path: Optional[Path] = None


def set_db_path(path: Path) -> None:
    """установить глобальный путь к файлу БД."""
    global DEFAULT_DB_PATH
    DEFAULT_DB_PATH = path


def override_db_path_for_testing(path: Optional[Path]) -> None:
    """Test helper: set DB path used by get_connection."""
    global _override_db_path
    _override_db_path = path


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    db_path = _override_db_path if _override_db_path is not None else DEFAULT_DB_PATH
    if db_path == Path(":memory:"):
        # in-memory база
        conn = sqlite3.connect(":memory:")
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
