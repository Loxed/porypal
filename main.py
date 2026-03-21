#!/usr/bin/env python3
"""
main.py – Porypal v3 launcher

Starts the FastAPI server and opens the browser automatically.
Usage:
    python main.py          # default port 7860
    python main.py --port 8080
    python main.py --no-browser
"""

import argparse
import os
import sys
import threading
import time
import webbrowser

# ── Frozen / PyInstaller support ──────────────────────────────────────────────
# When running as a PyInstaller bundle:
#   sys.frozen  = True
#   sys._MEIPASS = path to the temp extraction dir containing bundled assets
#   sys.executable = path to the actual .exe / binary
#
# Strategy:
#   • chdir to the exe's parent so all user-data paths (palettes/user,
#     palette_library, presets, projects.json) resolve correctly.
#   • Set PORYPAL_BUNDLE_DIR so server/app.py and model/ can find bundled
#     read-only assets (frontend/dist, palettes/defaults, presets defaults).

if getattr(sys, "frozen", False):
    _exe_dir = os.path.dirname(sys.executable)
    os.chdir(_exe_dir)
    os.environ["PORYPAL_BUNDLE_DIR"] = sys._MEIPASS

    # Create user-writable dirs next to the exe
    for _d in ("palettes/user", "palette_library", "presets"):
        os.makedirs(os.path.join(_exe_dir, _d), exist_ok=True)

    # Copy bundled read-only defaults next to the exe if not already there
    import shutil
    for _folder in ("palettes/defaults",):
        _src = os.path.join(sys._MEIPASS, _folder)
        _dst = os.path.join(_exe_dir, _folder)
        if os.path.isdir(_src) and not os.path.isdir(_dst):
            shutil.copytree(_src, _dst)

import uvicorn

DEFAULT_PORT = 7860
DEFAULT_HOST = "127.0.0.1"


def open_browser(host: str, port: int, delay: float = 1.5) -> None:
    """Open the browser after a short delay to let the server start."""
    time.sleep(delay)
    webbrowser.open(f"http://{host}:{port}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Porypal ΓÇô palette toolchain for Gen 3 ROM hacking"
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    reload = args.reload and not getattr(sys, "frozen", False)

    url = f"http://{args.host}:{args.port}"

    print("=" * 40)
    print("  Porypal v3.0")
    print("=" * 40)
    print(f"\n  Open your browser and go to:\n")
    print(f"      {url}\n")
    print("  Press Ctrl+C to stop the app.")
    print("=" * 40 + "\n")

    if not args.no_browser:
        t = threading.Thread(
            target=open_browser, args=(args.host, args.port), daemon=True
        )
        t.start()

    try:
        uvicorn.run(
            "server.app:app",
            host=args.host,
            port=args.port,
            reload=reload,
            log_level="warning",
        )
    except Exception as e:
        print(f"\n  ERROR: {e}")
    finally:
        # Keep console open so user can read any messages
        if getattr(sys, "frozen", False):
            input("\n  Press Enter to close...")


if __name__ == "__main__":
    main()