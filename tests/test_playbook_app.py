from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import playbook.config as cfg
from playbook.models.book import Book, BookStatus
from playbook.ui.app import PlayBookApp
from playbook.ui.library_page import LibraryPage
from playbook.ui.settings_page import SettingsPage


@pytest.fixture
def user_config_path(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "USER_CONFIG_PATH", tmp_path / "user_config.json")
    cfg._config = None
    yield tmp_path / "user_config.json"
    cfg._config = None


@pytest.fixture
def sample_book():
    return Book(
        id=1,
        title="My Book",
        author="Author",
        duration=120.0,
        file_path="/tmp/fake.mp3",
        progress=30.0,
        status=BookStatus.STARTED,
    )


def _make_page():
    page = MagicMock()
    page.overlay = []
    return page


def test_playbook_app_init_nav_mini_window(
    user_config_path, monkeypatch, sample_book, tmp_path
):
    monkeypatch.setattr(
        "playbook.ui.library_page.get_all_books",
        lambda status=None: [sample_book],
    )
    page = _make_page()
    app = PlayBookApp(page)

    assert app.current_section == "library"
    page.add.assert_called_once()

    class NavEv:
        control = MagicMock(selected_index=1)

    app._on_nav_change(NavEv())
    assert app.current_section == "player"

    app.switch_to_section("settings")
    assert app.current_section == "settings"

    app.update_mini_player(sample_book, True, 60.0, 120.0)
    assert app.mini_player.visible is True
    app.update_mini_player(None)
    assert app.mini_player.visible is False

    player = app.pages["player"]
    player.audio = MagicMock()
    player.current_book = sample_book
    player._on_play_pause = MagicMock()
    app._mini_play_pause(MagicMock())
    player._on_play_pause.assert_called_once_with(None)

    player.play_next = MagicMock()
    app._mini_next(MagicMock())
    player.play_next.assert_called_once()

    player._save_progress = MagicMock()
    we = MagicMock()
    we.data = "close"
    page.on_window_event(we)
    player._save_progress.assert_called_once()
    page.window_destroy.assert_called_once()


def test_library_filters_view_toggle_and_select(
    user_config_path, monkeypatch, sample_book
):
    monkeypatch.setattr(
        "playbook.ui.library_page.get_all_books",
        lambda status=None: [sample_book],
    )

    def fake_load(self, book):
        self.current_book = book
        self.playlist = [book]
        self.current_playlist_index = 0

    monkeypatch.setattr(
        "playbook.ui.player_page.PlayerPage.load_book",
        fake_load,
    )

    page = _make_page()
    app = PlayBookApp(page)
    lib: LibraryPage = app.pages["library"]

    lib._set_filter(BookStatus.STARTED)
    lib._toggle_view_mode(MagicMock())
    lib._toggle_view_mode(MagicMock())
    lib._book_selected(sample_book)
    assert app.current_section == "player"
    lib.refresh_data()


def test_filter_buttons_initial_state(user_config_path, monkeypatch, sample_book):
    monkeypatch.setattr(
        "playbook.ui.library_page.get_all_books",
        lambda status=None: [sample_book],
    )
    page = _make_page()
    app = PlayBookApp(page)
    lib: LibraryPage = app.pages["library"]

    buttons = lib.filter_buttons
    assert len(buttons) == 4
    assert buttons[0].text == "All"
    assert buttons[1].text == "New"
    assert buttons[2].text == "Started"
    assert buttons[3].text == "Finished"


def test_set_filter_updates_button_colors(user_config_path, monkeypatch, sample_book):
    monkeypatch.setattr(
        "playbook.ui.library_page.get_all_books",
        lambda status=None: [sample_book],
    )
    page = _make_page()
    app = PlayBookApp(page)
    lib: LibraryPage = app.pages["library"]

    lib._set_filter(BookStatus.NEW)
    assert lib._filter == BookStatus.NEW

    lib._set_filter(BookStatus.STARTED)
    assert lib._filter == BookStatus.STARTED

    lib._set_filter(None)
    assert lib._filter is None


