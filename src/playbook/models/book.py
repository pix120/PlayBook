from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class BookStatus(str, Enum):
    """Статус книги в библиотеке"""

    NEW = "new"
    STARTED = "started"
    FINISHED = "finished"


class Book(BaseModel):
    """модель аудиокниги"""

    id: Optional[int] = None  # первичный ключ в БД, None для новых книг
    title: str
    author: str = "Неизвестный автор"
    duration: float = 0.0  # общая длительность в секундах
    file_path: str  # абсолютный путь к аудиофайлу
    cover_path: Optional[str] = None  # путь к обложке
    status: BookStatus = BookStatus.NEW
    progress: float = 0.0  # текущая позиция в секундах
    last_played: Optional[datetime] = None
    date_added: datetime = Field(default_factory=datetime.now)

    """ model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        }
    }"""
