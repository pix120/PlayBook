from __future__ import annotations

import os
from pathlib import Path
from typing import List, Iterator, Optional
import mutagen

from .models.book import Book, BookStatus
from .db.database import get_book_by_path, add_book, update_book, get_all_books
from .cover_manager import save_cover

AUDIO_EXTENSIONS = {".mp3", ".m4b", ".m4a", ".ogg", ".flac", ".wav", ".opus"}


def find_audio_files(paths: List[Path]) -> Iterator[Path]:
    """Генератор, рекурсивно обходящий папки и возвращающий пути аудиофайлов."""
    for root_path in paths:
        if not root_path.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root_path):
            for filename in filenames:
                file_path = Path(dirpath) / filename
                if file_path.suffix.lower() in AUDIO_EXTENSIONS:
                    yield file_path


def extract_metadata(file_path: Path) -> dict:
    """Извлекает метаданные аудиокниги. Возвращает словарь с ключами title, author, duration, cover_data."""
    try:
        audio = mutagen.File(str(file_path))
    except Exception:
        return {
            "title": file_path.stem,
            "author": "Неизвестный автор",
            "duration": 0.0,
            "cover_data": None,
        }

    if audio is None:
        return {
            "title": file_path.stem,
            "author": "Неизвестный автор",
            "duration": 0.0,
            "cover_data": None,
        }

    duration = 0.0
    if hasattr(audio, "info") and hasattr(audio.info, "length"):
        duration = audio.info.length

    title = None
    author = "Неизвестный автор"

    if isinstance(audio, mutagen.mp3.MP3):
        if audio.tags:
            title = str(audio.tags.get("TIT2", ""))
            author = str(audio.tags.get("TPE1", author))
    elif isinstance(audio, mutagen.mp4.MP4):
        if audio.tags:
            title = str(audio.tags.get("\xa9nam", [""])[0])
            author = str(audio.tags.get("\xa9ART", [author])[0])
    elif isinstance(audio, mutagen.flac.FLAC):
        if audio.tags:
            title = str(audio.tags.get("title", [""])[0])
            author = str(audio.tags.get("artist", [author])[0])
    elif isinstance(audio, (mutagen.oggvorbis.OggVorbis, mutagen.oggopus.OggOpus)):
        if audio.tags:
            title = str(audio.tags.get("title", [""])[0])
            author = str(audio.tags.get("artist", [author])[0])

    if not title:
        title = file_path.stem

    cover_data = None
    if isinstance(audio, mutagen.mp3.MP3) and audio.tags:
        for tag in audio.tags.values():
            if tag.FrameID == "APIC":
                cover_data = tag.data
                break
    elif isinstance(audio, mutagen.mp4.MP4) and audio.tags:
        if "covr" in audio.tags:
            cover_data = bytes(audio.tags["covr"][0])
    elif isinstance(audio, mutagen.flac.FLAC) and audio.pictures:
        cover_data = audio.pictures[0].data
    # Ogg обложки пока не обрабатываем для простоты

    return {
        "title": title,
        "author": author,
        "duration": duration,
        "cover_data": cover_data,
    }


def scan_and_update_library(root_paths: List[Path]) -> Iterator[dict]:
    """
    Сканирует папки, обновляет БД.
    Генератор событий: progress, book_updated, book_added, finished.
    """
    existing_books = {book.file_path: book for book in get_all_books()}
    audio_files = list(find_audio_files(root_paths))
    total_files = len(audio_files)
    added_count = 0
    updated_count = 0

    for idx, file_path in enumerate(audio_files, 1):
        yield {
            "type": "progress",
            "current": idx,
            "total": total_files,
            "file": str(file_path),
        }

        meta = extract_metadata(file_path)

        cover_path = None
        if meta["cover_data"]:
            try:
                saved_cover_path = save_cover(str(file_path), meta["cover_data"])
                cover_path = str(saved_cover_path)
            except Exception as exc:
                print(f"Не удалось сохранить обложку для {file_path}: {exc}")

        if str(file_path) in existing_books:
            existing_book = existing_books[str(file_path)]
            existing_book.title = meta["title"]
            existing_book.author = meta["author"]
            existing_book.duration = meta["duration"]
            existing_book.cover_path = cover_path
            update_book(existing_book)
            updated_count += 1
            yield {"type": "book_updated", "book": existing_book}
        else:
            new_book = Book(
                title=meta["title"],
                author=meta["author"],
                duration=meta["duration"],
                file_path=str(file_path),
                cover_path=cover_path,
                status=BookStatus.NEW,
            )
            added_book = add_book(new_book)
            added_count += 1
            yield {"type": "book_added", "book": added_book}
            existing_books[str(file_path)] = added_book

    yield {
        "type": "finished",
        "added": added_count,
        "updated": updated_count,
    }
