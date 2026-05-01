from __future__ import annotations

import flet as ft
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .app import PlayBookApp


class SettingsPage:
    def __init__(self, app: PlayBookApp):
        self.app = app

    def build(self) -> ft.Column:
        return ft.Column(
            controls=[
                ft.Text("Настройки", size=24),
                ft.Text(
                    "Здесь можно будет указать папки с аудиокнигами и другие параметры."
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
