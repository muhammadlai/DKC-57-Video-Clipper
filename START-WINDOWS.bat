@echo off
setlocal EnableDelayedExpansion
title DKC 57 Video Clipper - One-Click Start
cd /d "%~dp0"

echo ==========================================
echo     DKC 57 VIDEO CLIPPER - One-Click Start
echo     AI-Powered Shorts Generator
echo ==========================================
echo.

rem ---------- Python check ----------
set "PY="
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 --version >nul 2>nul
    if !errorlevel!==0 set "PY=py -3"
)
if not defined PY (
    where python >nul 2>nul
    if !errorlevel!==0 set "PY=python"
)
if not defined PY (
    echo [ERROR] Python not found.
    echo         Install Python 3.10+ from https://www.python.org/downloads/
    echo         IMPORTANT: tick "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('%PY% --version 2^>nul') do echo [OK] %%v

rem ---------- Node check ----------
where node >nul 2>nul
if !errorlevel!==0 (
    for /f "delims=" %%v in ('node -v') do echo [OK] %%v
) else (
    echo [ERROR] Node.js not found.
    echo         Install Node.js 20+ from https://nodejs.org/  (LTS version)
    echo.
    pause
    exit /b 1
)

rem ---------- .env files ----------
if not exist backend\.env copy backend\.env.example backend\.env >nul
if not exist frontend\.env.local copy frontend\.env.example frontend\.env.local >nul
echo [OK] Environment files ready

rem ---------- Python venv ----------
if not exist .venv\Scripts\python.exe (
    echo.
    echo Creating Python environment (first run)...
    %PY% -m venv .venv
)
echo Installing/updating backend dependencies (first run ~2-5 min)...
.venv\Scripts\python -m pip install --upgrade pip >nul
.venv\Scripts\python -m pip install -r backend\requirements-core.txt
if !errorlevel! neq 0 (
    echo [ERROR] pip install failed. Check your internet connection and retry.
    pause
    exit /b 1
)

rem ---------- bundled FFmpeg (auto download, first run) ----------
echo Fetching bundled FFmpeg (first run only, ~30 MB)...
.venv\Scripts\python -c "import static_ffmpeg as sf; sf.add_paths(); from static_ffmpeg.run import get_or_fetch_platform_executables_else_raise as g; f,p = g(); print(f); print(p)" > ffmpeg_paths.txt
set "FFMPEG_BIN="
set "FFPROBE_BIN="
set /a LINE=0
for /f "usebackq delims=" %%l in ("ffmpeg_paths.txt") do (
    set /a LINE+=1
    if !LINE! EQU 1 set "FFMPEG_BIN=%%l"
    if !LINE! EQU 2 set "FFPROBE_BIN=%%l"
)
del ffmpeg_paths.txt 2>nul
if defined FFMPEG_BIN (
    echo [OK] FFmpeg ready
) else (
    echo [WARN] Could not locate bundled FFmpeg.
    echo        If video processing fails, install FFmpeg:  winget install ffmpeg
)

rem ---------- optional AI pack ----------
echo.
set /p AI=Install full AI pack? (local transcription + face tracking, ~3 GB download) [Y/n]: 
if /i "!AI!"=="Y" (
    echo Installing AI pack (this can take 10-30 min)...
    .venv\Scripts\python -m pip install -r backend\requirements-ai.txt
) else (
    echo.
    echo [NOTE] AI pack skipped - YouTube links will still work fully (official captions).
    echo        To add it later:  .venv\Scripts\pip install -r backend\requirements-ai.txt
)

rem ---------- frontend ----------
pushd frontend
if not exist node_modules (
    echo.
    echo Installing frontend dependencies (first run ~1-3 min)...
    call npm install --no-audit --no-fund
)
echo Building frontend (first run ~1 min)...
call npm run build
if !errorlevel! neq 0 (
    echo [ERROR] Frontend build failed.
    popd
    pause
    exit /b 1
)
popd

rem ---------- start servers ----------
echo.
echo ==========================================
echo    Starting DKC 57 Video Clipper...
echo.
echo    App:        http://localhost:5000
echo    API health: http://localhost:8000/api/health
echo.
echo    Keep the two server windows that open
echo    - closing them stops the app.
echo ==========================================

start "DKC57-Backend" /min "%~dp0run-backend.bat"
start "DKC57-Frontend" /min "%~dp0run-frontend.bat"

timeout /t 10 /nobreak >nul
start "" http://localhost:5000

echo.
echo App opened in your browser.
echo.
pause
