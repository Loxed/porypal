#!/usr/bin/env python3
"""
main.py — Porypal v3 launcher

Starts the FastAPI server and opens the browser automatically.
Usage:
    python main.py          # default port 7860
    python main.py --port 8080
    python main.py --no-browser
"""

import argparse
import threading
import time
import webbrowser
import sys

import uvicorn

DEFAULT_PORT = 7860
DEFAULT_HOST = "127.0.0.1"


def open_browser(host: str, port: int, delay: float = 1.2):
    """Open the browser after a short delay to let the server start."""
    time.sleep(delay)
    webbrowser.open(f"http://{host}:{port}")


def main():
    parser = argparse.ArgumentParser(description="Porypal — palette toolchain for Gen 3 ROM hacking")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host to bind (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to listen on (default: {DEFAULT_PORT})")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (dev mode)")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    print(f"\n  Porypal running at {url}\n")

    if not args.no_browser:
        t = threading.Thread(target=open_browser, args=(args.host, args.port), daemon=True)
        t.start()

    uvicorn.run(
        "server.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
