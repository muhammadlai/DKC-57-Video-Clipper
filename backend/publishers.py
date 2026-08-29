"""
publishers.py — official publishing adapters used by the AITZAZ AI
command center.

Only the YouTube publisher is fully implemented in this repository.
Facebook and TikTok expose real diagnostics and queue behaviour, but
remain blocked unless the required official app credentials/tokens are
configured.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx  # type: ignore

import control_db  # type: ignore
import youtube_oauth  # type: ignore


class Publisher:
    platform = "unknown"

    async def diagnostics(self) -> dict[str, Any]:
        raise NotImplementedError

    async def publish(self, *, moment: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class YouTubePublisher(Publisher):
    platform = "youtube"

    async def diagnostics(self) -> dict[str, Any]:
        status = await youtube_oauth.get_status()
        connected = bool(status.get("connected"))
        can_upload = connected
        return {
            "platform": self.platform,
            "ready": can_upload,
            "state": "ok" if can_upload else "warn",
            "message": "Ready to upload Shorts" if can_upload else (status.get("limitation") or "YouTube channel is not connected."),
        }

    async def publish(self, *, moment: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
        clip_path = moment.get("captioned_path") or moment.get("clip_path")
        if not clip_path:
            raise RuntimeError("No clip file exists for YouTube publishing.")
        privacy = await control_db.get_config("youtube_privacy_status", "private")
        result = await youtube_oauth.upload_short(
            clip_path,
            title=metadata.get("title") or moment.get("title") or "AITZAZ AI Short",
            description=metadata.get("description") or moment.get("description") or "",
            tags=metadata.get("hashtags") or moment.get("hashtags") or [],
            privacy_status=str(privacy or "private"),
        )
        return {
            "external_id": result.get("video_id"),
            "url": result.get("url"),
        }


class FacebookPublisher(Publisher):
    platform = "facebook"

    async def diagnostics(self) -> dict[str, Any]:
        page_id = os.getenv("FACEBOOK_PAGE_ID", "").strip()
        token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
        ready = bool(page_id and token)
        return {
            "platform": self.platform,
            "ready": ready,
            "state": "ok" if ready else "warn",
            "message": "Ready to publish to Facebook Page video API" if ready else "Facebook Page ID or Page access token is not configured.",
        }

    async def publish(self, *, moment: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
        page_id = os.getenv("FACEBOOK_PAGE_ID", "").strip()
        token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
        if not (page_id and token):
            raise RuntimeError("Facebook publishing is not configured.")
        clip_path = moment.get("captioned_path") or moment.get("clip_path")
        if not clip_path:
            raise RuntimeError("No clip file exists for Facebook publishing.")
        async with httpx.AsyncClient(timeout=300.0) as client:
            with open(clip_path, "rb") as fh:
                response = await client.post(
                    f"https://graph-video.facebook.com/v23.0/{page_id}/videos",
                    data={
                        "access_token": token,
                        "title": metadata.get("title") or moment.get("title") or "AITZAZ AI Clip",
                        "description": metadata.get("description") or moment.get("description") or "",
                    },
                    files={"source": (os.path.basename(clip_path), fh, "video/mp4")},
                )
                response.raise_for_status()
                payload = response.json()
        return {"external_id": payload.get("id"), "url": None}


class TikTokPublisher(Publisher):
    platform = "tiktok"

    async def diagnostics(self) -> dict[str, Any]:
        client_key = os.getenv("TIKTOK_CLIENT_KEY", "").strip()
        client_secret = os.getenv("TIKTOK_CLIENT_SECRET", "").strip()
        ready = bool(client_key and client_secret)
        return {
            "platform": self.platform,
            "ready": ready,
            "state": "warn",
            "message": "TikTok uses an approval workflow in this app." if ready else "TikTok official app credentials are not configured.",
        }

    async def publish(self, *, moment: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError(
            "TikTok publishing is approval-only in this build. The official app credentials and review flow must be configured before uploads can be automated."
        )


def build_publishers() -> dict[str, Publisher]:
    return {
        "youtube": YouTubePublisher(),
        "facebook": FacebookPublisher(),
        "tiktok": TikTokPublisher(),
    }
