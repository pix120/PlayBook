from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field, field_validator
from pathlib import Path


class AppConfig(BaseModel):
    library_paths: List[str] = Field(
        default_factory=lambda: [str(Path.home() / "Аудиокниги")],
        description="Список папок для сканирования аудиокниг.",
    )
    database_path: str = Field(
        default="data/playbook.db", description="Путь к файлу базы данных SQLite."
    )
    theme: str = Field(
        default="dark", description="Тема оформления: 'dark' или 'light'."
    )
    sleep_timer_default: int = Field(
        default=30, ge=0, le=120, description="Таймер сна по умолчанию (в минутах)."
    )

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: str) -> str:
        allowed = {"dark", "light"}
        if v.lower() not in allowed:
            raise ValueError(f"theme должен быть одним из {allowed}")
        return v.lower()

    def ensure_directories(self):
        """Создать родительские папки для базы данных, если их нет."""
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
