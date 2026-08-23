"""
test_ffmpeg_util.py — portable FFmpeg resolution logic (DKC 57).
"""

import os

import ffmpeg_util


def test_env_path_wins():
    # Point at a real existing file (the python executable) as a stand-in
    fake = os.environ.get("FFMPEG_PATH")
    # Reset cache to ensure resolution is fresh
    ffmpeg_util._cache.clear()
    try:
        os.environ["FFMPEG_PATH"] = "/nonexistent/ffmpeg-xyz"
        import pytest
        with pytest.raises(RuntimeError):
            ffmpeg_util.get_ffmpeg()
    finally:
        ffmpeg_util._cache.clear()
        if fake:
            os.environ["FFMPEG_PATH"] = fake
        else:
            os.environ.pop("FFMPEG_PATH", None)


def test_resolves_to_existing_file(monkeypatch):
    # If conftest set a static ffmpeg, resolution must return that path
    ffmpeg_util._cache.clear()
    if os.environ.get("FFMPEG_PATH"):
        path = ffmpeg_util.get_ffmpeg()
        assert path == os.environ["FFMPEG_PATH"]
        assert os.path.isfile(path)
    else:
        # No env var — must fall back to system PATH or bundled, or raise
        import pytest
        try:
            path = ffmpeg_util.get_ffmpeg()
            assert os.path.isfile(path)
        except RuntimeError:
            pass  # acceptable in a bare environment
    ffmpeg_util._cache.clear()


def test_ffprobe_resolves(monkeypatch):
    ffmpeg_util._cache.clear()
    if os.environ.get("FFPROBE_PATH"):
        assert ffmpeg_util.get_ffprobe() == os.environ["FFPROBE_PATH"]
    ffmpeg_util._cache.clear()


def test_available_flag_never_raises():
    ffmpeg_util._cache.clear()
    result = ffmpeg_util.ffmpeg_available()
    assert isinstance(result, bool)
    ffmpeg_util._cache.clear()
