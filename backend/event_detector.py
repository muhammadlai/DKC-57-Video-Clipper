"""
event_detector.py — cricket-specific moment detection from verified match
context.

The detector only emits events when it can justify them from the score
provider's current payload. It never invents player names or match data.
"""

from __future__ import annotations

import hashlib
from typing import Any, Optional


_INTERESTING_EVENT_TYPES = {
    "SIX",
    "FOUR",
    "WICKET",
    "CATCH",
    "RUN OUT",
    "BOWLED",
    "LBW",
    "STUMPING",
    "APPEAL",
    "BIG HIT",
    "DROPPED CATCH",
    "CELEBRATION",
    "CROWD REACTION",
    "PLAYER REACTION",
    "IMPORTANT MOMENT",
}


def detect_moment(previous: Optional[dict[str, Any]], current: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not current:
        return None

    event_text = _normalize(str(current.get("event") or ""))
    recent_balls = current.get("recent_balls") or []
    recent_token = _normalize(recent_balls[-1]) if recent_balls else ""

    event_type = _classify_event(event_text, recent_token, previous, current)
    if not event_type:
        return None

    match_id = current.get("match_id") or "unknown-match"
    player = current.get("striker") or None
    bowler = current.get("bowler") or None
    over_text = current.get("overs") or None
    score_text = _score_text(current)
    event_id = f"{match_id}:{event_type}:{over_text or current.get('timestamp') or 'n/a'}"
    fingerprint = hashlib.sha256(
        "|".join(
            [
                str(match_id),
                str(current.get("timestamp") or ""),
                event_type,
                str(player or ""),
                str(bowler or ""),
                str(over_text or ""),
                str(score_text or ""),
                str(recent_token or event_text or ""),
            ]
        ).encode("utf-8")
    ).hexdigest()

    return {
        "event_id": event_id,
        "match_id": match_id,
        "event_type": event_type,
        "player": player,
        "bowler": bowler,
        "over_text": over_text,
        "score_text": score_text,
        "timestamp": current.get("timestamp"),
        "fingerprint": fingerprint,
        "confidence": _estimate_confidence(event_text, recent_token),
        "event_json": current,
    }


def _classify_event(
    event_text: str,
    recent_token: str,
    previous: Optional[dict[str, Any]],
    current: dict[str, Any],
) -> Optional[str]:
    combined = f"{event_text} {recent_token}".strip()
    if not combined and not _score_changed(previous, current):
        return None

    if any(token in combined for token in ("run out",)):
        return "RUN OUT"
    if any(token in combined for token in ("bowled",)):
        return "BOWLED"
    if any(token in combined for token in ("lbw",)):
        return "LBW"
    if any(token in combined for token in ("stumping",)):
        return "STUMPING"
    if any(token in combined for token in ("dropped catch", "drop catch")):
        return "DROPPED CATCH"
    if any(token in combined for token in ("catch", "caught")):
        return "CATCH"
    if any(token in combined for token in ("appeal",)):
        return "APPEAL"
    if any(token in combined for token in ("celebration",)):
        return "CELEBRATION"
    if any(token in combined for token in ("crowd",)):
        return "CROWD REACTION"
    if any(token in combined for token in ("reaction",)):
        return "PLAYER REACTION"
    if any(token in combined for token in ("wicket", " out ", " wicket")) or _wicket_incremented(previous, current):
        return "WICKET"
    if any(token in combined for token in ("six",)) or recent_token == "6":
        return "SIX"
    if any(token in combined for token in ("four",)) or recent_token == "4":
        return "FOUR"
    if any(token in combined for token in ("big hit",)):
        return "BIG HIT"
    if _score_changed(previous, current):
        return "IMPORTANT MOMENT"
    return None


def _estimate_confidence(event_text: str, recent_token: str) -> float:
    if event_text and recent_token:
        return 0.95
    if event_text or recent_token:
        return 0.85
    return 0.65


def _score_changed(previous: Optional[dict[str, Any]], current: dict[str, Any]) -> bool:
    if not previous:
        return False
    return (_score_text(previous), previous.get("overs")) != (_score_text(current), current.get("overs"))


def _wicket_incremented(previous: Optional[dict[str, Any]], current: dict[str, Any]) -> bool:
    if not previous:
        return False
    try:
        return int(current.get("wickets") or 0) > int(previous.get("wickets") or 0)
    except Exception:
        return False


def _score_text(item: dict[str, Any]) -> Optional[str]:
    if item.get("score") is None and item.get("wickets") is None:
        return None
    return f"{item.get('score')}/{item.get('wickets')}"


def _normalize(value: Any) -> str:
    return f" {str(value or '').strip().lower()} "
