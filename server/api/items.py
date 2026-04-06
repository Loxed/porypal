"""
server/api/items.py

Routes: /api/items
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

router = APIRouter(prefix="/api/items", tags=["items"])

DEFAULT_BG        = "#73C5A4"
DEFAULT_THRESHOLD = 0.6


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_hex(hex_color: str) -> Color:
    h = hex_color.lstrip('#')
    return Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _load_rgba(data: bytes) -> np.ndarray:
    return np.array(Image.open(io.BytesIO(data)).convert("RGBA"))


def _extract_palette_for_sprite(image_data: bytes, filename: str, n_colors: int, bg_color: str) -> Palette:
    """
    Extract a clean palette using the shared extractor (same as Extract tab).
    Writes to a temp file, calls state.extractor.extract(), cleans up.
    Guarantees no duplicates, no padding — identical behaviour to the Extract tab.
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


def _silhouette_key(px: np.ndarray, input_bg_rgb: np.ndarray) -> tuple:
    alpha  = px[:, :, 3]
    rgb    = px[:, :, :3]
    opaque = alpha >= 255
    not_bg = ~np.all(rgb == input_bg_rgb, axis=2)
    mask   = (opaque & not_bg).flatten()
    return (px.shape[0], px.shape[1], mask.tobytes())


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
            best_slot, best_dist = 1, float('inf')
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
    out.info["transparency"] = 0
    return out


# ---------------------------------------------------------------------------
# Group extraction
# ---------------------------------------------------------------------------

def _build_aligned_palette(
    per_sprite_palettes: list[Palette],
    n_colors: int,
    output_bg: Color,
    shared_threshold: float,
) -> tuple[list[dict[tuple, int]], list[int]]:
    """
    Given a clean Palette per sprite (from state.extractor), build a shared
    slot assignment so all sprites in the group use consistent slot indices.
    """
    n         = len(per_sprite_palettes)
    threshold = max(2, round(shared_threshold * n)) if n > 1 else 1

    color_prevalence: dict[tuple, int] = {}
    for pal in per_sprite_palettes:
        for c in set(c.to_tuple() for c in pal.opaque_colors):
            color_prevalence[c] = color_prevalence.get(c, 0) + 1

    majority_colors = [c for c, count in color_prevalence.items() if count >= threshold]
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

    for pal in per_sprite_palettes:
        slot_map   = dict(shared_slot_map)
        local_slot = n_shared + 1

        for c in pal.opaque_colors:
            color = c.to_tuple()
            if color in slot_map:
                continue
            if local_slot > n_colors:
                assigned = list(slot_map.items())
                if assigned:
                    nearest = min(assigned, key=lambda x: sum((a - b) ** 2 for a, b in zip(color, x[0])))
                    slot_map[color] = nearest[1]
                else:
                    slot_map[color] = 1
            else:
                slot_map[color] = local_slot
                local_slot += 1

        per_sprite_slot_maps.append(slot_map)

    return per_sprite_slot_maps, sorted(shared_slot_map.values())


