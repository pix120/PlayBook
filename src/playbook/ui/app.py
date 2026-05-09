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

        self.root_view = ft.Row(
            controls=[
                self.nav_rail,
                ft.VerticalDivider(width=1),
                self.content_area,
            ],
            expand=True,
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

    def refresh_current_page(self):
        self.content_area.content = self.pages[self.current_section].build()
        self.page.update()
