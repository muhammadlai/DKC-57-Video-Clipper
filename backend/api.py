"""
api.py — FastAPI application for DKC 57 Video Clipper.

Main entry-point for the backend.  It wires together the database,
downloader, clipper, transcriber, LLM, reframer, captioner and
watermark modules behind a REST + WebSocket API that the Next.js
frontend consumes.

Pipeline stages (DKC 57 v2 — configurable):
    1. **Source**       — yt-dlp download (YouTube) or local upload.
    2. **Transcribe**   — YouTube captions or local Whisper.
    3. **Analyze**      — LLM suggests N best clip timestamps, or even
                          spacing when AI moment detection is off.
    4. **Cut clips**    — FFmpeg cut at the chosen timestamps.
    5. **Reframe**      — 9:16 reframe with face tracking (optional).
    6. **Captions**     — burn ASS captions (optional, style selectable).
    7. **Watermark**    — optional DKC 57 watermark overlay.
    8. **Save**         — clip + thumbnail records persisted to SQLite.

Job statuses: pending (QUEUED) → downloading/transcribing/analyzing/
processing (PROCESSING) → done (COMPLETED) | error (FAILED) |
cancelled (CANCELLED); retry sets "retrying" (RETRYING) before re-run.

Architecture notes:
    • ``_ws_connections`` maps ``project_id`` → set of WebSockets.
    • ``_cancel_events`` maps ``project_id`` → threading.Event used to
      abort a running job between stages (DKC 57 cancel support).
    • CPU/IO-bound work (FFmpeg, Whisper, LLM) runs in
      ``asyncio.to_thread`` to avoid blocking the event loop.

Based on OpenClip (MIT) by AIONIX — see NOTICE.md.
"""

import os
import re
import asyncio
import shutil
import logging
import threading
from typing import Optional

from fastapi import (  # type: ignore
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    BackgroundTasks,
    File,
    Form,
    UploadFile,
)
from fastapi.responses import FileResponse, JSONResponse  # type: ignore
from fastapi.staticfiles import StaticFiles  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from pydantic import BaseModel, Field  # type: ignore
from dotenv import load_dotenv  # type: ignore

load_dotenv()

import os
# Ensure bundled ffmpeg (if any) is available to subprocesses
_extra_paths = os.path.join(os.path.dirname(__file__), "bin")
os.environ["PATH"] = _extra_paths + ":" + os.environ.get("PATH", "")

# Internal modules
import database  # type: ignore
import downloader  # type: ignore
import clipper  # type: ignore
import transcriber  # type: ignore
import llm  # type: ignore
import reframer  # type: ignore
import captioner  # type: ignore
import watermark as watermark_mod  # type: ignore
import settings as settings_mod  # type: ignore
import ffmpeg_util  # type: ignore

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="DKC 57 Video Clipper API",
    description=(
        "DKC 57 Video Clipper — AI-Powered Shorts Generator. "
        "Local-first video clipping engine. "
        "Built on OpenClip (MIT) by AIONIX — see NOTICE.md for attribution."
    ),
    version="1.0.0",
)

# Allow the Next.js frontend dev server
_allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5000",
    os.getenv("CORS_ORIGIN", ""),
]
_allowed_origins = [o for o in _allowed_origins if o]
_replit_domain = os.environ.get("REPLIT_DEV_DOMAIN")
if _replit_domain:
    _allowed_origins.append(f"https://{_replit_domain}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://.*\.replit\.dev",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base directory for all temporary video / clip files
TMP_DIR = os.getenv("TMP_DIR", os.path.join(os.path.dirname(__file__), "..", "tmp"))
os.makedirs(TMP_DIR, exist_ok=True)

# DKC 57: max upload size (MB) — generous local default, configurable
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10240"))

# DKC 57: optional API-key auth (leave unset for open local access)
_API_KEY = os.getenv("D57_API_KEY", "").strip()

ALLOWED_UPLOAD_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}

PROCESSING_STATUSES = (
    "pending", "retrying", "downloading", "transcribing", "analyzing", "processing",
)

app.mount("/files", StaticFiles(directory=TMP_DIR), name="files")


# ---------------------------------------------------------------------------
# Optional API-key authentication (DKC 57)
# ---------------------------------------------------------------------------

