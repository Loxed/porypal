"""
server/api/items.py

Routes: /api/items

Silhouette-based grouping: sprites with identical opaque/transparent pixel masks
are grouped together by default. The user can override group membership by sending
a group_assignments JSON map (sprite_name -> group_id) from the frontend.

Within each group, palettes are index-aligned on shared colors (above the
configurable shared_threshold) but each sprite keeps its own unique colors
without cross-sprite clustering.

Strategy:
  1. Each sprite gets its own palette extracted independently (no cross-sprite k-means)
  2. Colors present in >= shared_threshold fraction of the group get fixed shared slots
  3. Each sprite fills remaining slots independently with its own colors
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
DEFAULT_THRESHOLD = 0.6


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

    # K-means only on this single sprite
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
    """
    Build per-sprite slot maps with two-phase slot assignment.

    shared_threshold: fraction of sprites that must contain a color for it to
    earn a fixed shared slot.
      0.0 → any color present in ≥1 sprite gets a shared slot
      0.5 → strict majority
      1.0 → only colors in every single sprite

    Phase 1 — Shared slots (reserved at the front):
      Colors present in >= shared_threshold fraction of sprites get fixed slot
      indices, sorted by prevalence descending. Same index in every palette.

    Phase 2 — Per-sprite local slots:
      Each sprite independently fills remaining slots with its own unique
      colors sorted by pixel frequency. No cross-sprite influence.

    Returns: (per_sprite_slot_maps, shared_indices)
      per_sprite_slot_maps: list of dicts mapping rgb_tuple -> 1-based slot index
      shared_indices: sorted list of 1-based slot indices that are shared (Phase 1)
    """
    n         = len(per_sprite_colors)
    threshold = max(2, round(shared_threshold * n)) if n > 1 else 1

    # Count how many sprites contain each color
    color_prevalence: dict[tuple, int] = {}
    for colors in per_sprite_colors:
        for c in set(colors):
            color_prevalence[c] = color_prevalence.get(c, 0) + 1

    # Phase 1: colors meeting the threshold, sorted by prevalence desc
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

    # Phase 2: each sprite fills remaining slots independently
    per_sprite_slot_maps: list[dict[tuple, int]] = []

    for sprite_colors in per_sprite_colors:
        slot_map   = dict(shared_slot_map)
        local_slot = n_shared + 1

        for color in sprite_colors:
            if color in slot_map:
                continue
            if local_slot > n_colors:
                # Overflow — map to nearest already-assigned color
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
    """Render a sprite to a PIL indexed image using the given slot map."""
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
    """
    Process a silhouette group:
    1. Extract colors independently per sprite (per-sprite k-means only if needed)
    2. Align shared colors to the same slot indices using shared_threshold
    3. Render each sprite with its own aligned palette
    """
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
    # Slot 0 (transparent) is always shared
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
            "pal_content": _make_pal_content(sprite_palette),
            "preview":     pil_to_b64(out_img.convert("RGBA")),
            "exact":       len(sprite_colors) <= n_colors,
        })

    results.sort(key=lambda r: r["name"].lower())

    # Build the shared palette strip: for each of the 16 slots, provide the hex color
    # from the first result (shared slots are identical across sprites; local slots vary).
    # Also report which slot indices are shared vs local.
    representative_colors = results[0]["colors"] if results else []
    shared_slot_colors = [
        {"hex": representative_colors[i] if i < len(representative_colors) else "#000000",
         "shared": i in shared_indices_set}
        for i in range(n_colors + 1)  # slot 0 + n_colors slots
    ]

    return {
        "reference":     sprites[0]["name"],
        "dimensions":    f"{w}\u00d7{h}",
        "n_unique":      n_unique,
        "exact":         exact,
        "results":       results,
        "shared_slots":  shared_slot_colors,   # [{hex, shared}, ...] len = n_colors+1
        "n_shared":      len(shared_indices),  # excludes slot 0
    }


def _build_groups(
    sprites: list[dict],
    n_colors: int,
    output_bg: Color,
    shared_threshold: float = DEFAULT_THRESHOLD,
    group_assignments: dict[str, str] | None = None,
) -> list[dict]:
    """
    Group sprites and extract palettes per group.

    group_assignments: optional dict mapping sprite name -> group_id.
      When provided, overrides the silhouette-based auto-grouping for those sprites.
      Sprites not mentioned fall back to silhouette grouping.
      This lets the user manually move outliers (ultraball etc.) into an existing group.
    """
    groups: dict[str, list[dict]] = {}

    for sprite in sprites:
        bg_rgb = np.array(_parse_hex(sprite["input_bg"]).to_tuple(), dtype=np.uint8)

        if group_assignments and sprite["name"] in group_assignments:
            # User-assigned group id (string key)
            gid = f"manual_{group_assignments[sprite['name']]}"
        else:
            # Auto-group by silhouette (bytes key → stable string)
            sil_key = _silhouette_key(sprite["px"], bg_rgb)
            gid     = f"sil_{hash(sil_key) & 0xFFFFFFFF}"

        groups.setdefault(gid, []).append(sprite)

    unsorted = []
    for gid, group_sprites in groups.items():
        group_data = _extract_group(group_sprites, n_colors, output_bg, shared_threshold)
        unsorted.append(group_data)

    # Sort groups: most sprites first
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
    group_assignments: str  = Form(default="{}"),  # JSON: { sprite_name: group_id }
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
# Variant extraction — N sprites share the same pixel layout, different hues
# ---------------------------------------------------------------------------

def _extract_variants(
    sprites: list[dict],   # [{name, px, input_bg}]
    n_colors: int,
    output_bg: Color,
) -> list[dict]:
    """
    Given N sprites that are recolor variants of the same base sprite:
    1. Extract the reference palette from sprite[0] (k-means if needed)
    2. For every other sprite, build a matched palette slot-by-slot:
       for each reference color, find what color occupies those same pixels
       in the variant → that becomes the variant's color at that slot.
    3. Render each sprite with its matched palette.

    Returns a list of results (one per sprite) each with:
      name, colors, pal_content, preview, slot_index (1-based slot in reference)
    """
    if not sprites:
        return []

    ref = sprites[0]
    ref_bg_rgb = np.array(_parse_hex(ref["input_bg"]).to_tuple(), dtype=np.uint8)

    # ── Step 1: extract reference palette ──────────────────────────────────
    ref_colors = _extract_sprite_colors(ref["px"], ref_bg_rgb, n_colors)
    # ref_colors is sorted by pixel frequency, index 0 = most frequent

    # Build slot map for reference: color_tuple -> 1-based slot
    ref_slot_map: dict[tuple, int] = {c: i + 1 for i, c in enumerate(ref_colors)}

    # Full reference palette (slot 0 = output_bg)
    ref_palette = [output_bg] + [Color(c[0], c[1], c[2]) for c in ref_colors]
    # Pad to 16 slots
    while len(ref_palette) < n_colors + 1:
        ref_palette.append(output_bg)

    # ── Step 2: build pixel→ref_slot map from reference image ──────────────
    h, w = ref["px"].shape[:2]
    ref_rgb   = ref["px"][:, :, :3]
    ref_alpha = ref["px"][:, :, 3]

    # For each pixel, store which slot it belongs to (0 = transparent/bg)
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
                # Nearest ref color (handles k-means reduced refs)
                best_slot, best_dist = 1, float('inf')
                r, g, b = px_rgb
                for rc, slot in ref_slot_map.items():
                    d = (r-rc[0])**2 + (g-rc[1])**2 + (b-rc[2])**2
                    if d < best_dist:
                        best_dist, best_slot = d, slot
                ref_slot_image[row, col] = best_slot

    # ── Step 3: for each variant, find color-per-slot via pixel sampling ───
    results = []

    for sprite in sprites:
        sp_bg_rgb = np.array(_parse_hex(sprite["input_bg"]).to_tuple(), dtype=np.uint8)
        sp_rgb    = sprite["px"][:, :, :3]
        sp_alpha  = sprite["px"][:, :, 3]

        # For each slot (1..n_colors), collect all variant pixel colors at
        # positions where the reference had that slot → take the most common one
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

        # Pick the most frequent color for each slot; fall back to ref color if empty
        variant_palette: list[Color] = [output_bg]
        for slot_i in range(1, len(ref_colors) + 1):
            freq = slot_colors[slot_i]
            if freq:
                best_color = max(freq, key=freq.get)
                variant_palette.append(Color(best_color[0], best_color[1], best_color[2]))
            else:
                # No pixels found for this slot — keep reference color
                rc = ref_colors[slot_i - 1]
                variant_palette.append(Color(rc[0], rc[1], rc[2]))

        # Pad to 16 slots
        while len(variant_palette) < n_colors + 1:
            variant_palette.append(output_bg)

        # Build slot map for rendering this variant
        # Map: variant_color -> slot_i (invert variant_palette)
        # We use ref_slot_image directly — same pixel layout, same slots
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
            "pal_content": _make_pal_content(variant_palette),
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
    """
    Extract index-compatible palettes from N recolor variants of the same sprite.

    All sprites must have the same dimensions. The sprite at reference_index
    establishes the palette slot order; all others are matched to it pixel-by-pixel.

    Returns: { reference, results: [{name, colors, pal_content, preview}] }
    """
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

    # Validate all same dimensions
    h0, w0 = sprites[0]["px"].shape[:2]
    for s in sprites[1:]:
        h, w = s["px"].shape[:2]
        if h != h0 or w != w0:
            raise HTTPException(
                400,
                f"All sprites must have the same dimensions. "
                f"'{sprites[0]['name']}' is {w0}×{h0} but '{s['name']}' is {w}×{h}."
            )

    # Put reference first
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
    """Download all variant palettes as a zip."""
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