"""
conftest.py — DKC 57 test fixtures.

Sets isolated environment (temp DB + tmp dir) BEFORE any app module is
imported, and points FFmpeg at the static binary when one is available.
"""

import os
import sys
import tempfile
import pathlib

TEST_ROOT = tempfile.mkdtemp(prefix="dkc57-test-")
os.environ["DB_PATH"] = os.path.join(TEST_ROOT, "test.db")
os.environ["TMP_DIR"] = os.path.join(TEST_ROOT, "tmp")
os.environ.pop("D57_API_KEY", None)

# Optional: real FFmpeg via static-ffmpeg (enables integration tests)
try:
    import static_ffmpeg  # type: ignore

    _ff, _fp = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()
    os.environ["FFMPEG_PATH"] = _ff
    os.environ["FFPROBE_PATH"] = _fp
except Exception:
    pass

BACKEND_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
