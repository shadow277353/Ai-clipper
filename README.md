---
title: Auto Clipper
emoji: ✂️
colorFrom: purple
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Auto Clipper

Auto Clipper is a self-hosted web app that turns uploaded long videos into vertical short clips. It includes an upload UI, FFmpeg rendering, optional Whisper speech transcription/subtitles, downloads, and an optional manual YouTube publishing action.

## Included features

- Upload MP4, MOV, MKV, WEBM, M4V, and AVI files (configurable size limit)
- Generate up to 10 candidate clips with configurable length
- Vertical 9:16 rendering (720 × 1280)
- Candidate selection based on scene-change signals with evenly spaced fallback segments
- Optional Whisper transcription and burned-in captions plus downloadable SRT files
- Manual YouTube upload, with title and privacy selection
- Docker deployment for Hugging Face Spaces and other Docker hosts

**Important:** This is an MVP, not a fully autonomous viral-content AI. Candidate selection is heuristic; it does not understand every video's meaning or guarantee engaging clips. YouTube publishing requires your own Google OAuth setup. Automatic scheduled posting, channel connection flow, and background monitoring are not included.

## Deploy on Hugging Face Spaces (free CPU)

1. Create a Space at https://huggingface.co/new-space.
2. Name it `ai-clipper`, choose **Docker** as the SDK, choose **CPU Basic** hardware, and set visibility to **Public** or **Private** as you prefer.
3. Copy the files in this repository into the new Space repository, including this README and the Dockerfile. The README front matter and Dockerfile are configured for port `7860`.
4. Wait for the Space to build, then open the Space's **App** page. The first build can take several minutes.
5. Test with a short video and keep subtitles off for the first test.

You can transfer files using Git if you have a computer with Git installed: clone both repositories, copy the project files into the Space clone, then commit and push to the Space's Git URL shown in its **Files** page. Do not copy `.git` from the GitHub repository into the Space repository.

### Free-tier limitations

- CPU Basic has limited compute; video encoding and Whisper transcription may be slow or run out of memory on long videos.
- Free Spaces may sleep when unused and have limited ephemeral storage. Uploaded videos and generated clips can disappear after a restart or rebuild; do not use this as permanent storage.
- The app keeps job status in process memory, so a restart can lose the job page.
- Do not upload confidential videos to a public Space. Use private visibility if available for your use case, and review the platform's current storage and privacy terms.

## Run locally

Install Python 3.11+ and FFmpeg (including ffprobe), then:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:10000 locally. For subtitles, choose the Whisper option; the first run downloads the model and may need substantial RAM and disk space. Without subtitles, processing is lighter.

## Deploy on Render

1. Push this repository to GitHub.
2. In Render, choose **New → Blueprint** and select this repository, or create a Docker web service.
3. Review the included `render.yaml`. It configures a persistent disk, so the declared Starter instance is **not a free-tier deployment**.
4. Deploy and wait for the build to finish.
5. In Render's environment settings, make sure `SECRET_KEY` is a strong random value and `DATA_DIR=/data`.
6. Open the service URL and test with a short, non-sensitive video first.

## Optional YouTube upload

The app does not publish automatically. It uploads only after you press the per-clip **Publish this clip to YouTube** button.

1. Create a Google Cloud project and enable YouTube Data API v3.
2. Configure OAuth consent and obtain an authorized user OAuth token with the `https://www.googleapis.com/auth/youtube.upload` scope.
3. Add the token JSON as the `YOUTUBE_TOKEN_JSON` environment variable in your host's settings. Do not commit credentials or tokens to GitHub or a public Space.
4. Test with **Private** visibility first.

Tokens can expire or be revoked, and Google's API quota and verification rules apply. Public publishing is an explicit choice in the UI.

## Environment variables

- `SECRET_KEY`: Flask session secret; set a strong random value in production.
- `MAX_UPLOAD_MB`: maximum upload size, default `800`; host/proxy limits may be lower.
- `DATA_DIR`: storage directory, default `data`; Render uses `/data`.
- `WHISPER_MODEL`: optional faster-whisper model name, default `base`.
- `YOUTUBE_TOKEN_JSON`: optional authorized OAuth token JSON; never commit it.

## Troubleshooting

- **FFmpeg/ffprobe not found:** install FFmpeg locally. The Docker image installs it automatically.
- **Upload rejected:** check the file extension and `MAX_UPLOAD_MB`; hosting proxy limits may also apply.
- **Subtitle step fails:** try again without subtitles or use an instance with more RAM.
- **YouTube upload fails:** verify token validity, upload scope, API enablement, quota, and channel access.
- **Service restart loses job page:** job state is currently in memory; re-upload after a restart.

## Safety and rights

Only upload and publish material you own or are authorized to use. Review every generated clip before publishing. Keep the service private if your videos are confidential.
