"""Unit tests for Book model helpers."""

from playbook.models.book import Book


def test_progress_percent_clamped():
    b = Book(
        title="x",
        duration=100,
        file_path="/a.mp3",
        progress=150,
    )
    assert b.progress_percent == 100.0


def test_progress_percent_zero_duration():
    b = Book(title="x", duration=0, file_path="/a.mp3", progress=5)
    assert b.progress_percent == 0.0


def test_duration_str_hours():
    b = Book(title="x", duration=3665, file_path="/a.mp3")
    assert b.duration_str == "01:01:05"


def test_progress_str_negative_seconds():
    b = Book(title="x", duration=100, file_path="/a.mp3", progress=-1)
    assert b.progress_str == "00:00"


def test_format_time_edge_seconds():
    assert Book._format_time(59.9) == "00:59"
