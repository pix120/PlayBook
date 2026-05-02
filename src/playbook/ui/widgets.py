# src/playbook/ui/widgets.py
from __future__ import annotations

import flet as ft
from pathlib import Path
from playbook.models.book import Book, BookStatus

DEFAULT_COVER_PATH = "assets/default_cover.png"


class BookGridCard(ft.Container):
    """Карточка книги для отображения в сетке."""

    def __init__(self, book: Book, on_click=None):
        super().__init__()
        self.book = book
        self.on_click = on_click

        cover_src = (
            book.cover_path
            if book.cover_path and Path(book.cover_path).exists()
            else DEFAULT_COVER_PATH
        )

        progress_pct = (book.progress / book.duration) if book.duration > 0 else 0.0
        progress_pct = min(max(progress_pct, 0.0), 1.0)

        self.content = ft.Stack(
            controls=[
                ft.Image(
                    src=cover_src,
                    fit="cover",
                    width=float("inf"),
                    height=float("inf"),
                ),
                ft.Container(
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment.TOP_CENTER,
                        end=ft.Alignment.BOTTOM_CENTER,
                        colors=[ft.Colors.TRANSPARENT, ft.Colors.BLACK_54],
                    ),
                    padding=10,
                    alignment=ft.Alignment.BOTTOM_LEFT,
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                book.title,
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                book.author,
                                size=12,
                                color=ft.Colors.WHITE_70,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.ProgressBar(
                                value=progress_pct,
                                color=ft.Colors.GREEN_ACCENT_400,
                                bgcolor=ft.Colors.WHITE_24,
                                height=4,
                            ),
                        ],
                        spacing=3,
                    ),
                ),
            ],
            width=200,
            height=280,
        )

        self.border_radius = 12
        self.clip_behavior = "antiAlias"
        self.ink = True
        if on_click:
            self.on_click = lambda e, b=book: on_click(b)


class BookListItem(ft.Container):
    """Карточка книги для отображения в списке."""

    def __init__(self, book: Book, on_click=None):
        super().__init__()
        self.book = book

        cover_src = (
            book.cover_path
            if book.cover_path and Path(book.cover_path).exists()
            else DEFAULT_COVER_PATH
        )
        progress_pct = (book.progress / book.duration) if book.duration > 0 else 0.0
        progress_pct = min(max(progress_pct, 0.0), 1.0)

        # Используем проверенный цвет (заменён SURFACE_VARIANT на SURFACE_CONTAINER_HIGHEST,
        # если тест снова упадёт)
        self.content = ft.Row(
            controls=[
                ft.Image(
                    src=cover_src,
                    width=48,
                    height=48,
                    fit="cover",
                    border_radius=8,
                ),
                ft.Column(
                    controls=[
                        ft.Text(
                            book.title,
                            weight=ft.FontWeight.BOLD,
                            size=14,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(
                            book.author,
                            size=12,
                            color=ft.Colors.GREY,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.ProgressBar(
                            value=progress_pct,
                            color=ft.Colors.GREEN_ACCENT_400,
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,  # бывший SURFACE_VARIANT
                            height=4,
                        ),
                    ],
                    spacing=3,
                    expand=True,
                ),
                (
                    ft.Icon(name=ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN, size=20)
                    if book.status == BookStatus.FINISHED
                    else ft.Text(f"{int(progress_pct * 100)}%")
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        )

        self.padding = 10
        self.border_radius = 10
        self.bgcolor = ft.Colors.SURFACE
        self.ink = True
        if on_click:
            self.on_click = lambda e, b=book: on_click(b)
