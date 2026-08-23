#!/usr/bin/env bash
# START-LINUX.sh — One-click launcher for Linux / macOS / Chromebook (Linux dev environment)
# Double-click in a file manager OR run:  bash START-LINUX.sh
set -e
cd "$(dirname "$0")"

echo "=========================================="
echo "    DKC 57 VIDEO CLIPPER - One-Click Start"
echo "    AI-Powered Shorts Generator"
echo "=========================================="
echo ""

# ---------- checks ----------
PYTHON=$(command -v python3 || command -v python || true)
if [ -z "$PYTHON" ]; then
    echo "[ERROR] Python 3 not found."
    echo "        Debian/Ubuntu/Chromebook Linux:  sudo apt install python3 python3-venv python3-pip"
    echo "        macOS:                           brew install python"
    exit 1
fi
echo "[OK] $($PYTHON --version)"

if ! command -v node >/dev/null 2>&1; then
    echo "[ERROR] Node.js not found. Install Node 20+ (LTS) from https://nodejs.org/"
    echo "        Chromebook Linux tip:  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt install -y nodejs"
    exit 1
fi
echo "[OK] $(node -v)"

if command -v ffmpeg >/dev/null 2>&1; then
    echo "[OK] system $(ffmpeg -version 2>/dev/null | head -1 | awk '{print $3}')"
else
    echo "[..] no system ffmpeg - will use bundled static FFmpeg (auto download)"
fi

# ---------- .env files ----------
[ -f backend/.env ] || cp backend/.env.example backend/.env
[ -f frontend/.env.local ] || cp frontend/.env.example frontend/.env.local
echo "[OK] Environment files ready"

# ---------- venv + core deps ----------
if [ ! -d .venv ]; then
    echo "Creating Python environment (first run)..."
    $PYTHON -m venv .venv
fi
.venv/bin/pip install -q --upgrade pip
echo "Installing/updating backend dependencies (first run ~2-5 min)..."
.venv/bin/pip install -q -r backend/requirements-core.txt

# ---------- ffmpeg resolution ----------
if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "Fetching bundled FFmpeg (first run only, ~30 MB)..."
    FFM=$(.venv/bin/python -c "import static_ffmpeg as sf; sf.add_paths(); from static_ffmpeg.run import get_or_fetch_platform_executables_else_raise as g; print(g()[0])" 2>/dev/null || true)
    FFPR=$(.venv/bin/python -c "import static_ffmpeg as sf; sf.add_paths(); from static_ffmpeg.run import get_or_fetch_platform_executables_else_raise as g; print(g()[1])" 2>/dev/null || true)
    [ -n "$FFM" ]  && export FFMPEG_PATH="$FFM"
    [ -n "$FFPR" ] && export FFPROBE_PATH="$FFPR"
    [ -n "$FFM" ] && echo "[OK] FFmpeg ready" || echo "[WARN] FFmpeg not found - install it: sudo apt install ffmpeg"
fi

# ---------- optional AI pack ----------
echo ""
read -r -p "Install full AI pack? (local transcription + face tracking, ~3 GB download) [Y/n]: " AI
if [ "$AI" = "Y" ] || [ "$AI" = "y" ]; then
    echo "Installing AI pack (can take 10-30 min)..."
    .venv/bin/pip install -r backend/requirements-ai.txt
else
    echo "[NOTE] AI pack skipped - YouTube links still work fully (official captions)."
    echo "       Add later: .venv/bin/pip install -r backend/requirements-ai.txt"
fi

# ---------- frontend ----------
cd frontend
if [ ! -d node_modules ]; then
    echo "Installing frontend dependencies (first run ~1-3 min)..."
    npm install --no-audit --no-fund
fi
echo "Building frontend (first run ~1 min)..."
npm run build
cd ..

# ---------- start servers ----------
echo ""
echo "=========================================="
echo "   Starting DKC 57 Video Clipper..."
echo ""
echo "   App:        http://localhost:5000"
echo "   API health: http://localhost:8000/api/health"
echo ""
echo "   Stop with Ctrl+C"
echo "=========================================="

cd backend
"$OLDPWD/.venv/bin/python" -m uvicorn api:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
cd ../frontend
(npm start &)
# wait for frontend to bind, then open browser
sleep 6
(command -v google-chrome >/dev/null 2>&1 && google-chrome http://localhost:5000) \
  || (command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:5000) \
  || true
echo ""
echo "Frontend starting on port 5000 (logs above). Press Ctrl+C to stop everything."
trap 'kill $BACKEND_PID 2>/dev/null; pkill -f "next start" 2>/dev/null; exit 0' INT TERM
wait $BACKEND_PID
