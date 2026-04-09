from __future__ import annotations
import logging
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from server.api import (
    palettes, convert, extract, batch,
    tileset, health, library,
    pipeline, items, shiny,
)
from server import preset_store as presets

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

app = FastAPI(title="Porypal API", version="3.1.4")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

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

_bundle = os.environ.get("PORYPAL_BUNDLE_DIR")
_base   = Path(_bundle) if _bundle else Path(__file__).parent.parent

example_dir   = _base / "example"
frontend_dist = _base / "frontend" / "dist"

if example_dir.exists():
    app.mount("/example", StaticFiles(directory=str(example_dir)), name="example")

if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")