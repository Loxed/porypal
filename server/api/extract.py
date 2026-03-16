"""
server/api/extract.py

Routes: /api/extract
"""

from __future__ import annotations
import io
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from server.state import state

router = APIRouter(prefix="/api/extract", tags=["extract"])


@router.post("")
async def extract_palette(
    file: UploadFile = File(...),
    n_colors: int = Form(default=15),
    bg_color: str | None = Form(default="#73C5A4"),
):
    """
    Extract a GBA palette from the uploaded sprite using k-means.
    Returns the palette as hex colors + a downloadable .pal file content.
    """
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        palette = state.extractor.extract(tmp_path, n_colors=n_colors, bg_color=bg_color)

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


@router.post("/save")
async def save_extracted_palette(
    name: str = Form(...),
    pal_content: str = Form(...),
):
    """
    Save an in-memory extracted palette into palettes/user/.
    Called from the Extract tab after a successful extraction.
    """
    dest_dir = Path("palettes") / "user"
    dest_dir.mkdir(parents=True, exist_ok=True)

    filename = name if name.endswith(".pal") else f"{name}.pal"
    dest = dest_dir / filename

    # Avoid clobbering — append suffix if name already exists
    counter = 1
    while dest.exists():
        stem = filename.removesuffix(".pal")
        dest = dest_dir / f"{stem}_{counter}.pal"
        counter += 1

    dest.write_text(pal_content, encoding="utf-8")
    state.palette_manager.reload()
    return {"saved": dest.name}