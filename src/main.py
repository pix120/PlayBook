# src/main.py
import flet as ft
from playbook.db.database import initialize_db


def main(page: ft.Page):
    page.title = "PlayBook"
    # ... остальной код


if __name__ == "__main__":
    initialize_db()
    ft.app(target=main)
