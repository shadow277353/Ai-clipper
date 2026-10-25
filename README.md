# Auto Clipper

Auto Clipper is a self-hostable AI-assisted long-video-to-short-clips web app. Upload a video, automatically detect promising segments, generate vertical clips, optionally add Whisper subtitles, and optionally publish clips to YouTube.

## Features

- Upload common video formats with size limits
- Automatic clip candidate generation using audio peaks and scene-change signals
- Optional speech transcription and subtitle burn-in with faster-whisper
- Vertical 9:16 output with FFmpeg
- Download generated clips
- Optional YouTube upload via OAuth credentials
- Simple responsive browser UI and background processing
- Dockerfile and Render deployment configuration

## Deploy

The easiest deployment is Render using the included `Dockerfile` and `render.yaml`. Video processing is CPU/RAM intensive; use a paid instance for longer videos. Set a persistent disk if you want uploads and clips to survive redeploys.

Environment variables:

- `SECRET_KEY`: set a random secret in production
- `MAX_UPLOAD_MB`: upload limit (default 800)
- `ENABLE_TRANSCRIPTION`: `true` to enable Whisper subtitles (downloads a model on first use)
- `YOUTUBE_CLIENT_SECRETS_JSON`: optional contents of a Google OAuth client secrets JSON file
- `YOUTUBE_TOKEN_JSON`: optional OAuth token JSON; never commit credentials

YouTube publishing is optional and requires your own Google OAuth setup and YouTube Data API access. The app does not upload without an explicit action in the UI.

## Run locally

Install FFmpeg, Python 3.11+, then:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:10000.

## Important

This is a starter production-oriented MVP, not a promise of viral performance. Clip ranking is heuristic (audio energy + scene changes); transcription is optional. Review clips and rights before publishing. Do not upload content you do not have permission to use.
