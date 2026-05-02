from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

COVERS_DIR = Path("data/covers")


def save_cover(book_file_path: str, cover_data: bytes) -> Path:
    """Сохраняет бинарные данные обложки в файл."""
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    hash_digest = hashlib.md5(book_file_path.encode("utf-8")).hexdigest()
    cover_path = COVERS_DIR / f"{hash_digest}.jpg"
    cover_path.write_bytes(cover_data)
    return cover_path


def get_cover_path_or_none(cover_path: Optional[str]) -> Optional[str]:
    """Проверяет существование файла обложки."""
    if cover_path is None:
        return None
    path = Path(cover_path)
    return str(path) if path.exists() else None
