from __future__ import annotations

import flet as ft

from .library_page import LibraryPage
from .player_page import PlayerPage
from .settings_page import SettingsPage


class PlayBookApp:
    """
    Главный контроллер приложения,
    управляющий навигацией и общим состоянием
    """

    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "PlayBook"
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.DARK

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
                # Библиотека – иконка книги
                ft.NavigationRailDestination(
                    icon=ft.Icons.BOOK,
                    selected_icon=ft.Icons.BOOK,
                    label="Библиотека",
                ),
                # Сейчас играет – иконка плей
                ft.NavigationRailDestination(
                    icon=ft.Icons.PLAY_CIRCLE_OUTLINED,
                    selected_icon=ft.Icons.PLAY_CIRCLE,
                    label="Сейчас играет",
                ),
                # Настройки
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label="Настройки",
                ),
            ],
            on_change=self._on_nav_change,
        )

        # Контейнер для контента
        self.content_area = ft.Container(
            expand=True,
            content=self.pages[self.current_section].build(),
        )

        # Главная компоновка: строка с навигацией и контентом
        self.root_view = ft.Row(
            controls=[
                self.nav_rail,
                ft.VerticalDivider(width=1),
                self.content_area,
            ],
            expand=True,
        )

        # Добавляем на страницу
        self.page.add(self.root_view)
        self.page.update()

    def _on_nav_change(self, e):
        """Переключение раздела."""
        index = e.control.selected_index
        sections = ["library", "player", "settings"]
        self.current_section = sections[index]
        self._update_content()

    def _update_content(self):
        """Обновить содержимое центральной области."""
        self.content_area.content = self.pages[self.current_section].build()
        self.page.update()

    def switch_to_section(self, section_name: str) -> None:
        """Программно переключить раздел."""
        if section_name in self.pages:
            self.current_section = section_name
            self.nav_rail.selected_index = ["library", "player", "settings"].index(
                section_name
            )
            self._update_content()
