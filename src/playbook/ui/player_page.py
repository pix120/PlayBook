from __future__ import annotations

import time
import threading
from pathlib import Path
from typing import Optional, List, TYPE_CHECKING

import flet as ft

if TYPE_CHECKING:
    from .app import PlayBookApp

from ..models.book import Book, BookStatus
from ..db.database import update_progress, update_book


class PlayerPage:
    def __init__(self, app: PlayBookApp):
        self.app = app
        self.current_book: Optional[Book] = None
        self.audio: Optional[ft.Audio] = None
        self.is_playing = False
        self.slider_being_dragged = False
        self._update_timer: Optional[threading.Timer] = None

        # UI элементы
        self.cover_image = ft.Image(
            src="assets/default_cover.png",
            width=250,
            height=250,
            fit="cover",
            border_radius=15,
        )
        self.title_text = ft.Text("", size=22, weight=ft.FontWeight.BOLD)
        self.author_text = ft.Text("", size=16, color=ft.colors.GREY)
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
            icon=ft.icons.PLAY_ARROW,
            tooltip="Play/Pause",
            on_click=self._on_play_pause,
        )
        self.stop_button = ft.IconButton(
            icon=ft.icons.STOP,
            tooltip="Stop",
            on_click=self._on_stop,
        )
        self.rewind_back_btn = ft.IconButton(
            icon=ft.icons.REPLAY_10,
            tooltip="Back 15s",
            on_click=lambda e: self._seek_relative(-15),
        )
        self.rewind_fwd_btn = ft.IconButton(
            icon=ft.icons.FORWARD_30,
            tooltip="Forward 15s",
            on_click=lambda e: self._seek_relative(15),
        )
        self.speed_dropdown = ft.Dropdown(
            label="Speed",
            options=[
                ft.dropdown.Option("0.5", "0.5x"),
                ft.dropdown.Option("1.0", "1.0x"),
                ft.dropdown.Option("1.25", "1.25x"),
                ft.dropdown.Option("1.5", "1.5x"),
                ft.dropdown.Option("2.0", "2.0x"),
            ],
            value="1.0",
            on_change=self._on_speed_change,
            width=100,
        )
        self.prev_button = ft.IconButton(
            icon=ft.icons.SKIP_PREVIOUS,
            tooltip="Previous",
            on_click=lambda e: self.play_previous(),
        )
        self.next_button = ft.IconButton(
            icon=ft.icons.SKIP_NEXT, tooltip="Next", on_click=lambda e: self.play_next()
        )
        self.reset_progress_btn = ft.IconButton(
            icon=ft.icons.REFRESH,
            tooltip="Reset progress",
            on_click=self._confirm_reset_progress,
        )
        self.playlist_panel = ft.Container(
            content=ft.Text(""),
            height=0,
            animate=ft.animation.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
        self.playlist_visible = False
        self.toggle_playlist_btn = ft.IconButton(
            icon=ft.icons.PLAYLIST_PLAY,
            tooltip="Playlist",
            on_click=self._toggle_playlist,
        )

        # Playlist state
        self.playlist: List[Book] = []
        self.current_playlist_index: int = -1

        # Sleep timer
        self.sleep_timer_dropdown = ft.Dropdown(
            label="Sleep timer",
            options=[
                ft.dropdown.Option("off", "Off"),
                ft.dropdown.Option("10", "10 min"),
                ft.dropdown.Option("20", "20 min"),
                ft.dropdown.Option("30", "30 min"),
                ft.dropdown.Option("60", "60 min"),
            ],
            value="off",
            on_change=self._on_sleep_timer_change,
            width=130,
        )
        self.sleep_timer_label = ft.Text("", size=12, color=ft.colors.GREEN_ACCENT_400)
        self.sleep_timer_active = False
        self.sleep_timer_remaining = 0
        self.sleep_timer_thread: Optional[threading.Thread] = None
        self._save_volume_before_timer = 1.0

        self.content = None

    def build(self) -> ft.Container:
        self.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[self.cover_image],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
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
                            self.prev_button,
                            self.rewind_back_btn,
                            self.play_button,
                            self.stop_button,
                            self.rewind_fwd_btn,
                            self.next_button,
                            self.reset_progress_btn,
                            self.toggle_playlist_btn,
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6,
                    ),
                    ft.Row(
                        controls=[
                            self.speed_dropdown,
                            self.sleep_timer_dropdown,
                            self.sleep_timer_label,
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    self.playlist_panel,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
                expand=True,
            ),
            padding=20,
            expand=True,
        )
        if self.current_book:
            self._update_ui_for_book()
        return self.content

    # ------ Playlist management ------
    def add_to_playlist(self, book: Book):
        for b in self.playlist:
            if b.id == book.id:
                return
        self.playlist.append(book)
        if self.current_playlist_index == -1:
            self.current_playlist_index = 0
            self.load_book(book)
        self._update_playlist_panel()
        self._notify_mini_player()

    def _remove_from_playlist(self, index: int):
        if 0 <= index < len(self.playlist):
            self.playlist.pop(index)
            if index == self.current_playlist_index:
                self._stop_audio_and_save_progress()
                if self.playlist:
                    self.current_playlist_index = min(index, len(self.playlist) - 1)
                    self.load_book(self.playlist[self.current_playlist_index])
                else:
                    self.current_playlist_index = -1
                    self.current_book = None
            elif index < self.current_playlist_index:
                self.current_playlist_index -= 1
            self._update_playlist_panel()
            self._notify_mini_player()

    def _move_playlist_item(self, index: int, direction: int):
        new_index = index + direction
        if 0 <= new_index < len(self.playlist):
            self.playlist.insert(new_index, self.playlist.pop(index))
            if index == self.current_playlist_index:
                self.current_playlist_index = new_index
            elif (
                index < self.current_playlist_index
                and new_index >= self.current_playlist_index
            ):
                self.current_playlist_index -= 1
            elif (
                index > self.current_playlist_index
                and new_index <= self.current_playlist_index
            ):
                self.current_playlist_index += 1
            self._update_playlist_panel()

    def play_next(self):
        if self.playlist and self.current_playlist_index < len(self.playlist) - 1:
            self._stop_audio_and_save_progress()
            self.current_playlist_index += 1
            self.load_book(self.playlist[self.current_playlist_index])
            self._update_playlist_panel()
        else:
            self._on_stop(None)

    def play_previous(self):
        if self.playlist and self.current_playlist_index > 0:
            self._stop_audio_and_save_progress()
            self.current_playlist_index -= 1
            self.load_book(self.playlist[self.current_playlist_index])
            self._update_playlist_panel()

    def _play_playlist_item(self, index: int):
        if 0 <= index < len(self.playlist):
            self._stop_audio_and_save_progress()
            self.current_playlist_index = index
            self.load_book(self.playlist[index])
            self._update_playlist_panel()

    def _toggle_playlist(self, e):
        self.playlist_visible = not self.playlist_visible
        self.playlist_panel.height = 300 if self.playlist_visible else 0
        self.app.page.update()

    def _update_playlist_panel(self):
        items = []
        for idx, book in enumerate(self.playlist):
            is_current = idx == self.current_playlist_index
            item = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            name=ft.icons.AUDIOTRACK,
                            color=ft.colors.GREEN if is_current else ft.colors.GREY,
                        ),
                        ft.Text(
                            book.title,
                            weight=(
                                ft.FontWeight.BOLD
                                if is_current
                                else ft.FontWeight.NORMAL
                            ),
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            expand=True,
                        ),
                        ft.IconButton(
                            icon=ft.icons.DELETE,
                            tooltip="Remove",
                            on_click=lambda e, i=idx: self._remove_from_playlist(i),
                        ),
                        ft.IconButton(
                            icon=ft.icons.ARROW_UPWARD,
                            tooltip="Up",
                            on_click=lambda e, i=idx: self._move_playlist_item(i, -1),
                        ),
                        ft.IconButton(
                            icon=ft.icons.ARROW_DOWNWARD,
                            tooltip="Down",
                            on_click=lambda e, i=idx: self._move_playlist_item(i, 1),
                        ),
                    ],
                    spacing=5,
                ),
                padding=5,
                border_radius=5,
                bgcolor=ft.colors.SURFACE if is_current else None,
                on_click=lambda e, i=idx: self._play_playlist_item(i),
            )
            items.append(item)
        self.playlist_panel.content = ft.Column(
            controls=items, spacing=5, scroll=ft.ScrollMode.AUTO
        )
        if self.playlist_visible:
            self.playlist_panel.height = 300
        self.app.page.update()

    # ------ Audio callbacks ------
    def load_book(self, book: Book):
        self.current_book = book
        if self.audio is not None:
            self._stop_audio_and_save_progress()
            self.app.page.overlay.remove(self.audio)
            self.audio = None
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
        self.app.page.update()
        self._update_ui_for_book()
        self._set_controls_enabled(False)
        self.play_button.icon = ft.icons.PLAY_ARROW
        self._notify_mini_player()

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

    def _on_audio_loaded(self, e):
        self._set_controls_enabled(True)
        if self.current_book and self.current_book.progress > 0:
            self.audio.seek(int(self.current_book.progress * 1000))

    def _on_audio_state_changed(self, e):
        state = e.data
        if state == "playing":
            self.is_playing = True
            self.play_button.icon = ft.icons.PAUSE
            self._start_progress_updates()
        elif state in ("paused", "completed"):
            self.is_playing = False
            self.play_button.icon = ft.icons.PLAY_ARROW
            self._stop_progress_updates()
            if state == "completed":
                self._on_book_finished()
            self._save_progress()
        self._notify_mini_player()
        self.app.page.update()

    def _on_position_changed(self, e):
        if not self.slider_being_dragged:
            position_ms = e.data
            position_sec = int(position_ms) / 1000.0
            self.progress_slider.value = position_sec
            self.current_time_text.value = self._format_time(position_sec)
            self.app.page.update()

    def _on_seek_complete(self, e):
        pass

    # ------ Play controls ------
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
            self.play_button.icon = ft.icons.PLAY_ARROW
            self._save_progress()
            self._notify_mini_player()
            self.app.page.update()

    def _seek_relative(self, delta_seconds: int):
        if not self.audio or not self.current_book:
            return
        new_pos = max(0.0, self.progress_slider.value + delta_seconds)
        new_pos = min(new_pos, self.current_book.duration)
        self.audio.seek(int(new_pos * 1000))
        self.progress_slider.value = new_pos
        self.current_time_text.value = self._format_time(new_pos)
        self._save_progress()
        self._notify_mini_player()
        self.app.page.update()

    def _on_slider_change_end(self, e):
        if not self.audio:
            return
        new_pos = self.progress_slider.value
        self.audio.seek(int(new_pos * 1000))
        self.slider_being_dragged = False
        self.current_time_text.value = self._format_time(new_pos)
        self._save_progress()
        self._notify_mini_player()
        self.app.page.update()

    def _on_speed_change(self, e):
        if self.audio:
            self.audio.playback_rate = float(self.speed_dropdown.value)

    def _set_controls_enabled(self, enabled: bool):
        self.play_button.disabled = not enabled
        self.stop_button.disabled = not enabled
        self.rewind_back_btn.disabled = not enabled
        self.rewind_fwd_btn.disabled = not enabled
        self.speed_dropdown.disabled = not enabled
        self.progress_slider.disabled = not enabled
        self.prev_button.disabled = not enabled
        self.next_button.disabled = not enabled
        self.reset_progress_btn.disabled = not enabled
        self.app.page.update()

    # ------ Progress persistence ------
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

    # ------ Book finished ------
    def _on_book_finished(self):
        if self.current_book:
            self.current_book.status = BookStatus.FINISHED
            self.current_book.progress = self.current_book.duration
            update_book(self.current_book)
        if self.playlist and self.current_playlist_index < len(self.playlist) - 1:
            self.play_next()
        else:
            self._on_stop(None)
            self.app.page.show_snack_bar(
                ft.SnackBar(content=ft.Text("Книга прочитана!"))
            )

    # ------ Sleep timer ------
    def _on_sleep_timer_change(self, e):
        value = self.sleep_timer_dropdown.value
        if value == "off":
            self._cancel_sleep_timer()
        else:
            minutes = int(value)
            self._start_sleep_timer(minutes)

    def _start_sleep_timer(self, minutes: int):
        self._cancel_sleep_timer()
        if not self.audio:
            return
        self.sleep_timer_remaining = minutes * 60
        self.sleep_timer_active = True
        self.sleep_timer_label.value = self._format_time(self.sleep_timer_remaining)
        self._save_volume_before_timer = self.audio.volume
        self.sleep_timer_thread = threading.Thread(
            target=self._sleep_timer_job,
            args=(self.sleep_timer_remaining, self._save_volume_before_timer),
            daemon=True,
        )
        self.sleep_timer_thread.start()
        self.app.page.update()

    def _cancel_sleep_timer(self):
        if self.sleep_timer_active and self.audio:
            self.audio.volume = getattr(self, "_save_volume_before_timer", 1.0)
        self.sleep_timer_active = False
        self.sleep_timer_label.value = ""
        self.sleep_timer_dropdown.value = "off"
        self.app.page.update()

    def _sleep_timer_job(self, total_seconds: int, start_volume: float):
        wait_seconds = max(0, total_seconds - 30)
        for _ in range(int(wait_seconds)):
            if not self.sleep_timer_active:
                return
            time.sleep(1)
            self.sleep_timer_remaining -= 1
            self.sleep_timer_label.value = self._format_time(self.sleep_timer_remaining)
            self.app.page.update()

        if not self.sleep_timer_active:
            return
        steps = 20
        step_volume = start_volume / steps
        step_delay = 30 / steps
        for i in range(1, steps + 1):
            if not self.sleep_timer_active:
                return
            new_volume = max(0.0, start_volume - step_volume * i)
            self.audio.volume = new_volume
            self.sleep_timer_remaining = 30 - int(i * step_delay)
            self.sleep_timer_label.value = self._format_time(
                max(0, self.sleep_timer_remaining)
            )
            self.app.page.update()
            time.sleep(step_delay)

        if self.sleep_timer_active:
            self.audio.pause()
            self._on_stop(None)
            self._cancel_sleep_timer()

    # ------ Reset progress ------
    def _confirm_reset_progress(self, e):
        if not self.current_book:
            return

        def on_yes(e):
            self._reset_progress()
            self.app.page.dialog.open = False
            self.app.page.update()

        def on_no(e):
            self.app.page.dialog.open = False
            self.app.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Сбросить прогресс?"),
            content=ft.Text(
                "Вы уверены, что хотите сбросить прогресс книги на начало?"
            ),
            actions=[
                ft.TextButton(content=ft.Text("Да"), on_click=on_yes),
                ft.TextButton(content=ft.Text("Нет"), on_click=on_no),
            ],
        )
        self.app.page.dialog = dialog
        dialog.open = True
        self.app.page.update()

    def _reset_progress(self):
        if self.audio:
            self.audio.seek(0)
        if self.current_book:
            self.current_book.progress = 0.0
            self.current_book.status = BookStatus.NEW
            update_book(self.current_book)
            self.progress_slider.value = 0.0
            self.current_time_text.value = "00:00"
            self._update_ui_for_book()
            self._notify_mini_player()

    # ------ Helpers ------
    def _format_time(self, seconds: float) -> str:
        if seconds < 0:
            seconds = 0
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def _notify_mini_player(self):
        if self.current_book:
            self.app.update_mini_player(
                book=self.current_book,
                is_playing=self.is_playing,
                progress=self.progress_slider.value,
                duration=self.current_book.duration,
            )
        else:
            self.app.update_mini_player(book=None)
