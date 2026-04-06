"""
server/api/shiny.py
"""

from __future__ import annotations
import io
import json
import os
import tempfile
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from model.palette import Color, Palette
from server.helpers import pil_to_b64, make_pal_content, save_png
from server.state import state

router = APIRouter(prefix="/api/shiny", tags=["shiny"])


def _parse_hex(hex_color: str) -> Color:
    h = hex_color.lstrip('#')
    return Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _load_rgba(data: bytes) -> np.ndarray:
    return np.array(Image.open(io.BytesIO(data)).convert("RGBA"))


def _remap_sprite(sprite_px: np.ndarray, normal_colors: list[Color], shiny_colors: list[Color]) -> Image.Image:
    """
    Remap sprite pixels: find the nearest color in normal_colors for each pixel,
    then output a paletted image using shiny_colors at the same indices.
    """
    h, w = sprite_px.shape[:2]
    rgb   = sprite_px[:, :, :3]
    alpha = sprite_px[:, :, 3]

    normal_rgb = np.array([c.to_tuple() for c in normal_colors], dtype=np.uint8)
    shiny_rgb  = np.array([c.to_tuple() for c in shiny_colors],  dtype=np.uint8)

    flat_rgb   = rgb.reshape(-1, 3).astype(np.uint8)
    flat_alpha = alpha.flatten()
    index_flat = np.zeros(h * w, dtype=np.uint8)
    bg_rgb     = normal_rgb[0]

    for i in range(h * w):
        if flat_alpha[i] < 128:
            index_flat[i] = 0
            continue
        px = flat_rgb[i]
        if np.all(px == bg_rgb):
            index_flat[i] = 0
            continue
        dists  = ((normal_rgb[1:].astype(np.int32) - px.astype(np.int32)) ** 2).sum(axis=1)
        idx    = int(dists.argmin()) + 1
        index_flat[i] = idx if idx < len(shiny_rgb) else 0

    out = Image.new("P", (w, h))
    pal_data: list[int] = []
    for c in shiny_colors:
        pal_data += list(c.to_tuple())
    pal_data += [0] * (768 - len(pal_data))
    out.putpalette(pal_data)
    out.putdata(index_flat.tolist())
    out.info["transparency"] = 0
    return out


def _extract_normal_palette(image_data: bytes, filename: str, n_colors: int, bg_color: str) -> Palette:
    """
    Extract a clean palette using the shared extractor (same as Extract tab).
    Writes to a temp file, calls state.extractor.extract(), cleans up.
    """
    suffix = Path(filename).suffix or ".png"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(image_data)
        tmp_path = tmp.name
    try:
        return state.extractor.extract(
            tmp_path,
            n_colors=n_colors,
            bg_color=bg_color,
            color_space="oklab",
            name=Path(filename).stem,
        )
    finally:
        os.unlink(tmp_path)


def _build_shiny_palette(
    normal_palette: Palette,
    normal_px: np.ndarray,
    shiny_px: np.ndarray,
    bg_color: str,
) -> Palette:
    """
    Given a clean normal palette and both sprite pixel arrays, build the shiny
    palette by: for each slot in normal_palette, find all pixels in shiny_px
    that correspond to that slot (via nearest-match in normal_px), then take
    their mean color as the shiny slot color.
    """
    bg     = _parse_hex(bg_color)
    bg_rgb = np.array(bg.to_tuple(), dtype=np.uint8)

    h, w      = normal_px.shape[:2]
    alpha     = normal_px[:, :, 3]
    rgb_n     = normal_px[:, :, :3]
    rgb_s     = shiny_px[:, :, :3]

    flat_n    = rgb_n.reshape(-1, 3).astype(np.uint8)
    flat_s    = rgb_s.reshape(-1, 3).astype(np.uint8)
    flat_a    = alpha.flatten()

    normal_colors = normal_palette.colors  # includes slot 0 = bg

    # For each opaque non-bg pixel, find its nearest slot in normal palette (skip slot 0)
    opaque_non_bg = (flat_a >= 255) & ~np.all(flat_n == bg_rgb, axis=1)
    pixels_n = flat_n[opaque_non_bg]
    pixels_s = flat_s[opaque_non_bg]

    if len(pixels_n) == 0:
        # Nothing to map — return identical palette
        return Palette(name=normal_palette.name + "_shiny", colors=list(normal_palette.colors))

    normal_rgb_arr = np.array([c.to_tuple() for c in normal_colors[1:]], dtype=np.int32)

    # Vectorised nearest-slot assignment
    diffs    = pixels_n.astype(np.int32)[:, np.newaxis, :] - normal_rgb_arr[np.newaxis, :, :]
    dists_sq = (diffs ** 2).sum(axis=2)          # (N_pixels, N_slots)
    nearest  = dists_sq.argmin(axis=1)           # slot index into normal_colors[1:]

    # For each slot, collect shiny pixel colors and take mean
    n_slots     = len(normal_colors) - 1
    shiny_slots: list[Color] = []

    for slot_i in range(n_slots):
        mask = nearest == slot_i
        if mask.any():
            mean = pixels_s[mask].astype(np.float32).mean(axis=0)
            shiny_slots.append(Color(int(mean[0]), int(mean[1]), int(mean[2])))
        else:
            # No pixels mapped here — keep the normal color
            shiny_slots.append(normal_colors[slot_i + 1])

    return Palette(
        name=normal_palette.name + "_shiny",
        colors=[bg] + shiny_slots,
    )


