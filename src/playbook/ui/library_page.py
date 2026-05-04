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

        self.filter_buttons = self._create_filter_buttons()
        self.view_toggle_button = ft.IconButton(
            icon=ft.icons.VIEW_LIST,
            tooltip="Toggle view",
            on_click=self._toggle_view_mode,
        )
        self.book_container = ft.Container(expand=True)

    def build(self) -> ft.Column:
        filter_row = ft.Row(
            controls=[ft.Text("Status:", weight=ft.FontWeight.BOLD)]
            + self.filter_buttons
            + [self.view_toggle_button],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self._render_books()
        return ft.Column(
            controls=[filter_row, ft.Divider(), self.book_container],
            expand=True,
        )

    def _create_filter_buttons(self):
        filters = [
            ("All", None),
            ("New", BookStatus.NEW),
            ("Started", BookStatus.STARTED),
            ("Finished", BookStatus.FINISHED),
        ]
        buttons = []
        for label, status in filters:
            selected = self._filter == status
            btn = ft.ElevatedButton(
                content=ft.Text(
                    label,
                    color=ft.colors.ON_PRIMARY if selected else ft.colors.ON_SURFACE,
                ),
                on_click=lambda e, s=status: self._set_filter(s),
                bgcolor=ft.colors.PRIMARY if selected else ft.colors.SURFACE,
            )
            buttons.append(btn)
        return buttons

    def _set_filter(self, status):
        self._filter = status
        filters = [
            ("All", None),
            ("New", BookStatus.NEW),
            ("Started", BookStatus.STARTED),
            ("Finished", BookStatus.FINISHED),
        ]
        for btn, (_, s) in zip(self.filter_buttons, filters):
            selected = s == status
            btn.bgcolor = ft.colors.PRIMARY if selected else ft.colors.SURFACE
            if isinstance(btn.content, ft.Text):
                btn.content.color = (
                    ft.colors.ON_PRIMARY if selected else ft.colors.ON_SURFACE
                )
        self._render_books()
        self.app.page.update()

    def _toggle_view_mode(self, e):
        self._view_mode = "list" if self._view_mode == "grid" else "grid"
        self.view_toggle_button.icon = (
            ft.icons.VIEW_MODULE if self._view_mode == "grid" else ft.icons.VIEW_LIST
        )
        self._render_books()
        self.app.page.update()

    def _render_books(self):
        books = get_all_books(status=self._filter)
        if self._view_mode == "grid":
            content = ft.GridView(
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
        else:
            content = ft.ListView(
                expand=True,
                spacing=10,
                controls=[
                    BookListItem(book, on_click=self._book_selected) for book in books
                ],
            )
        self.book_container.content = content

    def _book_selected(self, book):
        player = self.app.pages.get("player")
        if player:
            player.add_to_playlist(book)
            self.app.switch_to_section("player")

    def refresh_data(self):
        self._render_books()
