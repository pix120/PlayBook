# add_test_books.py
import sys

sys.path.insert(0, "src")
from playbook.db.connection import set_db_path
from playbook.db.database import initialize_db, add_book
from playbook.models.book import Book, BookStatus
from pathlib import Path
from datetime import datetime

set_db_path(Path("data/playbook.db"))
initialize_db()

books = [
    Book(
        title="Гарри Поттер и философский камень",
        author="Дж.К. Роулинг",
        duration=8 * 3600 + 30 * 60,  # 8 ч 30 мин
        file_path="/fake/hp1.mp3",
        status=BookStatus.STARTED,
        progress=3600,  # 1 час
        date_added=datetime.now(),
    ),
    Book(
        title="1984",
        author="Джордж Оруэлл",
        duration=11 * 3600,
        file_path="/fake/1984.mp3",
        status=BookStatus.NEW,
        date_added=datetime.now(),
    ),
    Book(
        title="Мастер и Маргарита",
        author="Михаил Булгаков",
        duration=16 * 3600,
        file_path="/fake/master.mp3",
        status=BookStatus.FINISHED,
        progress=16 * 3600,
        date_added=datetime.now(),
    ),
]

for b in books:
    add_book(b)
print("Тестовые книги добавлены.")