@router.post("/extract-matched")
async def extract_matched_palettes(
    normal_file: UploadFile = File(...),
    shiny_file:  UploadFile = File(...),
    n_colors: int = Form(default=15),
    bg_color: str = Form(default="#73C5A4"),
):
    normal_data = await normal_file.read()
    shiny_data  = await shiny_file.read()
    normal_px   = _load_rgba(normal_data)
    shiny_px    = _load_rgba(shiny_data)

    if normal_px.shape != shiny_px.shape:
        raise HTTPException(400, "Normal and shiny sprites must be the same dimensions")

    normal_pal = _extract_normal_palette(normal_data, normal_file.filename, n_colors, bg_color)
    shiny_pal  = _build_shiny_palette(normal_pal, normal_px, shiny_px, bg_color)

    return {
        "normal": {
            "name":        normal_pal.name,
            "colors":      [c.to_hex() for c in normal_pal.colors],
            "pal_content": make_pal_content(normal_pal),
        },
        "shiny": {
            "name":        shiny_pal.name,
            "colors":      [c.to_hex() for c in shiny_pal.colors],
            "pal_content": make_pal_content(shiny_pal),
        },
    }


@router.post("/extract-matched/download")
async def download_matched_palettes(
    normal_file: UploadFile = File(...),
    shiny_file:  UploadFile = File(...),
    n_colors: int = Form(default=15),
    bg_color: str = Form(default="#73C5A4"),
):
    normal_data = await normal_file.read()
    shiny_data  = await shiny_file.read()
    normal_px   = _load_rgba(normal_data)
    shiny_px    = _load_rgba(shiny_data)

    if normal_px.shape != shiny_px.shape:
        raise HTTPException(400, "Normal and shiny sprites must be the same dimensions")

    normal_pal = _extract_normal_palette(normal_data, normal_file.filename, n_colors, bg_color)
    shiny_pal  = _build_shiny_palette(normal_pal, normal_px, shiny_px, bg_color)

    stem_n = Path(normal_file.filename).stem
    stem_s = Path(shiny_file.filename).stem

    normal_img = _remap_sprite(normal_px, normal_pal.colors, normal_pal.colors)
    shiny_img  = _remap_sprite(normal_px, normal_pal.colors, shiny_pal.colors)

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"palettes/{stem_n}.pal",       make_pal_content(normal_pal))
        zf.writestr(f"palettes/{stem_s}_shiny.pal", make_pal_content(shiny_pal))
        zf.writestr(f"sprites/{stem_n}.png",        save_png(normal_img))
        zf.writestr(f"sprites/{stem_s}_shiny.png",  save_png(shiny_img))
        manifest = {
            "files": [
                {"name": stem_n, "palette": f"palettes/{stem_n}.pal",           "sprite": f"sprites/{stem_n}.png"},
                {"name": stem_s, "palette": f"palettes/{stem_s}_shiny.pal",     "sprite": f"sprites/{stem_s}_shiny.png"},
            ]
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

    zip_buf.seek(0)
    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{stem_n}_shiny_pair.zip"'},
    )


@router.post("/apply/download")
async def download_apply_shiny(
    sprite_file:     UploadFile = File(...),
    normal_pal:      str = Form(...),        # JSON hex array
    shiny_pal:       str = Form(...),        # JSON hex array
    normal_pal_name: str = Form(default="normal"),
    shiny_pal_name:  str = Form(default="shiny"),
    sprite_name:     str = Form(default="sprite"),
):
    try:
        normal_colors = [_parse_hex(h) for h in json.loads(normal_pal)]
        shiny_colors  = [_parse_hex(h) for h in json.loads(shiny_pal)]
    except Exception:
        raise HTTPException(400, "Invalid palette JSON")

    sprite_px = _load_rgba(await sprite_file.read())

    normal_img = _remap_sprite(sprite_px, normal_colors, normal_colors)
    shiny_img  = _remap_sprite(sprite_px, normal_colors, shiny_colors)

    stem        = sprite_name or Path(sprite_file.filename).stem
    normal_name = normal_pal_name.replace('.pal', '')
    shiny_name  = shiny_pal_name.replace('.pal', '')

    # Wrap raw color lists in Palette objects so make_pal_content works
    normal_palette_obj = Palette(name=normal_name, colors=normal_colors)
    shiny_palette_obj  = Palette(name=shiny_name,  colors=shiny_colors)

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"sprites/{stem}.png",             save_png(normal_img))
        zf.writestr(f"sprites/{stem}_shiny.png",       save_png(shiny_img))
        zf.writestr(f"palettes/{normal_name}.pal",     make_pal_content(normal_palette_obj))
        zf.writestr(f"palettes/{shiny_name}.pal",      make_pal_content(shiny_palette_obj))
        manifest = {
            "files": [
                {"name": stem,            "sprite": f"sprites/{stem}.png",       "palette": f"palettes/{normal_name}.pal"},
                {"name": f"{stem}_shiny", "sprite": f"sprites/{stem}_shiny.png", "palette": f"palettes/{shiny_name}.pal"},
            ]
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

    zip_buf.seek(0)
    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{stem}_shiny.zip"'},
    )
