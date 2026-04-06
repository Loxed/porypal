"""
server/api/batch.py

Routes: /api/batch
"""

from __future__ import annotations
import io
import os
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from server.helpers import save_png
from server.state import state

router = APIRouter(prefix="/api/batch", tags=["batch"])


@router.post("")
async def batch_convert(
    files: list[UploadFile] = File(...),
    palette_name: str = Form(...),
):
    """Convert multiple sprites against one palette. Returns a zip of all results."""
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
                zf.writestr(out_name, save_png(r.image))
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
