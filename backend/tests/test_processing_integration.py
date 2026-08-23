"""
test_processing_integration.py — REAL FFmpeg processing (DKC 57).

These tests generate a tiny synthetic video with the bundled static
FFmpeg, then run the actual reframer / captioner / watermark /
thumbnail code paths against it.  They are skipped automatically when
no FFmpeg binary is available in the environment.
"""

import asyncio
import os
import subprocess

import pytest

import ffmpeg_util

pytestmark = pytest.mark.skipif(
    not ffmpeg_util.ffmpeg_available(),
    reason="FFmpeg not available in this environment",
)

import reframer      # noqa: E402
import captioner     # noqa: E402
import watermark     # noqa: E402
import clipper       # noqa: E402


@pytest.fixture(scope="module")
def sample_video(tmp_path_factory):
    """Generate a 24s 1280x720 synthetic video with a tone track."""
    tmp = tmp_path_factory.mktemp("video")
    out = str(tmp / "sample.mp4")
    ffmpeg = ffmpeg_util.get_ffmpeg()
    subprocess.run(
        [
            ffmpeg, "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=24",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=24",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
            out,
        ],
        check=True, capture_output=True, timeout=300,
    )
    return out


def test_get_video_duration(sample_video):
    dur = clipper.get_video_duration(sample_video)
    assert 22.0 <= dur <= 26.0


def test_cut_and_reframe_face_tracking_off(sample_video, tmp_path):
    suggestion = {
        "start": 4.0, "end": 16.0,
        "title": "test", "reason": "", "viral_score": 5,
    }
    out = tmp_path / "clips"
    out.mkdir()

    clip = asyncio.run(
        reframer.process_clip(
            sample_video, suggestion, str(out), "itg",
            face_tracking=False,  # no MediaPipe in test env
            reframe=True,
        )
    )
    assert os.path.isfile(clip["file_path"])
    assert clip["reframed"] is True
    assert clip["layout_mode"] == "static_center"
    assert abs(clip["duration"] - 12.0) < 0.5

    # output must be 1080x1920
    w, h = _probe(clip["file_path"])
    assert (w, h) == (1080, 1920)


def test_cut_no_reframe_keeps_original_aspect(sample_video, tmp_path):
    suggestion = {"start": 2.0, "end": 10.0, "title": "t", "reason": "", "viral_score": 1}
    out = tmp_path / "clips"
    out.mkdir()

    clip = asyncio.run(
        reframer.process_clip(sample_video, suggestion, str(out), "itg2",
                              face_tracking=False, reframe=False)
    )
    assert os.path.isfile(clip["file_path"])
    assert clip["reframed"] is False
    assert clip["layout_mode"] == "original"
    w, h = _probe(clip["file_path"])
    assert (w, h) == (1280, 720)  # original framing preserved


def test_caption_burn_on_real_clip(sample_video, tmp_path):
    out = tmp_path / "clips"
    out.mkdir()
    suggestion = {"start": 0.0, "end": 12.0, "title": "t", "reason": "", "viral_score": 1}
    clip = asyncio.run(
        reframer.process_clip(sample_video, suggestion, str(out), "cap",
                              face_tracking=False, reframe=True)
    )

    transcript = [
        {"start": 0.0, "end": 4.0, "text": "welcome to the channel and thank you for stopping by"},
        {"start": 4.0, "end": 8.0, "text": "today we are going to build something really cool together"},
        {"start": 8.0, "end": 12.0, "text": "so let us get started and make something amazing"},
    ]
    captioned = asyncio.run(
        captioner.burn_captions(
            clip["file_path"], transcript,
            0.0, 12.0, "classic_white",
        )
    )
    assert captioned != clip["file_path"]
    assert os.path.isfile(captioned)
    w, h = _probe(captioned)
    assert (w, h) == (1080, 1920)


def test_watermark_burn_on_real_clip(sample_video, tmp_path):
    out = tmp_path / "clips"
    out.mkdir()
    suggestion = {"start": 0.0, "end": 8.0, "title": "t", "reason": "", "viral_score": 1}
    clip = asyncio.run(
        reframer.process_clip(sample_video, suggestion, str(out), "wm",
                              face_tracking=False, reframe=True)
    )
    cfg = watermark.normalize_config(
        {"enabled": True, "position": "bottom_right", "opacity": 0.8}
    )
    wm_out = str(tmp_path / "wm.mp4")
    result = asyncio.run(watermark.apply_watermark(clip["file_path"], wm_out, cfg))
    assert os.path.isfile(result)
    w, h = _probe(result)
    assert (w, h) == (1080, 1920)


def test_watermark_disabled_is_noop(sample_video, tmp_path):
    out = tmp_path / "clips"
    out.mkdir()
    suggestion = {"start": 0.0, "end": 8.0, "title": "t", "reason": "", "viral_score": 1}
    clip = asyncio.run(
        reframer.process_clip(sample_video, suggestion, str(out), "wm0",
                              face_tracking=False, reframe=True)
    )
    cfg = watermark.normalize_config({"enabled": False})
    result = asyncio.run(watermark.apply_watermark(clip["file_path"], str(tmp_path / "x.mp4"), cfg))
    # disabled → returns the input path unchanged
    assert result == clip["file_path"]


def test_thumbnail_generation(sample_video, tmp_path):
    import api
    thumb = str(tmp_path / "thumb.jpg")
    result = asyncio.run(api._generate_thumbnail(sample_video, thumb))
    assert result is not None
    assert os.path.isfile(thumb)
    assert os.path.getsize(thumb) > 0


def _probe(path):
    ffprobe = ffmpeg_util.get_ffprobe()
    res = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True, timeout=60,
    )
    w, h = res.stdout.strip().split(",")
    return int(w), int(h)
