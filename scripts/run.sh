#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Read venv path written by setup.sh
VENV_PATH_FILE="$REPO_DIR/.venv_path"
if [ ! -f "$VENV_PATH_FILE" ]; then
  echo "  x .venv_path not found. Run ./scripts/setup.sh first."
  exit 1
fi

VENV_DIR=$(cat "$VENV_PATH_FILE")

if [ ! -f "$VENV_DIR/bin/activate" ]; then
  echo "  x Virtual environment not found at $VENV_DIR"
  echo "    Run ./scripts/setup.sh to set it up."
  exit 1
fi

source "$VENV_DIR/bin/activate"
cd "$REPO_DIR"

if grep -qi microsoft /proc/version 2>/dev/null; then
  echo "  WSL detected - open http://127.0.0.1:7860 in your Windows browser"
  python main.py --no-browser "$@"
else
  python main.py "$@"
fi