from pathlib import Path
from playbook.db.connection import set_db_path
from playbook.db.database import initialize_db
from playbook.scanner import scan_and_update_library


def main():
    set_db_path(Path("data/playbook.db"))
    initialize_db()

    # Укажи здесь реальную папку с аудиокнигами (или создай тестовую)
    root_folders = [Path.home() / "Аудиокниги"]
    print("Начинаем сканирование...")
    for event in scan_and_update_library(root_folders):
        if event["type"] == "progress":
            print(f"[{event['current']}/{event['total']}] {event['file']}")
        elif event["type"] == "book_added":
            print(f"  + Добавлена: {event['book'].title}")
        elif event["type"] == "book_updated":
            print(f"  * Обновлена: {event['book'].title}")
        elif event["type"] == "finished":
            print(f"Готово! Добавлено: {event['added']}, обновлено: {event['updated']}")


if __name__ == "__main__":
    main()
