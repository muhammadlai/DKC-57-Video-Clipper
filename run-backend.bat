@echo off
title DKC57-Backend
cd /d "%~dp0backend"
if defined FFMPEG_BIN set "FFMPEG_PATH=%FFMPEG_BIN%"
if defined FFPROBE_BIN set "FFPROBE_PATH=%FFPROBE_BIN%"
echo Starting DKC 57 backend on http://127.0.0.1:8000 ...
"%~dp0.venv\Scripts\python.exe" -m uvicorn api:app --host 127.0.0.1 --port 8000
echo.
echo Backend stopped.
pause
