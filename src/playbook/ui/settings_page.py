from __future__ import annotations

import flet as ft
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .app import PlayBookApp

from ..config import get_config, save_config


class SettingsPage:
    def __init__(self, app: PlayBookApp):
        self.app = app
        self.config = get_config()
        self.path_fields: List[ft.TextField] = []
        self.progress_bar = ft.ProgressBar(width=400, visible=False)
        self.progress_text = ft.Text("", size=12)
        self.scan_button = ft.ElevatedButton(
            content=ft.Text("Обновить библиотеку"),
            icon=ft.Icons.REFRESH,
            on_click=self._start_scan,
        )

    def build(self) -> ft.Column:
        self.path_fields.clear()
        for i, path in enumerate(self.config.library_paths):
            tf = ft.TextField(
                value=path,
                label=f"Папка {i+1}",
                hint_text="Например, /home/user/Аудиокниги",
                expand=True,
            )
            self.path_fields.append(tf)

        add_folder_btn = ft.TextButton(
            content=ft.Text("Добавить папку"),
            icon=ft.Icons.ADD,
            on_click=self._add_path_field,
        )

        theme_switch = ft.Switch(
            label="Тёмная тема",
            value=self.config.theme == "dark",
            on_change=self._toggle_theme,
        )

        return ft.Column(
            controls=[
                ft.Text("Настройки", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("Папки с аудиокнигами:", size=16, weight=ft.FontWeight.W_500),
                ft.Column(
                    controls=self.path_fields + [add_folder_btn],
                    spacing=10,
                ),
                ft.Divider(),
                ft.Text("Оформление:", size=16),
                theme_switch,
                ft.Divider(),
                self.scan_button,
                ft.Row(
                    controls=[self.progress_bar, self.progress_text],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.ElevatedButton(
                    content=ft.Text("Сохранить настройки"),
                    on_click=self._save_settings,
                ),
            ],
            spacing=15,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def _add_path_field(self, e):
        self.config.library_paths.append("")
        self._refresh()

    def _start_scan(self, e):
        import threading

        def scan_job():
            # Парсим пути из текущих полей
            paths = []
            for tf in self.path_fields:
                p = tf.value.strip()
                if p:
                    paths.append(Path(p).expanduser().resolve())
            if not paths:
                self.app.page.show_snack_bar(
                    ft.SnackBar(content=ft.Text("Укажите хотя бы одну папку!"))
                )
                return
            self.progress_bar.visible = True
            self.progress_text.value = "Сканирование..."
            self.scan_button.disabled = True
            self.app.page.update()

            try:
                from ..scanner import scan_and_update_library

                total_added = 0
                total_updated = 0
                for event in scan_and_update_library(paths):
                    if event["type"] == "progress":
                        self.progress_bar.value = event["current"] / event["total"]
                        self.progress_text.value = (
                            f"{event['current']}/{event['total']} - {event['file']}"
                        )
                    elif event["type"] == "finished":
                        total_added = event["added"]
                        total_updated = event["updated"]
                    self.app.page.update()
                self.progress_bar.visible = False
                self.progress_text.value = (
                    f"Готово! Добавлено: {total_added}, обновлено: {total_updated}"
                )
                # Обновить библиотеку, если она открыта
                self.app.pages["library"].refresh_data()
            except Exception as ex:
                self.progress_text.value = f"Ошибка: {ex}"
            finally:
                self.scan_button.disabled = False
                self.app.page.update()

        threading.Thread(target=scan_job, daemon=True).start()

    def _toggle_theme(self, e):
        self.config.theme = "dark" if e.control.value else "light"
        self.app.page.theme_mode = (
            ft.ThemeMode.DARK if self.config.theme == "dark" else ft.ThemeMode.LIGHT
        )
        self.app.page.update()

    def _save_settings(self, e):
        new_paths = []
        for tf in self.path_fields:
            val = tf.value.strip()
            if val:
                val = str(Path(val).expanduser().resolve())
                new_paths.append(val)
        self.config.library_paths = new_paths
        save_config(self.config)
        self.app.page.show_snack_bar(
            ft.SnackBar(content=ft.Text("Настройки сохранены!"))
        )
        self.app.page.update()

    def _refresh(self):
        self.app.content_area.content = self.build()
        self.app.page.update()
