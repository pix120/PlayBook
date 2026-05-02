# src/playbook/ui/library_page.py
from __future__ import annotations

import flet as ft
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .app import PlayBookApp

from ..db.database import get_all_books
from ..models.book import BookStatus
from .widgets import BookGridCard, BookListItem


class LibraryPage:
    def __init__(self, app: PlayBookApp):
        self.app = app
        self._filter = None
        self._view_mode = "grid"

        self.book_container = ft.Container(expand=True)
        self.filter_buttons = self._create_filter_buttons()
        self.view_toggle_button = ft.IconButton(
            icon=ft.Icons.VIEW_LIST,
            tooltip="Переключить вид",
            on_click=self._toggle_view_mode,
        )
        self.filter_row = None

    def build(self) -> ft.Column:
        self.filter_row = ft.Row(
            controls=[
                ft.Text("Статус:", weight=ft.FontWeight.BOLD),
                *self.filter_buttons,
                self.view_toggle_button,
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self._render_books()  # здесь обновление страницы не требуется

        return ft.Column(
            controls=[
                self.filter_row,
                ft.Divider(),
                self.book_container,
            ],
            expand=True,
        )

    def _create_filter_buttons(self) -> list[ft.ElevatedButton]:
        filters = [
            ("Все", None),
            ("Новые", BookStatus.NEW),
            ("Начатые", BookStatus.STARTED),
            ("Прочитанные", BookStatus.FINISHED),
        ]
        buttons = []
        for label, status in filters:
            is_active = status == self._filter
            btn = ft.ElevatedButton(
                content=ft.Text(label),
                on_click=lambda e, s=status: self._set_filter(s),
                style=ft.ButtonStyle(
                    color=ft.Colors.ON_PRIMARY if is_active else ft.Colors.ON_SURFACE,
                    bgcolor=ft.Colors.PRIMARY if is_active else ft.Colors.SURFACE,
                ),
            )
            buttons.append(btn)
        return buttons

    def _set_filter(self, status: BookStatus | None):
        self._filter = status
        self.filter_buttons = self._create_filter_buttons()
        self.filter_row.controls = [
            ft.Text("Статус:", weight=ft.FontWeight.BOLD),
            *self.filter_buttons,
            self.view_toggle_button,
        ]
        self.filter_row.update()
        self._render_books()
        self.app.page.update()  # обновим страницу целиком

    def _toggle_view_mode(self, e):
        self._view_mode = "list" if self._view_mode == "grid" else "grid"
        self.view_toggle_button.icon = (
            ft.Icons.VIEW_MODULE if self._view_mode == "grid" else ft.Icons.VIEW_LIST
        )
        self._render_books()
        self.app.page.update()

    def _render_books(self):
        """Заполняет book_container.content книгами, НЕ обновляя страницу."""
        filtered_books = self._get_filtered_books()
        if self._view_mode == "grid":
            content = self._build_grid(filtered_books)
        else:
            content = self._build_list(filtered_books)
        self.book_container.content = content

    def _get_filtered_books(self) -> list:
        return get_all_books(status=self._filter)

    def _build_grid(self, books) -> ft.GridView:
        return ft.GridView(
            expand=True,
            runs_count=3,
            max_extent=250,
            child_aspect_ratio=0.7,
            spacing=10,
            run_spacing=10,
            controls=[
                BookGridCard(book, on_click=self._book_selected) for book in books
            ],
        )

    def _build_list(self, books) -> ft.ListView:
        return ft.ListView(
            expand=True,
            spacing=10,
            controls=[
                BookListItem(book, on_click=self._book_selected) for book in books
            ],
        )

    def _book_selected(self, book):
        player_page = self.app.pages.get("player")
        if player_page:
            player_page.add_to_playlist(book)
            self.app.switch_to_section("player")

    def refresh_data(self):
        self._render_books()
        self.app.page.update()
