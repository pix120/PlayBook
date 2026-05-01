from __future__ import annotations

import flet as ft
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .app import PlayBookApp


class PlayerPage:
    def __init__(self, app: PlayBookApp):
        self.app = app

    def build(self) -> ft.Column:
        return ft.Column(
            controls=[
                ft.Text("Плеер", size=24),
                ft.Text("Здесь будет располагаться плеер и текущая книга."),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
