"""
watermark.py — DKC 57 addition: optional "DKC 57" watermark for exported clips.

The watermark is **off by default** and never forced.  When enabled it is
burned into the final 9:16 clip as a small, semi-transparent logo overlay in
one of four corners with an adjustable opacity.

Implementation: FFmpeg ``filter_complex`` (logo scale + alpha + overlay).
No third-party service involved — fully local.
"""

import os
import logging
import asyncio
import subprocess
from typing import Any, Dict, Optional

import ffmpeg_util

logger = logging.getLogger(__name__)

VALID_POSITIONS = ("top_left", "top_right", "bottom_left", "bottom_right")

# Default assets
_ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
DEFAULT_LOGO = os.path.join(_ASSET_DIR, "dkc57-watermark.png")

# Visual defaults for the overlay
DEFAULT_MARGIN = 24          # px from the corner
DEFAULT_LOGO_WIDTH = 152     # px, scaled to this width on a 1080-wide clip
DEFAULT_OPACITY = 0.6        # 0.0 – 1.0


def normalize_config(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Coerce a raw watermark config (from project settings / API payload) into
    a validated dict with safe defaults.  Invalid positions/opacities are
    clamped rather than raising, so a bad setting can never break a job.
    """
    raw = raw or {}
    position = raw.get("position")
    if position not in VALID_POSITIONS:
        position = "bottom_right"
    try:
        opacity = float(raw.get("opacity", DEFAULT_OPACITY))
    except (TypeError, ValueError):
        opacity = DEFAULT_OPACITY
    opacity = max(0.05, min(1.0, opacity))
    try:
        margin = int(raw.get("margin", DEFAULT_MARGIN))
    except (TypeError, ValueError):
        margin = DEFAULT_MARGIN
    margin = max(8, min(120, margin))
    return {
        "enabled": bool(raw.get("enabled", False)),
        "position": position,
        "opacity": round(opacity, 2),
        "margin": margin,
        "logo_path": raw.get("logo_path") or DEFAULT_LOGO,
    }


def build_filter_complex(
    position: str,
    opacity: float,
    logo_width: int = DEFAULT_LOGO_WIDTH,
    margin: int = DEFAULT_MARGIN,
) -> str:
    """
    Build the FFmpeg ``-filter_complex`` string that overlays the watermark.

    Input 0 = video, input 1 = watermark logo (PNG with alpha).
    Outputs: [out] watermarked video.
    """
    if position not in VALID_POSITIONS:
        raise ValueError(f"Invalid watermark position: {position}")

    opacity = max(0.0, min(1.0, float(opacity)))
    m = max(0, int(margin))
    x, y = {
        "top_left": (str(m), str(m)),
        "top_right": (f"main_w-overlay_w-{m}", str(m)),
        "bottom_left": (str(m), f"main_h-overlay_h-{m}"),
        "bottom_right": (f"main_w-overlay_w-{m}", f"main_h-overlay_h-{m}"),
    }[position]

    return (
        f"[1:v]scale={logo_width}:-2,format=rgba,"
        f"colorchannelmixer=aa={opacity:.2f}[wm];"
        f"[0:v][wm]overlay=x={x}:y={y}[out]"
    )


def logo_available(logo_path: str = DEFAULT_LOGO) -> bool:
    """True if a watermark logo image exists on disk."""
    return os.path.isfile(logo_path)


async def apply_watermark(
    input_path: str,
    output_path: str,
    config: Dict[str, Any],
) -> str:
    """
    Burn the DKC 57 watermark into ``input_path`` and write ``output_path``.

    Args:
        input_path:  source clip (usually the final 1080x1920 mp4)
        output_path: destination path
        config:      normalized watermark config (see ``normalize_config``)

    Returns:
        The output path on success.

    Raises:
        RuntimeError: if FFmpeg fails or the logo asset is missing.
    """
    cfg = normalize_config(config)
    if not cfg["enabled"]:
        # Nothing to do — still return a usable path
        return input_path

    logo = cfg["logo_path"]
    if not os.path.isfile(logo):
        raise RuntimeError(
            f"Watermark logo not found at '{logo}'. "
            f"Provide a PNG logo or disable the watermark."
        )

    filter_complex = build_filter_complex(
        position=cfg["position"],
        opacity=cfg["opacity"],
        margin=cfg["margin"],
    )
    ffmpeg = ffmpeg_util.get_ffmpeg()
    cmd = [
        ffmpeg, "-y",
        "-i", input_path,
        "-i", logo,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-map", "0:a?",
        "-c:a", "copy",
        output_path,
    ]

    def _run() -> tuple[int, str]:
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode, (res.stderr or "")[-2000:]

    returncode, stderr = await asyncio.to_thread(_run)
    if returncode != 0:
        logger.error("Watermark render failed: %s", stderr)
        raise RuntimeError(f"Watermark render failed: {stderr}")

    return output_path
