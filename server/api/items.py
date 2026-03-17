"""
server/api/items.py

Routes: /api/items

Silhouette-based grouping: sprites with identical opaque/transparent pixel masks
are grouped together. Within each group, palettes are index-aligned on shared colors
but each sprite keeps its own unique colors without cross-sprite clustering.

Strategy:
  1. Each sprite gets its own palette extracted independently (no cross-sprite k-means)
  2. Colors identical across all sprites in the group go to the same slot index
  3. Remaining unique-per-sprite colors fill remaining slots
  4. Only if a single sprite has > n_colors unique colors does it get k-means reduced
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
    return (px.shape[0], px.shape[1], mask.tobytes())


def _extract_sprite_colors(
    px: np.ndarray,
    input_bg_rgb: np.ndarray,
    n_colors: int,
) -> list[tuple[int, int, int]]:
    """
    Extract up to n_colors unique colors from a single sprite's opaque pixels
    (excluding bg). If more than n_colors unique colors exist, k-means reduces
    just this sprite. Returns list of RGB tuples, sorted by frequency descending.
    """
    alpha   = px[:, :, 3]
    rgb     = px[:, :, :3]
    flat_rgb   = rgb.reshape(-1, 3).astype(np.uint8)
    flat_alpha = alpha.flatten()

    opaque_mask = flat_alpha >= 255
    non_bg_mask = opaque_mask & ~np.all(flat_rgb == input_bg_rgb, axis=1)
    sprite_pixels = flat_rgb[non_bg_mask]

    if len(sprite_pixels) == 0:
        return []

    unique, counts = np.unique(sprite_pixels, axis=0, return_counts=True)
    order = np.argsort(-counts)
    unique_sorted = unique[order]

    if len(unique_sorted) <= n_colors:
        # No reduction needed — keep all colors as-is
        return [tuple(c) for c in unique_sorted]
    else:
        # K-means only on this single sprite
        actual_clusters = min(n_colors, len(unique_sorted))
        lab = rgb_to_oklab(sprite_pixels)
        kmeans = KMeans(n_clusters=actual_clusters, random_state=42, n_init="auto")
        labels = kmeans.fit_predict(lab)
        sizes = np.bincount(labels, minlength=actual_clusters)
        order = np.argsort(-sizes)
        centers_rgb = oklab_to_rgb(kmeans.cluster_centers_[order].astype(np.float32))
        return [tuple(int(v) for v in c) for c in centers_rgb]


# A color must appear in at least this fraction of the group to earn a shared slot.
# e.g. 0.5 = majority (>50%), 0.75 = supermajority.
SHARED_COLOR_THRESHOLD = 0.6


def _build_aligned_palette(
    per_sprite_colors: list[list[tuple]],
    n_colors: int,
    output_bg: Color,
) -> list[dict[tuple, int]]:
    """
    Build per-sprite slot maps with two-phase slot assignment:

    Phase 1 — Shared slots (reserved at the front):
      Colors that appear in >= SHARED_COLOR_THRESHOLD fraction of sprites
      get fixed slot indices, sorted by prevalence descending.
      These slots are the same index in every sprite's palette.

    Phase 2 — Per-sprite local slots (fill remaining space):
      Each sprite independently fills its remaining slots with its own
      unique colors, sorted by pixel frequency. No cross-sprite influence.

    Returns: list of dicts mapping rgb_tuple -> 1-based slot index, one per sprite.
    """
    n = len(per_sprite_colors)
    threshold = max(2, round(SHARED_COLOR_THRESHOLD * n)) if n > 1 else 1

    # Count how many sprites contain each color
    color_prevalence: dict[tuple, int] = {}
    for colors in per_sprite_colors:
        for c in set(colors):
            color_prevalence[c] = color_prevalence.get(c, 0) + 1

    # Phase 1: assign shared slots to colors meeting the threshold
    # Sort by prevalence desc, then by total pixel count desc as tiebreak
    majority_colors = [
        c for c, count in color_prevalence.items()
        if count >= threshold
    ]
    majority_colors.sort(key=lambda c: -color_prevalence[c])

    shared_slot_map: dict[tuple, int] = {}  # color -> 1-based slot
    next_shared_slot = 1
    for color in majority_colors:
        if next_shared_slot > n_colors:
            break
        shared_slot_map[color] = next_shared_slot
        next_shared_slot += 1

    n_shared_slots_used = next_shared_slot - 1  # how many Phase 1 slots are occupied

    # Phase 2: each sprite fills remaining slots with its own colors independently
    per_sprite_slot_maps: list[dict[tuple, int]] = []

    for sprite_colors in per_sprite_colors:
        slot_map = dict(shared_slot_map)  # start with shared assignments
        local_slot = n_shared_slots_used + 1  # next available slot for this sprite

        for color in sprite_colors:
            if color in slot_map:
                continue  # already has a shared slot
            if local_slot > n_colors:
                # No more room — map to nearest already-assigned color
                assigned = list(slot_map.items())
                if assigned:
                    nearest = min(
                        assigned,
                        key=lambda x: sum((a - b) ** 2 for a, b in zip(color, x[0]))
                    )
                    slot_map[color] = nearest[1]
                else:
                    slot_map[color] = 1
            else:
                slot_map[color] = local_slot
                local_slot += 1

        per_sprite_slot_maps.append(slot_map)

    return per_sprite_slot_maps


def _render_sprite(
    px: np.ndarray,
    input_bg_rgb: np.ndarray,
    slot_map: dict[tuple, int],
    palette_colors: list[Color],
    output_bg: Color,
) -> Image.Image:
    """
    Render a sprite to a PIL indexed image using the given slot map.
    """
    h, w = px.shape[:2]
    alpha   = px[:, :, 3]
    rgb     = px[:, :, :3]

    flat_rgb   = rgb.reshape(-1, 3).astype(np.uint8)
    flat_alpha = alpha.flatten()

    index_flat = np.zeros(h * w, dtype=np.int32)

    for i in range(h * w):
        if flat_alpha[i] < 255:
            index_flat[i] = 0
            continue
        color_key = tuple(flat_rgb[i])
        if np.all(flat_rgb[i] == input_bg_rgb):
            index_flat[i] = 0
        elif color_key in slot_map:
            index_flat[i] = slot_map[color_key]
        else:
            # Nearest color in slot_map (fallback, should rarely trigger)
            best_slot = 1
            best_dist = float('inf')
            r, g, b = flat_rgb[i]
            for mapped_color, slot in slot_map.items():
                mr, mg, mb = mapped_color
                dist = (r - mr) ** 2 + (g - mg) ** 2 + (b - mb) ** 2
                if dist < best_dist:
                    best_dist = dist
                    best_slot = slot
            index_flat[i] = best_slot

    index_map = index_flat.reshape(h, w)

    out = Image.new("P", (w, h))
    pal_data = list(output_bg.to_tuple())
    for c in palette_colors[1:]:
        pal_data += list(c.to_tuple())
    pal_data += [0] * (768 - len(pal_data))
    out.putpalette(pal_data)
    out.putdata(index_map.flatten().tolist())

    return out


def _extract_group(
    sprites: list[dict],
    n_colors: int,
    output_bg: Color,
) -> dict:
    """
    Process a silhouette group:
    1. Extract colors independently per sprite (with per-sprite k-means only if needed)
    2. Align shared colors to the same slot indices
    3. Render each sprite with its aligned palette
    """
    h, w = sprites[0]["px"].shape[:2]

    # Step 1: extract colors per sprite independently
    per_sprite_colors: list[list[tuple]] = []
    per_sprite_bg: list[np.ndarray] = []

    for sprite in sprites:
        bg_rgb = np.array(_parse_hex(sprite["input_bg"]).to_tuple(), dtype=np.uint8)
        per_sprite_bg.append(bg_rgb)
        colors = _extract_sprite_colors(sprite["px"], bg_rgb, n_colors)
        per_sprite_colors.append(colors)

    # Step 2: build per-sprite slot maps
    # Shared majority colors get fixed low slot indices; each sprite fills
    # remaining slots independently with its own colors.
    per_sprite_slot_maps = _build_aligned_palette(per_sprite_colors, n_colors, output_bg)

    # Count total unique colors across all sprites (for UI info)
    all_colors: set[tuple] = set()
    for colors in per_sprite_colors:
        all_colors.update(colors)
    n_unique = len(all_colors)
    exact = all(len(c) <= n_colors for c in per_sprite_colors)

    # Step 3: render each sprite with its own palette derived from its own slot map
    results = []
    for sprite, bg_rgb, slot_map, sprite_colors in zip(
        sprites, per_sprite_bg, per_sprite_slot_maps, per_sprite_colors
    ):
        # Build this sprite's palette from its slot map: invert slot->color
        slot_to_color: dict[int, tuple] = {}
        for color, slot in slot_map.items():
            if slot not in slot_to_color:
                slot_to_color[slot] = color

        sprite_palette: list[Color] = [output_bg]
        for slot_i in range(1, n_colors + 1):
            if slot_i in slot_to_color:
                r, g, b = slot_to_color[slot_i]
                sprite_palette.append(Color(r, g, b))
            else:
                sprite_palette.append(output_bg)  # empty slot

        out_img = _render_sprite(sprite["px"], bg_rgb, slot_map, sprite_palette, output_bg)

        results.append({
            "name":        sprite["name"],
            "colors":      [c.to_hex() for c in sprite_palette],
            "pal_content": _make_pal_content(sprite_palette),
            "preview":     pil_to_b64(out_img.convert("RGBA")),
            "exact":       len(sprite_colors) <= n_colors,
        })

    return {
        "reference":  sprites[0]["name"],
        "dimensions": f"{w}×{h}",
        "n_unique":   n_unique,
        "exact":      exact,
        "results":    results,
    }


def _build_groups(
    sprites: list[dict],
    n_colors: int,
    output_bg: Color,
) -> list[dict]:
    """Group sprites by silhouette, extract palettes per group."""
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
    input_bg_colors: str = Form(default="[]"),
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
    group_names: str = Form(default="{}"),
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