from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from pathlib import Path


class AppConfig(BaseModel):
    """
    Конфигурация приложения PlayBook.
    Все поля имеют значения по умолчанию, чтобы при первом запуске
    приложение могло работать без файла конфигурации.
    """

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

    @field_validator("library_paths")
    @classmethod
    def validate_paths_exist(cls, v: List[str]) -> List[str]:
        # Не требуем обязательного существования, чтобы можно было настроить позже
        # Но если путь указан и не существует, можно предупредить (логирование).
        # Пока просто возвращаем как есть.
        return v

    def ensure_directories(self):
        """Создать необходимые папки (например, для базы данных)."""
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
