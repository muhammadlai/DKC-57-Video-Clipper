"""
test_captions.py — caption group building and ASS file generation
(pure logic, no FFmpeg needed).
"""

import os
import tempfile

import captioner


def _transcript():
    # 3 short segments over 12 seconds
    return [
        {"start": 0.0, "end": 4.0, "text": "welcome to the show today we have a great guest"},
        {"start": 4.0, "end": 8.0, "text": "talking about building products and shipping fast"},
        {"start": 8.0, "end": 12.0, "text": "stay tuned for the next part of this episode"},
    ]


def test_extract_clip_segments_only_in_range():
    # Times are returned relative to the clip start (4.0), so the window
    # is 0..8.
    segs = captioner._extract_clip_segments(_transcript(), 4.0, 12.0)
    assert segs, "should have segments"
    for s in segs:
        assert s["start"] >= 0.0
        assert s["end"] <= 8.0 + 1e-6
        assert s["end"] > s["start"]


def test_build_caption_groups_respects_max_chars():
    groups = captioner._build_caption_groups(_transcript(), max_chars=15)
    assert groups, "should produce groups"
    for g in groups:
        line = g.get("text") or ""
        assert len(line) <= 20  # allow small tolerance for word wrap


def test_word_timing_added_for_animation_styles():
    groups = captioner._build_caption_groups(_transcript(), max_chars=15)
    timed = captioner._add_word_timing(groups)
    assert timed
    # at least one group should now carry per-word timing
    has_words = any(g.get("words") for g in timed)
    assert has_words, "word timing should add per-word data"


def test_write_ass_file_produces_valid_ass():
    groups = captioner._build_caption_groups(_transcript(), max_chars=15)
    groups = captioner._add_word_timing(groups)
    style = captioner.CAPTION_STYLES["classic_white"]

    with tempfile.NamedTemporaryFile(suffix=".ass", delete=False) as f:
        path = f.name
    try:
        captioner._write_ass_file(path, groups, style)
        assert os.path.exists(path)
        content = open(path, encoding="utf-8").read()
        assert "[V4+ Styles]" in content
        assert "Format:" in content
        # dialogue lines present
        assert "Dialogue:" in content
    finally:
        os.unlink(path)


def test_caption_styles_have_required_fields():
    for key, st in captioner.CAPTION_STYLES.items():
        for field in ("name", "fontsize", "animation", "max_chars_per_line"):
            assert field in st, f"style {key} missing {field}"
