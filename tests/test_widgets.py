import pytest
import flet as ft
from playbook.models.book import Book, BookStatus
from playbook.ui.widgets import BookGridCard, BookListItem


@pytest.fixture
def sample_book():
    return Book(
        id=1,
        title="Тестовая",
        author="Автор",
        duration=100.0,
        file_path="/fake/test.mp3",
        cover_path=None,
        progress=30.0,
        status=BookStatus.STARTED,
    )


def test_grid_card_creation(sample_book):
    card = BookGridCard(sample_book, on_click=lambda b: None)
    assert isinstance(card, ft.Container)
    assert isinstance(card.content, ft.Stack)
    image = card.content.controls[0]
    assert isinstance(image, ft.Image)
    # Без обложки должна использоваться заглушка
    assert image.src == "assets/default_cover.png"


def test_list_item_creation(sample_book):
    item = BookListItem(sample_book, on_click=lambda b: None)
    row = item.content
    assert isinstance(row, ft.Row)
    images = [c for c in row.controls if isinstance(c, ft.Image)]
    assert len(images) == 1
    text_controls = [c for c in row.controls if isinstance(c, ft.Text)]
    assert len(text_controls) > 0
