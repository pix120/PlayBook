# src/playbook/ui/widgets.py
from __future__ import annotations

import flet as ft
from playbook.models.book import Book, BookStatus


class BookGridCard(ft.Container):
    """Карточка книги для отображения в сетке."""

    def __init__(self, book: Book, on_click):
        super().__init__()
        self.book = book

        progress_pct = (book.progress / book.duration) if book.duration > 0 else 0.0
        progress_pct = min(max(progress_pct, 0.0), 1.0)

        self.content = ft.Column(
            controls=[
                ft.Icon(ft.Icons.AUDIOTRACK, size=48, color=ft.Colors.GREY),
                ft.Text(
                    book.title,
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(book.author, size=12, color=ft.Colors.GREY),
                ft.ProgressBar(
                    value=progress_pct,
                    color=ft.Colors.GREEN_ACCENT_400,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    height=4,
                ),
            ],
            spacing=5,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.padding = 20
        self.border_radius = 12
        self.bgcolor = ft.Colors.SURFACE
        self.ink = True
        self.on_click = lambda e: on_click(book)


class BookListItem(ft.Container):
    """Элемент списка книг."""

    def __init__(self, book: Book, on_click):
        super().__init__()
        self.book = book

        progress_pct = (book.progress / book.duration) if book.duration > 0 else 0.0
        progress_pct = min(max(progress_pct, 0.0), 1.0)

        self.content = ft.Row(
            controls=[
                ft.Icon(ft.Icons.AUDIOTRACK, size=32, color=ft.Colors.GREY),
                ft.Column(
                    controls=[
                        ft.Text(book.title, weight=ft.FontWeight.BOLD, size=14),
                        ft.Text(book.author, size=12, color=ft.Colors.GREY),
                        ft.ProgressBar(
                            value=progress_pct,
                            color=ft.Colors.GREEN_ACCENT_400,
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                            height=4,
                        ),
                    ],
                    spacing=3,
                    expand=True,
                ),
                ft.Text(f"{int(progress_pct*100)}%"),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        )
        self.padding = 10
        self.border_radius = 10
        self.bgcolor = ft.Colors.SURFACE
        self.ink = True
        self.on_click = lambda e: on_click(book)
