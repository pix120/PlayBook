from playbook.config import get_config, save_config
from playbook.models.config import AppConfig


def test_default_config(monkeypatch, tmp_path):
    # Подменяем пути, чтобы не трогать реальный конфиг
    monkeypatch.setattr(
        "playbook.config.USER_CONFIG_PATH", tmp_path / "user_config.json"
    )
    # Сбрасываем глобальный кеш
    import playbook.config

    playbook.config._config = None
    config = get_config()
    assert isinstance(config, AppConfig)
    assert config.theme == "dark"


def test_save_and_load_user_config(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "playbook.config.USER_CONFIG_PATH", tmp_path / "user_config.json"
    )
    import playbook.config

    playbook.config._config = None
    config = get_config()
    config.library_paths = ["/my/books"]
    config.theme = "light"
    save_config(config)
    assert (tmp_path / "user_config.json").exists()
    playbook.config._config = None
    new_config = get_config()
    assert new_config.library_paths == ["/my/books"]
    assert new_config.theme == "light"
