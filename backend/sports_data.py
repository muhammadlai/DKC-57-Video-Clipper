"""
sports_data.py — sports data provider abstraction for AITZAZ AI.

A STUMPS adapter is included. It uses the public team page as the
legitimate discovery surface and only exposes data that can actually be
verified from that source. When live match data is not visible, it
returns an explicit limitation instead of fabricating a scorecard.
"""

from __future__ import annotations

import abc
import asyncio
import json
import re
from dataclasses import dataclass
from html import unescape
from typing import Any, Optional

import httpx  # type: ignore


@dataclass
class ProviderResult:
    connected: bool
    limitation: Optional[str]
    payload: dict[str, Any]


class SportsDataProvider(abc.ABC):
    @abc.abstractmethod
    async def get_status(self) -> ProviderResult:
        raise NotImplementedError


class StumpsProvider(SportsDataProvider):
    def __init__(self, team_id: str):
        self.team_id = team_id
        self.team_url = f"https://stumpsapp.com/team/{team_id}"

    async def get_status(self) -> ProviderResult:
        if not self.team_id:
            return ProviderResult(False, "No STUMPS team ID is configured.", self._base_payload())

        try:
            html = await self._fetch_text(self.team_url)
        except Exception as exc:
            payload = self._base_payload()
            payload["team_url"] = self.team_url
            return ProviderResult(False, f"Unable to reach the STUMPS team page: {exc}", payload)

        payload = self._parse_team_page(html)
        payload["team_url"] = self.team_url
        payload["team_id"] = self.team_id
        limitation = None if payload.get("live_data_available") else payload.get(
            "limitation",
            "No active live match data is visible on the public STUMPS team page.",
        )
        return ProviderResult(True, limitation, payload)

    async def _fetch_text(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True, verify=False, headers={"User-Agent": "AITZAZ-AI/1.0"}) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    def _base_payload(self) -> dict[str, Any]:
        return {
            "provider": "stumps",
            "team_id": self.team_id,
            "team_name": None,
            "live_data_available": False,
            "match": None,
            "limitation": None,
        }

    def _parse_team_page(self, html: str) -> dict[str, Any]:
        payload = self._base_payload()

        team_name = self._extract_team_name(html)
        if team_name:
            payload["team_name"] = team_name

        next_data = self._extract_next_data(html)
        if next_data:
            match = self._find_match_object(next_data)
            normalized = self._normalize_match(match)
            if normalized:
                payload["live_data_available"] = True
                payload["match"] = normalized
                return payload

        lines = self._html_to_lines(html)
        match = self._parse_from_lines(lines)
        if match:
            payload["live_data_available"] = True
            payload["match"] = match
        else:
            payload["limitation"] = (
                "STUMPS team page was reachable, but an active match with score, overs, and players "
                "was not visible in the public response."
            )
        return payload

    def _extract_team_name(self, html: str) -> Optional[str]:
        for pattern in (
            r"<h1[^>]*>(.*?)</h1>",
            r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
        ):
            match = re.search(pattern, html, re.I | re.S)
            if match:
                value = self._clean_text(match.group(1))
                if value:
                    return value
        return None

    def _extract_next_data(self, html: str) -> Optional[dict[str, Any]]:
        match = re.search(r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', html, re.S | re.I)
        if not match:
            return None
        raw = match.group(1).strip()
        try:
            return json.loads(raw)
        except Exception:
            return None

    def _find_match_object(self, obj: Any) -> Optional[dict[str, Any]]:
        queue = [obj]
        seen: set[int] = set()
        while queue:
            current = queue.pop(0)
            ident = id(current)
            if ident in seen:
                continue
            seen.add(ident)
            if isinstance(current, dict):
                lowered = {str(k).lower(): v for k, v in current.items()}
                # Only accept objects that already look like a scorecard.
                if any(k in lowered for k in ("striker", "non_striker", "bowler", "score", "overs", "recent_balls")):
                    return lowered
                queue.extend(current.values())
            elif isinstance(current, list):
                queue.extend(current)
        return None

    def _normalize_match(self, match: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if not match:
            return None
        score_text = self._clean_text(match.get("score") or match.get("runs") or "")
        wickets_text = self._clean_text(match.get("wickets") or "")
        overs_text = self._clean_text(match.get("overs") or match.get("over") or "")
        event_text = self._clean_text(match.get("event") or match.get("recent_event") or match.get("status") or "")
        if not any([score_text, wickets_text, overs_text, event_text, match.get("striker"), match.get("bowler")]):
            return None

        score, wickets = self._split_score(score_text, wickets_text)
        teams = self._extract_teams_from_obj(match)
        return {
            "match_id": self._clean_text(match.get("match_id") or match.get("id") or "") or None,
            "team_home": teams[0],
            "team_away": teams[1],
            "inning": self._clean_text(match.get("inning") or match.get("innings") or "") or None,
            "score": score,
            "wickets": wickets,
            "overs": overs_text or None,
            "striker": self._clean_text(match.get("striker") or "") or None,
            "non_striker": self._clean_text(match.get("non_striker") or match.get("nonstriker") or "") or None,
            "bowler": self._clean_text(match.get("bowler") or "") or None,
            "recent_balls": self._coerce_recent_balls(match.get("recent_balls") or match.get("balls")),
            "event": event_text or None,
            "timestamp": self._clean_text(match.get("timestamp") or match.get("updated_at") or "") or None,
        }

    def _parse_from_lines(self, lines: list[str]) -> Optional[dict[str, Any]]:
        joined = "\n".join(lines)
        vs_match = re.search(r"([A-Za-z0-9 .&'-]{2,})\s+vs\s+([A-Za-z0-9 .&'-]{2,})", joined, re.I)
        score_match = re.search(r"\b(\d{1,3})\s*/\s*(\d{1,2})\b", joined)
        overs_value = self._extract_labeled_value(lines, "overs")
        overs_match = re.search(r"\b(\d{1,2}(?:\.\d)?)\s*overs?\b", overs_value or joined, re.I)
        striker = self._extract_labeled_value(lines, "striker")
        non_striker = self._extract_labeled_value(lines, "non-striker") or self._extract_labeled_value(lines, "non striker")
        bowler = self._extract_labeled_value(lines, "bowler")
        recent = self._extract_labeled_value(lines, "recent balls")
        event = self._extract_labeled_value(lines, "event")

        if not (score_match or overs_match or striker or bowler or event):
            return None

        return {
            "match_id": None,
            "team_home": self._clean_text(vs_match.group(1)) if vs_match else None,
            "team_away": self._clean_text(vs_match.group(2)) if vs_match else None,
            "inning": None,
            "score": score_match.group(1) if score_match else None,
            "wickets": score_match.group(2) if score_match else None,
            "overs": overs_match.group(1) if overs_match else None,
            "striker": striker,
            "non_striker": non_striker,
            "bowler": bowler,
            "recent_balls": self._coerce_recent_balls(recent),
            "event": event,
            "timestamp": None,
        }

    def _extract_labeled_value(self, lines: list[str], label: str) -> Optional[str]:
        normalized_label = label.lower().rstrip(":")
        for idx, line in enumerate(lines):
            current = line.lower().strip().rstrip(":")
            if current == normalized_label:
                if idx + 1 < len(lines):
                    return self._clean_text(lines[idx + 1]) or None
            if current.startswith(normalized_label + ":"):
                return self._clean_text(line.split(":", 1)[1]) or None
        return None

    def _extract_teams_from_obj(self, match: dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
        for key in ("teams", "team_names"):
            value = match.get(key)
            if isinstance(value, list) and len(value) >= 2:
                return self._clean_text(value[0]) or None, self._clean_text(value[1]) or None
        home = self._clean_text(match.get("team_home") or match.get("home_team") or "") or None
        away = self._clean_text(match.get("team_away") or match.get("away_team") or "") or None
        title = self._clean_text(match.get("title") or match.get("match_name") or "")
        if title:
            vs_match = re.search(r"(.+?)\s+vs\s+(.+)", title, re.I)
            if vs_match:
                return self._clean_text(vs_match.group(1)) or None, self._clean_text(vs_match.group(2)) or None
        return home, away

    def _coerce_recent_balls(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [self._clean_text(v) for v in value if self._clean_text(v)]
        if isinstance(value, str):
            items = re.split(r"[\s,|]+", value)
            return [self._clean_text(v) for v in items if self._clean_text(v)]
        return []

    def _split_score(self, score_text: str, wickets_text: str) -> tuple[Optional[str], Optional[str]]:
        if score_text and "/" in score_text:
            runs, wickets = [p.strip() for p in score_text.split("/", 1)]
            return runs or None, wickets or None
        return (score_text or None), (wickets_text or None)

    def _html_to_lines(self, html: str) -> list[str]:
        html = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
        html = re.sub(r"<style.*?</style>", " ", html, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", "\n", html)
        text = unescape(text)
        lines = [self._clean_text(line) for line in text.splitlines()]
        return [line for line in lines if line]

    def _clean_text(self, value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()


async def detect_stumps_status(team_id: str) -> dict[str, Any]:
    provider = StumpsProvider(team_id)
    result = await provider.get_status()
    payload = dict(result.payload)
    payload["connected"] = result.connected
    payload["limitation"] = result.limitation
    return payload
