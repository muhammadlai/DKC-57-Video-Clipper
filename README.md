# AITZAZ AI / DKC 57 Video Clipper

**AITZAZ AI — Live Content Command Center** now ships in this repository.
It adds a real backend command center for **YouTube Live + STUMPS cricket
context + backend AI + rolling buffer + publishing queue**, while retaining
legacy DKC 57 clip-processing routes for on-demand video clipping.

Built on [OpenClip](https://github.com/aionixOS/Openclip) (MIT) by AIONIX.
See [NOTICE.md](NOTICE.md) for full provenance and attribution.

---

## What it does

Paste a YouTube link **or upload a video file**, pick your clip settings,
and hit **CREATE SHORTS**. Everything runs on your machine:

```
LONG VIDEO ─► UPLOAD/URL ─► TRANSCRIBE ─► ANALYZE ─► FIND BEST MOMENTS
     ─► CREATE SHORTS ─► 9:16 ─► CAPTIONS ─► REFRAME ─► PREVIEW ─► EXPORT
```

- **YouTube source** — downloads with yt-dlp, uses YouTube captions when
  available, falls back to local Whisper.
- **Local upload** — any common video file (mp4, mov, mkv, webm, avi);
  transcribed locally with Whisper. No cloud uploads, ever.
- **AI moment detection** — an LLM (OpenAI, Anthropic, Gemini, or local
  Ollama) reads the transcript and proposes the strongest moments, each
  with a title, reason, hashtags, tags and an AI score.
  **Turn it off** for evenly spaced cuts — no API key required.
- **9:16 reframe with face tracking** — MediaPipe (local) tracks speakers
  and the clip is dynamically cropped/zoomed to 1080×1920. Disable
  auto-reframe or face tracking per project.
- **Captions** — automatic subtitles burned in with several styles
  (Classic White, Yellow Bold, Neon Green, …).
- **Optional DKC 57 watermark** — off by default, never forced.
  Position (4 corners) and opacity adjustable per project or as a default.
- **Processing queue** — jobs run in the background with live
  WebSocket progress and the states
  `QUEUED → PROCESSING → COMPLETED | FAILED | RETRYING | CANCELLED`.
  Failures keep the source video, store the real error, and offer Retry.
- **Bulk processing** — upload 10 videos, get 10 background jobs and
  dozens of shorts.

> AI scores are **recommendations**, not a guarantee of viral performance.

## Features

| Area | Details |
|------|---------|
| Dashboard | Videos / Shorts / Processing counters, upload zone, YouTube quick-create, live processing queue with per-job cancel |
| Create Shorts workflow | Source (URL or file), number of shorts (1/3/5/10/custom), min/max duration, 9:16, captions on/off + style, auto reframe, face tracking, AI moment detection, watermark (position + opacity) |
| Video Library | Source videos + every generated short with thumbnails, duration, status, AI score; Preview / Edit / Regenerate / Export / Delete |
| Export | Direct MP4 download per short; clip API for programmatic export (see below) |
| Local-first | SQLite storage, local FFmpeg, local Whisper, local MediaPipe, optional Ollama — no paid SaaS required |

## Architecture

```
┌────────────────────────────┐        ┌──────────────────────────────────┐
│  Frontend (Next.js 16,    │  REST  │  Backend (FastAPI, port 8000)    │
│  React 19, Tailwind,      │◄──────►│                                  │
│  port 5000)               │  + WS  │  api.py      REST + WebSocket    │
│                           │        │  database  SQLite (aiosqlite)    │
└────────────────────────────┘        │  downloader yt-dlp (YouTube)     │
                                      │  transcriber captions → Whisper  │
                                      │  llm       map-reduce moments    │
                                      │  reframer  cut + face tracking   │
                                      │  captioner ASS burn-in           │
                                      │  watermark DKC 57 overlay        │
                                      │  ffmpeg_util portable FFmpeg     │
                                      └──────────────────────────────────┘
Storage: ./data (SQLite DB) · ./tmp (source videos + clips + thumbnails)
```

Processing runs as background jobs; progress streams over
`ws://…/ws/progress/{project_id}`. CPU/IO work (FFmpeg, Whisper, LLM)
runs in worker threads so the API stays responsive.

## Installation

### Docker (recommended)

Requirements: Docker + Docker Compose.

```bash
cp .env.example .env          # optional: API key, upload limit
docker compose up -d --build
```

- Frontend: **http://localhost:5000**
- Backend API + Swagger docs: **http://localhost:8000/docs**
- Data persists in `./data` (DB + videos + clips).

Optional fully-local AI (no API keys at all):

```bash
docker compose --profile ollama up -d ollama
ollama pull llama3            # or any instruct model
# Settings page → provider "Ollama"
```

> **Image size note:** the backend image installs `openai-whisper`
> (PyTorch) for local transcription, so it is large (~4–5 GB).

### Local (no Docker)

Requirements: **Python 3.11+**, **Node.js 18+**, **FFmpeg** on PATH.

```bash
bash setup.sh        # checks deps, creates venvs, installs everything
bash start.sh        # starts backend :8000 + frontend :5000
```

Or manually:

```bash
# backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python -m uvicorn api:app --host 0.0.0.0 --port 8000

# frontend (separate shell)
cd frontend
npm install
npm run dev          # port 5000
```

### FFmpeg setup

The backend resolves FFmpeg in this order:

1. `FFMPEG_PATH` / `FFPROBE_PATH` environment variables
2. `ffmpeg` / `ffprobe` on your system `PATH`
3. a bundled binary under `backend/bin/`

Install it with your package manager if it is missing:

```bash
# Ubuntu/Debian
sudo apt install ffmpeg
# macOS
brew install ffmpeg
# Windows
winget install Gyan.FFmpeg      # or choco install ffmpeg
```

Verify: `ffmpeg -version`. The Docker image ships FFmpeg — nothing to do.

### AI setup (moment detection)

Provider, model and API key are configured in **Settings** in the UI
(keys are stored **encrypted** in SQLite and never returned by the API).

| Provider | Notes |
|----------|-------|
| OpenAI | default model `gpt-4o` |
| Anthropic | default model `claude-3-5-sonnet-20241022` (or set your own) |
| Gemini | via `google-genai` |
| Ollama | **local, keyless** — `http://localhost:11434` (Docker: `http://ollama:11434`) |

Costs: paid providers bill per token (a 1-hour video ≈ several transcript
chunks + one ranking call — typically cents to a few cents). Ollama and
the “AI detection off” mode cost nothing. No paid service is required.

## Environment variables

Root (Docker Compose) — see [.env.example](.env.example):

| Var | Default | Purpose |
|-----|---------|---------|
| `CORS_ORIGIN` | `http://localhost:5000` | Frontend origin allowed by the backend |
| `MAX_UPLOAD_MB` | `10240` | Upload size limit (MB) |
| `D57_API_KEY` | *(empty = open)* | Enables API-key auth for all `/api/*` and the WebSocket |
| `OLLAMA_HOST` | `http://ollama:11434` | Ollama endpoint (Docker) |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend address the browser uses (build-time) |

Backend (`backend/.env`) — see [backend/.env.example](backend/.env.example):
`TMP_DIR`, `DB_PATH`, `CORS_ORIGIN`, `MAX_UPLOAD_MB`, `FFMPEG_PATH`,
`FFPROBE_PATH`, `D57_API_KEY`, `OLLAMA_HOST`.

Frontend (`frontend/.env.local`): `NEXT_PUBLIC_API_URL`,
`NEXT_PUBLIC_API_KEY` (only when the backend requires auth).

**Never commit real keys** — `.env*` files are git-ignored; only
placeholders are committed.

## Usage

1. **Create Shorts** (`/create`) — pick source, set clip options,
   **CREATE SHORTS**.
2. Watch the stage checklist (Transcribing → Finding moments → Creating
   clips → Captions → Rendering). You can leave the page — the job keeps
   running in the background queue.
3. **Review** the AI-recommended shorts (score shown as a percentage —
   a recommendation, not a guarantee): edit titles, reject weak ones,
   export the good ones, or regenerate all.
4. **Library** (`/library`) — browse every source video and short;
   preview, edit, regenerate, export, delete.
5. **Settings** — LLM provider/key, Whisper model, caption style,
   default watermark.

### Hand-off to DKC 57 Social AI

This project is independent of [DKC-57-Social-AI](https://github.com/).
Exported shorts are plain MP4 files you can feed to the Social AI
scheduler (upload media → schedule → publish to YouTube/Facebook):

```
Generated Clip → Export (MP4) → DKC 57 Social AI → Scheduler → YouTube + Facebook
```

## API

Base: `http://localhost:8000` · interactive docs at `/docs`.

| Method & path | Purpose |
|---------------|---------|
| `GET /api/health` | Liveness + FFmpeg availability |
| `GET /api/stats` | Dashboard counters (videos, shorts, processing, failed) |
| `POST /api/projects` | Create project from YouTube URL (+ optional `settings`) |
| `POST /api/projects/upload` | Create project from uploaded file (multipart) |
| `POST /api/projects/bulk` | Create many projects at once |
| `GET /api/projects` | List projects (newest first, clip counts) |
| `GET /api/projects/{id}` | Project detail incl. clips, config, error |
| `POST /api/projects/{id}/retry` | Retry a failed/completed job (source preserved) |
| `POST /api/projects/{id}/cancel` | Cancel a queued/running job |
| `DELETE /api/projects/{id}` | Delete project + clips + files |
| `GET /api/clips` | All clips across projects (library) |
| `PATCH /api/clips/{id}` | Rename a clip |
| `DELETE /api/clips/{id}` | Delete a clip |
| `GET /api/clips/{id}/download` | Stream the MP4 |
| `GET /api/caption-styles` | Available caption styles |
| `GET/POST /api/settings` | Read/update settings (keys never returned) |
| `WS /ws/progress/{id}` | Live job progress `{stage, percent, message}` |

When `D57_API_KEY` is set, every `/api/*` call needs `X-API-Key: <key>`
(or `Authorization: Bearer <key>`); the WebSocket takes `?key=<key>`.

## Processing pipeline (what actually happens)

1. **Source** — yt-dlp download, or the uploaded file as-is.
2. **Transcribe** — YouTube manual captions → auto captions → yt-dlp
   captions → local Whisper (`base`/`small`/`medium`, selectable).
3. **Analyze** — map-reduce over transcript chunks (≤8 min each) with the
   configured LLM; candidates ranked; final N validated against your
   min/max duration. Off → evenly spaced local cuts.
4. **Cut** — FFmpeg stream-copy cut per suggestion.
5. **Reframe** — MediaPipe face detection (1 fps sampling) drives a
   dynamic 9:16 crop/zoom (sendcmd); static fallbacks included.
   Disabled → original framing kept (stream copy).
6. **Captions** — word-timed ASS file burned with FFmpeg (style selectable).
7. **Watermark** — optional logo overlay (position/opacity).
8. **Save** — clip + mid-frame thumbnail + metadata to SQLite.

Cancellations take effect at stage boundaries; failures store the real
error and keep the source video for Retry.

## Tests

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/python -m pytest tests -q
```

48 tests: database, LLM suggestion logic (incl. custom durations and the
even-spacing fallback), watermark filter construction, caption/ASS
generation, FFmpeg resolution, all REST endpoints (auth included), and
**real FFmpeg integration** (cut → 1080×1920 reframe → caption burn →
watermark burn → thumbnail). The integration tests skip automatically if
no FFmpeg is available.

Frontend: `cd frontend && npm ci && npm run build` (type-check +
production build).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ffmpeg not found` error on a job | Install FFmpeg or set `FFMPEG_PATH` (see FFmpeg setup). `GET /api/health` reports availability. |
| Uploaded video fails at transcribing | No speech detected, or `openai-whisper` not installed locally. In Docker it is preinstalled. |
| `Invalid API key` at analyzing | Fix the key in Settings, or switch provider, or disable AI moment detection. |
| `Rate limit hit` | The LLM client backs off automatically; try again later or use a different provider/Ollama. |
| Upload rejected 413 | Raise `MAX_UPLOAD_MB`. |
| 401 from the API | `D57_API_KEY` is set — send `X-API-Key` (frontend does this automatically when built with the same key). |
| Frontend can't reach backend | Set `NEXT_PUBLIC_API_URL` (Docker: rebuild with the compose arg) to the address your **browser** uses. |
| Face tracking slow | It samples 1 fps with MediaPipe — expected. Disable Face Tracking for faster jobs (static 9:16 crop). |
| Jobs stuck after server restart | In-flight jobs don't survive a restart; hit **REGEN/Retry** in the Library — the source video is still on disk. |

## License / attribution

- **OpenClip (foundation):** MIT — Copyright (c) 2026 AIONIX.
  Upstream: <https://github.com/aionixOS/Openclip> at commit
  `3b7873b690deb7879bde7dd1592ae2e343d58dbd`. The [LICENSE](LICENSE)
  file and original copyright notices are preserved; see
  [NOTICE.md](NOTICE.md) for what is upstream and what is original DKC 57 work.
- **DKC 57 additions** (branding, dashboard, library, workflow UI,
  upload/bulk/retry/cancel/watermark/stats API, Docker, tests, docs):
  original DKC 57 work, clearly separable in the file tree.
- Runtime dependencies (FFmpeg, yt-dlp, MediaPipe, Whisper, Pillow,
  FastAPI, Next.js, …) each carry their own open-source licenses as
  declared in `requirements.txt` / `package.json`.

## Relationship to OpenClip

This project **is** OpenClip, rebranded and extended:

- Unchanged: the core pipeline (download → transcribe → LLM moments →
  cut → face-tracking reframe → captions), the SQLite data model,
  settings encryption, caption styles, and the WebSocket progress design.
- Fixed: the hard-coded Windows FFmpeg path (now portable on
  Linux/macOS/Windows), missing Docker support, the wrong frontend port
  printed by `start.sh`, no local-file source, no per-project clip
  settings, no cancel/retry, no queue visibility.
- Added: everything under “Features” above.