def test_set_filter_calls_render_books(user_config_path, monkeypatch, sample_book):
    monkeypatch.setattr(
        "playbook.ui.library_page.get_all_books",
        lambda status=None: [sample_book],
    )
    page = _make_page()
    app = PlayBookApp(page)
    lib: LibraryPage = app.pages["library"]
    page.update.reset_mock()
    lib._render_books = MagicMock()

    lib._set_filter(BookStatus.FINISHED)
    lib._render_books.assert_called_once()
    page.update.assert_called_once()


def test_delete_book_shows_dialog(user_config_path, monkeypatch, sample_book):
    monkeypatch.setattr(
        "playbook.ui.library_page.get_all_books",
        lambda status=None: [sample_book],
    )
    page = _make_page()
    app = PlayBookApp(page)
    lib: LibraryPage = app.pages["library"]

    lib._delete_book(sample_book)
    assert page.dialog is not None
    assert page.dialog.open is True
    assert page.dialog.title.value == "Delete book?"
    assert len(page.dialog.actions) == 2


def test_delete_book_confirm_deletes_and_refreshes(
    user_config_path, monkeypatch, sample_book
):
    monkeypatch.setattr(
        "playbook.ui.library_page.get_all_books",
        lambda status=None: [sample_book],
    )
    mock_delete = MagicMock()
    monkeypatch.setattr("playbook.ui.library_page.delete_book", mock_delete)

    page = _make_page()
    app = PlayBookApp(page)
    lib: LibraryPage = app.pages["library"]
    lib._render_books = MagicMock()

    lib._delete_book(sample_book)
    yes_button = page.dialog.actions[0]
    yes_button.on_click(MagicMock())

    mock_delete.assert_called_once_with(sample_book.id)
    lib._render_books.assert_called_once()


def test_delete_book_cancel_does_not_delete(
    user_config_path, monkeypatch, sample_book
):
    monkeypatch.setattr(
        "playbook.ui.library_page.get_all_books",
        lambda status=None: [sample_book],
    )
    mock_delete = MagicMock()
    monkeypatch.setattr("playbook.ui.library_page.delete_book", mock_delete)

    page = _make_page()
    app = PlayBookApp(page)
    lib: LibraryPage = app.pages["library"]

    lib._delete_book(sample_book)
    no_button = page.dialog.actions[1]
    no_button.on_click(MagicMock())

    mock_delete.assert_not_called()


def test_refresh_current_page(user_config_path, monkeypatch, sample_book):
    monkeypatch.setattr(
        "playbook.ui.library_page.get_all_books",
        lambda status=None: [sample_book],
    )
    page = _make_page()
    app = PlayBookApp(page)
    app.refresh_current_page()
    page.update.assert_called()


def test_settings_theme_save_add_path_scan(user_config_path, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "playbook.ui.library_page.get_all_books",
        lambda status=None: [],
    )

    class InlineThread:
        def __init__(
            self, group=None, target=None, name=None, args=(), kwargs=None, daemon=True
        ):
            self._target = target
            self._args = args or ()

        def start(self):
            if self._target:
                self._target(*self._args)

    def fake_scan(paths):
        yield {"type": "progress", "current": 1, "total": 1, "file": "/x.mp3"}
        yield {"type": "finished", "added": 1, "updated": 0}

    monkeypatch.setattr(
        "playbook.ui.settings_page.threading.Thread",
        InlineThread,
    )
    monkeypatch.setattr(
        "playbook.ui.settings_page.scan_and_update_library",
        fake_scan,
    )

    page = _make_page()
    app = PlayBookApp(page)
    sp: SettingsPage = app.pages["settings"]
    assert sp.build()

    ev = MagicMock()
    ev.control = MagicMock(value=False)
    sp._toggle_theme(ev)

    books_dir = tmp_path / "audiobooks"
    books_dir.mkdir()
    sp.path_fields[0].value = str(books_dir)
    sp._save_settings(MagicMock())
    page.show_snack_bar.assert_called()

    sp._add_path_field(MagicMock())
    sp.path_fields[-1].value = str(user_config_path.parent / "more")
    sp._start_scan(MagicMock())
    page.update.assert_called()