def _extract_group(
    sprites: list[dict],
    n_colors: int,
    output_bg: Color,
    shared_threshold: float = DEFAULT_THRESHOLD,
) -> dict:
    h, w = sprites[0]["px"].shape[:2]

    # Use state.extractor for each sprite — guarantees clean palettes
    per_sprite_palettes: list[Palette] = []
    per_sprite_bg: list[np.ndarray]    = []

    for sprite in sprites:
        bg_color = sprite["input_bg"]
        bg_rgb   = np.array(_parse_hex(bg_color).to_tuple(), dtype=np.uint8)
        per_sprite_bg.append(bg_rgb)
        pal = _extract_palette_for_sprite(sprite["raw"], sprite["name"] + ".png", n_colors, bg_color)
        per_sprite_palettes.append(pal)

    per_sprite_slot_maps, shared_indices = _build_aligned_palette(
        per_sprite_palettes, n_colors, output_bg, shared_threshold
    )
    shared_indices_set = {0} | set(shared_indices)

    all_colors: set[tuple] = set()
    for pal in per_sprite_palettes:
        all_colors.update(c.to_tuple() for c in pal.opaque_colors)
    n_unique = len(all_colors)
    exact    = all(len(pal.opaque_colors) <= n_colors for pal in per_sprite_palettes)

    results = []
    for sprite, bg_rgb, slot_map, pal in zip(
        sprites, per_sprite_bg, per_sprite_slot_maps, per_sprite_palettes
    ):
        slot_to_color: dict[int, tuple] = {}
        for color, slot in slot_map.items():
            if slot not in slot_to_color:
                slot_to_color[slot] = color

        # Build a clean palette with only the slots actually used
        sprite_palette: list[Color] = [output_bg]
        for slot_i in range(1, n_colors + 1):
            if slot_i in slot_to_color:
                r, g, b = slot_to_color[slot_i]
                sprite_palette.append(Color(r, g, b))
            else:
                sprite_palette.append(output_bg)

        out_img    = _render_sprite(sprite["px"], bg_rgb, slot_map, sprite_palette, output_bg)
        pal_object = Palette(name=sprite["name"], colors=sprite_palette)

        results.append({
            "name":        sprite["name"],
            "colors":      [c.to_hex() for c in sprite_palette],
            "pal_content": make_pal_content(pal_object),
            "preview":     pil_to_b64(out_img.convert("RGBA")),
            "png_bytes":   save_png(out_img),
            "exact":       len(pal.opaque_colors) <= n_colors,
        })

    results.sort(key=lambda r: r["name"].lower())

    representative_colors = results[0]["colors"] if results else []
    shared_slot_colors = [
        {
            "hex":    representative_colors[i] if i < len(representative_colors) else "#000000",
            "shared": i in shared_indices_set,
        }
        for i in range(n_colors + 1)
    ]

    return {
        "reference":    sprites[0]["name"],
        "dimensions":   f"{w}\u00d7{h}",
        "n_unique":     n_unique,
        "exact":        exact,
        "results":      results,
        "shared_slots": shared_slot_colors,
        "n_shared":     len(shared_indices),
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
# Variant extraction
# ---------------------------------------------------------------------------

def _extract_variants(
    sprites: list[dict],
    n_colors: int,
    output_bg: Color,
) -> list[dict]:
    """
    Extract index-compatible palettes for N recolored variants of the same sprite.

    The first sprite in the list is the reference. Its palette (extracted via
    state.extractor) defines the slot order. Every other sprite's colors are
    then mapped to those same slots by finding which slot each pixel belongs to
    in the reference image, then sampling the variant's color at that position.
    """
    if not sprites:
        return []

    ref    = sprites[0]
    ref_bg = ref["input_bg"]

    # Use state.extractor for the reference — clean, no dupes
    ref_pal    = _extract_palette_for_sprite(ref["raw"], ref["name"] + ".png", n_colors, ref_bg)
    ref_colors = ref_pal.opaque_colors   # list[Color], excludes slot 0

    # Build slot map: color_tuple → slot index (1-based)
    ref_slot_map: dict[tuple, int] = {c.to_tuple(): i + 1 for i, c in enumerate(ref_colors)}
    ref_bg_rgb = np.array(_parse_hex(ref_bg).to_tuple(), dtype=np.uint8)

    h, w      = ref["px"].shape[:2]
    ref_rgb   = ref["px"][:, :, :3]
    ref_alpha = ref["px"][:, :, 3]

    # Build per-pixel slot index image from reference
    ref_slot_image = np.zeros((h, w), dtype=np.int32)
    for row in range(h):
        for col in range(w):
            a      = ref_alpha[row, col]
            px_rgb = tuple(ref_rgb[row, col].tolist())
            if a < 255 or np.all(ref_rgb[row, col] == ref_bg_rgb):
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

        # For each slot, collect all variant pixel colors at that position and take majority
        slot_colors: dict[int, dict[tuple, int]] = {i: {} for i in range(1, len(ref_colors) + 1)}

        for row in range(h):
            for col in range(w):
                slot = ref_slot_image[row, col]
                if slot == 0:
                    continue
                if sp_alpha[row, col] < 255:
                    continue
                c = tuple(sp_rgb[row, col].tolist())
                if np.all(sp_rgb[row, col] == sp_bg_rgb):
                    continue
                slot_colors[slot][c] = slot_colors[slot].get(c, 0) + 1

        # Build variant palette using the ref slot structure
        variant_colors: list[Color] = [output_bg]
        for slot_i in range(1, len(ref_colors) + 1):
            freq = slot_colors[slot_i]
            if freq:
                best_color = max(freq, key=freq.get)
                variant_colors.append(Color(best_color[0], best_color[1], best_color[2]))
            else:
                # No pixels mapped here — fall back to the ref color for this slot
                variant_colors.append(ref_colors[slot_i - 1])

        # Render using the reference slot image (same pixel→slot mapping for all variants)
        out_img = Image.new("P", (w, h))
        pal_data = list(output_bg.to_tuple())
        for c in variant_colors[1:]:
            pal_data += list(c.to_tuple())
        pal_data += [0] * (768 - len(pal_data))
        out_img.putpalette(pal_data)
        out_img.putdata(ref_slot_image.flatten().tolist())
        out_img.info["transparency"] = 0

        pal_object = Palette(name=sprite["name"], colors=variant_colors)

        results.append({
            "name":        sprite["name"],
            "colors":      [c.to_hex() for c in variant_colors],
            "pal_content": make_pal_content(pal_object),
            "preview":     pil_to_b64(out_img.convert("RGBA")),
            "png_bytes":   save_png(out_img),
        })

    results.sort(key=lambda r: r["name"].lower())
    return results


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def _load_sprites(files_data: list[tuple[str, bytes]], input_bgs: list[str]) -> list[dict]:
    """Parse uploaded files into sprite dicts with px array + raw bytes."""
    sprites = []
    for i, (filename, data) in enumerate(files_data):
        sprites.append({
            "name":     Path(filename).stem,
            "raw":      data,                          # kept for state.extractor.extract()
            "px":       _load_rgba(data),
            "input_bg": input_bgs[i] if i < len(input_bgs) else DEFAULT_BG,
        })
    return sprites


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

    output_bg   = _parse_hex(output_bg_color)
    files_data  = [(f.filename, await f.read()) for f in files]
    sprites     = _load_sprites(files_data, input_bgs)

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

    output_bg  = _parse_hex(output_bg_color)
    files_data = [(f.filename, await f.read()) for f in files]
    sprites    = _load_sprites(files_data, input_bgs)

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
                group_manifest["palettes"].append({"sprite": r["name"], "palette": pal_path})

            manifest["groups"].append(group_manifest)

        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

    zip_buf.seek(0)
    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="item_palettes.zip"'},
    )


