"""
viral_scoring.py — deterministic viral scoring for cricket moments.

The score is intentionally explainable: it combines event importance,
match situation, audio intensity, and confidence without inventing
unknown factors.
"""

from __future__ import annotations

from typing import Any


_EVENT_BASE = {
    "WICKET": 92,
    "RUN OUT": 91,
    "BOWLED": 90,
    "LBW": 88,
    "STUMPING": 87,
    "SIX": 89,
    "FOUR": 82,
    "CATCH": 86,
    "DROPPED CATCH": 78,
    "APPEAL": 70,
    "BIG HIT": 75,
    "CELEBRATION": 73,
    "CROWD REACTION": 68,
    "PLAYER REACTION": 66,
    "IMPORTANT MOMENT": 72,
}


def score_moment(context: dict[str, Any]) -> dict[str, Any]:
    event_type = str(context.get("event_type") or "IMPORTANT MOMENT").upper()
    base = _EVENT_BASE.get(event_type, 65)

    overs = _to_float(context.get("overs"))
    wickets = _to_int(context.get("wickets"))
    confidence = max(0.0, min(1.0, _to_float(context.get("confidence"), 0.6)))
    audio_intensity = max(0.0, min(1.0, _to_float(context.get("audio_intensity"), 0.0)))
    crowd_reaction = max(0.0, min(1.0, _to_float(context.get("crowd_reaction"), 0.0)))
    player_significance = max(0.0, min(1.0, _to_float(context.get("player_significance"), 0.0)))
    unexpectedness = max(0.0, min(1.0, _to_float(context.get("unexpectedness"), 0.0)))

    score = float(base)
    score += audio_intensity * 6
    score += crowd_reaction * 5
    score += player_significance * 4
    score += unexpectedness * 4
    score += (confidence - 0.5) * 10

    if overs >= 15:
        score += 3
    if overs >= 18:
        score += 2
    if wickets >= 5 and event_type in {"WICKET", "RUN OUT", "CATCH", "LBW", "BOWLED", "STUMPING"}:
        score += 2

    return {
        "viral_score": max(0, min(100, round(score))),
        "threshold_recommended": max(0, min(100, round(score))) >= 85,
    }


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except Exception:
        return default
