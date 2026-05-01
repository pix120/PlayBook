import os
from pathlib import Path
from typing import List, Optional, Iterator, Tuple
import mutagen
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
from mutagen.wave import WAVE

from .models.book import Book, BookStatus
from .db.database import get_book_by_path, add_book, update_book, get_all_books

AUDIO_EXTENSIONS = {".mp3", ".m4b", ".m4a", ".ogg", ".flac", ".wav", ".opus"}


def find_audio_files(paths: List[Path]) -> Iterator[Path]:
    """
    генератор который рекурсивно обходит каждый путь из списка и выдает путь к аудиофайлу.
    """

    for root_path in paths:
        if not root_path.exists():
            continue
        for (
            dirpath,
            dirnames,
            filenames,
        ) in os.walk(root_path):
            for filename in filenames:
                file_path = Path(dirpath) / filename
                if file_path.suffix.lower() in AUDIO_EXTENSIONS:
                    yield file_path


def extract_metadata(file_path: Path) -> dict:
    """
    Извлекает метаданные аудиокниги из файла.
    Возвращает словарь с полями:
        title: str
        author: str
        duration: float (в секундах)
        cover_data: bytes или None
    """
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

    if isinstance(audio, MP3):
        # MP3 теги: ID3
        if audio.tags:
            title = str(audio.tags.get("TIT2", ""))
            author = str(audio.tags.get("TPE1", author))
    elif isinstance(audio, MP4):
        # M4B/M4A теги: MP4
        if audio.tags:
            title = str(audio.tags.get("\xa9nam", [""])[0])
            author = str(audio.tags.get("\xa9ART", [author])[0])
    elif isinstance(audio, FLAC):
        if audio.tags:
            title = str(audio.tags.get("title", [""])[0])
            author = str(audio.tags.get("artist", [author])[0])
    elif isinstance(audio, (OggVorbis, OggOpus)):
        if audio.tags:
            title = str(audio.tags.get("title", [""])[0])
            author = str(audio.tags.get("artist", [author])[0])
    elif isinstance(audio, WAVE):
        # WAV обычно без тегов
        pass

    # Если название пустое или отсутствует, используем имя файла
    if not title:
        title = file_path.stem

    # Обложка
    cover_data = None
    if isinstance(audio, MP3) and audio.tags:
        for tag in audio.tags.values():
            if tag.FrameID == "APIC":
                cover_data = tag.data
                break
    elif isinstance(audio, MP4) and audio.tags:
        if "covr" in audio.tags:
            cover_data = bytes(audio.tags["covr"][0])
    elif isinstance(audio, FLAC) and audio.pictures:
        cover_data = audio.pictures[0].data
    elif isinstance(audio, (OggVorbis, OggOpus)):
        # У Ogg обложка может лежать в metadata_block_picture
        if "metadata_block_picture" in audio.tags:
            import base64

            raw = base64.b64decode(audio.tags["metadata_block_picture"][0])
            # Парсить можно, но для простоты пока пропустим
            pass

    return {
        "title": title,
        "author": author,
        "duration": duration,
        "cover_data": cover_data,
    }


def scan_and_update_library(root_paths: List[Path]) -> Iterator[dict]:
    """
    Сканирует папки, обновляет БД.
    Возвращает генератор событий с состоянием процесса:
        {"type": "progress", "current": int, "total": int, "file": str}
        {"type": "book_updated", "book": Book}
        {"type": "book_added", "book": Book}
        {"type": "finished", "added": int, "updated": int}
    """
    # Получаем все существующие в БД книги для быстрой проверки дубликатов
    existing_books = {book.file_path: book for book in get_all_books()}

    # Собираем список всех найденных файлов, чтобы иметь общее количество
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
        # Проверяем, есть ли уже книга с таким путём
        if file_path_str := str(file_path) in existing_books:
            existing_book = existing_books[str(file_path)]
            # Обновляем метаданные, но сохраняем пользовательские поля
            existing_book.title = meta["title"]
            existing_book.author = meta["author"]
            existing_book.duration = meta["duration"]
            if meta["cover_data"]:
                existing_book.cover_path = "embedded"  # заглушка
            update_book(existing_book)
            updated_count += 1
            yield {"type": "book_updated", "book": existing_book}
        else:
            new_book = Book(
                title=meta["title"],
                author=meta["author"],
                duration=meta["duration"],
                file_path=str(file_path),
                cover_path="embedded" if meta["cover_data"] else None,
                status=BookStatus.NEW,
            )
            added_book = add_book(new_book)
            added_count += 1
            yield {"type": "book_added", "book": added_book}
            # Добавляем в кэш, чтобы не считать дубликатами в рамках одного сканирования
            existing_books[str(file_path)] = added_book

    yield {
        "type": "finished",
        "added": added_count,
        "updated": updated_count,
    }
