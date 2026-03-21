"""
server/app.py

FastAPI entrypoint - mounts routers and middleware only.
All route logic lives in server/api/*.py.
"""

from __future__ import annotations
import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from server.api import (
    palettes, convert, extract, batch,
    tileset, presets, health, library,
    pipeline, items, shiny,
)

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

app = FastAPI(title="Porypal API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(palettes.router)
app.include_router(convert.router)
app.include_router(extract.router)
app.include_router(batch.router)
app.include_router(tileset.router)
app.include_router(presets.router)
app.include_router(health.router)
app.include_router(library.router)
app.include_router(pipeline.router)
app.include_router(items.router)
app.include_router(shiny.router)

# --- Root redirect ---
# Must be registered before the static files mount, otherwise the SPA
# handler catches "/" first and serves index.html without redirecting.

@app.get("/")
def root():
    return RedirectResponse(url="/#/home")


# --- Static files ---
# When running as a PyInstaller bundle, bundled read-only assets live in
# PORYPAL_BUNDLE_DIR (sys._MEIPASS). In development they're relative to the
# repo root.

_bundle = os.environ.get("PORYPAL_BUNDLE_DIR")
_base   = Path(_bundle) if _bundle else Path(__file__).parent.parent

example_dir   = _base / "example"
frontend_dist = _base / "frontend" / "dist"

if example_dir.exists():
    app.mount(
        "/example",
        StaticFiles(directory=str(example_dir)),
        name="example",
    )

if frontend_dist.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(frontend_dist), html=True),
        name="frontend",
    )