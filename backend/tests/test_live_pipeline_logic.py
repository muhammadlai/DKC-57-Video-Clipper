import asyncio
import os
import subprocess
import time

import pytest

import control_db
import event_detector
import ffmpeg_util
from rolling_buffer import RollingBufferManager
from viral_scoring import score_moment


def test_event_detector_uses_verified_match_context_without_inventing_names():
    previous = {
        "match_id": "m1",
        "score": "92",
        "wickets": "3",
        "overs": "14.2",
        "striker": None,
        "bowler": "Bilal",
        "recent_balls": ["1", "2"],
        "event": None,
    }
    current = {
        "match_id": "m1",
        "score": "98",
        "wickets": "3",
        "overs": "14.3",
        "striker": None,
        "bowler": "Bilal",
        "recent_balls": ["1", "2", "6"],
        "event": "SIX",
        "timestamp": "2026-08-29T00:00:00Z",
    }
    moment = event_detector.detect_moment(previous, current)
    assert moment is not None
    assert moment["event_type"] == "SIX"
    assert moment["player"] is None
    assert moment["bowler"] == "Bilal"


def test_viral_scoring_rewards_major_events():
    six = score_moment({"event_type": "SIX", "overs": "18.4", "wickets": "3", "confidence": 0.95})
    wicket = score_moment({"event_type": "WICKET", "overs": "18.4", "wickets": "6", "confidence": 0.95})
    assert six["viral_score"] >= 85
    assert wicket["viral_score"] >= six["viral_score"]


@pytest.mark.asyncio
async def test_duplicate_protection_uses_fingerprint():
    await control_db.init_control_db()
    first_created, first = await control_db.insert_moment(
        {
            "event_type": "SIX",
            "fingerprint": "abc123",
            "match_id": "m1",
            "score_text": "98/3",
        }
    )
    second_created, second = await control_db.insert_moment(
        {
            "event_type": "SIX",
            "fingerprint": "abc123",
            "match_id": "m1",
            "score_text": "98/3",
        }
    )
    assert first_created is True
    assert second_created is False
    assert first["fingerprint"] == second["fingerprint"]


@pytest.mark.skipif(not ffmpeg_util.ffmpeg_available(), reason="FFmpeg not available")
def test_rolling_buffer_extracts_clip_from_recent_segments(tmp_path):
    ffmpeg = ffmpeg_util.get_ffmpeg()
    buffer_dir = tmp_path / "buffer"
    buffer_dir.mkdir()

    # Create three 4-second segments and set mtimes to simulate a recent rolling buffer.
    colors = ["red", "blue", "green"]
    now = time.time()
    for idx, color in enumerate(colors):
        path = buffer_dir / f"segment_{idx}.mp4"
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"color=c={color}:size=720x1280:rate=30:duration=4",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=44100:cl=stereo",
                "-shortest",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                str(path),
            ],
            check=True,
            capture_output=True,
            timeout=180,
        )
        mtime = now - (12 - (idx + 1) * 4)
        os.utime(path, (mtime, mtime))

    manager = RollingBufferManager(str(buffer_dir), segment_seconds=4, retain_seconds=60)
    output = tmp_path / "clip.mp4"
    manager.extract_clip(now - 9, now - 3, str(output))
    assert output.exists()
    ffprobe = ffmpeg_util.get_ffprobe()
    probe = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(output)],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    duration = float(probe.stdout.strip())
    assert 5.0 <= duration <= 7.5
