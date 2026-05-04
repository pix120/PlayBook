import tempfile
from pathlib import Path
from playbook.cover_manager import get_cover_path_or_none, save_cover


def test_save_cover_creates_file(monkeypatch, tmp_path):
    monkeypatch.setattr("playbook.cover_manager.COVERS_DIR", tmp_path / "covers")
    fake_data = b"fake_image"
    book_path = "/books/test.m4b"
    result = save_cover(book_path, fake_data)
    assert result.exists()
    assert result.read_bytes() == fake_data


def test_get_cover_path_or_none():
    assert get_cover_path_or_none(None) is None
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(b"test")
        tf.flush()
        assert get_cover_path_or_none(tf.name) == tf.name
        Path(tf.name).unlink()
        assert get_cover_path_or_none(tf.name) is None
