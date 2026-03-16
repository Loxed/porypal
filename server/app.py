"""
server/app.py

FastAPI server for Porypal v3.
Wraps the pure-Python model layer and exposes it as a REST API.
All image data is transferred as base64 PNG to avoid file system coupling with the browser.
"""

from __future__ import annotations
import base64
import io
import logging
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image

from model.palette import Palette
from model.palette_manager import PaletteManager
from model.image_manager import ImageManager, ConversionResult
from model.palette_extractor import PaletteExtractor

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="Porypal API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- helpers ----------

def pil_to_b64(img: Image.Image) -> str:
    """Convert a PIL image to a base64-encoded PNG string."""
    buf = io.BytesIO()
    img.convert("RGBA").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def load_config() -> dict:
    cfg_path = Path("config.yaml")
    if cfg_path.exists():
        import yaml
        return yaml.safe_load(cfg_path.read_text()) or {}
    return {}

# ---------- shared state ----------
# Simple in-process state — fine for a single-user local tool.

class AppState:
    def __init__(self):
        self.config = load_config()
        self.palette_manager = PaletteManager(self.config)
        self.image_manager = ImageManager(self.config)
        self.extractor = PaletteExtractor()

state = AppState()

# ---------- routes ----------

@app.get("/api/palettes")
def list_palettes():
    """Return all loaded palettes with their colors as hex strings."""
    return [
        {
            "name": p.name,
            "colors": [c.to_hex() for c in p.colors],
            "count": len(p.colors),
        }
        for p in state.palette_manager.get_palettes()
    ]


@app.post("/api/palettes/reload")
def reload_palettes():
    """Reload palettes from the palettes/ directory."""
    state.palette_manager.reload()
    return {"loaded": len(state.palette_manager.get_palettes())}


@app.post("/api/convert")
async def convert(
    file: UploadFile = File(...),
    palette_name: str | None = Form(default=None),
):
    """
    Convert an uploaded sprite against all (or one specific) palette(s).
    Returns base64 PNG previews + color counts for each result.
    """
    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data))
    except Exception as e:
        raise HTTPException(400, f"Cannot open image: {e}")

    # Write to a temp file so ImageManager can use its path-based loader
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        state.image_manager.load_image(tmp_path)

        palettes = state.palette_manager.get_palettes()
        if palette_name:
            palettes = [p for p in palettes if p.name == palette_name]
            if not palettes:
                raise HTTPException(404, f"Palette '{palette_name}' not found")

        results = state.image_manager.process_all_palettes(palettes)
        best = state.image_manager.get_best_indices()

        return {
            "original": pil_to_b64(state.image_manager._original_rgba),
            "results": [
                {
                    "palette_name": r.palette.name,
                    "colors_used": r.colors_used,
                    "used_indices": sorted(r.used_indices),
                    "colors": [c.to_hex() for c in r.palette.colors],
                    "image": pil_to_b64(r.image.convert("RGBA")),
                    "best": i in best,
                }
                for i, r in enumerate(results)
            ],
        }
    finally:
        os.unlink(tmp_path)


@app.post("/api/convert/download")
async def download_converted(
    file: UploadFile = File(...),
    palette_name: str = Form(...),
):
    """
    Convert and return a single GBA-compatible indexed PNG for download.
    """
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        state.image_manager.load_image(tmp_path)
        palette = state.palette_manager.get_palette_by_name(palette_name)
        if not palette:
            raise HTTPException(404, f"Palette '{palette_name}' not found")

        results = state.image_manager.process_all_palettes([palette])
        result = results[0]

        out_buf = io.BytesIO()
        result.image.save(out_buf, format="PNG", bits=4, optimize=True)
        out_buf.seek(0)

        stem = Path(file.filename).stem
        pal_stem = Path(palette_name).stem
        filename = f"{stem}_{pal_stem}.png"

        return StreamingResponse(
            out_buf,
            media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        os.unlink(tmp_path)


@app.post("/api/convert/download-all")
async def download_all_converted(file: UploadFile = File(...)):
    """
    Convert against all palettes and return a zip of all results.
    """
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        state.image_manager.load_image(tmp_path)
        results = state.image_manager.process_all_palettes(
            state.palette_manager.get_palettes()
        )

        zip_buf = io.BytesIO()
        stem = Path(file.filename).stem
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for r in results:
                pal_stem = Path(r.palette.name).stem
                img_buf = io.BytesIO()
                r.image.save(img_buf, format="PNG", bits=4, optimize=True)
                zf.writestr(f"{stem}_{pal_stem}.png", img_buf.getvalue())
        zip_buf.seek(0)

        return StreamingResponse(
            zip_buf,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{stem}_all_palettes.zip"'},
        )
    finally:
        os.unlink(tmp_path)


@app.post("/api/extract")
async def extract_palette(
    file: UploadFile = File(...),
    n_colors: int = Form(default=15),
    bg_color: str | None = Form(default="#73C5A4"),
):
    """
    Extract a GBA palette from the uploaded sprite using k-means.
    Returns the palette as hex colors + a downloadable .pal file as base64.
    """
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        palette = state.extractor.extract(tmp_path, n_colors=n_colors, bg_color=bg_color)

        # bg_color is slot 0 — extractor must return it first
        if len(palette.colors) > 16:
            raise HTTPException(400, f"Image has too many colors ({len(palette.colors)}); max 16 for GBA")

        pal_buf = io.StringIO()
        pal_buf.write("JASC-PAL\n0100\n")
        pal_buf.write(f"{len(palette.colors)}\n")
        for c in palette.colors:
            pal_buf.write(f"{c.r} {c.g} {c.b}\n")

        return {
            "name": palette.name,
            "colors": [c.to_hex() for c in palette.colors],
            "pal_content": pal_buf.getvalue(),
        }
    finally:
        os.unlink(tmp_path)


@app.post("/api/batch")
async def batch_convert(
    files: list[UploadFile] = File(...),
    palette_name: str = Form(...),
):
    """
    Convert multiple sprites against one palette.
    Returns a zip of all converted images.
    """
    palette = state.palette_manager.get_palette_by_name(palette_name)
    if not palette:
        raise HTTPException(404, f"Palette '{palette_name}' not found")

    zip_buf = io.BytesIO()
    results_meta = []

    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for upload in files:
            data = await upload.read()
            with tempfile.NamedTemporaryFile(suffix=Path(upload.filename).suffix, delete=False) as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            try:
                state.image_manager.load_image(tmp_path)
                results = state.image_manager.process_all_palettes([palette])
                r = results[0]
                stem = Path(upload.filename).stem
                pal_stem = Path(palette_name).stem
                out_name = f"{stem}_{pal_stem}.png"
                img_buf = io.BytesIO()
                r.image.save(img_buf, format="PNG", bits=4, optimize=True)
                zf.writestr(out_name, img_buf.getvalue())
                results_meta.append({"file": upload.filename, "colors_used": r.colors_used, "output": out_name})
            except Exception as e:
                results_meta.append({"file": upload.filename, "error": str(e)})
            finally:
                os.unlink(tmp_path)

    zip_buf.seek(0)
    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="batch_output.zip"'},
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "palettes_loaded": len(state.palette_manager.get_palettes())}


