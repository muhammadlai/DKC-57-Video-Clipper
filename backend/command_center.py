"""
command_center.py — real backend state for the AITZAZ AI Live Content
Command Center.

This service keeps the dashboard honest: every status shown in the UI is
backed by an actual backend check, not a hard-coded frontend flag.
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Optional

import httpx  # type: ignore

import captioner  # type: ignore
import control_db  # type: ignore
import event_detector  # type: ignore
import ffmpeg_util  # type: ignore
import llm  # type: ignore
import transcriber  # type: ignore
import youtube_oauth  # type: ignore
from publishers import build_publishers  # type: ignore
from rolling_buffer import RollingBufferManager  # type: ignore
from sports_data import detect_stumps_status  # type: ignore
from viral_scoring import score_moment  # type: ignore


logger = logging.getLogger(__name__)


class CommandCenterService:
    def __init__(self, tmp_dir: str):
        self.tmp_dir = tmp_dir
        self.live_dir = os.path.join(tmp_dir, "live_command_center")
        self.buffer = RollingBufferManager(
            os.path.join(self.live_dir, "rolling_buffer"),
            segment_seconds=int(os.getenv("ROLLING_SEGMENT_SECONDS", "5")),
            retain_seconds=int(os.getenv("ROLLING_RETAIN_SECONDS", "180")),
        )
        self.publishers = build_publishers()
        self.subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._state_lock = asyncio.Lock()
        self._snapshot: dict[str, Any] = {}
        self._production_active = False
        self._production_task: Optional[asyncio.Task[Any]] = None
        self._previous_match: Optional[dict[str, Any]] = None
        self._ai_cache: tuple[float, dict[str, Any]] = (0.0, {})
        self._last_youtube_live: Optional[bool] = None
        self._last_score_signature: Optional[str] = None

    async def initialize(self) -> None:
        Path(self.live_dir).mkdir(parents=True, exist_ok=True)

    async def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.subscribers.add(queue)
        await queue.put({"event": "SNAPSHOT", "data": self._snapshot or await self.refresh(force=True)})
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self.subscribers.discard(queue)

    async def emit(self, event: str, data: dict[str, Any]) -> None:
        packet = {"event": event, "data": data}
        dead: list[asyncio.Queue[dict[str, Any]]] = []
        for queue in list(self.subscribers):
            try:
                queue.put_nowait(packet)
            except Exception:
                dead.append(queue)
        for queue in dead:
            self.subscribers.discard(queue)

    async def get_snapshot(self) -> dict[str, Any]:
        if not self._snapshot:
            return await self.refresh(force=True)
        return copy.deepcopy(self._snapshot)

    async def refresh(self, force: bool = False) -> dict[str, Any]:
        async with self._state_lock:
            if not force and self._snapshot and (time.time() - self._snapshot.get("refreshed_at_ts", 0)) < 3:
                return copy.deepcopy(self._snapshot)

            config = await control_db.get_all_config()
            youtube = await youtube_oauth.get_status()
            # Prime the rolling buffer as soon as a real live source is available so the
            # Start Production button can depend on an actual pre-roll buffer.
            if youtube.get("live_active") and youtube.get("source", {}).get("ok"):
                self.buffer.start(youtube["source"]["stream_url"])
            elif not self._production_active:
                self.buffer.stop()

            stumps = await detect_stumps_status(str(config.get("stumps_team_id") or ""))
            ai = await self._get_ai_status(force=force)
            buffer_status = self.buffer.status()
            publisher_diags = await self._get_publisher_diagnostics()
            moments = await control_db.list_moments(10)
            jobs = await control_db.list_publishing_jobs(25)
            diagnostics = self._build_diagnostics(youtube, stumps, ai, buffer_status, publisher_diags)
            blockers = [d["message"] for d in diagnostics if d["required_for_start"] and d["state"] != "ok"]

            current_event = moments[0] if moments else None
            snapshot = {
                "app": {
                    "name": "AITZAZ AI",
                    "subtitle": "LIVE CONTENT COMMAND CENTER",
                },
                "config": {
                    "stumps_team_id": config.get("stumps_team_id"),
                    "publish_mode": config.get("publish_mode", "approval"),
                    "auto_publish_minimum": int(config.get("auto_publish_minimum", 85)),
                    "pre_roll_seconds": int(config.get("pre_roll_seconds", 10)),
                    "post_roll_seconds": int(config.get("post_roll_seconds", 15)),
                    "youtube_privacy_status": config.get("youtube_privacy_status", "private"),
                },
                "youtube": youtube,
                "stumps": stumps,
                "ai_engine": ai,
                "live_analysis": {
                    "watching": self._production_active and bool(youtube.get("live_active")) and bool(stumps.get("match")),
                    "current_event": current_event,
                },
                "moments": moments,
                "publishing": {
                    "mode": config.get("publish_mode", "approval"),
                    "jobs": jobs,
                    "platforms": publisher_diags,
                },
                "diagnostics": diagnostics,
                "production": {
                    "active": self._production_active,
                    "can_start": len(blockers) == 0,
                    "blockers": blockers,
                },
                "buffer": buffer_status,
                "refreshed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "refreshed_at_ts": time.time(),
            }
            self._emit_state_change_events(self._snapshot or None, snapshot)
            self._snapshot = snapshot
            return copy.deepcopy(snapshot)

    async def start_production(self) -> dict[str, Any]:
        snapshot = await self.refresh(force=True)
        blockers = snapshot["production"]["blockers"]
        if blockers:
            raise RuntimeError("Production prerequisites are not verified: " + "; ".join(blockers))
        if self._production_active:
            return snapshot
        self._production_active = True
        self._production_task = asyncio.create_task(self._production_loop(), name="aitzaz-production-loop")
        await self.emit("AI_ANALYZING", {"active": True})
        return await self.refresh(force=True)

    async def stop_production(self) -> dict[str, Any]:
        self._production_active = False
        self.buffer.stop()
        if self._production_task:
            self._production_task.cancel()
            try:
                await self._production_task
            except BaseException:
                pass
        self._production_task = None
        await self.emit("AI_ANALYZING", {"active": False})
        return await self.refresh(force=True)

    async def approve_job(self, job_id: str) -> dict[str, Any]:
        job = await control_db.get_publishing_job(job_id)
        if not job:
            raise RuntimeError("Publishing job not found")
        moment_id = job["moment_id"]
        moments = await control_db.list_moments(100)
        moment = next((m for m in moments if m["id"] == moment_id), None)
        if not moment:
            raise RuntimeError("Moment not found")
        metadata = job.get("metadata") or {
            "title": moment.get("title"),
            "description": moment.get("description"),
            "hashtags": moment.get("hashtags") or [],
        }
        publisher = self.publishers.get(job["platform"])
        if not publisher:
            raise RuntimeError("Unsupported publishing platform")
        await control_db.update_publishing_job(job_id, status="publishing", error_message=None)
        try:
            result = await publisher.publish(moment=moment, metadata=metadata)
            await control_db.update_publishing_job(job_id, status="published", external_id=result.get("external_id"))
            await self.emit("PUBLISH_SUCCESS", {"platform": job["platform"], "job_id": job_id, "result": result})
        except Exception as exc:
            await control_db.update_publishing_job(job_id, status="failed", error_message=str(exc))
            await self.emit("PUBLISH_FAILED", {"platform": job["platform"], "job_id": job_id, "error": str(exc)})
        return await self.refresh(force=True)

    async def _production_loop(self) -> None:
        while self._production_active:
            try:
                snapshot = await self.refresh(force=True)
                youtube = snapshot["youtube"]
                stumps = snapshot["stumps"]
                match = stumps.get("match")

                if youtube.get("live_active") and youtube.get("source", {}).get("ok"):
                    self.buffer.start(youtube["source"]["stream_url"])
                else:
                    self.buffer.stop()

                if match:
                    moment = event_detector.detect_moment(self._previous_match, match)
                    if moment:
                        detected_at_ts = time.time()
                        moment["detected_at_ts"] = detected_at_ts
                        moment["event_json"] = {**match, "detected_at_ts": detected_at_ts}
                        score_ctx = {
                            "event_type": moment["event_type"],
                            "overs": match.get("overs"),
                            "wickets": match.get("wickets"),
                            "confidence": moment.get("confidence", 0.85),
                        }
                        moment.update(score_moment(score_ctx))
                        created, record = await control_db.insert_moment(moment)
                        if created:
                            await self.emit("EVENT_DETECTED", record)
                            asyncio.create_task(self._finalize_moment(record, match))
                self._previous_match = match
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Production loop tick failed")
            await asyncio.sleep(int(os.getenv("PRODUCTION_POLL_SECONDS", "8")))

    async def _finalize_moment(self, moment: dict[str, Any], match: dict[str, Any]) -> None:
        try:
            pre_roll = int(await control_db.get_config("pre_roll_seconds", 10))
            post_roll = int(await control_db.get_config("post_roll_seconds", 15))
            await self.emit("CLIP_STARTED", {"moment_id": moment["id"]})
            await asyncio.sleep(post_roll)

            event_json = moment.get("event_json") or {}
            detected_at_ts = float(event_json.get("detected_at_ts") or moment.get("detected_at_ts") or time.time())
            clip_dir = os.path.join(self.live_dir, "clips")
            os.makedirs(clip_dir, exist_ok=True)
            clip_path = os.path.join(clip_dir, f"{moment['id']}.mp4")
            self.buffer.extract_clip(detected_at_ts - pre_roll, detected_at_ts + post_roll, clip_path)

            transcript = await transcriber.extract_captions(None, clip_path, whisper_model="base")
            captioned_path = clip_path
            if transcript:
                try:
                    burned = await captioner.burn_captions(
                        clip_path,
                        transcript,
                        0.0,
                        float(pre_roll + post_roll),
                        "classic_white",
                    )
                    if burned and os.path.exists(burned):
                        captioned_path = burned
                except Exception:
                    logger.exception("Caption burn failed for moment %s", moment["id"])

            metadata = await self._generate_metadata(moment, match)
            await control_db.update_moment(
                moment["id"],
                clip_path=clip_path,
                captioned_path=captioned_path,
                title=metadata["title"],
                description=metadata["description"],
                hashtags=metadata["hashtags"],
                status="queued",
                viral_score=moment.get("viral_score"),
            )
            refreshed_moment = next((m for m in await control_db.list_moments(50) if m["id"] == moment["id"]), moment)
            await self._queue_publication_jobs(refreshed_moment, metadata)
            await self.emit("CLIP_READY", {"moment_id": moment["id"], "clip_path": clip_path, "captioned_path": captioned_path})
            await self.refresh(force=True)
        except Exception as exc:
            logger.exception("Finalizing moment failed: %s", exc)
            await control_db.update_moment(moment["id"], status="failed")

    async def _queue_publication_jobs(self, moment: dict[str, Any], metadata: dict[str, Any]) -> None:
        mode = str(await control_db.get_config("publish_mode", "approval"))
        auto_publish_minimum = int(await control_db.get_config("auto_publish_minimum", 85))
        viral_score = int(moment.get("viral_score") or 0)

        for platform, publisher in self.publishers.items():
            diag = await publisher.diagnostics()
            approval_required = platform == "tiktok" or mode == "approval" or (mode == "auto" and viral_score < auto_publish_minimum)
            status = "approval_required" if approval_required else ("queued" if diag.get("ready") else "blocked")
            job = await control_db.upsert_publishing_job(
                moment_id=moment["id"],
                platform=platform,
                status=status,
                approval_required=approval_required,
                metadata=metadata,
                error_message=None if diag.get("ready") else diag.get("message"),
            )
            await self.emit("PUBLISH_STARTED", {"platform": platform, "job": job})
            if status == "queued":
                try:
                    await control_db.update_publishing_job(job["id"], status="publishing", error_message=None)
                    result = await publisher.publish(moment=moment, metadata=metadata)
                    await control_db.update_publishing_job(job["id"], status="published", external_id=result.get("external_id"))
                    await self.emit("PUBLISH_SUCCESS", {"platform": platform, "job_id": job["id"], "result": result})
                except Exception as exc:
                    await control_db.update_publishing_job(job["id"], status="failed", error_message=str(exc))
                    await self.emit("PUBLISH_FAILED", {"platform": platform, "job_id": job["id"], "error": str(exc)})

    async def _get_publisher_diagnostics(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for platform, publisher in self.publishers.items():
            result[platform] = await publisher.diagnostics()
        return result

    async def _get_ai_status(self, force: bool = False) -> dict[str, Any]:
        if not force and (time.time() - self._ai_cache[0]) < 60 and self._ai_cache[1]:
            return self._ai_cache[1]

        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

        async def verify_openai() -> tuple[bool, str]:
            if not openai_key:
                return False, "OPENAI_API_KEY is not configured."
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {openai_key}"},
                    )
                    response.raise_for_status()
                return True, "OpenAI API verified"
            except Exception as exc:
                return False, f"OpenAI verification failed: {exc}"

        async def verify_gemini() -> tuple[bool, str]:
            if not gemini_key:
                return False, "GEMINI_API_KEY is not configured."
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(
                        "https://generativelanguage.googleapis.com/v1beta/models",
                        params={"key": gemini_key},
                    )
                    response.raise_for_status()
                return True, "Gemini API verified"
            except Exception as exc:
                return False, f"Gemini verification failed: {exc}"

        openai_ok, openai_message = await verify_openai()
        gemini_ok, gemini_message = await verify_gemini()
        state = {
            "online": bool(openai_ok or gemini_ok),
            "primary": "OpenAI" if openai_ok else ("Gemini" if gemini_ok else None),
            "fallback": "Gemini" if openai_ok and gemini_ok else None,
            "providers": {
                "openai": {"ok": openai_ok, "message": openai_message},
                "gemini": {"ok": gemini_ok, "message": gemini_message},
            },
            "message": "AI engine online" if (openai_ok or gemini_ok) else "AI backend is not configured or verification failed.",
        }
        self._ai_cache = (time.time(), state)
        return state

    async def _generate_metadata(self, moment: dict[str, Any], match: dict[str, Any]) -> dict[str, Any]:
        event_type = str(moment.get("event_type") or "IMPORTANT MOMENT")
        player = moment.get("player")
        bowler = moment.get("bowler")
        teams = " vs ".join([t for t in [match.get("team_home"), match.get("team_away")] if t]) or "Cricket Match"
        score_text = moment.get("score_text") or f"{match.get('score')}/{match.get('wickets')}"
        overs = match.get("overs") or moment.get("over_text") or ""

        prompt = (
            "Return JSON only with keys title, description, hashtags. "
            "Write short-form cricket clip metadata using ONLY the verified facts provided. "
            "If a player name is missing, do not invent one. "
            f"Event: {event_type}. Teams: {teams}. Score: {score_text}. Over: {overs}. "
            f"Striker: {player or 'unknown'}. Bowler: {bowler or 'unknown'}. "
            f"Viral score: {moment.get('viral_score')}."
        )

        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        raw = None
        if openai_key:
            try:
                raw = await llm._call_openai(prompt, openai_key, os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
            except Exception:
                raw = None
        if raw is None and gemini_key:
            try:
                raw = await llm._call_gemini(prompt, gemini_key, os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
            except Exception:
                raw = None

        if raw:
            parsed = self._parse_metadata_json(raw)
            if parsed:
                return parsed
        return self._fallback_metadata(moment, match)

    def _fallback_metadata(self, moment: dict[str, Any], match: dict[str, Any]) -> dict[str, Any]:
        event_type = str(moment.get("event_type") or "IMPORTANT MOMENT")
        player = moment.get("player")
        bowler = moment.get("bowler")
        home = match.get("team_home")
        away = match.get("team_away")
        teams = " vs ".join([t for t in [home, away] if t]) or "Cricket"
        score = moment.get("score_text") or f"{match.get('score')}/{match.get('wickets')}"
        over_text = moment.get("over_text") or match.get("overs") or ""
        if player:
            title = f"{player.upper()} {event_type}! 🔥🏏"
        else:
            title = f"{event_type}! 🔥🏏"
        description = f"{teams} • {score} • Over {over_text}".strip(" •")
        if bowler:
            description += f" • Bowler: {bowler}"
        return {
            "title": title[:100],
            "description": description[:5000],
            "hashtags": ["#cricket", "#shorts", "#sports", f"#{event_type.replace(' ', '').lower()}"][:8],
        }

    def _parse_metadata_json(self, raw: str) -> Optional[dict[str, Any]]:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
        except Exception:
            return None
        title = str(data.get("title") or "").strip()
        description = str(data.get("description") or "").strip()
        hashtags = data.get("hashtags") or []
        if isinstance(hashtags, str):
            hashtags = [tag for tag in re.split(r"[\s,]+", hashtags) if tag]
        if not title:
            return None
        return {
            "title": title[:100],
            "description": description[:5000],
            "hashtags": [str(tag) for tag in hashtags][:8],
        }

    def _build_diagnostics(
        self,
        youtube: dict[str, Any],
        stumps: dict[str, Any],
        ai: dict[str, Any],
        buffer_status: dict[str, Any],
        publisher_diags: dict[str, Any],
    ) -> list[dict[str, Any]]:
        ffmpeg_ok = ffmpeg_util.ffmpeg_available()
        media_pipeline_ok = ffmpeg_ok and bool(youtube.get("source", {}).get("ok"))
        rolling_ready = bool(buffer_status.get("ready"))
        diagnostics = [
            self._diag("youtube_oauth", "YouTube OAuth", youtube.get("configured") and youtube.get("connected"), youtube.get("limitation") or ("Connected" if youtube.get("connected") else "Not connected"), True),
            self._diag("youtube_live", "YouTube Live", youtube.get("live_active"), youtube.get("source", {}).get("message") if youtube.get("live_active") else "Channel is offline or no active live stream was detected.", True),
            self._diag("youtube_source", "YouTube source", youtube.get("source", {}).get("ok"), youtube.get("source", {}).get("message") or "Direct source not resolved.", True),
            self._diag("stumps", "STUMPS", stumps.get("connected"), stumps.get("limitation") or "Connected", True),
            self._diag("stumps_live_data", "STUMPS live data", bool(stumps.get("match")), stumps.get("limitation") or "Live score available", True),
            self._diag("ai_engine", "AI Engine", ai.get("online"), ai.get("message") or "AI engine offline", True),
            self._diag("openai", "OpenAI", ai.get("providers", {}).get("openai", {}).get("ok"), ai.get("providers", {}).get("openai", {}).get("message", "Unavailable"), False),
            self._diag("gemini", "Gemini", ai.get("providers", {}).get("gemini", {}).get("ok"), ai.get("providers", {}).get("gemini", {}).get("message", "Unavailable"), False),
            self._diag("ffmpeg", "FFmpeg", ffmpeg_ok, "FFmpeg available" if ffmpeg_ok else "FFmpeg is not available on the backend.", False),
            self._diag("media_pipeline", "Media Pipeline", media_pipeline_ok, "FFmpeg and YouTube live source are available" if media_pipeline_ok else "FFmpeg or the YouTube live source is not ready.", True),
            self._diag("rolling_buffer", "Rolling Buffer", rolling_ready, "Rolling buffer has recent live segments" if rolling_ready else "Rolling buffer is not ready.", True),
            self._diag("ai_worker", "AI Worker", ai.get("online"), "AI worker ready" if ai.get("online") else "AI worker is unavailable because the backend AI engine is offline.", True),
            self._diag("clip_worker", "Clip Worker", ffmpeg_ok and rolling_ready, "Clip worker can extract from the rolling buffer" if (ffmpeg_ok and rolling_ready) else "Clip worker is waiting for FFmpeg and a real rolling buffer.", True),
            self._diag("publishing_queue", "Publishing Queue", True, "Publishing queue available", True),
            self._diag("youtube_publisher", "YouTube Publisher", publisher_diags["youtube"].get("ready"), publisher_diags["youtube"].get("message"), False),
            self._diag("facebook_publisher", "Facebook Publisher", publisher_diags["facebook"].get("ready"), publisher_diags["facebook"].get("message"), False),
            self._diag("tiktok_publisher", "TikTok Publisher", False, publisher_diags["tiktok"].get("message"), False),
        ]
        return diagnostics

    def _diag(self, key: str, label: str, ok: Any, message: str, required_for_start: bool) -> dict[str, Any]:
        return {
            "key": key,
            "label": label,
            "state": "ok" if ok else "warn",
            "message": message,
            "required_for_start": required_for_start,
        }

    def _emit_state_change_events(self, previous: Optional[dict[str, Any]], current: dict[str, Any]) -> None:
        try:
            if not previous:
                return
            prev_yt = previous.get("youtube", {})
            cur_yt = current.get("youtube", {})
            if not prev_yt.get("connected") and cur_yt.get("connected"):
                asyncio.create_task(self.emit("YOUTUBE_CONNECTED", cur_yt))
            if not prev_yt.get("live_active") and cur_yt.get("live_active"):
                asyncio.create_task(self.emit("YOUTUBE_LIVE_STARTED", cur_yt.get("live") or {}))
            if prev_yt.get("live_active") and not cur_yt.get("live_active"):
                asyncio.create_task(self.emit("YOUTUBE_LIVE_STOPPED", cur_yt))

            prev_stumps = previous.get("stumps", {})
            cur_stumps = current.get("stumps", {})
            if not prev_stumps.get("connected") and cur_stumps.get("connected"):
                asyncio.create_task(self.emit("STUMPS_CONNECTED", cur_stumps))
            if not prev_stumps.get("match") and cur_stumps.get("match"):
                asyncio.create_task(self.emit("STUMPS_MATCH_FOUND", cur_stumps.get("match") or {}))

            score_sig = self._match_signature(cur_stumps.get("match"))
            prev_score_sig = self._match_signature(prev_stumps.get("match"))
            if score_sig and score_sig != prev_score_sig:
                asyncio.create_task(self.emit("STUMPS_SCORE_UPDATED", cur_stumps.get("match") or {}))
        except Exception:
            logger.exception("Failed to emit state change events")

    def _match_signature(self, match: Optional[dict[str, Any]]) -> Optional[str]:
        if not match:
            return None
        return json.dumps(
            {
                "score": match.get("score"),
                "wickets": match.get("wickets"),
                "overs": match.get("overs"),
                "striker": match.get("striker"),
                "non_striker": match.get("non_striker"),
                "bowler": match.get("bowler"),
                "event": match.get("event"),
            },
            sort_keys=True,
        )
