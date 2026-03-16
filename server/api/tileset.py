"""
server/api/tileset.py

Routes: /api/tileset
"""

from __future__ import annotations
import io
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from PIL import Image as PILImage

from model.tileset_manager import TilesetManager
from server.helpers import pil_to_b64

router = APIRouter(prefix="/api/tileset", tags=["tileset"])


@router.post("/slice")
async def tileset_slice(
    file: UploadFile = File(...),
    tile_width: int = Form(default=32),
    tile_height: int = Form(default=32),
):
    """Slice a tileset into individual tiles. Returns source image + all tile images as base64."""
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
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


@router.post("/arrange")
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
        tmp.write(data)
        tmp_path = tmp.name
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
            buf,
            media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="{stem}_arranged.png"'},
        )
    finally:
        os.unlink(tmp_path)