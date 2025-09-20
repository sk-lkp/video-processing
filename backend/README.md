# Video Processing Backend

A FastAPI backend for video processing with FFmpeg, PostgreSQL, and Celery.

## Features

- Video upload with metadata extraction
- Video trimming
- Watermark and overlay support
- Multiple output qualities (1080p, 720p, 480p)
- Asynchronous processing with Celery
- Neon Postgres database

## Prerequisites

- Python 3.10+ (recommended 3.11)
- FFmpeg installed and available on PATH
- PostgreSQL (e.g., Neon) connection URL
- Redis server (for Celery broker and result backend)

## Setup

1. Clone the repository
   - Ensure your working directory is `backend/` when running commands below, because `.env` is loaded from `backend/.env` by `app/config.py` and static paths are relative to `backend/`.

2. Create a virtual environment and install dependencies
   - Windows (PowerShell):
     - `python -m venv .venv`
     - `.\.venv\Scripts\Activate.ps1`
     - `pip install -r requirements.txt`

3. Configure environment variables in `backend/.env`
   - The app reads env vars via `app/config.py` using `python-dotenv`.
   - Required keys:
     - `DATABASE_URL` (e.g., Neon PostgreSQL URL)
     - `REDIS_URL` (e.g., `redis://localhost:6379/0`)

4. Install FFmpeg
   - Option A (Chocolatey): `choco install ffmpeg` (run elevated PowerShell)
   - Option B: Download from https://ffmpeg.org/download.html, extract, and add `ffmpeg/bin` to your PATH.
   - Verify: `ffmpeg -version`

5. Start Redis
   - Easiest on Windows is Docker:
     - `docker run --name redis -p 6379:6379 -d redis:7`
   - Or use WSL/WSL2 with `sudo apt-get install redis` and run `redis-server`.

6. Initialize the database
   - No manual migration is required initially. Tables are created automatically on first run by `Base.metadata.create_all(bind=engine)` in `app/main.py`.
   - Alembic is included in `requirements.txt` for future schema migrations if needed.

7. Run the FastAPI server (from `backend/`)
   - `uvicorn app.main:app --reload`
   - API docs: http://localhost:8000/docs

8. Start the Celery worker (separate terminal, from `backend/`)
   - `celery -A app.celery_worker.celery_app worker --loglevel=info`
   - Requires Redis to be running and `REDIS_URL` correctly set.

## Assets and Static Files

The app expects certain demo assets to exist and will also create output directories automatically:

- Created at startup:
  - `static/videos/`
  - `static/watermarks/`
  - `static/assets/base_videos/`
  - `static/assets/overlay_videos/`
  - `static/assets/overlay_images/`

- Expected demo asset filenames (used by endpoints in `app/main.py`):
  - Base video: `static/assets/base_videos/A-roll.mp4`
  - B-roll videos: `static/assets/overlay_videos/B-roll 1.mp4`, `static/assets/overlay_videos/B-roll 2.mp4`
  - Overlay image: `static/assets/overlay_images/image overlay.png`

## API Documentation

Once running, access the OpenAPI docs at http://localhost:8000/docs

## Notes

- Do not edit `app/database.py` to change the DB URL. Instead, set `DATABASE_URL` in `.env`. `app/config.py` loads `.env` and injects it into the environment.
- Always run `uvicorn` and `celery` from the `backend/` directory so relative paths (static folders, `.env`) resolve correctly.