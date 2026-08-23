#!/usr/bin/env bash
# ============================================================
#  INSTALL-CHROMEBOOK.sh
#  DKC 57 Video Clipper — one-command setup for Chromebook
#  (Linux development environment / Crostini)
#
#  Prerequisite (one time, cannot be scripted):
#    Chrome Settings -> Developers -> Linux development
#    environment (Beta) -> Turn on
#
#  Then open Terminal and run:
#    curl -O https://raw.githubusercontent.com/muhammadlai/DKC-57-Video-Clipper/main/INSTALL-CHROMEBOOK.sh && bash INSTALL-CHROMEBOOK.sh
#
#  After 10-15 minutes the app opens at http://localhost:5000
# ============================================================
set -e

echo "=============================================="
echo "   DKC 57 VIDEO CLIPPER - Chromebook Installer"
echo "=============================================="
echo ""

# ---------- 1. system packages ----------
echo "==> [1/4] Installing system packages (password may be asked)..."
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip ffmpeg unzip ca-certificates curl

# ---------- 2. Node 20+ ----------
NODE_OK=0
if command -v node >/dev/null 2>&1; then
    NODE_MAJOR=$(node -v | sed 's/v//' | cut -d. -f1)
    if [ "${NODE_MAJOR:-0}" -ge 20 ]; then
        NODE_OK=1
    fi
fi
if [ "$NODE_OK" -eq 0 ]; then
    echo "==> [2/4] Installing Node.js 22 (LTS)..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
    sudo apt install -y nodejs
else
    echo "==> [2/4] Node $(node -v) already present"
fi
echo "[OK] Node $(node -v), Python $(python3 --version | awk '{print $2}')"

# ---------- 3. get the app ----------
echo "==> [3/4] Getting the app..."
cd ~
if [ -d DKC-57-Video-Clipper ]; then
    cd DKC-57-Video-Clipper
    git pull --ff-only 2>/dev/null || true
    echo "[OK] App folder already here - updated"
else
    git clone https://github.com/muhammadlai/DKC-57-Video-Clipper.git
    cd DKC-57-Video-Clipper
    echo "[OK] App downloaded"
fi

# ---------- 4. run the launcher ----------
echo "==> [4/4] Setting up and starting DKC 57 Video Clipper..."
echo ""
echo "    First run takes 10-15 minutes (downloads happen)."
echo "    When it asks about the AI pack, just press ENTER"
echo "    (skips the ~3GB pack - YouTube links still work fully)."
echo ""
bash START-LINUX.sh
