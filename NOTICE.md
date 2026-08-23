# NOTICE — DKC 57 Video Clipper

## Foundation: OpenClip (third-party open source)

This project is built on **OpenClip**, an open-source, local-first video
clipping engine.

- **Upstream repository:** https://github.com/aionixOS/Openclip.git
- **Upstream commit imported:** `3b7873b690deb7879bde7dd1592ae2e343d58dbd` (branch `main`)
- **License:** MIT (see `LICENSE`)
- **Copyright:** (c) 2026 AIONIX

The MIT license grants the rights to use, copy, modify, merge, publish and
distribute the OpenClip source. The `LICENSE` file and the copyright notices
in the OpenClip source files are **preserved** and must remain in any
distribution of this project.

## DKC 57 modifications (original work)

All DKC 57 changes layered on top of OpenClip are original work, clearly
distinguishable from the upstream source. They include, but are not limited
to:

- **Branding** — "DKC 57 Video Clipper / AI-Powered Shorts Generator" UI
  branding, DKC 57 DARKNIGHT visual identity (black / dark gray / red /
  white), logo, favicon, and theme (`frontend/public/logo.png`,
  `frontend/app/icon.svg`, `frontend/components/layout/DkcLogo.tsx`,
  `frontend/app/globals.css`, `frontend/tailwind.config.ts`,
  `frontend/app/layout.tsx`, `frontend/components/layout/Navbar.tsx`).
- **Dashboard & workflow UI** — DKC 57 dashboard, video library, shorts
  generation workflow, clip settings, watermark controls, bulk processing,
  and processing queue (`frontend/app/*`, `frontend/components/*`).
- **Backend extensions** — local video upload, clip settings, watermark
  rendering, processing queue statuses, retry/cancel, statistics, and export
  API endpoints (`backend/*`), clearly marked as DKC 57 additions.
- **Docker / self-hosting** — `Dockerfile.backend`, `Dockerfile.frontend`,
  `docker-compose.yml` (upstream OpenClip shipped without Docker).
- **Tests** — `backend/tests/*` (upstream shipped manual probe scripts only).
- **Documentation** — `README.md`, this `NOTICE.md`, `.env.example` updates.

Ownership of the DKC 57 branding and original code above belongs to DKC 57.
It does **not** extend to, or supersede, the OpenClip source code, which
remains under the MIT license and the AIONIX copyright.

## Third-party runtime dependencies (attribution)

The processing pipeline relies on well-known open-source tools, each with its
own license:

| Component | Used for | License |
|-----------|----------|---------|
| FFmpeg | video cutting, reframing, caption burn-in, watermark | LGPL/GPL |
| yt-dlp | YouTube download | Unlicense |
| MediaPipe | face detection / tracking | Apache-2.0 |
| OpenAI Whisper | local transcription | MIT |
| Pillow / numpy | image & frame analysis | Pillow / BSD-3 |
| FastAPI / aiosqlite / Uvicorn | backend framework & storage | BSD-3 / MIT |
| Next.js / React | frontend | MIT |

These are declared in `backend/requirements.txt` and
`frontend/package.json` and are installed from their official sources.

---

**Bottom line:** OpenClip remains OpenClip — MIT, © 2026 AIONIX. DKC 57
branded the UI and added original features on top, without removing any
original license, copyright notice, or attribution.
