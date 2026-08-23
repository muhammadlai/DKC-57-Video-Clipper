"""
test_llm_logic.py — transcript chunking, suggestion validation/parsing
and the even-spacing fallback (no network calls).
"""

import llm


def _segments(n, dur_each=10.0, text="hello world"):
    return [
        {"start": i * dur_each, "end": (i + 1) * dur_each, "text": text}
        for i in range(n)
    ]


def test_chunk_transcript_splits_with_bounds():
    segs = _segments(30)  # 300s
    chunks = llm._chunk_transcript(segs, chunk_minutes=4)  # 240s chunks
    assert len(chunks) >= 2
    # every segment lands in at least one chunk
    covered = {s["start"] for c in chunks for s in c}
    assert covered == {s["start"] for s in segs}


def test_validate_suggestions_respects_custom_bounds():
    suggestions = [
        {"start": 0.0, "end": 100.0, "title": "long", "reason": "", "viral_score": 9},
        {"start": 110.0, "end": 150.0, "title": "good", "reason": "", "viral_score": 8},
        {"start": 160.0, "end": 170.0, "title": "too-short", "reason": "", "viral_score": 7},
        {"start": 180.0, "end": 220.0, "title": "good2", "reason": "", "viral_score": 6},
    ]
    out = llm._validate_suggestions(
        suggestions, video_duration=300.0,
        num_clips=5, min_duration=30.0, max_duration=90.0,
    )
    # "too-short" (10s) must be dropped; the 100s clip must be clamped to <= 90
    for s in out:
        assert 30.0 <= (s["end"] - s["start"]) <= 90.0, s
    titles = {s["title"] for s in out}
    assert "too-short" not in titles
    assert "good" in titles and "long" in titles


def test_validate_suggestions_caps_at_num_clips():
    suggestions = [
        {"start": i * 120.0, "end": i * 120.0 + 60.0,
         "title": f"c{i}", "reason": "", "viral_score": 10 - i}
        for i in range(8)
    ]
    out = llm._validate_suggestions(
        suggestions, video_duration=1000.0,
        num_clips=3, min_duration=30.0, max_duration=90.0,
    )
    # strict pass returns up to the cap only in lenient fallback; here the
    # strict pass keeps everything non-overlapping, so at most num_clips
    # survive after the cap is applied.
    assert len(out) <= 3
    # highest scores kept
    kept = {s["title"] for s in out}
    assert "c0" in kept and "c1" in kept


def test_validate_suggestions_empty_and_degenerate():
    assert llm._validate_suggestions([], 100.0) == []
    out = llm._validate_suggestions(
        [{"start": 50.0, "end": 40.0, "title": "swapped", "reason": "", "viral_score": 5}],
        video_duration=100.0, min_duration=5.0, max_duration=15.0,
    )
    # swapped start/end is corrected, not dropped
    assert any(s["start"] == 40.0 and s["end"] == 50.0 for s in out)


def test_parse_llm_json_handles_fences_and_trailing_commas():
    raw = '''Here you go:
```json
[
  {"start": 10.0, "end": 70.0, "title": "A", "reason": "r", "viral_score": 8, "hashtags": "#a #b", "tags": "x, y",},
  {"start": 80.0, "end": 120.0, "title": "B", "reason": "r", "viral_score": 7,},
]
```
Hope that helps!'''
    parsed = llm._parse_llm_json(raw)
    assert len(parsed) == 2
    assert parsed[0]["hashtags"] == ["#a", "#b"]
    assert parsed[0]["tags"] == ["x", "y"]
    assert parsed[1]["end"] == 120.0


def test_parse_llm_json_skips_invalid_entries():
    raw = '''[
      {"start": 1.0, "end": 2.0, "title": "ok"},
      {"start": "not-a-number", "end": 5.0, "title": "bad"},
      {"title": "missing-times"},
      "just a string"
    ]'''
    parsed = llm._parse_llm_json(raw)
    assert len(parsed) == 1
    assert parsed[0]["title"] == "ok"
    assert parsed[0]["reason"] == ""


def test_even_suggestions_spacing_and_count():
    from api import _even_suggestions

    out = _even_suggestions(duration=300.0, num_clips=5, min_duration=30, max_duration=90)
    assert 1 <= len(out) <= 5
    total = 0
    last_end = -1
    for s in out:
        assert s["start"] >= last_end, "overlap"
        last_end = s["end"]
        total += s["end"] - s["start"]
        assert s["viral_score"] is None
        assert s["end"] <= 300.0 + 1e-6
    # should use a reasonable share of the video
    assert total > 60


def test_even_suggestions_tiny_video_yields_few_or_none():
    from api import _even_suggestions

    out = _even_suggestions(duration=12.0, num_clips=10, min_duration=30, max_duration=90)
    assert len(out) <= 1
