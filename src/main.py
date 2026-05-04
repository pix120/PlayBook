import flet as ft
from pathlib import Path
from playbook.db.connection import set_db_path
from playbook.db.database import initialize_db
from playbook.ui.app import PlayBookApp


def main(page: ft.Page):
    set_db_path(Path("data/playbook.db"))
    initialize_db()
    PlayBookApp(page)


if __name__ == "__main__":
    # Flet 0.24.x exposes `ft.app`; `ft.run` was added in a later release.
    ft.app(main)
