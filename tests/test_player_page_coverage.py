"""Broader PlayerPage coverage with mocks (no real audio device)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from playbook.models.book import Book
from playbook.ui.player_page import PlayerPage


def _book(**kwargs):
    defaults = dict(
        id=1,
        title="T",
        author="A",
        duration=100.0,
        file_path="/tmp/x.mp3",
        progress=0.0,
    )
    defaults.update(kwargs)
    return Book(**defaults)


@pytest.fixture
def player_ctx():
    page = MagicMock()
    page.overlay = []
    page.update = MagicMock()
    page.show_snack_bar = MagicMock()
    page.dialog = None
    app = MagicMock(page=page)
    app.update_mini_player = MagicMock()
    app.pages = {"player": MagicMock()}
    player = PlayerPage(app)
    app.pages["player"] = player
    return player, app, page


def test_add_to_playlist_duplicate_ignored(player_ctx):
    player, _, _ = player_ctx
    b = _book()
    player.add_to_playlist(b)
    player.add_to_playlist(b)
    assert len(player.playlist) == 1


def test_playlist_remove_current_and_reorder(player_ctx):
    player, _, _ = player_ctx
    books = [_book(id=1), _book(id=2, title="t2", file_path="/2.mp3")]
    for bk in books:
        player.add_to_playlist(bk)
    player._remove_from_playlist(1)
    assert len(player.playlist) == 1
    player.add_to_playlist(_book(id=3, title="t3", file_path="/3.mp3"))
    player.add_to_playlist(_book(id=4, title="t4", file_path="/4.mp3"))
    player.current_playlist_index = 1
    player._move_playlist_item(1, -1)
    assert player.current_playlist_index == 0


def test_play_next_and_previous_and_play_item(player_ctx):
    player, _, page = player_ctx
    with patch.object(player, "load_book") as lb:
        player.add_to_playlist(_book(id=1))
        player.add_to_playlist(_book(id=2, file_path="/b2.mp3"))
        lb.reset_mock()
        player.play_next()
        assert player.current_playlist_index == 1
        player.play_previous()
        assert player.current_playlist_index == 0
        player._play_playlist_item(1)
        assert player.current_playlist_index == 1


def test_play_next_at_end_stops(player_ctx):
    player, _, _ = player_ctx
    with patch.object(player, "load_book"), patch.object(player, "_on_stop") as stop:
        player.add_to_playlist(_book())
        player.play_next()
        stop.assert_called_once()


def test_toggle_playlist_and_panel(player_ctx):
    player, _, page = player_ctx
    player.add_to_playlist(_book())
    player.build()
    player._toggle_playlist(MagicMock())
    assert player.playlist_visible is True
    player._update_playlist_panel()
    page.update.assert_called()


def test_load_book_adds_audio(player_ctx):
    player, _, page = player_ctx
    b = _book()
    with patch("playbook.ui.player_page.ft.Audio") as A:
        audio = MagicMock()
        A.return_value = audio
        player.load_book(b)
    assert player.current_book == b
    assert len(page.overlay) == 1
    A.assert_called_once()


def test_audio_loaded_seeks_when_progress(player_ctx):
    player, _, _ = player_ctx
    b = _book(progress=12.0)
    with patch("playbook.ui.player_page.ft.Audio") as A:
        A.return_value = MagicMock()
        player.load_book(b)
    player._on_audio_loaded(MagicMock())
    player.audio.seek.assert_called()


def test_audio_state_playing_and_paused(player_ctx):
    player, _, page = player_ctx
    with patch("playbook.ui.player_page.ft.Audio") as A:
        A.return_value = MagicMock()
        player.load_book(_book())
    ev = MagicMock()
    ev.data = "playing"
    with patch.object(player, "_start_progress_updates"):
        player._on_audio_state_changed(ev)
    assert player.is_playing is True
    ev.data = "paused"
    with patch.object(player, "_stop_progress_updates"):
        player._on_audio_state_changed(ev)
    assert player.is_playing is False


def test_audio_completed_finishes_book(player_ctx):
    player, _, page = player_ctx
    with patch("playbook.ui.player_page.ft.Audio") as A:
        A.return_value = MagicMock()
        player.load_book(_book())
    with patch("playbook.ui.player_page.update_book"):
        ev = MagicMock()
        ev.data = "completed"
        with patch.object(player, "_on_book_finished"):
            player._on_audio_state_changed(ev)


def test_position_changed_respects_slider_drag(player_ctx):
    player, _, page = player_ctx
    player.build()
    page.update.reset_mock()
    player.slider_being_dragged = True
    player._on_position_changed(MagicMock(data=5000))
    page.update.assert_not_called()
    player.slider_being_dragged = False
    player._on_position_changed(MagicMock(data=5000))
    page.update.assert_called()


def test_play_pause_stop_seek_speed(player_ctx):
    player, _, page = player_ctx
    with patch("playbook.ui.player_page.ft.Audio") as A:
        A.return_value = MagicMock()
        player.load_book(_book())
    player.is_playing = True
    player._on_play_pause(MagicMock())
    player.audio.pause.assert_called()
    player.is_playing = False
    player._on_play_pause(MagicMock())
    player.audio.play.assert_called()
    player._on_stop(MagicMock())
    player._seek_relative(10)
    player.progress_slider.value = 50
    player._on_slider_change_end(MagicMock())
    player._on_speed_change(MagicMock())


def test_save_and_periodic_progress(player_ctx):
    player, _, _ = player_ctx
    with patch("playbook.ui.player_page.ft.Audio") as A:
        A.return_value = MagicMock()
        player.load_book(_book())
    with patch("playbook.ui.player_page.update_progress") as up:
        player.progress_slider.value = 44.0
        player._save_progress()
        up.assert_called_once_with(1, 44.0)
    with patch.object(player, "_save_progress") as sp:
        player.is_playing = True
        player._periodic_save()
        sp.assert_called()


def test_sleep_timer_off_and_cancel(player_ctx):
    player, _, page = player_ctx
    with patch("playbook.ui.player_page.ft.Audio") as A:
        A.return_value = MagicMock()
        player.load_book(_book())
    player.sleep_timer_dropdown.value = "off"
    player._on_sleep_timer_change(MagicMock())
    player._cancel_sleep_timer()


def test_reset_progress_dialog_and_apply(player_ctx):
    player, _, page = player_ctx
    with patch("playbook.ui.player_page.ft.Audio") as A:
        A.return_value = MagicMock()
        player.load_book(_book())
    player._confirm_reset_progress(MagicMock())
    dialog = page.dialog
    assert dialog is not None
    yes = dialog.actions[0]
    yes.on_click(MagicMock())
    no = dialog.actions[1]
    player._confirm_reset_progress(MagicMock())
    no.on_click(MagicMock())


def test_notify_mini_player_none(player_ctx):
    player, app, _ = player_ctx
    player.current_book = None
    player._notify_mini_player()
    app.update_mini_player.assert_called_with(book=None)


def test_on_book_finished_advances_or_stops(player_ctx):
    player, _, page = player_ctx
    with patch("playbook.ui.player_page.ft.Audio") as A:
        A.return_value = MagicMock()
        player.load_book(_book())
    player.playlist = [_book(), _book(id=2, file_path="/2.mp3")]
    player.current_playlist_index = 0
    with patch.object(player, "play_next") as pn:
        player._on_book_finished()
        pn.assert_called_once()
    player.playlist = [_book()]
    player.current_playlist_index = 0
    with patch.object(player, "_on_stop"):
        player._on_book_finished()


def test_remove_from_playlist_before_current_index(player_ctx):
    player, _, _ = player_ctx
    for i in range(1, 4):
        player.add_to_playlist(_book(id=i, file_path=f"/{i}.mp3"))
    player.current_playlist_index = 2
    with patch.object(player, "load_book"):
        player._remove_from_playlist(0)
    assert player.current_playlist_index == 1
