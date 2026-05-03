from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from .models.config import AppConfig

DEFAULT_CONFIG_PATH = (
    Path(__file__).parent.parent.parent / "config" / "default_config.json"
)
USER_CONFIG_PATH = Path("config/user_config.json")

_config: Optional[AppConfig] = None


def _load_default_config() -> dict:
    if DEFAULT_CONFIG_PATH.exists():
        with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_user_config() -> dict:
    if USER_CONFIG_PATH.exists():
        with open(USER_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_config() -> AppConfig:
    global _config
    if _config is None:
        default_data = _load_default_config()
        user_data = _load_user_config()
        merged = {**default_data, **user_data}
        _config = AppConfig(**merged)
        _config.ensure_directories()
    return _config


def save_config(config: AppConfig) -> None:
    USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(USER_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
    global _config
    _config = config
