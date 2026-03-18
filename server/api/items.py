"""
server/api/items.py

Routes: /api/items
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
DEFAULT_THRESHOLD = 0.6


def _make_pal_content(colors: list[Color]) -> str:
    """
    Write a JASC-PAL string, trimming any trailing colors that are
    identical to slot 0 (the transparent/bg color). This prevents
    palettes with e.g. 12 real colors being padded out to 16 slots
    of repeated bg color.
    """
    if not colors:
        return "JASC-PAL\n0100\n0\n"

    bg = colors[0]
    # Find the last index that is NOT the bg color
    last_real = 0
    for i, c in enumerate(colors):
        if c != bg:
            last_real = i
    trimmed = colors[:last_real + 1]

    buf = io.StringIO()
    buf.write("JASC-PAL\n0100\n")
    buf.write(f"{len(trimmed)}\n")
    for c in trimmed:
        buf.write(f"{c.r} {c.g} {c.b}\n")
    return buf.getvalue()


def _parse_hex(hex_color: str) -> Color:
    h = hex_color.lstrip('#')
    return Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _load_rgba(data: bytes) -> np.ndarray:
    return np.array(Image.open(io.BytesIO(data)).convert("RGBA"))


def _silhouette_key(px: np.ndarray, input_bg_rgb: np.ndarray) -> tuple:
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
    alpha      = px[:, :, 3]
    rgb        = px[:, :, :3]
    flat_rgb   = rgb.reshape(-1, 3).astype(np.uint8)
    flat_alpha = alpha.flatten()

    opaque_mask  = flat_alpha >= 255
    non_bg_mask  = opaque_mask & ~np.all(flat_rgb == input_bg_rgb, axis=1)
    sprite_pixels = flat_rgb[non_bg_mask]

    if len(sprite_pixels) == 0:
        return []

    unique, counts = np.unique(sprite_pixels, axis=0, return_counts=True)
    order          = np.argsort(-counts)
    unique_sorted  = unique[order]

    if len(unique_sorted) <= n_colors:
        return [tuple(c) for c in unique_sorted]

    actual_clusters = min(n_colors, len(unique_sorted))
    lab    = rgb_to_oklab(sprite_pixels)
    kmeans = KMeans(n_clusters=actual_clusters, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(lab)
    sizes  = np.bincount(labels, minlength=actual_clusters)
    order  = np.argsort(-sizes)
    centers_rgb = oklab_to_rgb(kmeans.cluster_centers_[order].astype(np.float32))
    return [tuple(int(v) for v in c) for c in centers_rgb]


def _build_aligned_palette(
    per_sprite_colors: list[list[tuple]],
    n_colors: int,
    output_bg: Color,
    shared_threshold: float = DEFAULT_THRESHOLD,
) -> list[dict[tuple, int]]:
    n         = len(per_sprite_colors)
    threshold = max(2, round(shared_threshold * n)) if n > 1 else 1

    color_prevalence: dict[tuple, int] = {}
    for colors in per_sprite_colors:
        for c in set(colors):
            color_prevalence[c] = color_prevalence.get(c, 0) + 1

    majority_colors = [
        c for c, count in color_prevalence.items()
        if count >= threshold
    ]
    majority_colors.sort(key=lambda c: -color_prevalence[c])

    shared_slot_map: dict[tuple, int] = {}
    next_shared_slot = 1
    for color in majority_colors:
        if next_shared_slot > n_colors:
            break
        shared_slot_map[color] = next_shared_slot
        next_shared_slot += 1

    n_shared = next_shared_slot - 1

    per_sprite_slot_maps: list[dict[tuple, int]] = []

    for sprite_colors in per_sprite_colors:
        slot_map   = dict(shared_slot_map)
        local_slot = n_shared + 1

        for color in sprite_colors:
            if color in slot_map:
                continue
            if local_slot > n_colors:
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

    return per_sprite_slot_maps, sorted(shared_slot_map.values())


def _render_sprite(
    px: np.ndarray,
    input_bg_rgb: np.ndarray,
    slot_map: dict[tuple, int],
    palette_colors: list[Color],
    output_bg: Color,
) -> Image.Image:
    h, w       = px.shape[:2]
    alpha      = px[:, :, 3]
    rgb        = px[:, :, :3]
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
            best_slot = 1
            best_dist = float('inf')
            r, g, b   = flat_rgb[i]
            for mapped_color, slot in slot_map.items():
                mr, mg, mb = mapped_color
                dist = (r - mr) ** 2 + (g - mg) ** 2 + (b - mb) ** 2
                if dist < best_dist:
                    best_dist = dist
                    best_slot = slot
            index_flat[i] = best_slot

    index_map = index_flat.reshape(h, w)
    out = Image.new("P", (w, h))
    pal_data  = list(output_bg.to_tuple())
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
    shared_threshold: float = DEFAULT_THRESHOLD,
) -> dict:
    h, w = sprites[0]["px"].shape[:2]

    per_sprite_colors: list[list[tuple]] = []
    per_sprite_bg: list[np.ndarray]      = []

    for sprite in sprites:
        bg_rgb = np.array(_parse_hex(sprite["input_bg"]).to_tuple(), dtype=np.uint8)
        per_sprite_bg.append(bg_rgb)
        colors = _extract_sprite_colors(sprite["px"], bg_rgb, n_colors)
        per_sprite_colors.append(colors)

    per_sprite_slot_maps, shared_indices = _build_aligned_palette(
        per_sprite_colors, n_colors, output_bg, shared_threshold
    )
    shared_indices_set = {0} | set(shared_indices)

    all_colors: set[tuple] = set()
    for colors in per_sprite_colors:
        all_colors.update(colors)
    n_unique = len(all_colors)
    exact    = all(len(c) <= n_colors for c in per_sprite_colors)

    results = []
    for sprite, bg_rgb, slot_map, sprite_colors in zip(
        sprites, per_sprite_bg, per_sprite_slot_maps, per_sprite_colors
    ):
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
                sprite_palette.append(output_bg)

        out_img = _render_sprite(sprite["px"], bg_rgb, slot_map, sprite_palette, output_bg)

        results.append({
            "name":        sprite["name"],
            "colors":      [c.to_hex() for c in sprite_palette],
            "pal_content": _make_pal_content(sprite_palette),  # trims trailing bg dupes
            "preview":     pil_to_b64(out_img.convert("RGBA")),
            "exact":       len(sprite_colors) <= n_colors,
        })

    results.sort(key=lambda r: r["name"].lower())

    representative_colors = results[0]["colors"] if results else []
    shared_slot_colors = [
        {"hex": representative_colors[i] if i < len(representative_colors) else "#000000",
         "shared": i in shared_indices_set}
        for i in range(n_colors + 1)
    ]

    return {
        "reference":     sprites[0]["name"],
        "dimensions":    f"{w}\u00d7{h}",
        "n_unique":      n_unique,
        "exact":         exact,
        "results":       results,
        "shared_slots":  shared_slot_colors,
        "n_shared":      len(shared_indices),
    }


def _build_groups(
    sprites: list[dict],
    n_colors: int,
    output_bg: Color,
    shared_threshold: float = DEFAULT_THRESHOLD,
    group_assignments: dict[str, str] | None = None,
) -> list[dict]:
    groups: dict[str, list[dict]] = {}

    for sprite in sprites:
        bg_rgb = np.array(_parse_hex(sprite["input_bg"]).to_tuple(), dtype=np.uint8)

        if group_assignments and sprite["name"] in group_assignments:
            gid = f"manual_{group_assignments[sprite['name']]}"
        else:
            sil_key = _silhouette_key(sprite["px"], bg_rgb)
            gid     = f"sil_{hash(sil_key) & 0xFFFFFFFF}"

        groups.setdefault(gid, []).append(sprite)

    unsorted = []
    for gid, group_sprites in groups.items():
        group_data = _extract_group(group_sprites, n_colors, output_bg, shared_threshold)
        unsorted.append(group_data)

    unsorted.sort(key=lambda g: -len(g["results"]))

    result_groups = []
    for i, group_data in enumerate(unsorted):
        group_data["group_id"] = f"shape_{i + 1}"
        result_groups.append(group_data)

    return result_groups


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/extract")
async def extract_item_palettes(
    files: list[UploadFile] = File(...),
    n_colors: int           = Form(default=15),
    input_bg_colors: str    = Form(default="[]"),
    output_bg_color: str    = Form(default=DEFAULT_BG),
    shared_threshold: float = Form(default=DEFAULT_THRESHOLD),
    group_assignments: str  = Form(default="{}"),
):
    if not files:
        raise HTTPException(400, "At least one file required")

    shared_threshold = max(0.0, min(1.0, shared_threshold))

    try:
        input_bgs        = json.loads(input_bg_colors)
        group_assign_map = json.loads(group_assignments)
    except Exception:
        input_bgs        = []
        group_assign_map = {}

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
        groups = _build_groups(sprites, n_colors, output_bg, shared_threshold, group_assign_map)
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {"groups": groups}


@router.post("/download-all")
async def download_all_item_palettes(
    files: list[UploadFile] = File(...),
    n_colors: int           = Form(default=15),
    input_bg_colors: str    = Form(default="[]"),
    output_bg_color: str    = Form(default=DEFAULT_BG),
    group_names: str        = Form(default="{}"),
    shared_threshold: float = Form(default=DEFAULT_THRESHOLD),
    group_assignments: str  = Form(default="{}"),
):
    shared_threshold = max(0.0, min(1.0, shared_threshold))

    try:
        input_bgs        = json.loads(input_bg_colors)
        gnames           = json.loads(group_names)
        group_assign_map = json.loads(group_assignments)
    except Exception:
        input_bgs        = []
        gnames           = {}
        group_assign_map = {}

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
        groups = _build_groups(sprites, n_colors, output_bg, shared_threshold, group_assign_map)
    except ValueError as e:
        raise HTTPException(400, str(e))

    zip_buf  = io.BytesIO()
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


# ---------------------------------------------------------------------------
# Variant extraction
# ---------------------------------------------------------------------------

def _extract_variants(
    sprites: list[dict],
    n_colors: int,
    output_bg: Color,
) -> list[dict]:
    if not sprites:
        return []

    ref = sprites[0]
    ref_bg_rgb = np.array(_parse_hex(ref["input_bg"]).to_tuple(), dtype=np.uint8)

    ref_colors = _extract_sprite_colors(ref["px"], ref_bg_rgb, n_colors)
    ref_slot_map: dict[tuple, int] = {c: i + 1 for i, c in enumerate(ref_colors)}

    ref_palette = [output_bg] + [Color(c[0], c[1], c[2]) for c in ref_colors]
    while len(ref_palette) < n_colors + 1:
        ref_palette.append(output_bg)

    h, w = ref["px"].shape[:2]
    ref_rgb   = ref["px"][:, :, :3]
    ref_alpha = ref["px"][:, :, 3]

    ref_slot_image = np.zeros((h, w), dtype=np.int32)
    for row in range(h):
        for col in range(w):
            a = ref_alpha[row, col]
            px_rgb = tuple(ref_rgb[row, col].tolist())
            if a < 255 or px_rgb == tuple(ref_bg_rgb.tolist()):
                ref_slot_image[row, col] = 0
            elif px_rgb in ref_slot_map:
                ref_slot_image[row, col] = ref_slot_map[px_rgb]
            else:
                best_slot, best_dist = 1, float('inf')
                r, g, b = px_rgb
                for rc, slot in ref_slot_map.items():
                    d = (r-rc[0])**2 + (g-rc[1])**2 + (b-rc[2])**2
                    if d < best_dist:
                        best_dist, best_slot = d, slot
                ref_slot_image[row, col] = best_slot

    results = []

    for sprite in sprites:
        sp_bg_rgb = np.array(_parse_hex(sprite["input_bg"]).to_tuple(), dtype=np.uint8)
        sp_rgb    = sprite["px"][:, :, :3]
        sp_alpha  = sprite["px"][:, :, 3]

        slot_colors: dict[int, dict[tuple, int]] = {i: {} for i in range(1, len(ref_colors) + 1)}

        for row in range(h):
            for col in range(w):
                slot = ref_slot_image[row, col]
                if slot == 0:
                    continue
                a = sp_alpha[row, col]
                if a < 255:
                    continue
                c = tuple(sp_rgb[row, col].tolist())
                if c == tuple(sp_bg_rgb.tolist()):
                    continue
                slot_colors[slot][c] = slot_colors[slot].get(c, 0) + 1

        variant_palette: list[Color] = [output_bg]
        for slot_i in range(1, len(ref_colors) + 1):
            freq = slot_colors[slot_i]
            if freq:
                best_color = max(freq, key=freq.get)
                variant_palette.append(Color(best_color[0], best_color[1], best_color[2]))
            else:
                rc = ref_colors[slot_i - 1]
                variant_palette.append(Color(rc[0], rc[1], rc[2]))

        while len(variant_palette) < n_colors + 1:
            variant_palette.append(output_bg)

        out_img = Image.new("P", (w, h))
        pal_data = list(output_bg.to_tuple())
        for c in variant_palette[1:]:
            pal_data += list(c.to_tuple())
        pal_data += [0] * (768 - len(pal_data))
        out_img.putpalette(pal_data)
        out_img.putdata(ref_slot_image.flatten().tolist())

        results.append({
            "name":        sprite["name"],
            "colors":      [c.to_hex() for c in variant_palette],
            "pal_content": _make_pal_content(variant_palette),  # trims trailing bg dupes
            "preview":     pil_to_b64(out_img.convert("RGBA")),
        })

    results.sort(key=lambda r: r["name"].lower())
    return results


@router.post("/extract-variants")
async def extract_variants(
    files: list[UploadFile] = File(...),
    n_colors: int           = Form(default=15),
    input_bg_colors: str    = Form(default="[]"),
    output_bg_color: str    = Form(default=DEFAULT_BG),
    reference_index: int    = Form(default=0),
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

    h0, w0 = sprites[0]["px"].shape[:2]
    for s in sprites[1:]:
        h, w = s["px"].shape[:2]
        if h != h0 or w != w0:
            raise HTTPException(
                400,
                f"All sprites must have the same dimensions. "
                f"'{sprites[0]['name']}' is {w0}×{h0} but '{s['name']}' is {w}×{h}."
            )

    ref_idx = max(0, min(reference_index, len(sprites) - 1))
    if ref_idx != 0:
        sprites.insert(0, sprites.pop(ref_idx))

    try:
        results = _extract_variants(sprites, n_colors, output_bg)
    except Exception as e:
        raise HTTPException(400, str(e))

    return {
        "reference": sprites[0]["name"],
        "results":   results,
    }


@router.post("/extract-variants/download")
async def download_variants(
    files: list[UploadFile] = File(...),
    n_colors: int           = Form(default=15),
    input_bg_colors: str    = Form(default="[]"),
    output_bg_color: str    = Form(default=DEFAULT_BG),
    reference_index: int    = Form(default=0),
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

    h0, w0 = sprites[0]["px"].shape[:2]
    for s in sprites[1:]:
        h, w = s["px"].shape[:2]
        if h != h0 or w != w0:
            raise HTTPException(400, f"Dimension mismatch: '{s['name']}' is {w}×{h}, expected {w0}×{h0}.")

    ref_idx = max(0, min(reference_index, len(sprites) - 1))
    if ref_idx != 0:
        sprites.insert(0, sprites.pop(ref_idx))

    results = _extract_variants(sprites, n_colors, output_bg)

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in results:
            zf.writestr(f"{r['name']}.pal", r["pal_content"])
    zip_buf.seek(0)

    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="variant_palettes.zip"'},
    )