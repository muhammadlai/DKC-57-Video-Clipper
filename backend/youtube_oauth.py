"""
youtube_oauth.py — official YouTube OAuth + Data API helpers.

Implements Google OAuth 2.0 using direct HTTPS calls so the backend can
connect a channel, detect the authenticated user's active live stream,
resolve a playable live source via yt-dlp, and upload finished clips to
YouTube Shorts when the required scopes are granted.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import secrets
import subprocess
from typing import Any, Optional
from urllib.parse import urlencode

import httpx  # type: ignore

import downloader  # type: ignore
import settings  # type: ignore


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.upload",
]
TOKENS_KEY = "youtube_oauth_tokens"


class YouTubeConfigError(RuntimeError):
    pass


def oauth_env() -> dict[str, str]:
    return {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", "").strip(),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", "").strip(),
        "redirect_uri": os.getenv("YOUTUBE_OAUTH_REDIRECT_URI", "").strip(),
        "app_base_url": os.getenv("APP_BASE_URL", "http://localhost:5000").strip(),
    }


def oauth_configured() -> bool:
    env = oauth_env()
    return bool(env["client_id"] and env["client_secret"] and env["redirect_uri"])


def build_auth_url(state: str) -> str:
    env = oauth_env()
    if not oauth_configured():
        raise YouTubeConfigError("Google OAuth is not configured on the backend.")
    query = urlencode(
        {
            "client_id": env["client_id"],
            "redirect_uri": env["redirect_uri"],
            "response_type": "code",
            "scope": " ".join(DEFAULT_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
        }
    )
    return f"{GOOGLE_AUTH_URL}?{query}"


def new_state() -> str:
    return secrets.token_urlsafe(24)


async def get_tokens() -> Optional[dict[str, Any]]:
    return await settings.get_json_setting(TOKENS_KEY)


async def clear_tokens() -> None:
    await settings.set_json_setting(TOKENS_KEY, {})


async def store_tokens(tokens: dict[str, Any]) -> None:
    await settings.set_json_setting(TOKENS_KEY, tokens)


async def exchange_code(code: str) -> dict[str, Any]:
    env = oauth_env()
    if not oauth_configured():
        raise YouTubeConfigError("Google OAuth is not configured on the backend.")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": env["client_id"],
                "client_secret": env["client_secret"],
                "redirect_uri": env["redirect_uri"],
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        payload = response.json()
    tokens = normalize_tokens(payload)
    await store_tokens(tokens)
    return tokens


async def refresh_tokens(tokens: dict[str, Any]) -> dict[str, Any]:
    env = oauth_env()
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise RuntimeError("No YouTube refresh token stored.")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": env["client_id"],
                "client_secret": env["client_secret"],
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        payload = response.json()
    refreshed = normalize_tokens(payload, existing=tokens)
    await store_tokens(refreshed)
    return refreshed


def normalize_tokens(payload: dict[str, Any], existing: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    tokens = dict(existing or {})
    tokens.update(payload)
    expires_in = int(payload.get("expires_in") or 0)
    expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=max(0, expires_in - 60))
    tokens["expires_at"] = expires_at.isoformat()
    if existing and existing.get("refresh_token") and not tokens.get("refresh_token"):
        tokens["refresh_token"] = existing["refresh_token"]
    return tokens


async def get_access_token() -> Optional[str]:
    tokens = await get_tokens()
    if not tokens or not tokens.get("access_token"):
        return None
    expires_at = tokens.get("expires_at")
    if expires_at:
        try:
            if dt.datetime.fromisoformat(expires_at) <= dt.datetime.now(dt.timezone.utc):
                tokens = await refresh_tokens(tokens)
        except ValueError:
            tokens = await refresh_tokens(tokens)
    return tokens.get("access_token")


async def youtube_get(path: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    access_token = await get_access_token()
    if not access_token:
        raise RuntimeError("YouTube is not connected.")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{YOUTUBE_API_BASE}/{path.lstrip('/')}",
            params=params or {},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


async def get_channel() -> Optional[dict[str, Any]]:
    payload = await youtube_get("channels", {"part": "id,snippet", "mine": "true", "maxResults": 1})
    items = payload.get("items") or []
    if not items:
        return None
    item = items[0]
    return {
        "channel_id": item.get("id"),
        "channel_name": item.get("snippet", {}).get("title"),
    }


async def get_active_live() -> Optional[dict[str, Any]]:
    channel = await get_channel()
    if not channel or not channel.get("channel_id"):
        return None

    # search.list reliably surfaces active live videos for a channel.
    payload = await youtube_get(
        "search",
        {
            "part": "id,snippet",
            "channelId": channel["channel_id"],
            "eventType": "live",
            "type": "video",
            "maxResults": 1,
            "order": "date",
        },
    )
    items = payload.get("items") or []
    if not items:
        return None
    video_id = items[0].get("id", {}).get("videoId")
    if not video_id:
        return None

    details = await youtube_get(
        "videos",
        {
            "part": "id,snippet,liveStreamingDetails,status,contentDetails",
            "id": video_id,
        },
    )
    video_items = details.get("items") or []
    if not video_items:
        return None
    video = video_items[0]
    live = video.get("liveStreamingDetails") or {}
    snippet = video.get("snippet") or {}
    return {
        "video_id": video_id,
        "title": snippet.get("title"),
        "description": snippet.get("description"),
        "published_at": snippet.get("publishedAt"),
        "actual_start_time": live.get("actualStartTime"),
        "concurrent_viewers": live.get("concurrentViewers"),
        "url": f"https://www.youtube.com/watch?v={video_id}",
    }


def resolve_live_source(youtube_url: str) -> dict[str, Any]:
    """Resolve a direct media URL for the active YouTube live using yt-dlp."""
    cmd = [
        *downloader._resolve_ytdlp_argv(),
        "-g",
        "--live-from-start",
        youtube_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    if result.returncode != 0:
        return {
            "ok": False,
            "message": (result.stderr or result.stdout or "yt-dlp could not resolve the live source.").strip()[:500],
            "stream_url": None,
        }
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip().startswith("http")]
    stream_url = lines[0] if lines else None
    return {
        "ok": bool(stream_url),
        "message": "Resolved YouTube live source" if stream_url else "No direct media URL returned by yt-dlp.",
        "stream_url": stream_url,
    }


async def get_status() -> dict[str, Any]:
    status: dict[str, Any] = {
        "configured": oauth_configured(),
        "connected": False,
        "channel_name": None,
        "channel_id": None,
        "live_active": False,
        "live": None,
        "source": {"ok": False, "stream_url": None, "message": "No live stream detected."},
        "limitation": None,
    }
    if not status["configured"]:
        status["limitation"] = "Google OAuth client ID, secret, or redirect URI is missing."
        return status

    access_token = await get_access_token()
    if not access_token:
        status["limitation"] = "YouTube is not connected."
        return status

    try:
        channel = await get_channel()
        if channel:
            status.update({"connected": True, **channel})
        live = await get_active_live()
        if live:
            status["live_active"] = True
            status["live"] = live
            status["source"] = resolve_live_source(live["url"])
        else:
            status["source"] = {"ok": False, "stream_url": None, "message": "Channel is offline or no active live was returned by the YouTube Data API."}
    except httpx.HTTPStatusError as exc:
        status["limitation"] = f"YouTube API error {exc.response.status_code}"
    except Exception as exc:
        status["limitation"] = str(exc)
    return status


async def upload_short(
    file_path: str,
    title: str,
    description: str,
    tags: list[str],
    privacy_status: str = "private",
) -> dict[str, Any]:
    access_token = await get_access_token()
    if not access_token:
        raise RuntimeError("YouTube upload is unavailable because the channel is not connected.")

    metadata = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:15],
            "categoryId": "17",  # Sports
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }
    boundary = f"==============={secrets.token_hex(12)}=="
    metadata_part = (
        f"--{boundary}\r\n"
        "Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadata)}\r\n"
        f"--{boundary}\r\n"
        "Content-Type: video/mp4\r\n\r\n"
    ).encode("utf-8")
    closing = f"\r\n--{boundary}--\r\n".encode("utf-8")
    with open(file_path, "rb") as fh:
        body = metadata_part + fh.read() + closing

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            "https://www.googleapis.com/upload/youtube/v3/videos",
            params={"uploadType": "multipart", "part": "snippet,status"},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": f"multipart/related; boundary={boundary}",
            },
            content=body,
        )
        response.raise_for_status()
        payload = response.json()
        return {
            "video_id": payload.get("id"),
            "url": f"https://www.youtube.com/watch?v={payload.get('id')}" if payload.get("id") else None,
            "raw": payload,
        }
