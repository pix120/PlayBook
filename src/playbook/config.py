from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from .models.config import AppConfig

# Путь к встроенным настройкам (внутри пакета)
DEFAULT_CONFIG_PATH = (
    Path(__file__).parent.parent.parent / "config" / "default_config.json"
)
# Путь, куда пользовательские настройки будут сохраняться
USER_CONFIG_PATH = Path("config/user_config.json")

# Глобальный экземпляр конфигурации (синглтон)
_config: Optional[AppConfig] = None


def _load_default_config() -> dict:
    """Загрузить конфигурацию по умолчанию из файла пакета."""
    if DEFAULT_CONFIG_PATH.exists():
        with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    # Если файла нет, возвращаем пустой словарь — AppConfig сам подставит дефолты
    return {}


def _load_user_config() -> dict:
    """Загрузить пользовательские настройки из JSON."""
    if USER_CONFIG_PATH.exists():
        with open(USER_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_config() -> AppConfig:
    """
    Получить текущую конфигурацию.
    При первом вызове объединяет дефолтные и пользовательские настройки.
    """
    global _config
    if _config is None:
        default_data = _load_default_config()
        user_data = _load_user_config()
        # Слияние: пользовательские ключи переопределяют дефолтные
        merged = {**default_data, **user_data}
        _config = AppConfig(**merged)
        # Создаём необходимые директории
        _config.ensure_directories()
    return _config


def save_config(config: AppConfig) -> None:
    """Сохранить конфигурацию в пользовательский JSON-файл."""
    USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(USER_CONFIG_PATH, "w", encoding="utf-8") as f:
        # Сохраняем с отступами для читаемости, исключая значения по умолчанию? Нет, сохраняем всё.
        json.dump(config.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
    global _config
    _config = config  # обновляем кэш
