from __future__ import annotations

import time
import threading
from pathlib import Path
from typing import Optional

import flet as ft
from ..models.book import Book, BookStatus
from ..db.database import update_progress, update_book


class PlayerPage:
    def __init__(self, app):
        self.app = app
        self.current_book: Optional[Book] = None
        self.audio: Optional[ft.Audio] = None
        self.is_playing = False
        self.slider_being_dragged = False

        # Таймер периодического сохранения
        self._update_timer: Optional[threading.Timer] = None

        # Элементы UI (создаются один раз)
        self.cover_image = ft.Image(
            src="assets/default_cover.png",
            width=250,
            height=250,
            fit="cover",
            border_radius=15,
        )
        self.title_text = ft.Text("", size=22, weight=ft.FontWeight.BOLD)
        self.author_text = ft.Text("", size=16, color=ft.Colors.GREY)
        self.current_time_text = ft.Text("00:00", size=14)
        self.total_time_text = ft.Text("00:00", size=14)
        self.progress_slider = ft.Slider(
            min=0,
            max=1.0,
            value=0.0,
            on_change_start=lambda e: setattr(self, "slider_being_dragged", True),
            on_change_end=self._on_slider_change_end,
        )
        self.play_button = ft.IconButton(
            icon=ft.Icons.PLAY_ARROW,
            tooltip="Воспроизвести",
            on_click=self._on_play_pause,
        )
        self.stop_button = ft.IconButton(
            icon=ft.Icons.STOP,
            tooltip="Остановить",
            on_click=self._on_stop,
        )
        self.rewind_back_btn = ft.IconButton(
            icon=ft.Icons.REPLAY_10,
            tooltip="Назад на 15 с",
            on_click=lambda e: self._seek_relative(-15),
        )
        self.rewind_fwd_btn = ft.IconButton(
            icon=ft.Icons.FORWARD_30,
            tooltip="Вперёд на 15 с",
            on_click=lambda e: self._seek_relative(15),
        )
        self.speed_dropdown = ft.Dropdown(
            label="Скорость",
            options=[
                ft.dropdown.Option("0.5", "0.5x"),
                ft.dropdown.Option("1.0", "1.0x"),
                ft.dropdown.Option("1.25", "1.25x"),
                ft.dropdown.Option("1.5", "1.5x"),
                ft.dropdown.Option("2.0", "2.0x"),
            ],
            value="1.0",
            width=100,
        )
        self.speed_dropdown.on_change = self._on_speed_change

    def build(self) -> ft.Container:
        self.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row([self.cover_image], alignment=ft.MainAxisAlignment.CENTER),
                    self.title_text,
                    self.author_text,
                    ft.Row(
                        controls=[
                            self.current_time_text,
                            self.progress_slider,
                            self.total_time_text,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        controls=[
                            self.rewind_back_btn,
                            self.play_button,
                            self.stop_button,
                            self.rewind_fwd_btn,
                            self.speed_dropdown,
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=15,
                expand=True,
            ),
            padding=20,
            expand=True,
        )
        if self.current_book:
            self._update_ui_for_book()
        return self.content

    # ---------- Управление книгой ----------
    def load_book(self, book: Book):
        """Загружает книгу в плеер."""
        if self.audio is not None:
            self._stop_audio_and_save_progress()
            self.app.page.overlay.remove(self.audio)
            self.audio = None

        self.current_book = book
        self.audio = ft.Audio(
            src=book.file_path,
            autoplay=False,
            volume=1.0,
            on_loaded=self._on_audio_loaded,
            on_state_changed=self._on_audio_state_changed,
            on_position_changed=self._on_position_changed,
            on_seek_complete=self._on_seek_complete,
        )
        self.app.page.overlay.append(self.audio)
        self._update_ui_for_book()
        self._set_controls_enabled(False)
        self.play_button.icon = ft.Icons.PLAY_ARROW
        self.app.page.update()

    def _update_ui_for_book(self):
        if not self.current_book:
            return
        self.title_text.value = self.current_book.title
        self.author_text.value = self.current_book.author
        cover_path = self.current_book.cover_path
        if cover_path and Path(cover_path).exists():
            self.cover_image.src = cover_path
        else:
            self.cover_image.src = "assets/default_cover.png"
        self.total_time_text.value = self.current_book.duration_str
        self.progress_slider.max = self.current_book.duration
        self.progress_slider.value = self.current_book.progress
        self.current_time_text.value = self.current_book.progress_str
        self.app.page.update()

    # ---------- Обработчики аудио ----------
    def _on_audio_loaded(self, e):
        self._set_controls_enabled(True)
        if self.current_book and self.current_book.progress > 0:
            self.audio.seek(int(self.current_book.progress * 1000))

    def _on_audio_state_changed(self, e):
        state = e.data
        if state == "playing":
            self.is_playing = True
            self.play_button.icon = ft.Icons.PAUSE
            self._start_progress_updates()
        elif state in ("paused", "completed"):
            self.is_playing = False
            self.play_button.icon = ft.Icons.PLAY_ARROW
            self._stop_progress_updates()
            if state == "completed":
                self._on_book_finished()
            self._save_progress()
        self.app.page.update()

    def _on_position_changed(self, e):
        if not self.slider_being_dragged:
            position_sec = int(e.data) / 1000.0
            self.progress_slider.value = position_sec
            self.current_time_text.value = self._format_time(position_sec)
            self.app.page.update()

    def _on_seek_complete(self, e):
        pass

    # ---------- Кнопки управления ----------
    def _on_play_pause(self, e):
        if not self.audio:
            return
        if self.is_playing:
            self.audio.pause()
        else:
            self.audio.play()

    def _on_stop(self, e):
        if self.audio:
            self.audio.pause()
            self.audio.seek(0)
            self.progress_slider.value = 0.0
            self.current_time_text.value = "00:00"
            self.is_playing = False
            self.play_button.icon = ft.Icons.PLAY_ARROW
            self._save_progress()
            self.app.page.update()

    def _seek_relative(self, delta_seconds: int):
        if not self.audio or not self.current_book:
            return
        new_pos = max(
            0.0,
            min(self.current_book.duration, self.progress_slider.value + delta_seconds),
        )
        self.audio.seek(int(new_pos * 1000))
        self.progress_slider.value = new_pos
        self.current_time_text.value = self._format_time(new_pos)
        self._save_progress()
        self.app.page.update()

    def _on_slider_change_end(self, e):
        if not self.audio:
            return
        new_pos = self.progress_slider.value
        self.audio.seek(int(new_pos * 1000))
        self.slider_being_dragged = False
        self.current_time_text.value = self._format_time(new_pos)
        self._save_progress()
        self.app.page.update()

    def _on_speed_change(self, e):
        if self.audio:
            self.audio.playback_rate = float(self.speed_dropdown.value)

    # ---------- Сохранение прогресса ----------
    def _save_progress(self):
        if not self.current_book:
            return
        progress = self.progress_slider.value
        update_progress(self.current_book.id, progress)
        self.current_book.progress = progress

    def _start_progress_updates(self):
        if self._update_timer:
            self._update_timer.cancel()
        self._update_timer = threading.Timer(5.0, self._periodic_save)
        self._update_timer.daemon = True
        self._update_timer.start()

    def _stop_progress_updates(self):
        if self._update_timer:
            self._update_timer.cancel()
            self._update_timer = None

    def _periodic_save(self):
        if self.is_playing:
            self._save_progress()
            self._start_progress_updates()

    def _stop_audio_and_save_progress(self):
        if self.audio:
            self.audio.pause()
        self._save_progress()

    # ---------- Завершение книги ----------
    def _on_book_finished(self):
        if self.current_book:
            self.current_book.status = BookStatus.FINISHED
            self.current_book.progress = self.current_book.duration
            update_book(self.current_book)
            self._update_ui_for_book()
            self.app.page.show_snack_bar(
                ft.SnackBar(content=ft.Text("Книга прочитана!"))
            )

    # ---------- Вспомогательные методы ----------
    def _set_controls_enabled(self, enabled: bool):
        for ctrl in [
            self.play_button,
            self.stop_button,
            self.rewind_back_btn,
            self.rewind_fwd_btn,
            self.speed_dropdown,
            self.progress_slider,
        ]:
            ctrl.disabled = not enabled
        self.app.page.update()

    def _format_time(self, seconds: float) -> str:
        if seconds < 0:
            seconds = 0
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
