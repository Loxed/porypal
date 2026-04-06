"""
server/api/extract.py
Routes: /api/extract
"""
from __future__ import annotations
import io
import json
import os
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from model.image_manager import ImageManager
from server.helpers import make_pal_content
from server.state import state

router = APIRouter(prefix="/api/extract", tags=["extract"])


def _palette_response(palette, method: str, color_space: str) -> dict:
    return {
        "name":        palette.name,
        "colors":      [c.to_hex() for c in palette.colors],
        "pal_content": make_pal_content(palette),
        "color_space": color_space,
        "method":      method,          # "embedded" | "kmeans"
    }


@router.post("")
async def extract_palette(
    file: UploadFile = File(...),
    n_colors: int = Form(default=15),
    bg_color: str | None = Form(default="#73C5A4"),
    color_space: str = Form(default="oklab"),
):
    """
    Extract a GBA palette from the uploaded sprite.

    For paletted PNGs with ≤16 colors (4bpp), the embedded palette is used
    directly and both oklab/rgb responses are identical.
    For all other images, k-means clustering is applied in the requested color space.

    Returns palette hex colors, JASC .pal content, and method ('embedded'|'kmeans').
    """
    if color_space not in ("oklab", "rgb"):
        raise HTTPException(400, f"color_space must be 'oklab' or 'rgb', got {color_space!r}")

    data = await file.read()
    suffix = Path(file.filename).suffix
    name   = Path(file.filename).stem

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        palette, method = state.extractor.extract(
            tmp_path,
            n_colors=n_colors,
            bg_color=bg_color,
            color_space=color_space,
            name=name,
        )

        if len(palette.colors) > 16:
            raise HTTPException(
                400,
                f"Image has too many colors ({len(palette.colors)}); max 16 for GBA",
            )

        return _palette_response(palette, method, color_space)

    finally:
        os.unlink(tmp_path)


@router.post("/download-zip")
async def download_extract_zip(
    file: UploadFile = File(...),
    n_colors: int = Form(default=15),
    bg_color: str | None = Form(default="#73C5A4"),
    color_space: str = Form(default="oklab"),
    name: str = Form(default=""),
):
    """
    Extract palette and return a zip containing:
      manifest.json
      <name>.png  — 4bpp indexed PNG with palette embedded
      <name>.pal  — JASC-PAL

    The indexed PNG uses the extracted palette so palette slots match exactly
    between the .png and .pal files.
    """
    if color_space not in ("oklab", "rgb"):
        raise HTTPException(400, f"color_space must be 'oklab' or 'rgb', got {color_space!r}")

    data   = await file.read()
    suffix = Path(file.filename).suffix or ".png"
    stem   = (name or Path(file.filename).stem).strip() or "palette"
    bg     = bg_color or "#73C5A4"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        # 1. Extract palette
        palette, method = state.extractor.extract(
            tmp_path,
            n_colors=n_colors,
            bg_color=bg,
            color_space=color_space,
            name=stem,
        )

        # 2. Render 4bpp indexed PNG via ImageManager
        #    (nearest-neighbour pixel→slot mapping, same pipeline as Convert tab)
        img_mgr = ImageManager()
        img_mgr.load_image(tmp_path, bg_color=bg)
        results = img_mgr.process_all_palettes([palette])
        indexed_img = results[0].image   # mode "P"

        # 3. Build zip
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # Indexed 4bpp PNG
            png_buf = io.BytesIO()
            indexed_img.save(png_buf, format="PNG", bits=4, optimize=True)
            zf.writestr(f"{stem}.png", png_buf.getvalue())

            # JASC-PAL
            zf.writestr(f"{stem}.pal", make_pal_content(palette))

            # Manifest
            manifest = {
                "name":        stem,
                "method":      method,
                "color_space": color_space,
                "bg_color":    bg,
                "n_colors":    len(palette.colors),
                "colors":      [c.to_hex() for c in palette.colors],
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        zip_buf.seek(0)
        return StreamingResponse(
            zip_buf,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{stem}.zip"'},
        )
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

    counter = 1
    while dest.exists():
        stem = filename.removesuffix(".pal")
        dest = dest_dir / f"{stem}_{counter}.pal"
        counter += 1

    dest.write_text(pal_content, encoding="utf-8")
    state.palette_manager.reload()
    return {"saved": dest.name}