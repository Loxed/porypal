"""
server/api/items.py

Routes: /api/items

Silhouette-based grouping: sprites with identical opaque/transparent pixel masks
are grouped together. Within each group, palettes are index-compatible.
"""

from __future__ import annotations
import io
import json
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

router = APIRouter(prefix="/api/items", tags=["items"])

DEFAULT_BG = "#73C5A4"


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


def _silhouette_key(px: np.ndarray, input_bg_rgb: np.ndarray) -> tuple:
    """
    Returns a hashable key representing the opaque/transparent mask of a sprite.
    Two sprites with the same silhouette will have the same key.
    """
    alpha = px[:, :, 3]
    rgb   = px[:, :, :3]
    opaque = alpha >= 255
    not_bg = ~np.all(rgb == input_bg_rgb, axis=2)
    mask = (opaque & not_bg).flatten()
    # Include dimensions in key so different-sized sprites never group together
    return (px.shape[0], px.shape[1], mask.tobytes())


def _extract_group(
    sprites: list[dict],  # each has: name, px, input_bg, output_bg
    n_colors: int,
    output_bg: Color,
) -> dict:
    """
    Extract a union palette for a silhouette group.
    
    If unique colors <= n_colors: exact mapping, no clustering.
    If unique colors > n_colors: k-means on the union of all sprite pixels.
    
    All sprites in the group share the same palette slot indices.
    """
    ref = sprites[0]
    ref_bg_rgb = np.array(_parse_hex(ref["input_bg"]).to_tuple(), dtype=np.uint8)

    h, w = ref["px"].shape[:2]

    # Build the shared opaque mask from the reference silhouette
    ref_alpha   = ref["px"][:, :, 3]
    ref_rgb     = ref["px"][:, :, :3]
    flat_alpha  = ref_alpha.flatten()
    flat_ref    = ref_rgb.reshape(-1, 3).astype(np.uint8)
    opaque_mask = flat_alpha >= 255
    non_bg_mask = opaque_mask & ~np.all(flat_ref == ref_bg_rgb, axis=1)

    # Collect all sprite pixels at non-bg positions (union)
    all_sprite_pixels = []
    for sprite in sprites:
        flat = sprite["px"][:, :, :3].reshape(-1, 3).astype(np.uint8)
        all_sprite_pixels.append(flat[non_bg_mask])

    union_pixels = np.concatenate(all_sprite_pixels, axis=0)  # (N*M, 3)

    # Find unique colors in the union
    unique_colors = np.unique(union_pixels, axis=0)  # (K, 3)
    n_unique = len(unique_colors)

    if n_unique <= n_colors:
        # ── Exact mapping ──
        # Sort by frequency descending so most-used colors get low indices
        color_counts = {}
        for px in union_pixels:
            key = tuple(px)
            color_counts[key] = color_counts.get(key, 0) + 1

        sorted_colors = sorted(
            unique_colors,
            key=lambda c: -color_counts.get(tuple(c), 0)
        )

        # slot 0 = output_bg, slots 1..K = sorted unique colors
        palette_colors = [output_bg] + [
            Color(int(c[0]), int(c[1]), int(c[2])) for c in sorted_colors
        ]

        # Build a lookup: rgb tuple → palette index
        color_to_idx = {
            tuple(c): i + 1
            for i, c in enumerate(sorted_colors)
        }

        def map_sprite(sprite):
            s_bg_rgb  = np.array(_parse_hex(sprite["input_bg"]).to_tuple(), dtype=np.uint8)
            full_rgb  = sprite["px"][:, :, :3]
            full_alpha = sprite["px"][:, :, 3]

            flat = full_rgb.reshape(-1, 3).astype(np.uint8)
            index_flat = np.zeros(h * w, dtype=np.int32)

            for pos in range(h * w):
                if not opaque_mask[pos]:
                    index_flat[pos] = 0
                    continue
                key = tuple(flat[pos])
                if key == tuple(s_bg_rgb):
                    index_flat[pos] = 0
                else:
                    index_flat[pos] = color_to_idx.get(key, 0)

            index_map = index_flat.reshape(h, w)
            index_map[full_alpha < 255] = 0
            return index_map

    else:
        # ── K-means on union ──
        actual_clusters = min(n_colors, n_unique)
        lab_union = rgb_to_oklab(union_pixels)
        kmeans    = KMeans(n_clusters=actual_clusters, random_state=42, n_init="auto")
        kmeans.fit(lab_union)

        # Cluster centers → palette colors
        # Sort by cluster size descending (most-used first)
        # We need per-sprite labels to get sizes, so predict on union
        union_labels  = kmeans.predict(lab_union)
        cluster_sizes = np.bincount(union_labels, minlength=actual_clusters)
        order         = np.argsort(-cluster_sizes)

        centers_lab = kmeans.cluster_centers_[order]
        centers_rgb = oklab_to_rgb(centers_lab.astype(np.float32))

        palette_colors = [output_bg] + [
            Color(int(c[0]), int(c[1]), int(c[2])) for c in centers_rgb
        ]

        # Reorder mapping: old cluster idx → new sorted position
        rank = np.empty_like(order)
        rank[order] = np.arange(len(order))

        def map_sprite(sprite):
            s_bg_rgb   = np.array(_parse_hex(sprite["input_bg"]).to_tuple(), dtype=np.uint8)
            full_rgb   = sprite["px"][:, :, :3]
            full_alpha = sprite["px"][:, :, 3]

            flat_lab   = rgb_to_oklab(full_rgb.reshape(-1, 3).astype(np.uint8))
            predicted  = kmeans.predict(flat_lab)
            index_flat = rank[predicted] + 1  # +1 for transparent slot
            index_flat = index_flat.reshape(h, w)

            index_flat[full_alpha < 255] = 0
            index_flat[np.all(full_rgb == s_bg_rgb, axis=2)] = 0
            return index_flat

    # ── Build output for each sprite ──
    results = []
    for sprite in sprites:
        index_map = map_sprite(sprite)
        used      = set(np.unique(index_map).tolist())

        out = Image.new("P", (w, h))
        pal_data = list(output_bg.to_tuple())
        for c in palette_colors[1:]:
            pal_data += list(c.to_tuple())
        pal_data += [0] * (768 - len(pal_data))
        out.putpalette(pal_data)
        out.putdata(index_map.flatten().tolist())

        results.append({
            "name":        sprite["name"],
            "colors":      [c.to_hex() for c in palette_colors],
            "pal_content": _make_pal_content(palette_colors),
            "preview":     pil_to_b64(out.convert("RGBA")),
            "exact":       n_unique <= n_colors,  # flag for frontend
        })

    return {
        "reference":  ref["name"],
        "dimensions": f"{w}×{h}",
        "n_unique":   n_unique,
        "exact":      n_unique <= n_colors,
        "results":    results,
    }


