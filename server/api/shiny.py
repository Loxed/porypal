"""
server/api/shiny.py
"""

from __future__ import annotations
import base64
import io
import json
import os
import tempfile
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from model.palette import Color
from model.palette_extractor import rgb_to_oklab, oklab_to_rgb
from server.helpers import pil_to_b64

router = APIRouter(prefix="/api/shiny", tags=["shiny"])


def _make_pal_content(colors: list[Color]) -> str:
    buf = io.StringIO()
    buf.write("JASC-PAL\n0100\n")
    buf.write(f"{len(colors)}\n")
    for c in colors:
        buf.write(f"{c.r} {c.g} {c.b}\n")
    return buf.getvalue()


def _parse_hex(hex_color: str) -> Color:
    h = hex_color.lstrip('#')
    return Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _load_rgba(data: bytes) -> np.ndarray:
    return np.array(Image.open(io.BytesIO(data)).convert("RGBA"))


def _remap_sprite(sprite_px: np.ndarray, normal_colors: list[Color], shiny_colors: list[Color]) -> Image.Image:
    """Remap sprite pixels using normal palette indices, render with shiny palette."""
    h, w = sprite_px.shape[:2]
    rgb   = sprite_px[:, :, :3]
    alpha = sprite_px[:, :, 3]

    normal_rgb = np.array([c.to_tuple() for c in normal_colors], dtype=np.uint8)
    shiny_rgb  = np.array([c.to_tuple() for c in shiny_colors],  dtype=np.uint8)

    flat_rgb   = rgb.reshape(-1, 3).astype(np.uint8)
    flat_alpha = alpha.flatten()

    out_flat = np.zeros((h * w, 4), dtype=np.uint8)
    bg_rgb   = normal_rgb[0]
    bg_shiny = shiny_rgb[0]

    for i in range(h * w):
        if flat_alpha[i] < 128:
            out_flat[i] = [*bg_shiny, 255]
            continue
        px = flat_rgb[i]
        if np.all(px == bg_rgb):
            out_flat[i] = [*bg_shiny, 255]
            continue
        dists = ((normal_rgb[1:].astype(np.int32) - px.astype(np.int32)) ** 2).sum(axis=1)
        idx   = int(dists.argmin()) + 1
        mapped = shiny_rgb[idx] if idx < len(shiny_rgb) else bg_shiny
        out_flat[i] = [*mapped, 255]

    out_img = Image.fromarray(out_flat.reshape(h, w, 4), "RGBA")
    return out_img


