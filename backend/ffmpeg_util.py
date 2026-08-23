"""
ffmpeg_util.py — DKC 57 addition: portable FFmpeg / FFprobe resolution.

Upstream OpenClip hard-codes a Windows WinGet FFmpeg path inside the
processing modules.  This helper makes the backend work on Linux, macOS
and Windows without code changes:

    Resolution order for ``ffmpeg`` / ``ffprobe``:
        1. ``FFMPEG_PATH`` / ``FFPROBE_PATH`` environment variables
        2. ``ffmpeg`` / ``ffprobe`` on the system ``PATH``
        3. A bundled binary under ``backend/bin`` (searched recursively)
        4. A clear, actionable error

The returned paths are cached after the first successful lookup.
"""

import os
import shutil
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_cache: dict[str, str] = {}

_BIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")


def _find_bundled(tool: str) -> Optional[str]:
    """Search ``backend/bin`` recursively for a bundled ``tool`` binary."""
    if not os.path.isdir(_BIN_DIR):
        return None
    exe = f"{tool}.exe" if os.name == "nt" else tool
    for root, _dirs, files in os.walk(_BIN_DIR):
        for name in files:
            if name == exe or name == tool:
                candidate = os.path.join(root, name)
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return candidate
    # Fall back to an executable-looking file even without +x bit set
    for root, _dirs, files in os.walk(_BIN_DIR):
        for name in files:
            if name == exe:
                return os.path.join(root, name)
    return None


def _resolve(tool: str, env_var: str) -> str:
    with _lock:
        if tool in _cache:
            return _cache[tool]

        env = os.environ.get(env_var, "").strip()
        if env:
            if os.path.exists(env):
                _cache[tool] = env
                return env
            raise RuntimeError(
                f"{env_var} is set to '{env}' but that file does not exist."
            )

        system = shutil.which(tool)
        if system:
            _cache[tool] = system
            return system

        bundled = _find_bundled(tool)
        if bundled:
            logger.info("Using bundled %s at %s", tool, bundled)
            _cache[tool] = bundled
            return bundled

        raise RuntimeError(
            f"{tool} not found. Install FFmpeg (e.g. 'apt install ffmpeg', "
            f"'brew install ffmpeg', or 'winget install Gyan.FFmpeg') or set "
            f"the {env_var} environment variable to the full path of the "
            f"{tool} binary."
        )


def get_ffmpeg() -> str:
    """Return the path to an ``ffmpeg`` binary (cached)."""
    return _resolve("ffmpeg", "FFMPEG_PATH")


def get_ffprobe() -> str:
    """Return the path to an ``ffprobe`` binary (cached)."""
    return _resolve("ffprobe", "FFPROBE_PATH")


def ffmpeg_available() -> bool:
    """True if an FFmpeg binary can be resolved without raising."""
    try:
        get_ffmpeg()
        return True
    except RuntimeError:
        return False
