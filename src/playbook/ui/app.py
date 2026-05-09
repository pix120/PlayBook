from __future__ import annotations

import flet as ft
from pathlib import Path

from .library_page import LibraryPage
from .player_page import PlayerPage
from .settings_page import SettingsPage


class PlayBookApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "PlayBook"
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.window.width = 1000
        self.page.window.height = 700

        self.pages = {
            "library": LibraryPage(self),
            "player": PlayerPage(self),
            "settings": SettingsPage(self),
        }
        self.current_section = "library"

        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=80,
            min_extended_width=160,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.icons.LIBRARY_BOOKS,
                    selected_icon=ft.icons.LIBRARY_BOOKS,
                    label="Библиотека",
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.PLAY_CIRCLE_FILL_OUTLINED,
                    selected_icon=ft.icons.PLAY_CIRCLE,
                    label="Сейчас играет",
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.SETTINGS_OUTLINED,
                    selected_icon=ft.icons.SETTINGS,
                    label="Настройки",
                ),
            ],
            on_change=self._on_nav_change,
        )

        self.content_area = ft.Container(
            expand=True,
            content=self.pages[self.current_section].build(),
        )

        self.mini_player = self._create_mini_player()
        self.mini_player.visible = False

        self.root_view = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        self.nav_rail,
                        ft.VerticalDivider(width=1),
                        self.content_area,
                    ],
                    expand=True,
                ),
                self.mini_player,
            ],
            expand=True,
            spacing=0,
        )

        self.page.add(self.root_view)
        self.page.update()

        self.page.app = self

        def on_window_event(e):
            if e.data == "close":
                player = self.pages.get("player")
                if player and player.current_book:
                    player._save_progress()
                if getattr(page, "window", None) is not None:
                    page.window_destroy()

        # In some runtimes/sessions, page.window may exist while the internal
        # native window handle is still unavailable. Binding can raise there.
        try:
            page.on_window_event = on_window_event
        except AttributeError:
            # Non-window session or window backend not ready; continue safely.
            pass

    def _on_nav_change(self, e):
        index = e.control.selected_index
        sections = ["library", "player", "settings"]
        self.current_section = sections[index]
        self.content_area.content = self.pages[self.current_section].build()
        self.page.update()

    def switch_to_section(self, section_name: str) -> None:
        if section_name in self.pages:
            self.current_section = section_name
            self.nav_rail.selected_index = ["library", "player", "settings"].index(
                section_name
            )
            self.content_area.content = self.pages[self.current_section].build()
            self.page.update()

    def _create_mini_player(self) -> ft.Container:
        self.mini_cover = ft.Image(
            src="assets/default_cover.png",
            width=40,
            height=40,
            fit="cover",
            border_radius=4,
        )
        self.mini_title = ft.Text(
            "",
            size=14,
            weight=ft.FontWeight.BOLD,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.mini_author = ft.Text(
            "",
            size=12,
            color=ft.colors.GREY,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.mini_play_pause_btn = ft.IconButton(
            icon=ft.icons.PLAY_ARROW,
            tooltip="Play/Pause",
            on_click=self._mini_play_pause,
        )
        self.mini_next_btn = ft.IconButton(
            icon=ft.icons.SKIP_NEXT,
            tooltip="Next",
            on_click=self._mini_next,
        )
        self.mini_progress_bar = ft.ProgressBar(
            value=0.0,
            color=ft.colors.GREEN_ACCENT_400,
            bgcolor=ft.colors.SURFACE_VARIANT,
            height=2,
        )

        mini_info = ft.GestureDetector(
            expand=True,
            mouse_cursor=ft.MouseCursor.CLICK,
            content=ft.Row(
                controls=[
                    self.mini_cover,
                    ft.Column(
                        controls=[self.mini_title, self.mini_author],
                        spacing=2,
                        expand=True,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            on_tap=lambda _: self.switch_to_section("player"),
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    self.mini_progress_bar,
                    ft.Row(
                        controls=[
                            mini_info,
                            self.mini_play_pause_btn,
                            self.mini_next_btn,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        expand=True,
                    ),
                ],
                spacing=0,
            ),
            padding=ft.padding.only(left=10, right=10, bottom=5, top=5),
            bgcolor=ft.colors.SURFACE_VARIANT,
            visible=False,
        )

    def update_mini_player(
        self, book=None, is_playing=False, progress=0.0, duration=0.0
    ):
        if book is None:
            self.mini_player.visible = False
        else:
            self.mini_player.visible = True
            cover = (
                str(Path(book.cover_path).resolve())
                if book.cover_path and Path(book.cover_path).exists()
                else "assets/default_cover.png"
            )
            self.mini_cover.src = cover
            self.mini_title.value = book.title
            self.mini_author.value = book.author
            self.mini_play_pause_btn.icon = (
                ft.icons.PAUSE if is_playing else ft.icons.PLAY_ARROW
            )
            progress_pct = (progress / duration) if duration > 0 else 0.0
            self.mini_progress_bar.value = min(max(progress_pct, 0.0), 1.0)
        self.page.update()

    def _mini_play_pause(self, e):
        player = self.pages.get("player")
        if player and player.audio:
            player._on_play_pause(None)

    def _mini_next(self, e):
        player = self.pages.get("player")
        if player:
            player.play_next()

    def refresh_current_page(self):
        self.content_area.content = self.pages[self.current_section].build()
        self.page.update()