@app.middleware("http")
async def dk57_auth_middleware(request, call_next):
    """
    When ``D57_API_KEY`` is set, every /api/* request must present the key
    via the ``X-API-Key`` header or an ``Authorization: Bearer <key>``
    header.  Static /files/* and docs stay open (local tooling).
    """
    if _API_KEY and request.url.path.startswith("/api/"):
        header = request.headers.get("x-api-key", "")
        auth = request.headers.get("authorization", "")
        bearer = auth[7:] if auth.lower().startswith("bearer ") else ""
        if header != _API_KEY and bearer != _API_KEY:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )
    return await call_next(request)


# ---------------------------------------------------------------------------
# WebSocket connection registry + cancel events
# ---------------------------------------------------------------------------

_ws_connections: dict[str, set[WebSocket]] = {}
_cancel_events: dict[str, threading.Event] = {}


class _PipelineCancelled(Exception):
    """Raised inside the pipeline when a cancel is requested (DKC 57)."""


async def _broadcast(project_id: str, stage: str, percent: float, message: str) -> None:
    """
    Send a progress update to every WebSocket client listening for
    the given project.
    """
    payload = {"stage": stage, "percent": percent, "message": message}
    dead: list[WebSocket] = []
    for ws in _ws_connections.get(project_id, set()):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_connections.get(project_id, set()).discard(ws)


def _raise_if_cancelled(project_id: str) -> None:
    event = _cancel_events.get(project_id)
    if event is not None and event.is_set():
        raise _PipelineCancelled()


# ---------------------------------------------------------------------------
# Startup event — initialise the database
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def on_startup() -> None:
    """Ensure the SQLite tables exist when the server starts."""
    await database.init_db()
    os.makedirs(TMP_DIR, exist_ok=True)
    logger.info("Database initialised, tmp dir ready at %s", TMP_DIR)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class WatermarkSettings(BaseModel):
    """DKC 57 watermark options (off by default, never forced)."""
    enabled: bool = False
    position: str = "bottom_right"
    opacity: float = Field(default=0.6, ge=0.05, le=1.0)


class ClipSettings(BaseModel):
    """
    DKC 57 clip settings — only options the pipeline actually supports.
    """
    num_clips: int = Field(default=5, ge=1, le=20)
    min_duration: float = Field(default=30.0, ge=5.0, le=300.0)
    max_duration: float = Field(default=90.0, ge=10.0, le=600.0)
    aspect_ratio: str = "9:16"          # fixed by the reframer
    captions: str = "none"              # "none" or a caption style key
    reframe: bool = True                # auto 9:16 reframe
    face_tracking: bool = True          # MediaPipe face tracking
    ai_detection: bool = True           # LLM moment detection
    watermark: Optional[WatermarkSettings] = None

    def model_dict(self) -> dict:
        d = self.model_dump()
        return d


class CreateProjectRequest(BaseModel):
    """Payload for creating a new project from a YouTube URL."""
    youtube_url: str
    settings: Optional[ClipSettings] = None


class BulkCreateRequest(BaseModel):
    """DKC 57 bulk processing: many URLs in one call."""
    youtube_urls: list[str]
    settings: Optional[ClipSettings] = None


class CreateProjectResponse(BaseModel):
    """Returned immediately after project creation."""
    project_id: str
    status: str


class BulkCreateResponse(BaseModel):
    """Result of a bulk creation."""
    projects: list[CreateProjectResponse]


class ProjectListItem(BaseModel):
    """One item in the projects list."""
    id: str
    title: Optional[str] = None
    youtube_url: str
    status: str
    created_at: str
    clip_count: int
    source_type: str = "youtube"
    error_message: Optional[str] = None


class ClipResponse(BaseModel):
    """Serialised clip record."""
    id: str
    project_id: str
    file_path: str
    start_time: float
    end_time: float
    duration: float
    reframed: bool
    captioned: bool
    title: Optional[str] = None
    reason: Optional[str] = None
    viral_score: Optional[int] = None
    face_count: Optional[int] = None
    layout_mode: Optional[str] = None
    caption_style: Optional[str] = None
    needs_user_confirm: bool = False
    hashtags: list[str] = []
    tags: list[str] = []
    thumbnail: Optional[str] = None
    created_at: str


class ProjectDetailResponse(BaseModel):
    """Full project detail including nested clips."""
    id: str
    title: Optional[str] = None
    youtube_url: str
    status: str
    created_at: str
    clips: list[ClipResponse] = []
    source_type: str = "youtube"
    source_file: Optional[str] = None
    error_message: Optional[str] = None
    config: Optional[dict] = None


