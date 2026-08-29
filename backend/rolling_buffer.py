"""
rolling_buffer.py — continuous rolling capture for the active YouTube
live source.

The implementation records short local segments with FFmpeg, keeps only
recent files, and can extract a final clip spanning pre-roll + post-roll
by concatenating overlapping segments and trimming the requested window.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Any, Optional

import ffmpeg_util  # type: ignore


class RollingBufferManager:
    def __init__(self, root_dir: str, segment_seconds: int = 5, retain_seconds: int = 180):
        self.root_dir = root_dir
        self.segment_seconds = max(2, segment_seconds)
        self.retain_seconds = max(retain_seconds, self.segment_seconds * 4)
        self.source_url: Optional[str] = None
        self.process: Optional[subprocess.Popen[str]] = None
        self.cleanup_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self._segment_meta_cache: dict[str, dict[str, Any]] = {}
        os.makedirs(self.root_dir, exist_ok=True)

    def start(self, source_url: str) -> None:
        if self.process and self.process.poll() is None and self.source_url == source_url:
            return
        self.stop()
        self.source_url = source_url
        self.stop_event.clear()
        shutil.rmtree(self.root_dir, ignore_errors=True)
        os.makedirs(self.root_dir, exist_ok=True)

        ffmpeg = ffmpeg_util.get_ffmpeg()
        output_pattern = os.path.join(self.root_dir, "segment_%Y%m%dT%H%M%S.mp4")
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-i",
            source_url,
            "-c",
            "copy",
            "-f",
            "segment",
            "-segment_time",
            str(self.segment_seconds),
            "-reset_timestamps",
            "1",
            "-strftime",
            "1",
            output_pattern,
        ]
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
        self.process = None
        self.source_url = None

    def status(self) -> dict[str, Any]:
        segments = self.list_segments()
        latest_end = max((s["end_ts"] for s in segments), default=0.0)
        ready = bool(segments and (time.time() - latest_end) < self.segment_seconds * 3)
        return {
            "running": bool(self.process and self.process.poll() is None),
            "ready": ready,
            "segment_count": len(segments),
            "latest_segment_end": latest_end or None,
            "source_url": self.source_url,
        }

    def list_segments(self) -> list[dict[str, Any]]:
        files = sorted(glob.glob(os.path.join(self.root_dir, "segment_*.mp4")))
        segments = []
        now = time.time()
        for path in files:
            try:
                stat = os.stat(path)
            except FileNotFoundError:
                continue
            if stat.st_size == 0:
                continue
            meta = self._segment_meta_cache.get(path)
            if not meta or meta.get("mtime") != stat.st_mtime or meta.get("size") != stat.st_size:
                duration = self._probe_duration(path)
                meta = {"duration": duration, "mtime": stat.st_mtime, "size": stat.st_size}
                self._segment_meta_cache[path] = meta
            duration = float(meta["duration"])
            if duration <= 0:
                continue
            end_ts = stat.st_mtime
            start_ts = end_ts - duration
            if now - end_ts > self.retain_seconds + 60:
                continue
            segments.append(
                {
                    "path": path,
                    "duration": duration,
                    "start_ts": start_ts,
                    "end_ts": end_ts,
                }
            )
        return segments

    def extract_clip(self, window_start_ts: float, window_end_ts: float, output_path: str) -> str:
        if window_end_ts <= window_start_ts:
            raise RuntimeError("Invalid extraction window")
        segments = [
            s for s in self.list_segments()
            if s["end_ts"] > window_start_ts and s["start_ts"] < window_end_ts
        ]
        if not segments:
            raise RuntimeError("Rolling buffer does not contain the requested time window.")

        with tempfile.TemporaryDirectory(prefix="aitzaz-buffer-") as tmp:
            concat_list = os.path.join(tmp, "segments.txt")
            merged_path = os.path.join(tmp, "merged.mp4")
            with open(concat_list, "w", encoding="utf-8") as fh:
                for segment in segments:
                    escaped = segment["path"].replace("'", "'\\''")
                    fh.write(f"file '{escaped}'\n")
            ffmpeg = ffmpeg_util.get_ffmpeg()
            concat_cmd = [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_list,
                "-c",
                "copy",
                merged_path,
            ]
            result = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=180)
            if result.returncode != 0:
                raise RuntimeError((result.stderr or result.stdout or "Failed to concatenate buffer segments")[:600])

            first_start = segments[0]["start_ts"]
            clip_offset = max(0.0, window_start_ts - first_start)
            clip_duration = max(0.5, window_end_ts - window_start_ts)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            trim_cmd = [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{clip_offset:.3f}",
                "-i",
                merged_path,
                "-t",
                f"{clip_duration:.3f}",
                "-c",
                "copy",
                output_path,
            ]
            trim = subprocess.run(trim_cmd, capture_output=True, text=True, timeout=180)
            if trim.returncode != 0 or not os.path.exists(output_path):
                fallback = [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-ss",
                    f"{clip_offset:.3f}",
                    "-i",
                    merged_path,
                    "-t",
                    f"{clip_duration:.3f}",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-c:a",
                    "aac",
                    output_path,
                ]
                fallback_result = subprocess.run(fallback, capture_output=True, text=True, timeout=300)
                if fallback_result.returncode != 0 or not os.path.exists(output_path):
                    raise RuntimeError((fallback_result.stderr or fallback_result.stdout or "Failed to trim clip from rolling buffer")[:600])
            return output_path

    def _cleanup_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                self._prune_old_segments()
            except Exception:
                pass
            self.stop_event.wait(max(2, self.segment_seconds))

    def _prune_old_segments(self) -> None:
        cutoff = time.time() - self.retain_seconds
        for path in glob.glob(os.path.join(self.root_dir, "segment_*.mp4")):
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
                    self._segment_meta_cache.pop(path, None)
            except FileNotFoundError:
                pass

    def _probe_duration(self, path: str) -> float:
        ffprobe = ffmpeg_util.get_ffprobe()
        res = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if res.returncode != 0:
            return 0.0
        try:
            return float(res.stdout.strip())
        except Exception:
            return 0.0
