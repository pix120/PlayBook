# PlayBook

[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)

PlayBook is a desktop audiobook library and player built with **Python**, **Flet 0.24.1**, and **SQLite**. It scans folders for audio files, stores metadata and listening progress, and offers a simple library grid/list, full player with playlist, sleep timer, and a mini player bar.

## Features

- SQLite library with migrations, progress, and book status (new / started / finished)
- Folder scan (MP3, M4B, M4A, FLAC, Ogg, etc.) with **mutagen** metadata and optional embedded cover extraction
- **Library** page: status filters, grid/list toggle, tap to add to playlist and open the player
- **Player**: cover, seek slider, speed, skip ±15s, previous/next in playlist, reset progress, sleep timer (fade and stop)
- **Settings**: library paths, dark/light theme, scan with progress, save config to `config/user_config.json`
- **Mini player**: cover, title, progress strip, play/pause and next; tap the title area to open the player

## Requirements

- Python 3.10+
- OS audio support appropriate for Flet’s `Audio` control (see [Flet docs](https://flet.dev/docs/controls/audio/))

## Installation

```bash
git clone https://github.com/OWNER/REPO.git
cd REPO
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Default cover asset

If `assets/default_cover.png` is missing, generate it (requires Pillow, included in dev requirements):

```bash
pip install Pillow
python assets/generate_default_cover.py
```

## Usage

From the repository root (so `assets/` resolves correctly):

```bash
source .venv/bin/activate
python src/main.py
```

Flet **0.24.1** uses `ft.app(main)` as the entrypoint; newer Flet versions may expose `ft.run` instead.

The app creates `data/playbook.db` by default (see `src/main.py` and config). Add audiobook folders under **Settings**, then **Refresh library**.

## Development

Install runtime and dev dependencies:

```bash
pip install -r requirements-dev.txt
```

Run tests (coverage must be ≥ 80%):

```bash
pytest tests/
```

Lint and format:

```bash
flake8 src tests
black --check src tests
```

Project layout uses a **`src`** tree (`src/playbook/`). Pytest is configured with `pythonpath = ["src"]` and `--import-mode=importlib` so imports and coverage stay consistent.

## CI

GitHub Actions runs `flake8`, `black --check`, and `pytest` on Python 3.10 and 3.12. Replace `OWNER/REPO` in the badge URL above with your GitHub user or organization and repository name.

## License

This project is licensed under the **MIT License**; see the [`LICENSE`](LICENSE) file.
