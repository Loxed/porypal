"""
server/api/convert.py

Routes: /api/convert
"""

from __future__ import annotations
import io
import os
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from PIL import Image

from server.helpers import pil_to_b64
from server.state import state

router = APIRouter(prefix="/api/convert", tags=["convert"])


@router.post("")
async def convert(
    file: UploadFile = File(...),
    palette_name: str | None = Form(default=None),
    bg_color: str | None = Form(default=None),
):
    """
    Convert an uploaded sprite against all (or one specific) palette(s).
    Returns base64 PNG previews + color counts for each result.
    """
    data = await file.read()
    try:
        Image.open(io.BytesIO(data))
    except Exception as e:
        raise HTTPException(400, f"Cannot open image: {e}")

    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        state.image_manager.load_image(tmp_path, bg_color=bg_color)

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


@router.post("/download")
async def download_converted(
    file: UploadFile = File(...),
    palette_name: str = Form(...),
    bg_color: str | None = Form(default=None),
):
    """Convert and return a single GBA-compatible indexed PNG for download."""
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        state.image_manager.load_image(tmp_path, bg_color=bg_color)
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


@router.post("/download-all")
async def download_all_converted(
    file: UploadFile = File(...),
    bg_color: str | None = Form(default=None),
):
    """Convert against all palettes and return a zip of all results."""
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        state.image_manager.load_image(tmp_path, bg_color=bg_color)
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