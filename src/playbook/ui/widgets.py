from __future__ import annotations

import base64
from pathlib import Path
import flet as ft
from ..models.book import Book, BookStatus

DEFAULT_COVER_PATH = "/assets/default_cover.png"

_COVER_CACHE: dict[str, str] = {}
_DEFAULT_COVER_B64: str | None = None


def _get_default_cover_b64() -> str:
    global _DEFAULT_COVER_B64
    if _DEFAULT_COVER_B64 is None:
        try:
            with open("assets/default_cover.png", "rb") as f:
                _DEFAULT_COVER_B64 = base64.b64encode(f.read()).decode("utf-8")
        except (FileNotFoundError, OSError):
            _DEFAULT_COVER_B64 = ""
    return _DEFAULT_COVER_B64


def get_cover_kwargs(cover_path: str | None) -> dict:
    if cover_path and Path(cover_path).exists():
        resolved = str(Path(cover_path).resolve())
        if resolved not in _COVER_CACHE:
            try:
                with open(resolved, "rb") as f:
                    _COVER_CACHE[resolved] = base64.b64encode(f.read()).decode("utf-8")
            except (FileNotFoundError, OSError):
                return {"src": DEFAULT_COVER_PATH}
        return {"src_base64": _COVER_CACHE[resolved]}
    b64 = _get_default_cover_b64()
    if b64:
        return {"src_base64": b64}
    return {"src": DEFAULT_COVER_PATH}


class BookGridCard(ft.Container):
    def __init__(self, book: Book, on_click, on_delete=None):
        super().__init__()
        self.book = book
        self.on_click = on_click
        cover_kwargs = get_cover_kwargs(book.cover_path)
        progress_pct = (book.progress / book.duration) if book.duration > 0 else 0.0
        progress_pct = min(max(progress_pct, 0.0), 1.0)

        self.content = ft.Stack(
            controls=[
                ft.Image(
                    **cover_kwargs,
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
                ft.Container(
                    content=ft.PopupMenuButton(
                        icon=ft.icons.MORE_VERT,
                        icon_color=ft.colors.WHITE,
                        items=[
                            ft.PopupMenuItem(
                                text="Delete",
                                on_click=lambda e: on_delete(book) if on_delete else None,
                            ),
                        ],
                    ),
                    alignment=ft.alignment.top_right,
                    padding=5,
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
    def __init__(self, book: Book, on_click, on_delete=None):
        super().__init__()
        self.book = book
        cover_kwargs = get_cover_kwargs(book.cover_path)
        progress_pct = (book.progress / book.duration) if book.duration > 0 else 0.0
        progress_pct = min(max(progress_pct, 0.0), 1.0)

        self.content = ft.Row(
            controls=[
                ft.Image(
                    **cover_kwargs, width=48, height=48, fit="cover", border_radius=8
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
                ft.PopupMenuButton(
                    icon=ft.icons.MORE_VERT,
                    items=[
                        ft.PopupMenuItem(
                            text="Delete",
                            on_click=lambda e: on_delete(book) if on_delete else None,
                        ),
                    ],
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
