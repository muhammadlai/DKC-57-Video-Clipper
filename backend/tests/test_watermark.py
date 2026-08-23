"""
test_watermark.py — DKC 57 watermark config normalisation and FFmpeg
filter construction (pure logic, no FFmpeg needed).
"""

import pytest

import watermark


def test_normalize_defaults_off_and_safe():
    cfg = watermark.normalize_config(None)
    assert cfg["enabled"] is False
    assert cfg["position"] == "bottom_right"
    assert 0.05 <= cfg["opacity"] <= 1.0
    assert cfg["margin"] > 0


def test_normalize_clamps_invalid_values():
    cfg = watermark.normalize_config(
        {"enabled": "yes", "position": "middle", "opacity": 7.5, "margin": -50}
    )
    assert cfg["enabled"] is True
    assert cfg["position"] == "bottom_right"  # invalid → default
    assert cfg["opacity"] == 1.0             # clamped to max
    assert cfg["margin"] == 8                # clamped to min


def test_build_filter_complex_all_positions():
    for pos in watermark.VALID_POSITIONS:
        f = watermark.build_filter_complex(pos, 0.6)
        assert f.endswith("[out]")
        assert "overlay=" in f
        assert "aa=0.60" in f
        assert f"[wm]" in f

    # corner expressions
    tl = watermark.build_filter_complex("top_left", 0.5)
    assert "x=24:y=24" in tl
    tr = watermark.build_filter_complex("top_right", 0.5)
    assert "main_w-overlay_w-24" in tr
    bl = watermark.build_filter_complex("bottom_left", 0.5)
    assert "main_h-overlay_h-24" in bl
    br = watermark.build_filter_complex("bottom_right", 0.5)
    assert "main_w-overlay_w-24" in br and "main_h-overlay_h-24" in br


def test_build_filter_complex_rejects_bad_position_and_clamps_opacity():
    with pytest.raises(ValueError):
        watermark.build_filter_complex("center", 0.5)
    f = watermark.build_filter_complex("top_left", 1.9)
    assert "aa=1.00" in f


def test_logo_asset_shipped():
    assert watermark.logo_available(), "watermark PNG asset must be committed"
