from unittest.mock import MagicMock

from playbook.models.book import Book
from playbook.ui.player_page import PlayerPage


def test_add_to_empty_playlist():
    page = MagicMock()
    page.services = []  # вместо overlay
    app = MagicMock(page=page, pages={})
    app.update_mini_player = MagicMock()
    player = PlayerPage(app)
    player.audio = MagicMock()

    book = Book(
        id=1, title="Book1", author="A", duration=100, file_path="/b1.mp3", progress=0
    )
    player.add_to_playlist(book)

    assert len(player.playlist) == 1
    assert player.current_playlist_index == 0
