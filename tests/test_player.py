import pytest
from unittest.mock import MagicMock

from playbook.models.book import Book
from playbook.ui.player_page import PlayerPage
import flet as ft


@pytest.fixture
def mock_page():
    page = MagicMock()
    page.services = []  # flet-audio
    page.dialog = None
    page.update = MagicMock()
    page.show_snack_bar = MagicMock()
    return page


@pytest.fixture
def app(mock_page):
    app = MagicMock(page=mock_page)
    app.update_mini_player = MagicMock()
    return app


@pytest.fixture
def player_page(app):
    return PlayerPage(app)


def test_save_progress_calls_update(monkeypatch, player_page):
    # Мокаем update_progress из БД
    mock_update = MagicMock()
    monkeypatch.setattr("playbook.ui.player_page.update_progress", mock_update)

    player_page.current_book = Book(
        id=1,
        title="Test",
        duration=100,
        progress=40,
        file_path="/fake/test.mp3",  # ← обязательно!
    )
    player_page.progress_slider = MagicMock(value=40.0)
    player_page._save_progress()
    mock_update.assert_called_once_with(1, 40.0)


def test_seek_relative_forward(player_page):
    player_page.current_book = Book(
        id=2, title="Test2", duration=200, progress=100, file_path="/fake/test2.mp3"
    )
    player_page.audio = MagicMock()
    player_page.progress_slider = MagicMock(value=100.0)
    player_page._seek_relative(15)
    # Проверяем, что seek был вызван с позицией 115 * 1000 мс
    player_page.audio.seek.assert_called_with(115 * 1000)


def test_on_stop_resets_position(player_page):
    player_page.current_book = Book(
        id=3, title="Test3", duration=100, progress=50, file_path="/fake/test3.mp3"
    )
    player_page.audio = MagicMock()
    player_page.progress_slider = MagicMock(value=50.0)
    player_page.play_button = MagicMock()
    player_page._on_stop(None)

    player_page.audio.pause.assert_called_once()
    player_page.audio.seek.assert_called_with(0)
    assert player_page.progress_slider.value == 0.0
    assert player_page.play_button.icon == ft.icons.PLAY_ARROW