@router.post("/download-group")
async def download_group_palettes(
    files: list[UploadFile] = File(...),
    n_colors: int           = Form(default=15),
    input_bg_colors: str    = Form(default="[]"),
    output_bg_color: str    = Form(default=DEFAULT_BG),
    shared_threshold: float = Form(default=DEFAULT_THRESHOLD),
    group_assignments: str  = Form(default="{}"),
    group_name: str         = Form(default="group"),
):
    shared_threshold = max(0.0, min(1.0, shared_threshold))

    try:
        input_bgs        = json.loads(input_bg_colors)
        group_assign_map = json.loads(group_assignments)
    except Exception:
        input_bgs        = []
        group_assign_map = {}

    output_bg  = _parse_hex(output_bg_color)
    files_data = [(f.filename, await f.read()) for f in files]
    sprites    = _load_sprites(files_data, input_bgs)

    if not sprites:
        raise HTTPException(400, "No sprites provided")

    try:
        group_data = _extract_group(sprites, n_colors, output_bg, shared_threshold)
    except ValueError as e:
        raise HTTPException(400, str(e))

    label = group_name or "group"

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in group_data["results"]:
            zf.writestr(f"palettes/{r['name']}.pal", r["pal_content"])
            zf.writestr(f"sprites/{r['name']}.png",  r["png_bytes"])
        manifest = {
            "group":     label,
            "reference": group_data["reference"],
            "files": [
                {
                    "name":    r["name"],
                    "palette": f"palettes/{r['name']}.pal",
                    "sprite":  f"sprites/{r['name']}.png",
                }
                for r in group_data["results"]
            ],
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

    zip_buf.seek(0)
    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{label}.zip"'},
    )


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

    output_bg  = _parse_hex(output_bg_color)
    files_data = [(f.filename, await f.read()) for f in files]
    sprites    = _load_sprites(files_data, input_bgs)

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

    return {"reference": sprites[0]["name"], "results": results}


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

    output_bg  = _parse_hex(output_bg_color)
    files_data = [(f.filename, await f.read()) for f in files]
    sprites    = _load_sprites(files_data, input_bgs)

    h0, w0 = sprites[0]["px"].shape[:2]
    for s in sprites[1:]:
        h, w = s["px"].shape[:2]
        if h != h0 or w != w0:
            raise HTTPException(400, f"Dimension mismatch: '{s['name']}' is {w}×{h}, expected {w0}×{h0}.")

    ref_idx = max(0, min(reference_index, len(sprites) - 1))
    if ref_idx != 0:
        sprites.insert(0, sprites.pop(ref_idx))

    results        = _extract_variants(sprites, n_colors, output_bg)
    reference_name = sprites[0]["name"]

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in results:
            zf.writestr(f"palettes/{r['name']}.pal", r["pal_content"])
            zf.writestr(f"sprites/{r['name']}.png",  r["png_bytes"])
        manifest = {
            "reference": reference_name,
            "files": [
                {
                    "name":    r["name"],
                    "palette": f"palettes/{r['name']}.pal",
                    "sprite":  f"sprites/{r['name']}.png",
                }
                for r in results
            ],
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

    zip_buf.seek(0)
    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="variant_palettes.zip"'},
    )