def _build_groups(
    sprites: list[dict],
    n_colors: int,
    output_bg: Color,
) -> list[dict]:
    """Group sprites by silhouette, extract palettes per group."""
    # Group by silhouette key
    groups: dict[tuple, list[dict]] = {}
    for sprite in sprites:
        bg_rgb = np.array(_parse_hex(sprite["input_bg"]).to_tuple(), dtype=np.uint8)
        key    = _silhouette_key(sprite["px"], bg_rgb)
        groups.setdefault(key, []).append(sprite)

    result_groups = []
    for i, (key, group_sprites) in enumerate(groups.items()):
        group_data = _extract_group(group_sprites, n_colors, output_bg)
        group_data["group_id"] = f"shape_{i + 1}"
        result_groups.append(group_data)

    return result_groups


@router.post("/extract")
async def extract_item_palettes(
    files: list[UploadFile] = File(...),
    n_colors: int = Form(default=15),
    input_bg_colors: str = Form(default="[]"),   # JSON array, one per file
    output_bg_color: str = Form(default=DEFAULT_BG),
):
    if not files:
        raise HTTPException(400, "At least one file required")

    try:
        input_bgs = json.loads(input_bg_colors)
    except Exception:
        input_bgs = []

    output_bg = _parse_hex(output_bg_color)

    sprites = []
    for i, f in enumerate(files):
        data = await f.read()
        sprites.append({
            "name":     Path(f.filename).stem,
            "px":       _load_rgba(data),
            "input_bg": input_bgs[i] if i < len(input_bgs) else DEFAULT_BG,
        })

    try:
        groups = _build_groups(sprites, n_colors, output_bg)
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {"groups": groups}


@router.post("/download-all")
async def download_all_item_palettes(
    files: list[UploadFile] = File(...),
    n_colors: int = Form(default=15),
    input_bg_colors: str = Form(default="[]"),
    output_bg_color: str = Form(default=DEFAULT_BG),
    group_names: str = Form(default="{}"),  # JSON dict: group_id → custom name
):
    try:
        input_bgs  = json.loads(input_bg_colors)
        gnames     = json.loads(group_names)
    except Exception:
        input_bgs  = []
        gnames     = {}

    output_bg = _parse_hex(output_bg_color)

    sprites = []
    for i, f in enumerate(files):
        data = await f.read()
        sprites.append({
            "name":     Path(f.filename).stem,
            "px":       _load_rgba(data),
            "input_bg": input_bgs[i] if i < len(input_bgs) else DEFAULT_BG,
        })

    try:
        groups = _build_groups(sprites, n_colors, output_bg)
    except ValueError as e:
        raise HTTPException(400, str(e))

    zip_buf = io.BytesIO()
    manifest = {"groups": []}

    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for group in groups:
            gid      = group["group_id"]
            label    = gnames.get(gid, gid)
            ref_name = group["reference"]

            group_manifest = {
                "id":         gid,
                "name":       label,
                "reference":  ref_name,
                "dimensions": group["dimensions"],
                "palettes":   [],
            }

            for r in group["results"]:
                pal_path = f"{label}/{r['name']}.pal"
                zf.writestr(pal_path, r["pal_content"])
                group_manifest["palettes"].append({
                    "sprite":  r["name"],
                    "palette": pal_path,
                })

            manifest["groups"].append(group_manifest)

        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

    zip_buf.seek(0)
    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="item_palettes.zip"'},
    )