# ---------- serve frontend in production ----------
example_dir = Path(__file__).parent.parent / "example"
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if example_dir.exists():
    app.mount("/example", StaticFiles(directory=str(example_dir)), name="example")

if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")



# ---------- tileset routes ----------

from model.tileset_manager import TilesetManager
from server.presets import list_presets, load_preset, save_preset, delete_preset
from pydantic import BaseModel
from typing import Optional

# -- presets --

@app.get("/api/presets")
def get_presets():
    return list_presets()

@app.get("/api/presets/{preset_id}")
def get_preset(preset_id: str):
    p = load_preset(preset_id)
    if not p:
        raise HTTPException(404, f"Preset '{preset_id}' not found")
    return p

class PresetBody(BaseModel):
    name: str
    tile_w: int = 32
    tile_h: int = 32
    cols: int = 9
    rows: int = 1
    slots: list
    slot_labels: Optional[list] = None

@app.post("/api/presets/{preset_id}")
def upsert_preset(preset_id: str, body: PresetBody):
    return save_preset(preset_id, body.model_dump())

@app.delete("/api/presets/{preset_id}")
def remove_preset(preset_id: str):
    p = load_preset(preset_id)
    if not p:
        raise HTTPException(404, f"Preset '{preset_id}' not found")
    if p.get("is_default", False):
        raise HTTPException(403, f"Preset '{preset_id}' is a default preset and cannot be deleted")
    if not delete_preset(preset_id):
        raise HTTPException(500, "Failed to delete preset")
    return {"deleted": preset_id}


# -- tileset --

@app.post("/api/tileset/slice")
async def tileset_slice(
    file: UploadFile = File(...),
    tile_width: int = Form(default=32),
    tile_height: int = Form(default=32),
):
    """Slice a tileset into individual tiles. Returns source image + all tile images as base64."""
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        tmp.write(data); tmp_path = tmp.name
    try:
        config = {
            "tileset": {
                "output_sprite_size": {"width": tile_width, "height": tile_height},
                "sprite_order": [0],
                "resize_tileset": False,
                "resize_to": 128,
                "supported_sizes": [],
            },
            "output": {"output_width": tile_width, "output_height": tile_height},
        }
        from PIL import Image as PILImage
        source_img = PILImage.open(tmp_path).convert("RGBA")
        source_w, source_h = source_img.size

        mgr = TilesetManager(config)
        if not mgr.load(tmp_path):
            raise HTTPException(400, "Failed to slice tileset")

        return {
            "source": pil_to_b64(mgr.get_source()),
            "source_w": source_w,
            "source_h": source_h,
            "tiles": [pil_to_b64(t) for t in mgr.get_tiles()],
            "tile_count": len(mgr.get_tiles()),
            "tile_width": tile_width,
            "tile_height": tile_height,
        }
    finally:
        os.unlink(tmp_path)


@app.post("/api/tileset/arrange")
async def tileset_arrange(
    file: UploadFile = File(...),
    tile_width: int = Form(default=32),
    tile_height: int = Form(default=32),
    cols: int = Form(default=9),
    rows: int = Form(default=1),
    sprite_order: str = Form(...),
):
    """Arrange tiles by order string and return a downloadable PNG."""
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        tmp.write(data); tmp_path = tmp.name
    try:
        order = [int(x.strip()) for x in sprite_order.split(",") if x.strip()]
        config = {
            "tileset": {
                "output_sprite_size": {"width": tile_width, "height": tile_height},
                "sprite_order": order,
                "resize_tileset": False,
                "resize_to": 128,
                "supported_sizes": [],
            },
            "output": {
                "output_width": cols * tile_width,
                "output_height": rows * tile_height,
            },
        }
        mgr = TilesetManager(config)
        if not mgr.load(tmp_path):
            raise HTTPException(400, "Failed to process tileset")

        buf = io.BytesIO()
        mgr.get_processed().save(buf, format="PNG")
        buf.seek(0)
        stem = Path(file.filename).stem
        return StreamingResponse(
            buf, media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="{stem}_arranged.png"'},
        )
    finally:
        os.unlink(tmp_path)


# ---------- serve static ----------

example_dir = Path(__file__).parent.parent / "example"
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"

if example_dir.exists():
    app.mount("/example", StaticFiles(directory=str(example_dir)), name="example")

if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")