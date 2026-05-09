from __future__ import annotations

from pathlib import Path
import flet as ft
from ..models.book import Book, BookStatus

DEFAULT_COVER_PATH = "assets/default_cover.png"


class BookGridCard(ft.Container):
    def __init__(self, book: Book, on_click):
        super().__init__()
        self.book = book
        self.on_click = on_click
        cover_src = (
            str(Path(book.cover_path).resolve())
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
                        begin=ft.alignment.top_center,
                        end=ft.alignment.bottom_center,
                        colors=[ft.colors.TRANSPARENT, ft.colors.BLACK54],
                    ),
                    padding=10,
                    alignment=ft.alignment.bottom_left,
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                book.title,
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=ft.colors.WHITE,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                book.author,
                                size=12,
                                color=ft.colors.WHITE70,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.ProgressBar(
                                value=progress_pct,
                                color=ft.colors.GREEN_ACCENT_400,
                                bgcolor=ft.colors.WHITE24,
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
        self.clip_behavior = ft.ClipBehavior.ANTI_ALIAS
        self.ink = True
        self.on_click = lambda e: on_click(book)


class BookListItem(ft.Container):
    def __init__(self, book: Book, on_click):
        super().__init__()
        self.book = book
        cover_src = (
            str(Path(book.cover_path).resolve())
            if book.cover_path and Path(book.cover_path).exists()
            else DEFAULT_COVER_PATH
        )
        progress_pct = (book.progress / book.duration) if book.duration > 0 else 0.0
        progress_pct = min(max(progress_pct, 0.0), 1.0)

        self.content = ft.Row(
            controls=[
                ft.Image(
                    src=cover_src, width=48, height=48, fit="cover", border_radius=8
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
                            color=ft.colors.GREY,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.ProgressBar(
                            value=progress_pct,
                            color=ft.colors.GREEN_ACCENT_400,
                            bgcolor=ft.colors.SURFACE_VARIANT,
                            height=4,
                        ),
                    ],
                    spacing=3,
                    expand=True,
                ),
                (
                    ft.Icon(name=ft.icons.CHECK_CIRCLE, color=ft.colors.GREEN, size=20)
                    if book.status == BookStatus.FINISHED
                    else ft.Text(f"{int(progress_pct*100)}%")
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        )
        self.padding = 10
        self.border_radius = 10
        self.bgcolor = ft.colors.SURFACE
        self.ink = True
        self.on_click = lambda e: on_click(book)
