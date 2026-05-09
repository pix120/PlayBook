from __future__ import annotations

import time
import threading
from pathlib import Path
from typing import Optional, List, TYPE_CHECKING

import flet as ft

import re

if TYPE_CHECKING:
    from .app import PlayBookApp

from ..models.book import Book, BookStatus
from ..db.database import update_progress, update_book
from ..scanner import AUDIO_EXTENSIONS, extract_metadata
from .widgets import get_cover_kwargs


class PlayerPage:
    def __init__(self, app: PlayBookApp):
        self.app = app
        self.current_book: Optional[Book] = None
        self.audio: Optional[ft.Audio] = None
        self.is_playing = False
        self.slider_being_dragged = False
        self._update_timer: Optional[threading.Timer] = None
        self._pending_seek_seconds = 0.0

        # UI элементы
        self.cover_image = ft.Image(
            **get_cover_kwargs(None),
            width=250,
            height=250,
            fit="cover",
            border_radius=15,
        )
        self.title_text = ft.Text("", size=22, weight=ft.FontWeight.BOLD)
        self.author_text = ft.Text("", size=16, color=ft.colors.GREY)
        self.current_time_text = ft.Text("00:00", size=14)
        self.total_time_text = ft.Text("00:00", size=14)
        self.stats_text = ft.Text("", size=13, color=ft.colors.GREY)
        self.progress_slider = ft.Slider(
            min=0,
            max=1.0,
            value=0.0,
            expand=True,
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
            height=300,
            animate=ft.animation.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
        self.playlist_visible = True
        self.toggle_playlist_btn = ft.IconButton(
            icon=ft.icons.PLAYLIST_PLAY,
            tooltip="Playlist",
            on_click=self._toggle_playlist,
        )

        # Playlist state (chapter files for currently selected book)
        self.playlist: List[Path] = []
        self.playlist_durations: List[float] = []
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

    @staticmethod
    def _natural_key(path: Path):
        """
        Ключ для естественной сортировки: разбивает имя на части (текст + числа).
        Пример: 'file10part2.txt' -> ['file', 10, 'part', 2, '.txt']
        """
        return [
            int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", path.name)
        ]

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
                        expand=True,
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
                            self.speed_dropdown,
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6,
                    ),
                    ft.Row(
                        controls=[
                            self.sleep_timer_dropdown,
                            self.sleep_timer_label,
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    self.stats_text,
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
        self._stop_audio_and_save_progress()
        self.playlist.clear()
        self.playlist_durations.clear()
        self.current_playlist_index = -1
        self.current_book = book

        book_folder = Path(book.file_path)
        if book_folder.is_dir():
            chapter_files = sorted(
                [
                    path
                    for path in book_folder.iterdir()
                    if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
                ],
                key=PlayerPage._natural_key,
            )
        elif book_folder.suffix.lower() in AUDIO_EXTENSIONS:
            # Backward compatibility for existing single-file records/tests.
            chapter_files = [book_folder]
        else:
            self._handle_missing_audio_file(book)
            return
        if not chapter_files:
            self.app.page.show_snack_bar(
                ft.SnackBar(content=ft.Text(f"В папке нет аудиофайлов: {book_folder}"))
            )
            self._update_playlist_panel()
            self._notify_mini_player()
            return

        self.playlist = chapter_files
        self.playlist_durations = [
            extract_metadata(path).get("duration", 0.0) for path in chapter_files
        ]
        track_index, track_offset = self._resolve_resume_position()
        self.current_playlist_index = track_index
        self.load_current_track(start_position=track_offset)
        self._update_playlist_panel()
        self._notify_mini_player()

    def _remove_from_playlist(self, index: int):
        if 0 <= index < len(self.playlist):
            self.playlist.pop(index)
            if index < len(self.playlist_durations):
                self.playlist_durations.pop(index)
            if index == self.current_playlist_index:
                self._stop_audio_and_save_progress()
                if self.playlist:
                    self.current_playlist_index = min(index, len(self.playlist) - 1)
                    self.load_current_track(start_position=0.0)
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
            self.playlist_durations.insert(
                new_index, self.playlist_durations.pop(index)
            )
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
            self.load_current_track(start_position=0.0)
            self._update_playlist_panel()
        else:
            self._on_stop(None)

    def play_previous(self):
        if self.playlist and self.current_playlist_index > 0:
            self._stop_audio_and_save_progress()
            self.current_playlist_index -= 1
            self.load_current_track(start_position=0.0)
            self._update_playlist_panel()

    def _play_playlist_item(self, index: int):
        if 0 <= index < len(self.playlist):
            self._stop_audio_and_save_progress()
            self.current_playlist_index = index
            self.load_current_track(start_position=0.0)
            self._update_playlist_panel()

    def _toggle_playlist(self, e):
        self.playlist_visible = not self.playlist_visible
        self.playlist_panel.height = 300 if self.playlist_visible else 0
        self.app.page.update()

    def _update_playlist_panel(self):
        items = []
        for idx, track_path in enumerate(self.playlist):
            is_current = idx == self.current_playlist_index
            item = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            name=ft.icons.AUDIOTRACK,
                            color=ft.colors.GREEN if is_current else ft.colors.GREY,
                        ),
                        ft.Text(
                            track_path.stem,
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
        # Backward-compatible entrypoint: selecting a book always rebuilds chapter playlist.
        self.add_to_playlist(book)

    def load_current_track(self, start_position: float = 0.0):
        if not self.current_book or not self.playlist:
            return
        current_track_path = self.playlist[self.current_playlist_index]
        if not current_track_path.exists():
            self._handle_missing_audio_file(self.current_book)
            return
        if self.audio is not None:
            self._stop_audio_and_save_progress()
            self.app.page.overlay.remove(self.audio)
            self.audio = None
        self.audio = ft.Audio(
            src=str(current_track_path),
            autoplay=False,
            volume=1.0,
            on_loaded=self._on_audio_loaded,
            on_state_changed=self._on_audio_state_changed,
            on_position_changed=self._on_position_changed,
            on_seek_complete=self._on_seek_complete,
        )
        self._pending_seek_seconds = max(0.0, start_position)
        self.app.page.overlay.append(self.audio)
        self.app.page.update()
        self._update_ui_for_book()
        self._set_controls_enabled(False)
        self.play_button.icon = ft.icons.PLAY_ARROW
        self._notify_mini_player()

    def _handle_missing_audio_file(self, book: Book):
        self.audio = None
        self.is_playing = False
        self.play_button.icon = ft.icons.PLAY_ARROW
        self._set_controls_enabled(False)
        self.app.page.show_snack_bar(
            ft.SnackBar(content=ft.Text(f"Audio file not found: {book.file_path}"))
        )
        self.app.page.update()

    def _update_ui_for_book(self):
        if not self.current_book:
            return
        book = self.current_book
        self.title_text.value = book.title
        self.author_text.value = book.author
        cover_kw = get_cover_kwargs(book.cover_path)
        if "src_base64" in cover_kw:
            self.cover_image.src_base64 = cover_kw["src_base64"]
        else:
            self.cover_image.src = cover_kw["src"]
        current_track_duration = self._current_track_duration()
        self.total_time_text.value = self._format_time(current_track_duration)
        self.progress_slider.max = current_track_duration
        self.progress_slider.value = min(
            self._pending_seek_seconds, current_track_duration
        )
        self.current_time_text.value = self._format_time(self.progress_slider.value)
        track_info = f"{self.current_playlist_index + 1}/{len(self.playlist)}"
        pct = book.progress_percent
        self.stats_text.value = (
            f"Total: {book.duration_str}  |  "
            f"Progress: {pct:.0f}%  |  "
            f"Track: {track_info}"
        )
        self.app.page.update()

    def _on_audio_loaded(self, e):
        self._set_controls_enabled(True)
        if self.audio and self._pending_seek_seconds > 0:
            self.slider_being_dragged = True
            self.audio.seek(int(self._pending_seek_seconds * 1000))

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
        self.slider_being_dragged = False

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
            self.slider_being_dragged = True
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
        self.slider_being_dragged = True
        new_pos = max(0.0, self.progress_slider.value + delta_seconds)
        max_duration = self._current_track_duration()
        if max_duration <= 0 and self.current_book:
            max_duration = self.current_book.duration
        new_pos = min(new_pos, max_duration)
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
        if not self.current_book or self.current_book.id is None:
            return
        progress = self._playlist_prefix_duration() + self.progress_slider.value
        progress = min(max(progress, 0.0), self.current_book.duration)
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
            try:
                self.audio.pause()
            except AssertionError:
                # Some tests/mocks use an unattached audio control.
                pass
            self._save_progress()

    def _current_track_duration(self) -> float:
        if 0 <= self.current_playlist_index < len(self.playlist_durations):
            return max(self.playlist_durations[self.current_playlist_index], 0.0)
        return 0.0

    def _playlist_prefix_duration(self) -> float:
        if self.current_playlist_index <= 0:
            return 0.0
        return sum(self.playlist_durations[: self.current_playlist_index])

    def _resolve_resume_position(self) -> tuple[int, float]:
        if not self.playlist:
            return 0, 0.0
        target_progress = max(
            0.0, self.current_book.progress if self.current_book else 0.0
        )
        if all(duration <= 0 for duration in self.playlist_durations):
            return 0, target_progress
        accumulated = 0.0
        for idx, duration in enumerate(self.playlist_durations):
            if target_progress <= accumulated + duration:
                return idx, max(0.0, target_progress - accumulated)
            accumulated += duration
        last_index = len(self.playlist) - 1
        return last_index, 0.0

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
            self.slider_being_dragged = True
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