class UpdateClipRequest(BaseModel):
    """DKC 57: rename a clip."""
    title: str = Field(min_length=1, max_length=200)


class StatsResponse(BaseModel):
    """DKC 57 dashboard counters."""
    videos: int
    shorts: int
    processing: int
    failed: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_settings(raw: Optional[dict]) -> dict:
    """Coerce a raw settings payload into the canonical dict (DKC 57)."""
    raw = dict(raw or {})
    wm_raw = raw.pop("watermark", None) or {}
    wm = watermark_mod.normalize_config(wm_raw)
    try:
        num_clips = max(1, min(20, int(raw.get("num_clips", 5))))
    except (TypeError, ValueError):
        num_clips = 5
    try:
        min_duration = max(5.0, min(300.0, float(raw.get("min_duration", 30.0))))
    except (TypeError, ValueError):
        min_duration = 30.0
    try:
        max_duration = max(min_duration, min(600.0, float(raw.get("max_duration", 90.0))))
    except (TypeError, ValueError):
        max_duration = max(90.0, min_duration)
    captions = raw.get("captions", "none")
    if captions not in captioner.CAPTION_STYLES:
        captions = "none"
    return {
        "num_clips": num_clips,
        "min_duration": min_duration,
        "max_duration": max_duration,
        "aspect_ratio": "9:16",
        "captions": captions,
        "reframe": bool(raw.get("reframe", True)),
        "face_tracking": bool(raw.get("face_tracking", True)),
        "ai_detection": bool(raw.get("ai_detection", True)),
        "watermark": wm,
    }


