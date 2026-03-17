"""
server/api/shiny.py

Routes: /api/shiny

Mode 2: given a normal sprite and its shiny recolor, extract two palettes
with matching indices — same pixel maps to the same slot in both .pal files.
"""

from __future__ import annotations
import io
import os
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from model.palette import Color, Palette
from model.palette_extractor import rgb_to_oklab, oklab_to_rgb

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


def _load_rgba(data: bytes, suffix: str) -> np.ndarray:
    img = Image.open(io.BytesIO(data)).convert("RGBA")
    return np.array(img)


@router.post("/extract-matched")
async def extract_matched_palettes(
    normal_file: UploadFile = File(...),
    shiny_file: UploadFile = File(...),
    n_colors: int = Form(default=15),
    bg_color: str = Form(default="#73C5A4"),
):
    """
    Given a normal sprite and its shiny recolor, extract two palettes
    with matching indices. Cluster using the normal sprite, then for each
    cluster find the corresponding shiny color.

    Returns both palettes as hex arrays + JASC .pal content.
    """
    normal_data = await normal_file.read()
    shiny_data  = await shiny_file.read()

    normal_px = _load_rgba(normal_data, normal_file.filename)
    shiny_px  = _load_rgba(shiny_data,  shiny_file.filename)

    if normal_px.shape != shiny_px.shape:
        raise HTTPException(400, "Normal and shiny sprites must be the same dimensions")

    bg = _parse_hex(bg_color)
    bg_rgb = np.array(bg.to_tuple(), dtype=np.uint8)

    # Build mask: opaque pixels that aren't the bg color
    alpha   = normal_px[:, :, 3]
    rgb_n   = normal_px[:, :, :3]
    rgb_s   = shiny_px[:, :, :3]

    opaque_mask = alpha.flatten() >= 255
    flat_n = rgb_n.reshape(-1, 3)
    flat_s = rgb_s.reshape(-1, 3)

    non_bg_mask = opaque_mask & ~np.all(flat_n == bg_rgb, axis=1)

    sprite_pixels_n = flat_n[non_bg_mask].astype(np.uint8)
    sprite_pixels_s = flat_s[non_bg_mask].astype(np.uint8)

    if len(sprite_pixels_n) == 0:
        raise HTTPException(400, "No sprite pixels found — check bg_color")

    max_sprite_colors = 15
    n_colors = min(n_colors, max_sprite_colors)

    # Cluster the NORMAL sprite in Oklab space
    lab_n = rgb_to_oklab(sprite_pixels_n)
    unique_colors = len(np.unique(sprite_pixels_n, axis=0))
    actual_clusters = min(n_colors, unique_colors)

    kmeans = KMeans(n_clusters=actual_clusters, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(lab_n)

    # For each cluster: normal centroid = mean of normal pixels in cluster
    # shiny centroid = mean of SHINY pixels at same positions
    normal_colors = []
    shiny_colors  = []

    cluster_sizes = np.bincount(labels, minlength=actual_clusters)
    order = np.argsort(-cluster_sizes)  # sort by size descending

    for cluster_idx in order:
        mask = labels == cluster_idx

        # Normal: convert centroid back from Oklab
        center_lab = kmeans.cluster_centers_[cluster_idx]
        center_rgb = oklab_to_rgb(center_lab[np.newaxis, :])[0]
        normal_colors.append(Color(int(center_rgb[0]), int(center_rgb[1]), int(center_rgb[2])))

        # Shiny: mean of shiny pixels that correspond to this cluster
        shiny_mean = sprite_pixels_s[mask].astype(np.float32).mean(axis=0)
        shiny_colors.append(Color(int(shiny_mean[0]), int(shiny_mean[1]), int(shiny_mean[2])))

    normal_full = [bg] + normal_colors
    shiny_full  = [bg] + shiny_colors

    stem_n = Path(normal_file.filename).stem
    stem_s = Path(shiny_file.filename).stem

    return {
        "normal": {
            "name": stem_n,
            "colors": [c.to_hex() for c in normal_full],
            "pal_content": _make_pal_content(normal_full),
        },
        "shiny": {
            "name": stem_s,
            "colors": [c.to_hex() for c in shiny_full],
            "pal_content": _make_pal_content(shiny_full),
        },
    }