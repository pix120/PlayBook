import flet as ft
from pathlib import Path
from playbook.db.connection import set_db_path
from playbook.db.database import initialize_db
from playbook.config import get_config
from playbook.ui.app import PlayBookApp


def main(page: ft.Page):
    config = get_config()
    db_path = Path(config.database_path).resolve()
    set_db_path(db_path)
    initialize_db()
    page.theme_mode = (
        ft.ThemeMode.DARK if config.theme == "dark" else ft.ThemeMode.LIGHT
    )
    PlayBookApp(page)


if __name__ == "__main__":
    ft.run(main)
