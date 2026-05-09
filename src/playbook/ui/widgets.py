from __future__ import annotations

import base64
from pathlib import Path
import flet as ft
from ..models.book import Book, BookStatus

_COVER_CACHE: dict[str, str] = {}


def get_cover_kwargs(cover_path: str | None) -> dict | None:
    if cover_path and Path(cover_path).exists():
        resolved = str(Path(cover_path).resolve())
        if resolved not in _COVER_CACHE:
            try:
                with open(resolved, "rb") as f:
                    _COVER_CACHE[resolved] = base64.b64encode(f.read()).decode("utf-8")
            except (FileNotFoundError, OSError):
                return None
        return {"src_base64": _COVER_CACHE[resolved]}
    return None


def book_binding(title: str, author: str) -> ft.Container:
    return ft.Container(
        expand=True,
        bgcolor="#C4A882",
        border=ft.border.all(2, ft.colors.with_opacity(0.3, ft.colors.BLACK)),
        border_radius=ft.border_radius.all(8),
        content=ft.Stack(
            controls=[
                ft.Container(
                    width=10, height=10,
                    left=14, top=12,
                    border=ft.border.all(1.5, ft.colors.with_opacity(0.35, ft.colors.BLACK)),
                    rotate=0.785,
                ),
                ft.Container(
                    width=10, height=10,
                    right=14, top=12,
                    border=ft.border.all(1.5, ft.colors.with_opacity(0.35, ft.colors.BLACK)),
                    rotate=0.785,
                ),
                ft.Container(
                    width=10, height=10,
                    left=14, bottom=12,
                    border=ft.border.all(1.5, ft.colors.with_opacity(0.35, ft.colors.BLACK)),
                    rotate=0.785,
                ),
                ft.Container(
                    width=10, height=10,
                    right=14, bottom=12,
                    border=ft.border.all(1.5, ft.colors.with_opacity(0.35, ft.colors.BLACK)),
                    rotate=0.785,
                ),
                ft.Container(
                    height=1.5,
                    bgcolor=ft.colors.with_opacity(0.25, ft.colors.BLACK),
                    left=30, right=30, top=35,
                ),
                ft.Container(
                    height=1.5,
                    bgcolor=ft.colors.with_opacity(0.25, ft.colors.BLACK),
                    left=30, right=30, bottom=42,
                ),
                ft.Container(
                    content=ft.Text(
                        title,
                        size=15,
                        weight=ft.FontWeight.BOLD,
                        color=ft.colors.with_opacity(0.85, ft.colors.BLACK),
                        text_align=ft.TextAlign.CENTER,
                        max_lines=4,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    alignment=ft.alignment.center,
                    padding=ft.padding.only(left=20, right=20),
                ),
                ft.Container(
                    content=ft.Text(
                        author,
                        size=11,
                        italic=True,
                        color=ft.colors.with_opacity(0.7, ft.colors.BLACK),
                        text_align=ft.TextAlign.CENTER,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    alignment=ft.alignment.bottom_center,
                    bottom=18,
                ),
            ],
        ),
    )


class BookGridCard(ft.Container):
    def __init__(self, book: Book, on_click, on_delete=None):
        super().__init__()
        self.book = book
        self.on_click = on_click
        cover_kwargs = get_cover_kwargs(book.cover_path)
        progress_pct = (book.progress / book.duration) if book.duration > 0 else 0.0
        progress_pct = min(max(progress_pct, 0.0), 1.0)

        if cover_kwargs:
            cover_content = ft.Image(
                **cover_kwargs,
                fit="cover",
                width=float("inf"),
                height=float("inf"),
            )
            overlay_content = ft.Container(
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
            )
        else:
            cover_content = book_binding(book.title, book.author)
            overlay_content = ft.Container(
                content=ft.ProgressBar(
                    value=progress_pct,
                    color=ft.colors.GREEN_ACCENT_400,
                    bgcolor=ft.colors.with_opacity(0.15, ft.colors.BLACK),
                    height=4,
                ),
                alignment=ft.alignment.bottom_center,
                padding=ft.padding.only(left=10, right=10, bottom=8),
            )

        self.content = ft.Stack(
            controls=[
                cover_content,
                overlay_content,
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

        if cover_kwargs:
            cover_control = ft.Image(
                **cover_kwargs, width=48, height=48, fit="cover", border_radius=8
            )
        else:
            cover_control = ft.Container(
                width=48,
                height=48,
                bgcolor="#C4A882",
                border_radius=8,
                alignment=ft.alignment.center,
                content=ft.Text(
                    book.title[0].upper() if book.title else "?",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=ft.colors.with_opacity(0.7, ft.colors.BLACK),
                ),
            )

        self.content = ft.Row(
            controls=[
                cover_control,
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
