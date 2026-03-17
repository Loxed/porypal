"""
server/app.py

FastAPI entrypoint — mounts routers and middleware only.
All route logic lives in server/api/*.py.
"""

from __future__ import annotations
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.api import palettes, convert, extract, batch, tileset, presets, health, library

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

app = FastAPI(title="Porypal API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- routers ----------

app.include_router(palettes.router)
app.include_router(convert.router)
app.include_router(extract.router)
app.include_router(batch.router)
app.include_router(tileset.router)
app.include_router(presets.router)
app.include_router(health.router)
app.include_router(library.router)

# ---------- static files ----------

example_dir = Path(__file__).parent.parent / "example"
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"

if example_dir.exists():
    app.mount("/example", StaticFiles(directory=str(example_dir)), name="example")

if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")