@router.post("/extract-matched")
async def extract_matched_palettes(
    normal_file: UploadFile = File(...),
    shiny_file:  UploadFile = File(...),
    n_colors: int = Form(default=15),
    bg_color: str = Form(default="#73C5A4"),
):
    normal_data = await normal_file.read()
    shiny_data  = await shiny_file.read()

    normal_px = _load_rgba(normal_data)
    shiny_px  = _load_rgba(shiny_data)

    if normal_px.shape != shiny_px.shape:
        raise HTTPException(400, "Normal and shiny sprites must be the same dimensions")

    bg     = _parse_hex(bg_color)
    bg_rgb = np.array(bg.to_tuple(), dtype=np.uint8)

    alpha   = normal_px[:, :, 3]
    rgb_n   = normal_px[:, :, :3]
    rgb_s   = shiny_px[:, :, :3]

    opaque_mask = alpha.flatten() >= 255
    flat_n = rgb_n.reshape(-1, 3)
    flat_s = rgb_s.reshape(-1, 3)

    non_bg_mask     = opaque_mask & ~np.all(flat_n == bg_rgb, axis=1)
    sprite_pixels_n = flat_n[non_bg_mask].astype(np.uint8)
    sprite_pixels_s = flat_s[non_bg_mask].astype(np.uint8)

    if len(sprite_pixels_n) == 0:
        raise HTTPException(400, "No sprite pixels found — check bg_color")

    n_colors = min(n_colors, 15)
    lab_n    = rgb_to_oklab(sprite_pixels_n)
    unique_colors   = len(np.unique(sprite_pixels_n, axis=0))
    actual_clusters = min(n_colors, unique_colors)

    kmeans = KMeans(n_clusters=actual_clusters, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(lab_n)

    normal_colors = []
    shiny_colors  = []
    cluster_sizes = np.bincount(labels, minlength=actual_clusters)
    order = np.argsort(-cluster_sizes)

    for cluster_idx in order:
        mask       = labels == cluster_idx
        center_lab = kmeans.cluster_centers_[cluster_idx]
        center_rgb = oklab_to_rgb(center_lab[np.newaxis, :])[0]
        normal_colors.append(Color(int(center_rgb[0]), int(center_rgb[1]), int(center_rgb[2])))
        shiny_mean = sprite_pixels_s[mask].astype(np.float32).mean(axis=0)
        shiny_colors.append(Color(int(shiny_mean[0]), int(shiny_mean[1]), int(shiny_mean[2])))

    normal_full = [bg] + normal_colors
    shiny_full  = [bg] + shiny_colors

    stem_n = Path(normal_file.filename).stem
    stem_s = Path(shiny_file.filename).stem

    return {
        "normal": {
            "name":        stem_n,
            "colors":      [c.to_hex() for c in normal_full],
            "pal_content": _make_pal_content(normal_full),
        },
        "shiny": {
            "name":        stem_s,
            "colors":      [c.to_hex() for c in shiny_full],
            "pal_content": _make_pal_content(shiny_full),
        },
    }


@router.post("/extract-matched/download")
async def download_matched_palettes(
    normal_file: UploadFile = File(...),
    shiny_file:  UploadFile = File(...),
    n_colors: int = Form(default=15),
    bg_color: str = Form(default="#73C5A4"),
):
    """Re-runs extraction and returns a zip with palettes/ + sprites/ + manifest."""
    normal_data = await normal_file.read()
    shiny_data  = await shiny_file.read()

    normal_px = _load_rgba(normal_data)
    shiny_px  = _load_rgba(shiny_data)

    if normal_px.shape != shiny_px.shape:
        raise HTTPException(400, "Normal and shiny sprites must be the same dimensions")

    bg     = _parse_hex(bg_color)
    bg_rgb = np.array(bg.to_tuple(), dtype=np.uint8)

    alpha   = normal_px[:, :, 3]
    rgb_n   = normal_px[:, :, :3]
    rgb_s   = shiny_px[:, :, :3]

    opaque_mask     = alpha.flatten() >= 255
    flat_n          = rgb_n.reshape(-1, 3)
    flat_s          = rgb_s.reshape(-1, 3)
    non_bg_mask     = opaque_mask & ~np.all(flat_n == bg_rgb, axis=1)
    sprite_pixels_n = flat_n[non_bg_mask].astype(np.uint8)
    sprite_pixels_s = flat_s[non_bg_mask].astype(np.uint8)

    if len(sprite_pixels_n) == 0:
        raise HTTPException(400, "No sprite pixels found — check bg_color")

    n_colors = min(n_colors, 15)
    lab_n    = rgb_to_oklab(sprite_pixels_n)
    actual_clusters = min(n_colors, len(np.unique(sprite_pixels_n, axis=0)))

    kmeans = KMeans(n_clusters=actual_clusters, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(lab_n)

    normal_colors: list[Color] = []
    shiny_colors:  list[Color] = []
    order = np.argsort(-np.bincount(labels, minlength=actual_clusters))

    for idx in order:
        mask       = labels == idx
        center_rgb = oklab_to_rgb(kmeans.cluster_centers_[idx][np.newaxis, :])[0]
        normal_colors.append(Color(int(center_rgb[0]), int(center_rgb[1]), int(center_rgb[2])))
        shiny_mean = sprite_pixels_s[mask].astype(np.float32).mean(axis=0)
        shiny_colors.append(Color(int(shiny_mean[0]), int(shiny_mean[1]), int(shiny_mean[2])))

    normal_full = [bg] + normal_colors
    shiny_full  = [bg] + shiny_colors

    stem_n = Path(normal_file.filename).stem
    stem_s = Path(shiny_file.filename).stem

    # Render remapped sprites
    normal_img = _remap_sprite(normal_px, normal_full, normal_full)
    shiny_img  = _remap_sprite(normal_px, normal_full, shiny_full)

    def _png_bytes(img: Image.Image) -> bytes:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"palettes/{stem_n}.pal", _make_pal_content(normal_full))
        zf.writestr(f"palettes/{stem_s}_shiny.pal", _make_pal_content(shiny_full))
        zf.writestr(f"sprites/{stem_n}.png",       _png_bytes(normal_img))
        zf.writestr(f"sprites/{stem_s}_shiny.png", _png_bytes(shiny_img))
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
    sprite_file: UploadFile = File(...),
    normal_pal:  str = Form(...),   # JSON hex array
    shiny_pal:   str = Form(...),   # JSON hex array
    normal_pal_name: str = Form(default="normal"),
    shiny_pal_name:  str = Form(default="shiny"),
    sprite_name: str = Form(default="sprite"),
):
    try:
        normal_colors = [_parse_hex(h) for h in json.loads(normal_pal)]
        shiny_colors  = [_parse_hex(h) for h in json.loads(shiny_pal)]
    except Exception:
        raise HTTPException(400, "Invalid palette JSON")

    data      = await sprite_file.read()
    sprite_px = _load_rgba(data)

    normal_img = _remap_sprite(sprite_px, normal_colors, normal_colors)
    shiny_img  = _remap_sprite(sprite_px, normal_colors, shiny_colors)

    def _png_bytes(img: Image.Image) -> bytes:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    stem        = sprite_name or Path(sprite_file.filename).stem
    normal_name = normal_pal_name.replace('.pal', '')
    shiny_name  = shiny_pal_name.replace('.pal', '')

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"sprites/{stem}.png",             _png_bytes(normal_img))
        zf.writestr(f"sprites/{stem}_shiny.png",       _png_bytes(shiny_img))
        zf.writestr(f"palettes/{normal_name}.pal",     _make_pal_content(normal_colors))
        zf.writestr(f"palettes/{shiny_name}.pal",      _make_pal_content(shiny_colors))
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