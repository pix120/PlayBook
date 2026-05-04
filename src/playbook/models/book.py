from __future__ import annotations

from datetime import datetime
from enum import Enum
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

    @property
    def progress_percent(self) -> float:
        if self.duration > 0:
            return min(100.0, max(0.0, (self.progress / self.duration) * 100.0))
        return 0.0

    @property
    def duration_str(self) -> str:
        return self._format_time(self.duration)

    @property
    def progress_str(self) -> str:
        return self._format_time(self.progress)

    @staticmethod
    def _format_time(seconds: float) -> str:
        if seconds < 0:
            seconds = 0
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