@router.post("/apply-variants/download")
async def download_apply_variants(
    sprite_file: UploadFile = File(...),
    ref_pal:     str        = Form(...),
    pal_names:   list[str]  = Form(...),
    pal_colors:  list[str]  = Form(...),
):
    """
    Apply N palettes to one sprite using the ref palette for slot mapping.
    Returns a zip with sprites/ + palettes/ + manifest.json.
    """
    if len(pal_names) != len(pal_colors):
        raise HTTPException(400, "pal_names and pal_colors must have the same length")

    try:
        ref_colors = [_parse_hex(h) for h in json.loads(ref_pal)]
    except Exception:
        raise HTTPException(400, "Invalid ref_pal JSON")

    palettes = []
    for name, colors_json in zip(pal_names, pal_colors):
        try:
            colors = [_parse_hex(h) for h in json.loads(colors_json)]
            palettes.append((name, colors))
        except Exception:
            raise HTTPException(400, f"Invalid palette JSON for {name}")

    sprite_data   = await sprite_file.read()
    sprite_px     = _load_rgba(sprite_data)
    stem          = Path(sprite_file.filename).stem
    output_bg     = ref_colors[0]
    output_bg_rgb = np.array(output_bg.to_tuple(), dtype=np.uint8)

    slot_map: dict[tuple, int] = {
        c.to_tuple(): i + 1 for i, c in enumerate(ref_colors[1:], start=0)
    }

    zip_buf        = io.BytesIO()
    manifest_files = []

    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for pal_name, pal_colors_list in palettes:
            # Align variant palette length to ref
            variant_palette = list(pal_colors_list)
            while len(variant_palette) < len(ref_colors):
                variant_palette.append(output_bg)
            variant_palette = variant_palette[:len(ref_colors)]

            out_img   = _render_sprite(sprite_px, output_bg_rgb, slot_map, variant_palette, output_bg)
            safe_name = pal_name.replace('.pal', '')
            pal_obj   = Palette(name=safe_name, colors=variant_palette)

            zf.writestr(f"sprites/{safe_name}.png",  save_png(out_img))
            zf.writestr(f"palettes/{safe_name}.pal", make_pal_content(pal_obj))
            manifest_files.append({
                "name":    safe_name,
                "sprite":  f"sprites/{safe_name}.png",
                "palette": f"palettes/{safe_name}.pal",
            })

        manifest = {
            "sprite":            sprite_file.filename,
            "reference_palette": pal_names[0] if pal_names else "",
            "files":             manifest_files,
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

    zip_buf.seek(0)
    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{stem}_variants.zip"'},
    )
