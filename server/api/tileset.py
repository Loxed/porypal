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
from server.helpers import pil_to_b64, is_4bpp_bytes, save_png

router = APIRouter(prefix="/api/tileset", tags=["tileset"])


@router.post("/slice")
async def tileset_slice(
    file: UploadFile = File(...),
    tile_width: int = Form(default=32),
    tile_height: int = Form(default=32),
    input_tile_width: int | None = Form(default=None),
    input_tile_height: int | None = Form(default=None),
    output_tile_width: int | None = Form(default=None),
    output_tile_height: int | None = Form(default=None),
):
    """Slice a tileset into individual tiles. Returns source image + all tile images as base64."""
    input_tile_width = input_tile_width or tile_width
    input_tile_height = input_tile_height or tile_height
    output_tile_width = output_tile_width or input_tile_width
    output_tile_height = output_tile_height or input_tile_height

    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        config = {
            "tileset": {
                "input_sprite_size": {"width": input_tile_width, "height": input_tile_height},
                "output_sprite_size": {"width": output_tile_width, "height": output_tile_height},
                "sprite_order": [0],
                "resize_tileset": False,
                "resize_to": 128,
                "supported_sizes": [],
            },
            "output": {"output_width": output_tile_width, "output_height": output_tile_height},
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
            "input_tile_width": input_tile_width,
            "input_tile_height": input_tile_height,
            "tile_width": output_tile_width,
            "tile_height": output_tile_height,
        }
    finally:
        os.unlink(tmp_path)


@router.post("/arrange")
async def tileset_arrange(
    file: UploadFile = File(...),
    tile_width: int = Form(default=32),
    tile_height: int = Form(default=32),
    input_tile_width: int | None = Form(default=None),
    input_tile_height: int | None = Form(default=None),
    output_tile_width: int | None = Form(default=None),
    output_tile_height: int | None = Form(default=None),
    cols: int = Form(default=9),
    rows: int = Form(default=1),
    sprite_order: str = Form(...),
):
    """Arrange tiles by order string and return a downloadable PNG."""
    input_tile_width = input_tile_width or tile_width
    input_tile_height = input_tile_height or tile_height
    output_tile_width = output_tile_width or input_tile_width
    output_tile_height = output_tile_height or input_tile_height

    data = await file.read()
    was_4bpp = is_4bpp_bytes(data)
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        order = []
        for x in sprite_order.split(","):
            x = x.strip()
            order.append(int(x) if x else None)
        config = {
            "tileset": {
                "input_sprite_size": {"width": input_tile_width, "height": input_tile_height},
                "output_sprite_size": {"width": output_tile_width, "height": output_tile_height},
                "sprite_order": order,
                "resize_tileset": False,
                "resize_to": 128,
                "supported_sizes": [],
            },
            "output": {
                "output_width": cols * output_tile_width,
                "output_height": rows * output_tile_height,
            },
        }
        mgr = TilesetManager(config)
        if not mgr.load(tmp_path):
            raise HTTPException(400, "Failed to process tileset")

        out_bytes = save_png(mgr.get_processed(), preserve_4bpp=was_4bpp)
        stem = Path(file.filename).stem
        return StreamingResponse(
            io.BytesIO(out_bytes),
            media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="{stem}_arranged.png"'},
        )
    finally:
        os.unlink(tmp_path)
