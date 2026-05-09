import pytest
import flet as ft
from playbook.models.book import Book, BookStatus
from playbook.ui.widgets import BookGridCard, BookListItem, book_binding


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


def test_book_binding_creation():
    binding = book_binding("Test Title", "Test Author")
    assert isinstance(binding, ft.Container)


def test_grid_card_creation(sample_book):
    card = BookGridCard(sample_book, on_click=lambda b: None)
    assert isinstance(card, ft.Container)
    assert isinstance(card.content, ft.Stack)
    first = card.content.controls[0]
    assert isinstance(first, ft.Container)


def test_grid_card_has_popup_menu(sample_book):
    card = BookGridCard(sample_book, on_click=lambda b: None)
    assert len(card.content.controls) == 3
    menu_container = card.content.controls[2]
    assert isinstance(menu_container, ft.Container)
    assert isinstance(menu_container.content, ft.PopupMenuButton)
    assert len(menu_container.content.items) == 1
    assert menu_container.content.items[0].text == "Delete"


def test_grid_card_popup_menu_calls_on_delete(sample_book):
    calls = []
    card = BookGridCard(
        sample_book, on_click=lambda b: None, on_delete=lambda b: calls.append(b)
    )
    menu_container = card.content.controls[2]
    item = menu_container.content.items[0]
    item.on_click(None)
    assert len(calls) == 1
    assert calls[0] is sample_book


def test_grid_card_popup_menu_no_on_delete(sample_book):
    card = BookGridCard(sample_book, on_click=lambda b: None)
    menu_container = card.content.controls[2]
    item = menu_container.content.items[0]
    item.on_click(None)


def test_list_item_creation(sample_book):
    item = BookListItem(sample_book, on_click=lambda b: None)
    row = item.content
    assert isinstance(row, ft.Row)
    first = row.controls[0]
    assert isinstance(first, ft.Container)


def test_list_item_has_popup_menu(sample_book):
    item = BookListItem(sample_book, on_click=lambda b: None)
    row = item.content
    last = row.controls[-1]
    assert isinstance(last, ft.PopupMenuButton)
    assert len(last.items) == 1
    assert last.items[0].text == "Delete"


def test_list_item_popup_menu_calls_on_delete(sample_book):
    calls = []
    item = BookListItem(
        sample_book, on_click=lambda b: None, on_delete=lambda b: calls.append(b)
    )
    row = item.content
    menu = row.controls[-1]
    menu.items[0].on_click(None)
    assert len(calls) == 1
    assert calls[0] is sample_book


def test_list_item_popup_menu_no_on_delete(sample_book):
    item = BookListItem(sample_book, on_click=lambda b: None)
    row = item.content
    menu = row.controls[-1]
    menu.items[0].on_click(None)