def _even_suggestions(
    duration: float,
    num_clips: int,
    min_duration: float,
    max_duration: float,
) -> list[dict]:
    """
    DKC 57 fallback when AI moment detection is OFF: cut evenly spaced
    segments.  No LLM, no network — purely local.
    """
    target = min(max((min_duration + max_duration) / 2.0, 15.0), max_duration)
    n = max(1, min(num_clips, int(duration // target) + 1))
    seg = duration / n
    out: list[dict] = []
    for i in range(n):
        start = i * seg
        end = min(start + target, duration)
        if end - start < 8.0:
            break
        out.append({
            "start": round(start, 2),
            "end": round(end, 2),
            "title": f"Segment {i + 1}",
            "reason": "Evenly spaced segment (AI moment detection off)",
            "viral_score": None,
            "hashtags": [],
            "tags": [],
        })
    return out


async def _generate_thumbnail(video_path: str, out_path: str) -> Optional[str]:
    """
    DKC 57: extract a mid-video frame as a thumbnail (best-effort —
    a failure here never fails the job).
    """
    try:
        duration = await asyncio.to_thread(clipper.get_video_duration, video_path)
    except Exception:
        duration = 2.0

    def _run() -> bool:
        try:
            ffmpeg = ffmpeg_util.get_ffmpeg()
            subprocess = __import__("subprocess")
            res = subprocess.run(
                [
                    ffmpeg, "-y", "-loglevel", "error",
                    "-ss", str(max(0.5, duration / 2)),
                    "-i", video_path,
                    "-frames:v", "1", "-q:v", "3",
                    out_path,
                ],
                capture_output=True, text=True, timeout=120,
            )
            return res.returncode == 0
        except Exception as exc:
            logger.warning("Thumbnail generation failed: %s", exc)
            return False

    ok = await asyncio.to_thread(_run)
    if ok and os.path.exists(out_path):
        return out_path
    return None


async def _clear_project_clips(project_id: str) -> None:
    """Remove a project's stored clips (DB rows + clip files) — DKC 57 retry."""
    project = await database.get_project(project_id)
    if project:
        for clip in project.get("clips", []):
            raw_path = clip.get("file_path", "")
            if raw_path.startswith("/files/"):
                path = os.path.join(TMP_DIR, raw_path[len("/files/"):])
                try:
                    if os.path.isfile(path):
                        os.remove(path)
                except OSError:
                    pass
    # Delete clip rows
    conn = await database._get_connection()
    try:
        await conn.execute("DELETE FROM clips WHERE project_id = ?", (project_id,))
        await conn.commit()
    except Exception as exc:
        logger.warning("Failed clearing clip rows: %s", exc)
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Background processing pipeline (DKC 57 v2)
# ---------------------------------------------------------------------------

async def _run_pipeline(project_id: str) -> None:
    """
    Execute the full pipeline in the background, honouring the project's
    stored clip settings (DKC 57).

    Steps:
        1. Source: download (YouTube) or use uploaded file.
        2. Transcribe (captions API → local Whisper).
        3. Analyze: LLM suggestions, or even spacing when AI is off.
        4. Cut + reframe clips (face tracking optional).
        5. Burn captions (optional).
        6. Watermark (optional).
        7. Thumbnails + save clip records.
    """
    project_dir = os.path.join(TMP_DIR, project_id)
    clips_dir = os.path.join(project_dir, "clips")
    os.makedirs(clips_dir, exist_ok=True)

    try:
        project = await database.get_project(project_id)
        if project is None:
            return
        youtube_url = project.get("youtube_url") or ""
        source_type = project.get("source_type") or "youtube"
        source_file = project.get("source_file")
        cfg = _normalize_settings(project.get("config"))

        loop = asyncio.get_running_loop()

        # ---- STEP 1: Source ----
        if source_type == "upload" and source_file and os.path.isfile(source_file):
            file_path = source_file
            title = project.get("title") or os.path.splitext(os.path.basename(source_file))[0]
            if title:
                await database.update_project_title(project_id, title)
            await _broadcast(project_id, "transcribing", 10, "Local video ready")
        else:
            await database.update_project_status(project_id, "downloading")
            await _broadcast(project_id, "downloading", 5, "Starting download…")

            def download_progress(percent: float, msg: str):
                _raise_if_cancelled(project_id)
                asyncio.run_coroutine_threadsafe(
                    _broadcast(project_id, "downloading", min(percent * 0.2 + 5, 25), msg),
                    loop,
                )

            result = await asyncio.to_thread(
                downloader.download_video,
                youtube_url,
                project_dir,
                download_progress,
            )
            file_path = result["file_path"]
            title = result["title"]
            await database.update_project_title(project_id, title)
            await _broadcast(project_id, "downloading", 25, "Download complete")

        _raise_if_cancelled(project_id)

        # ---- STEP 2: Transcribe ----
        await database.update_project_status(project_id, "transcribing")
        await _broadcast(project_id, "transcribing", 30, "Extracting transcript…")

        whisper_model = await settings_mod.get_setting("whisper_model") or "base"

        def transcript_progress(percent: float, msg: str):
            _raise_if_cancelled(project_id)
            scaled = 30 + (percent / 100) * 20  # 30-50 range
            asyncio.run_coroutine_threadsafe(
                _broadcast(project_id, "transcribing", scaled, msg),
                loop,
            )

        transcript_segments = await transcriber.extract_captions(
            youtube_url or None,
            file_path,
            progress_callback=transcript_progress,
            whisper_model=whisper_model,
        )

        if not transcript_segments:
            await database.update_project_status(project_id, "error")
            await database.update_project_error(
                project_id,
                "Could not extract a transcript. For uploaded videos this "
                "means local Whisper transcription found no speech (or "
                "openai-whisper is not installed).",
            )
            await _broadcast(project_id, "error", 0, "Could not extract a transcript for this video.")
            return

        _raise_if_cancelled(project_id)
        await _broadcast(project_id, "transcribing", 50, "Transcript ready")

        # ---- STEP 3: Analyze (AI moment detection, optional) ----
        video_duration = float(
            await asyncio.to_thread(clipper.get_video_duration, file_path)
        )

        if not cfg["ai_detection"]:
            suggestions = _even_suggestions(
                video_duration,
                cfg["num_clips"],
                cfg["min_duration"],
                cfg["max_duration"],
            )
            if not suggestions:
                await database.update_project_status(project_id, "error")
                await database.update_project_error(
                    project_id, "Video is too short to cut any clips."
                )
                await _broadcast(project_id, "error", 0, "Video is too short to cut clips.")
                return
            await _broadcast(
                project_id, "analyzing", 75,
                f"Planned {len(suggestions)} evenly spaced clips (AI off)",
            )
        else:
            await database.update_project_status(project_id, "analyzing")
            await _broadcast(project_id, "analyzing", 55, "AI analyzing video…")

            provider = await settings_mod.get_setting("llm_provider") or "openai"
            api_key = await settings_mod.get_setting("llm_api_key") or ""
            model = await settings_mod.get_setting("llm_model") or ""

            try:
                def analyze_progress(stage: str, percent: float, msg: str):
                    asyncio.run_coroutine_threadsafe(
                        _broadcast(project_id, stage, percent, msg),
                        loop,
                    )

                suggestions: list[dict] = await llm.get_clip_suggestions(
                    transcript_segments, provider, api_key, model, video_duration,
                    progress_callback=analyze_progress,
                    num_clips=cfg["num_clips"],
                    min_duration=cfg["min_duration"],
                    max_duration=cfg["max_duration"],
                )

            except Exception as e:
                msg = str(e).lower()
                if "401" in msg or "403" in msg:
                    err_msg = "Invalid API key. Check your settings."
                elif "429" in msg:
                    err_msg = "Rate limit hit. Wait a moment and try again."
                else:
                    err_msg = f"AI Error: {e}"
                await database.update_project_status(project_id, "error")
                await database.update_project_error(project_id, err_msg)
                await _broadcast(project_id, "error", 0, err_msg)
                return

            if not suggestions:
                await database.update_project_status(project_id, "error")
                await database.update_project_error(
                    project_id,
                    "AI could not find clip moments. Try a different video, "
                    "a different AI provider, or turn off AI moment detection "
                    "to use evenly spaced cuts.",
                )
                await _broadcast(project_id, "error", 0, "AI could not find clip moments.")
                return

            _raise_if_cancelled(project_id)
            await _broadcast(
                project_id, "analyzing", 75,
                f"Found {len(suggestions)} AI-recommended clips",
            )

        # ---- STEP 4-6: Cut, reframe, captions, watermark ----
        await database.update_project_status(project_id, "processing")

        for i, suggestion in enumerate(suggestions):
            _raise_if_cancelled(project_id)
            progress_pct = 75 + (i / max(1, len(suggestions)) * 18)
            await _broadcast(project_id, "processing", progress_pct,
                             f"Creating clip {i+1} of {len(suggestions)}…")

            clip = await asyncio.to_thread(
                _sync_process_clip,
                file_path, suggestion, clips_dir, project_id,
                cfg["face_tracking"], cfg["reframe"],
            )

            # Captions (optional)
            if cfg["captions"] and cfg["captions"] != "none":
                await _broadcast(project_id, "processing", progress_pct + 1,
                                 f"Adding captions to clip {i+1}…")
                try:
                    captioned_clip = await captioner.burn_captions(
                        clip["file_path"],
                        transcript_segments,
                        suggestion["start"],
                        suggestion["end"],
                        cfg["captions"],
                    )
                    if captioned_clip != clip["file_path"] and os.path.exists(captioned_clip):
                        os.replace(captioned_clip, clip["file_path"])
                    clip["caption_style"] = cfg["captions"]
                    clip["captioned"] = True
                except Exception as exc:
                    logger.warning("Caption burn failed for clip %s: %s", i, exc)

            # Watermark (optional — DKC 57)
            wm = cfg.get("watermark") or {}
            if wm.get("enabled"):
                wm_out = clip["file_path"].replace(".mp4", "_wm.mp4")
                try:
                    await watermark_mod.apply_watermark(clip["file_path"], wm_out, wm)
                    if wm_out != clip["file_path"] and os.path.exists(wm_out):
                        os.replace(wm_out, clip["file_path"])
                except Exception as exc:
                    logger.warning("Watermark failed for clip %s: %s", i, exc)
                    if os.path.exists(wm_out):
                        try:
                            os.remove(wm_out)
                        except OSError:
                            pass

            # Thumbnail (best-effort — DKC 57)
            thumb_rel = None
            thumb_name = f"thumb_{os.path.basename(clip['file_path'])}"
            thumb_path = os.path.join(clips_dir, thumb_name)
            if await _generate_thumbnail(clip["file_path"], thumb_path):
                thumb_rel = f"/files/{project_id}/clips/{thumb_name}"

            filename = os.path.basename(clip["file_path"])
            file_url = f"/files/{project_id}/clips/{filename}"

            await database.save_clip(
                project_id=project_id,
                file_path=file_url,
                start_time=clip["start_time"],
                end_time=clip["end_time"],
                title=clip.get("title"),
                reason=clip.get("reason"),
                viral_score=clip.get("viral_score"),
                face_count=clip.get("face_count"),
                layout_mode=clip.get("layout_mode"),
                caption_style=clip.get("caption_style"),
                needs_user_confirm=clip.get("needs_user_confirm", False),
                reframed=clip.get("reframed", True),
                hashtags=suggestion.get("hashtags", []),
                tags=suggestion.get("tags", []),
                thumbnail=thumb_rel,
            )

        await database.update_project_status(project_id, "done")
        await _broadcast(project_id, "done", 100, "Complete")

    except _PipelineCancelled:
        logger.info("Pipeline cancelled for project %s", project_id)
        await database.update_project_status(project_id, "cancelled")
        await _broadcast(project_id, "cancelled", 0, "Cancelled by user")

    except Exception as exc:
        import traceback
        trace_path = os.path.join(TMP_DIR, f"error_trace_{project_id}.txt")
        try:
            with open(trace_path, "w") as f:
                f.write(traceback.format_exc())
        except OSError:
            pass

        logger.exception("Pipeline failed for project %s", project_id)
        await database.update_project_status(project_id, "error")
        await database.update_project_error(project_id, f"Pipeline error: {exc}")
        await _broadcast(project_id, "error", 0, f"Pipeline error: {exc}")


def _sync_process_clip(
    video_path: str,
    suggestion: dict,
    clips_dir: str,
    project_id: str,
    face_tracking: bool,
    reframe: bool,
) -> dict:
    """Run the (async) reframer pipeline for one clip from a thread."""
    return asyncio.run(
        reframer.process_clip(
            video_path,
            suggestion,
            clips_dir,
            project_id,
            face_tracking=face_tracking,
            reframe=reframe,
        )
    )


# ---------------------------------------------------------------------------
# REST routes — Projects
# ---------------------------------------------------------------------------

_YT_URL_RE = re.compile(r"^(https?://)?(www\.youtube\.com|youtu\.be)/.+$")


async def _create_project_core(
    youtube_url: str,
    settings_dict: Optional[dict],
) -> dict:
    result = await database.create_project(
        youtube_url=youtube_url,
        config=settings_dict,
        source_type="youtube",
    )
    return result


@app.post("/api/projects", response_model=CreateProjectResponse, status_code=201)
async def create_project(
    body: CreateProjectRequest,
    background_tasks: BackgroundTasks,
):
    """
    Create a new project from a YouTube URL.

    The project row is inserted immediately and the pipeline is kicked
    off in the background.  The response is returned without waiting
    for the download/clip work to finish.
    """
    if not _YT_URL_RE.match(body.youtube_url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    settings_dict = _normalize_settings(
        body.settings.model_dict() if body.settings else None
    )
    result = await _create_project_core(body.youtube_url, settings_dict)
    project_id = result["project_id"]

    background_tasks.add_task(_run_pipeline, project_id)
    return {"project_id": project_id, "status": "pending"}


@app.post("/api/projects/upload", response_model=CreateProjectResponse, status_code=201)
async def create_project_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    settings_json: Optional[str] = Form(default=None),
):
    """
    DKC 57: create a project from a locally uploaded video file
    (multipart/form-data).  Skips the download stage and transcribes
    locally with Whisper.
    """
    filename = os.path.basename(file.filename or "upload.mp4").replace("\\", "/")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext or 'unknown'}'. "
                   f"Allowed: {', '.join(sorted(ALLOWED_UPLOAD_EXT))}",
        )

    raw_settings = None
    if settings_json:
        import json as _json
        try:
            raw_settings = _json.loads(settings_json)
        except _json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid settings JSON")
    settings_dict = _normalize_settings(raw_settings)

    result = await database.create_project(
        youtube_url="",
        config=settings_dict,
        source_type="upload",
    )
    project_id = result["project_id"]

    project_dir = os.path.join(TMP_DIR, project_id)
    os.makedirs(project_dir, exist_ok=True)
    source_path = os.path.join(project_dir, f"source{ext}")

    # Stream the upload to disk with a size cap
    written = 0
    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    try:
        with open(source_path, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds the {MAX_UPLOAD_MB} MB upload limit",
                    )
                out.write(chunk)
    except HTTPException:
        if os.path.exists(source_path):
            os.remove(source_path)
        await database.delete_project(project_id)
        if os.path.isdir(project_dir):
            shutil.rmtree(project_dir, ignore_errors=True)
        raise
    except Exception as exc:
        if os.path.exists(source_path):
            os.remove(source_path)
        await database.delete_project(project_id)
        if os.path.isdir(project_dir):
            shutil.rmtree(project_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}")

    if written == 0:
        await database.delete_project(project_id)
        if os.path.isdir(project_dir):
            shutil.rmtree(project_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    base_title = os.path.splitext(filename)[0] or "Untitled upload"
    await database.update_project_source(project_id, "upload", source_path)
    await database.update_project_title(project_id, base_title)

    background_tasks.add_task(_run_pipeline, project_id)
    return {"project_id": project_id, "status": "pending"}


@app.post("/api/projects/bulk", response_model=BulkCreateResponse, status_code=201)
async def bulk_create_projects(
    body: BulkCreateRequest,
    background_tasks: BackgroundTasks,
):
    """
    DKC 57: create many projects at once (bulk processing).
    Each URL is validated; invalid ones are skipped with a note.
    """
    if not body.youtube_urls:
        raise HTTPException(status_code=400, detail="No YouTube URLs provided")
    if len(body.youtube_urls) > 25:
        raise HTTPException(status_code=400, detail="Max 25 videos per bulk request")

    settings_dict = _normalize_settings(
        body.settings.model_dict() if body.settings else None
    )

    projects = []
    for url in body.youtube_urls:
        if not _YT_URL_RE.match(url):
            continue
        result = await _create_project_core(url, settings_dict)
        background_tasks.add_task(_run_pipeline, result["project_id"])
        projects.append({"project_id": result["project_id"], "status": "pending"})

    return {"projects": projects}


@app.get("/api/projects", response_model=list[ProjectListItem])
async def list_projects():
    """Return all projects, newest first, with clip counts."""
    items = await database.get_all_projects()
    for item in items:
        item.setdefault("error_message", None)
    return items


@app.get("/api/projects/{project_id}", response_model=ProjectDetailResponse)
async def get_project(project_id: str):
    """Get a single project by ID, including its clips."""
    project = await database.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    """
    Delete a project and all of its clips (both DB rows and files).
    """
    project = await database.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # DKC 57: make sure a running job stops
    event = _cancel_events.get(project_id)
    if event is not None:
        event.set()

    await database.delete_project(project_id)

    project_dir = os.path.join(TMP_DIR, project_id)
    if os.path.isdir(project_dir):
        shutil.rmtree(project_dir, ignore_errors=True)

    return {"success": True}


@app.post("/api/projects/{project_id}/retry")
async def retry_project(project_id: str, background_tasks: BackgroundTasks):
    """
    DKC 57: retry a failed (or completed) project.  Old clips are cleared
    and the full pipeline runs again.  The source video is preserved, so
    retries never re-download.
    """
    project = await database.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["status"] in PROCESSING_STATUSES:
        raise HTTPException(
            status_code=409, detail="Project is already queued or running"
        )

    await _clear_project_clips(project_id)
    await database.update_project_error(project_id, None)
    await database.update_project_status(project_id, "retrying")
    _cancel_events[project_id] = threading.Event()
    background_tasks.add_task(_run_pipeline, project_id)
    return {"success": True, "status": "retrying"}


@app.post("/api/projects/{project_id}/cancel")
async def cancel_project(project_id: str):
    """
    DKC 57: request cancellation of a queued/running project.  The job
    stops at the next stage boundary and is marked CANCELLED.  The source
    video and any already-created clips are preserved.
    """
    project = await database.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["status"] not in PROCESSING_STATUSES:
        raise HTTPException(
            status_code=409, detail="Project is not queued or running"
        )

    event = _cancel_events.setdefault(project_id, threading.Event())
    event.set()
    await _broadcast(project_id, "cancelled", 0, "Cancel requested…")
    return {"success": True}


# ---------------------------------------------------------------------------
# REST routes — Clips (DKC 57 video library)
# ---------------------------------------------------------------------------

@app.get("/api/clips")
async def list_clips():
    """All generated clips across projects (newest first)."""
    return await database.get_all_clips()


@app.get("/api/clips/{clip_id}/download")
async def download_clip(clip_id: str):
    """Stream a clip file for export."""
    clip = await database.get_clip(clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    raw = clip["file_path"]
    if raw.startswith("/files/"):
        path = os.path.join(TMP_DIR, raw[len("/files/"):])
    else:
        path = raw
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Clip file missing on disk")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=os.path.basename(path),
    )


@app.patch("/api/clips/{clip_id}")
async def update_clip(clip_id: str, body: UpdateClipRequest):
    """Rename a clip (DKC 57: user-editable titles)."""
    clip = await database.get_clip(clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    await database.update_clip_title(clip_id, body.title)
    return {"success": True}


@app.delete("/api/clips/{clip_id}")
async def delete_clip(clip_id: str):
    """Delete a single clip (DKC 57: reject an AI suggestion)."""
    clip = await database.get_clip(clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    raw = clip["file_path"]
    if raw.startswith("/files/"):
        path = os.path.join(TMP_DIR, raw[len("/files/"):])
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass
    ok = await database.delete_clip(clip_id)
    return {"success": ok}


# ---------------------------------------------------------------------------
# REST routes — Stats (DKC 57 dashboard)
# ---------------------------------------------------------------------------

@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Dashboard counters: videos, shorts, processing, failed."""
    return await database.get_stats()


# ---------------------------------------------------------------------------
# REST routes — Caption styles
# ---------------------------------------------------------------------------

@app.get("/api/caption-styles")
async def list_caption_styles():
    def ass_to_hex(ass_color):
        if not ass_color: return None
        if len(ass_color) >= 10:
            return f"#{ass_color[8:10]}{ass_color[6:8]}{ass_color[4:6]}"
        return None

    styles = []
    for key, style in captioner.CAPTION_STYLES.items():
        styles.append({
            "key": key,
            "name": style["name"],
            "animation": style["animation"],
            "preview_colors": {
                "text": ass_to_hex(style.get("primary_color")),
                "highlight": ass_to_hex(style.get("highlight_color")),
                "background": ass_to_hex(style.get("bg_color")) if style.get("background") else None
            }
        })
    return styles


# ---------------------------------------------------------------------------
# REST routes — Settings
# ---------------------------------------------------------------------------

class UpdateSettingsRequest(BaseModel):
    """Payload for updating settings."""
    llm_provider: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None
    whisper_model: Optional[str] = None
    caption_style: Optional[str] = None
    # DKC 57 watermark defaults
    watermark_enabled: Optional[bool] = None
    watermark_position: Optional[str] = None
    watermark_opacity: Optional[float] = None


@app.get("/api/settings")
async def get_settings():
    """
    Return all settings.  API keys are **never** returned — only a
    boolean ``has_api_key`` flag.
    """
    return await settings_mod.get_all_settings()


@app.post("/api/settings")
async def update_settings(body: UpdateSettingsRequest):
    """
    Create or update one or more settings.
    """
    pairs = {
        "llm_provider": body.llm_provider,
        "llm_api_key": body.llm_api_key,
        "llm_model": body.llm_model,
        "whisper_model": body.whisper_model,
        "caption_style": body.caption_style,
        "watermark_enabled": (
            str(int(body.watermark_enabled)).lower()
            if body.watermark_enabled is not None else None
        ),
        "watermark_position": body.watermark_position,
        "watermark_opacity": (
            str(body.watermark_opacity) if body.watermark_opacity is not None else None
        ),
    }
    for key, value in pairs.items():
        if value is not None:
            await settings_mod.set_setting(key, value)
    return {"success": True}


@app.get("/api/health")
async def health():
    """Liveness probe (DKC 57 / Docker)."""
    return {
        "status": "ok",
        "app": "DKC 57 Video Clipper",
        "ffmpeg": ffmpeg_util.ffmpeg_available(),
    }


# ---------------------------------------------------------------------------
# WebSocket — real-time progress
# ---------------------------------------------------------------------------

@app.websocket("/ws/progress/{project_id}")
async def websocket_progress(websocket: WebSocket, project_id: str):
    """
    WebSocket endpoint that streams processing-progress updates to
    the frontend for a given project.

    Message format (JSON sent from server):
        {
          "stage":   "downloading|transcribing|analyzing|processing|done|error|cancelled",
          "percent": 0.0 – 100.0,
          "message": "human-readable status"
        }
    """
    # DKC 57: honour the optional API key via ?key=… when auth is enabled
    if _API_KEY and websocket.query_params.get("key") != _API_KEY:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    _cancel_events.setdefault(project_id, threading.Event())

    if project_id not in _ws_connections:
        _ws_connections[project_id] = set()
    _ws_connections[project_id].add(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _ws_connections.get(project_id, set()).discard(websocket)
        if project_id in _ws_connections and not _ws_connections[project_id]:
            _ws_connections.pop(project_id, None)


# ---------------------------------------------------------------------------
# Entrypoint (for development)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn  # type: ignore
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
