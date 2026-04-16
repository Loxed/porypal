#!/usr/bin/env python3
"""
main.py ΓÇô Porypal v3 launcher

Starts the FastAPI server and opens the browser automatically.
Usage:
    python main.py          # default port 8080 (auto-finds free port)
    python main.py --port 9000
    python main.py --no-browser
"""

import argparse
import os
import shutil
import socket
import sys
import threading
import time
import webbrowser

# ΓöÇΓöÇ Frozen / PyInstaller support ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

if getattr(sys, "frozen", False):
    _exe_dir = os.path.dirname(sys.executable)
    os.chdir(_exe_dir)
    os.environ["PORYPAL_BUNDLE_DIR"] = sys._MEIPASS  # type: ignore[attr-defined]

    # Create user-writable dirs next to the exe
    for _d in ("palettes/user", "palette_library", "presets"):
        os.makedirs(os.path.join(_exe_dir, _d), exist_ok=True)

    # Copy bundled read-only defaults next to the exe on first launch
    for _folder in ("palettes/defaults",):
        _src = os.path.join(sys._MEIPASS, _folder)  # type: ignore[attr-defined]
        _dst = os.path.join(_exe_dir, _folder)
        if os.path.isdir(_src) and not os.path.isdir(_dst):
            shutil.copytree(_src, _dst)

import uvicorn

DEFAULT_HOST  = "127.0.0.1"
DEFAULT_START_PORT = 7860


def find_free_port(start: int = DEFAULT_START_PORT, attempts: int = 10) -> int:
    """Try ports start, start+1, ... until one is free."""
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(
        f"Could not find a free port in range {start}-{start + attempts - 1}. "
        "Try specifying one manually with --port."
    )


def open_browser(host: str, port: int, delay: float = 1.5) -> None:
    time.sleep(delay)
    webbrowser.open(f"http://{host}:{port}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Porypal ΓÇô palette toolchain for Gen 3 ROM hacking"
    )
    parser.add_argument(
        "--host", default=DEFAULT_HOST,
        help=f"Host to bind (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port", type=int, default=None,
        help=f"Port to listen on (default: auto-find starting at {DEFAULT_START_PORT})",
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Don't open browser automatically",
    )
    parser.add_argument(
        "--reload", action="store_true",
        help="Enable auto-reload (dev mode, not available when frozen)",
    )
    args = parser.parse_args()

    reload = args.reload and not getattr(sys, "frozen", False)

    # Resolve port
    try:
        port = args.port if args.port else find_free_port()
    except RuntimeError as e:
        print(f"\n  ERROR: {e}\n")
        if getattr(sys, "frozen", False):
            input("  Press Enter to close...")
        sys.exit(1)

    url = f"http://{args.host}:{port}"

    print("=" * 40)
    print("  Porypal v3.2")
    print("=" * 40)
    print(f"\n  Open your browser and go to:\n")
    print(f"      {url}\n")
    print("  Press Ctrl+C to stop the app.")
    print("=" * 40 + "\n")

    if not args.no_browser:
        t = threading.Thread(
            target=open_browser, args=(args.host, port), daemon=True
        )
        t.start()

    try:
        uvicorn.run(
            "server.app:app",
            host=args.host,
            port=port,
            reload=reload,
            log_level="warning",
        )
    except Exception as e:
        print(f"\n  ERROR: {e}\n")
    finally:
        # Keep console open in frozen builds so users can read any messages
        if getattr(sys, "frozen", False):
            input("\n  Press Enter to close...")


if __name__ == "__main__":
    main()