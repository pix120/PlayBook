from __future__ import annotations

import threading
from pathlib import Path

import flet as ft

from .library_page import LibraryPage
from .player_page import PlayerPage
from .settings_page import SettingsPage
from ..db.database import get_all_books
from ..config import get_config, save_config
from ..scanner import scan_and_update_library


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

        if not get_all_books():
            self._show_first_run_dialog()

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

    def _show_first_run_dialog(self):
        path_field = ft.TextField(
            value=str(Path.home() / "Аудиокниги"),
            label="Folder with audiobooks",
            hint_text="/home/user/Audiobooks",
            expand=True,
        )
        progress_bar = ft.ProgressBar(width=400, visible=False)
        progress_text = ft.Text("", size=12)

        def on_scan(e):
            raw = path_field.value.strip()
            if not raw:
                return
            p = str(Path(raw).expanduser().resolve())
            cfg = get_config()
            cfg.library_paths = [p]
            save_config(cfg)
            dialog.open = False
            self.page.update()
            self._run_first_scan(p, progress_bar, progress_text)

        def on_skip(e):
            dialog.open = False
            self.page.update()

        scan_btn = ft.ElevatedButton("Scan", on_click=on_scan)
        skip_btn = ft.TextButton("Skip", on_click=on_skip)

        dialog = ft.AlertDialog(
            title=ft.Text("Welcome to PlayBook!"),
            content=ft.Column(
                [
                    ft.Text("Select a folder with audiobooks to get started:"),
                    path_field,
                    progress_bar,
                    progress_text,
                ],
                tight=True,
            ),
            actions=[scan_btn, skip_btn],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def _run_first_scan(self, path: str, progress_bar, progress_text):
        def scan_job():
            try:
                total_added = 0
                for event in scan_and_update_library([Path(path)]):
                    if event["type"] == "progress":
                        progress_bar.visible = True
                        progress_bar.value = event["current"] / event["total"]
                        progress_text.value = (
                            f"{event['current']}/{event['total']} – {event['file']}"
                        )
                    elif event["type"] == "finished":
                        total_added = event["added"]
                    self.page.update()
                self.pages["library"].refresh_data()
                self.switch_to_section("library")
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(f"Added {total_added} audiobooks!")
                    )
                )
            except Exception as ex:
                self.page.show_snack_bar(
                    ft.SnackBar(content=ft.Text(f"Scan error: {ex}"))
                )
            finally:
                self.page.update()

        threading.Thread(target=scan_job, daemon=True).start()
