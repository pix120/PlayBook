from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path
from typing import Iterator, List, Dict

import mutagen
import re

from .models.book import Book, BookStatus
from .db.database import add_book, get_all_books, update_book, delete_book
from .cover_manager import save_cover

AUDIO_EXTENSIONS = {".mp3", ".m4b", ".m4a", ".ogg", ".flac", ".wav", ".opus"}


def _natural_key(path: Path):
    """
    Ключ для естественной сортировки: разбивает имя на части (текст + числа).
    Пример: 'file10part2.txt' -> ['file', 10, 'part', 2, '.txt']
    """
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", path.name)
    ]


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
    """Extract metadata: title, author, duration, cover_data."""
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
            # MP3 теги возвращают объекты, преобразуем в строку аккуратно
            title_tag = audio.tags.get("TIT2")
            title = str(title_tag.text[0]) if title_tag else ""
            author_tag = audio.tags.get("TPE1")
            author = str(author_tag.text[0]) if author_tag else author
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
    Генератор событий: progress, book_updated, book_added, book_deleted, finished.
    Логика: каждая папка, содержащая аудиофайлы, становится одной книгой.
    """
    # 1. Удаляем старые записи, у которых file_path указывает на файл (старая схема)
    books_before = get_all_books()
    for book in books_before:
        if Path(book.file_path).is_file() or not Path(book.file_path).exists():
            delete_book(book.id)
            yield {"type": "book_deleted", "book": book}

    # 2. Получаем всё аудио и группируем по папкам
    audio_files = list(find_audio_files(root_paths))
    grouped: Dict[Path, List[Path]] = defaultdict(list)
    for f in audio_files:
        grouped[f.parent].append(f)

    folder_items = sorted(grouped.items(), key=lambda item: str(item[0]).lower())
    total_folders = len(folder_items)

    # 3. Загружаем текущие книги для обновления (уже без старых файловых)
    existing_books = {book.file_path: book for book in get_all_books()}
    added_count = 0
    updated_count = 0

    for idx, (folder_path, files_in_folder) in enumerate(folder_items, 1):
        sorted_files = sorted(files_in_folder, key=_natural_key)
        representative_file = sorted_files[0]
        yield {
            "type": "progress",
            "current": idx,
            "total": total_folders,
            "file": str(folder_path),
        }

        # Суммируем длительность всех файлов в папке
        total_duration = 0.0
        for chapter_file in sorted_files:
            meta = extract_metadata(chapter_file)
            total_duration += meta["duration"]

        first_meta = extract_metadata(representative_file)
        cover_path = None
        if first_meta["cover_data"]:
            try:
                saved_cover_path = save_cover(
                    str(representative_file), first_meta["cover_data"]
                )
                cover_path = str(saved_cover_path)
            except Exception as exc:
                print(f"Не удалось сохранить обложку для {representative_file}: {exc}")

        book_key = str(folder_path)  # теперь file_path = путь к папке

        if book_key in existing_books:
            existing_book = existing_books[book_key]
            existing_book.title = folder_path.name
            existing_book.author = first_meta["author"]
            existing_book.duration = total_duration
            existing_book.cover_path = cover_path
            update_book(existing_book)
            updated_count += 1
            yield {"type": "book_updated", "book": existing_book}
        else:
            new_book = Book(
                title=folder_path.name,
                author=first_meta["author"],
                duration=total_duration,
                file_path=book_key,
                cover_path=cover_path,
                status=BookStatus.NEW,
            )
            added_book = add_book(new_book)
            added_count += 1
            yield {"type": "book_added", "book": added_book}
            existing_books[book_key] = added_book

    # 4. Очистка: удаляем книги, чьи папки больше не существуют в сканируемых путях
    current_folders = {str(folder) for folder, _ in folder_items}
    all_books_in_db = get_all_books()
    for book in all_books_in_db:
        if book.file_path not in current_folders:
            delete_book(book.id)
            yield {"type": "book_deleted", "book": book}

    yield {
        "type": "finished",
        "added": added_count,
        "updated": updated_count,
    }
