#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo ""
echo "  Porypal setup"
echo "  -------------"
echo ""

# -- Detect platform -----------------------------------------------------------
IS_WSL=false
IS_MAC=false
IS_LINUX=false

if grep -qi microsoft /proc/version 2>/dev/null; then
  IS_WSL=true
  echo "  Platform: WSL"
elif [[ "$OSTYPE" == "darwin"* ]]; then
  IS_MAC=true
  echo "  Platform: macOS"
else
  IS_LINUX=true
  echo "  Platform: Linux"
fi

# -- Python check --------------------------------------------------------------
PYTHON=""
for cmd in python3 python; do
  if command -v "$cmd" &>/dev/null; then
    MAJOR=$("$cmd" -c "import sys; print(sys.version_info.major)")
    MINOR=$("$cmd" -c "import sys; print(sys.version_info.minor)")
    VERSION=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 10 ]; then
      PYTHON="$cmd"
      echo "  + Python $VERSION ($cmd)"
      break
    else
      echo "  ! Python $VERSION found but 3.10+ required, skipping $cmd"
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  echo ""
  echo "  x Python 3.10+ not found."
  if $IS_MAC; then
    echo "    Install via Homebrew:  brew install python"
    echo "    Or download from:      https://python.org"
  else
    echo "    Ubuntu/Debian:  sudo apt install python3.11"
    echo "    Or download from:      https://python.org"
  fi
  exit 1
fi

# -- python3-venv check (Linux/WSL only) ---------------------------------------
if $IS_LINUX || $IS_WSL; then
  if ! "$PYTHON" -m venv --help &>/dev/null 2>&1; then
    echo ""
    echo "  x python3-venv is not installed."
    echo "    Fix:  sudo apt install python3-venv"
    exit 1
  fi
fi

# -- Node check ----------------------------------------------------------------
if ! command -v node &>/dev/null; then
  echo ""
  echo "  x Node.js not found."
  if $IS_MAC; then
    echo "    Install via Homebrew:  brew install node"
  else
    echo "    Recommended (nvm):"
    echo "      curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash"
    echo "      source ~/.bashrc"
    echo "      nvm install --lts"
    echo ""
    echo "    Or via NodeSource:"
    echo "      curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -"
    echo "      sudo apt install -y nodejs"
  fi
  exit 1
fi

NODE_MAJOR=$(node -e "process.stdout.write(String(process.versions.node.split('.')[0]))")
NODE_VERSION=$(node --version)
if [ "$NODE_MAJOR" -lt 18 ]; then
  echo ""
  echo "  x Node $NODE_VERSION found but 18+ required."
  echo "    Upgrade via nvm:  nvm install --lts && nvm use --lts"
  exit 1
fi
echo "  + Node $NODE_VERSION"

# -- Python venv ---------------------------------------------------------------
# WSL: put the venv in home to avoid slow mounted drive I/O
if $IS_WSL; then
  VENV_DIR="$HOME/.venvs/porypal"
else
  VENV_DIR="$REPO_DIR/venv"
fi

if [ ! -d "$VENV_DIR" ]; then
  echo ""
  echo "  Creating Python virtual environment..."
  mkdir -p "$(dirname "$VENV_DIR")"
  "$PYTHON" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo "  Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r "$REPO_DIR/requirements.txt"
echo "  + Python dependencies installed"

# -- Store venv path so run.sh can find it -------------------------------------
echo "$VENV_DIR" > "$REPO_DIR/.venv_path"

# -- Frontend ------------------------------------------------------------------
echo ""
echo "  Building frontend..."
cd "$REPO_DIR/frontend"
npm install
npm run build
cd "$REPO_DIR"
echo "  + Frontend built"

# -- Required directories ------------------------------------------------------
mkdir -p "$REPO_DIR/palettes/defaults" "$REPO_DIR/palettes/user" "$REPO_DIR/palette_library" "$REPO_DIR/presets"

echo ""
echo ""
echo ""
echo "  -------------------------------------"
echo "  Setup complete!"
echo ""
if $IS_WSL; then
  echo "  WSL detected - the browser won't open automatically."
  echo "  Run the app with:"
  echo "    ./scripts/run.sh"
  echo ""
  echo "  Then open http://127.0.0.1:7860 in your Windows browser."
else
  echo "  To run Porypal:"
  echo "    ./scripts/run.sh"
  echo ""
  echo "  Then open http://127.0.0.1:7860"
fi
echo ""