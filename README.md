# Auto Clipper

Auto Clipper is a self-hosted web app that turns uploaded long videos into vertical short clips. It includes an upload UI, FFmpeg rendering, optional Whisper speech transcription/subtitles, downloads, and an optional manual YouTube publishing action.

## Included features

- Upload MP4, MOV, MKV, WEBM, M4V, and AVI files (configurable size limit)
- Generate up to 10 candidate clips with configurable length
- Vertical 9:16 rendering (720 × 1280)
- Candidate selection based on scene-change signals with evenly spaced fallback segments
- Optional Whisper transcription and burned-in captions plus downloadable SRT files
- Manual YouTube upload, with title and privacy selection
- Docker and Render configuration

**Important:** This is a working MVP, not a fully autonomous viral-content AI. Candidate selection is heuristic; it does not understand every video's meaning or guarantee engaging clips. YouTube publishing requires your own Google OAuth setup. There is no automatic scheduled posting, channel connection flow, or background monitoring in this first version.

## Run locally

Install Python 3.11+ and FFmpeg (including ffprobe), then:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:10000. For subtitles, choose the Whisper option; the first run downloads the model and may need substantial RAM and disk space. Without subtitles, processing is lighter.

## Deploy on Render

1. Push this repository to GitHub.
2. In Render, choose **New → Blueprint** and select this repository, or create a Docker web service.
3. Review the included `render.yaml`. It configures a persistent disk, so the declared Starter instance is **not a free-tier deployment**.
4. Deploy and wait for the build to finish.
5. In Render's environment settings, make sure `SECRET_KEY` is a strong random value and `DATA_DIR=/data`.
6. Open the service URL and test with a short, non-sensitive video first.

Video encoding is CPU/RAM intensive. Long videos and Whisper transcription can exceed small-instance resource limits. Uploaded videos and generated clips use persistent disk space; monitor it and remove files you no longer need. The first MVP stores job status in process memory, so jobs/status do not survive service restarts.

## Optional YouTube upload

The app does not publish automatically. It uploads only after you press the per-clip **Publish this clip to YouTube** button.

1. Create a Google Cloud project and enable YouTube Data API v3.
2. Configure OAuth consent and obtain an authorized user OAuth token with the `https://www.googleapis.com/auth/youtube.upload` scope.
3. Add the token JSON as the `YOUTUBE_TOKEN_JSON` environment variable in Render. Do not commit credentials or tokens to GitHub.
4. Test with **Private** visibility first.

Tokens can expire or be revoked, and Google's API quota and verification rules apply. Public publishing is an explicit choice in the UI.

## Environment variables

- `SECRET_KEY`: Flask session secret; set a strong random value in production.
- `MAX_UPLOAD_MB`: maximum upload size, default `800`.
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
