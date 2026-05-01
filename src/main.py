# src/main.py
import flet as ft
from pathlib import Path
from playbook.db.connection import set_db_path
from playbook.db.database import initialize_db
from playbook.ui.app import PlayBookApp


def main(page: ft.Page):
    # Инициализация базы данных
    set_db_path(Path("data/playbook.db"))
    initialize_db()

    # Создаём и отображаем наше приложение
    PlayBookApp(page)


if __name__ == "__main__":
    ft.run(main)
