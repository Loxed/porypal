"""
server/api/eightbpp.py   — Routes: /api/8bpp

Endpoints
─────────
POST /load          JASC-PAL or 8bpp indexed PNG → palette banks
POST /shrink        8bpp indexed PNG → greedy-merge + optional k-medoids → new PNG + palette
POST /create        Any image → k-medoids 256-color palette → quantized PNG + palette
POST /export-bank   One 16-color bank → JASC-PAL download
"""

from __future__ import annotations
import base64
import io
import json as _json
from pathlib import Path

import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from PIL import Image

router = APIRouter(prefix="/api/8bpp", tags=["8bpp"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Colour helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _srgb_to_linear(c: np.ndarray) -> np.ndarray:
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def _linear_to_srgb(c: np.ndarray) -> np.ndarray:
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.maximum(c, 0) ** (1 / 2.4) - 0.055)

def _rgb_to_oklab(px: np.ndarray) -> np.ndarray:
    """(N,3) uint8  →  (N,3) float32 Oklab"""
    rgb = px.astype(np.float32) / 255.0
    lin = _srgb_to_linear(rgb)
    l = 0.4122214708*lin[:,0] + 0.5363325363*lin[:,1] + 0.0514459929*lin[:,2]
    m = 0.2119034982*lin[:,0] + 0.6806995451*lin[:,1] + 0.1073969566*lin[:,2]
    s = 0.0883024619*lin[:,0] + 0.2817188376*lin[:,1] + 0.6299787005*lin[:,2]
    l_ = np.cbrt(np.maximum(l, 0))
    m_ = np.cbrt(np.maximum(m, 0))
    s_ = np.cbrt(np.maximum(s, 0))
    L  =  0.2104542553*l_ + 0.7936177850*m_ - 0.0040720468*s_
    a  =  1.9779984951*l_ - 2.4285922050*m_ + 0.4505937099*s_
    b  =  0.0259040371*l_ + 0.7827717662*m_ - 0.8086757660*s_
    return np.stack([L, a, b], axis=1).astype(np.float32)

def _oklab_to_rgb(lab: np.ndarray) -> np.ndarray:
    """(N,3) float32 Oklab  →  (N,3) uint8"""
    L, a, b = lab[:,0], lab[:,1], lab[:,2]
    l_ = L + 0.3963377774*a + 0.2158037573*b
    m_ = L - 0.1055613458*a - 0.0638541728*b
    s_ = L - 0.0894841775*a - 1.2914855480*b
    l = l_**3; m = m_**3; s = s_**3
    r  =  4.0767416621*l - 3.3077115913*m + 0.2309699292*s
    g  = -1.2684380046*l + 2.6097574011*m - 0.3413193965*s
    b_ = -0.0041960863*l - 0.7034186147*m + 1.7076147010*s
    srgb = _linear_to_srgb(np.stack([r, g, b_], axis=1))
    return (np.clip(srgb, 0, 1) * 255 + 0.5).astype(np.uint8)

def _sq_dists(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Squared Euclidean distances: (N,3) vs (M,3) → (N,M)"""
    # ||a-b||² = ||a||² + ||b||² - 2 a·b
    return (
        (a * a).sum(1, keepdims=True)
        + (b * b).sum(1, keepdims=True).T
        - 2 * (a @ b.T)
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Palette / bank helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _parse_jasc_pal(text: str) -> list[tuple[int,int,int]]:
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() not in ("JASC-PAL", "JASC-PAL\r"):
        raise ValueError("Not a valid JASC-PAL file")
    count  = int(lines[2].strip())
    colors = []
    for line in lines[3:]:
        parts = line.strip().split()
        if len(parts) >= 3:
            colors.append((int(parts[0]), int(parts[1]), int(parts[2])))
        if len(colors) >= count:
            break
    return colors

def _colors_to_banks(colors: list[tuple[int,int,int]]) -> list[dict]:
    padded = (list(colors) + [(0,0,0)] * 256)[:256]
    banks  = []
    for bi in range(16):
        bc = []
        for si in range(16):
            idx = bi*16 + si
            r,g,b = padded[idx]
            bc.append({"index": idx, "slot": si,
                       "hex": f"#{r:02x}{g:02x}{b:02x}", "r":r, "g":g, "b":b})
        banks.append({"bank": bi, "colors": bc,
                      "used_colors": sum(1 for c in bc if c["r"] or c["g"] or c["b"])})
    return banks

def _banks_response(colors: list[tuple[int,int,int]], name: str) -> dict:
    banks = _colors_to_banks(colors)
    return {"name": name,
            "total_colors": len(colors),
            "used_banks": sum(1 for b in banks if b["used_colors"] > 0),
            "banks": banks}

def _img_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Greedy merge  (perceptual palette simplification)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _greedy_merge(
    pixels:    np.ndarray,          # (H*W,) uint8 palette indices
    palette:   np.ndarray,          # (N,3)  uint8 RGB
    threshold: float,               # Oklab Euclidean distance
    transp_idx: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Merge near-identical palette entries greedily (least-frequent first).
    Returns (new_pixels, new_palette).
    """
    # Build frequency table for indices actually present
    unique, counts = np.unique(pixels, return_counts=True)
    freq = np.zeros(len(palette), dtype=np.int64)
    for u, c in zip(unique, counts):
        freq[u] = c

    # mapping[i] = which index i should be remapped to (starts as identity)
    mapping = np.arange(len(palette), dtype=np.int32)
    active  = set(range(len(palette)))
    if transp_idx is not None:
        active.discard(transp_idx)

    changed = True
    while changed:
        changed = False
        # Sort active by ascending frequency
        order = sorted(active, key=lambda i: freq[i])
        lab   = _rgb_to_oklab(palette)

        for i in order:
            if i not in active:
                continue
            # Candidates: more frequent active colors (not itself, not transp)
            candidates = [j for j in active
                          if j != i and freq[j] >= freq[i]
                          and j != transp_idx]
            if not candidates:
                continue
            cand_arr  = lab[candidates]
            dists     = np.sqrt(((lab[i] - cand_arr) ** 2).sum(axis=1))
            min_idx   = int(np.argmin(dists))
            if dists[min_idx] < threshold:
                target = candidates[min_idx]
                # Remap i → target
                mapping[mapping == i] = target
                freq[target] += freq[i]
                freq[i]       = 0
                active.discard(i)
                changed = True

    # Build compact palette preserving order
    used_indices = sorted(active)
    idx_remap    = {old: new for new, old in enumerate(used_indices)}
    new_palette  = palette[used_indices]
    # Compose: pixel → mapping[pixel] → idx_remap
    full_map     = np.array([idx_remap.get(int(mapping[i]), 0)
                              for i in range(len(palette))], dtype=np.uint8)
    new_pixels   = full_map[pixels]
    return new_pixels, new_palette


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Weighted k-medoids  (palette reduction)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _kmedoids(
    colors:  np.ndarray,   # (C,3) unique RGB colors
    weights: np.ndarray,   # (C,)  pixel frequency per color
    k:       int,
    max_iter: int = 50,
    seed:    int  = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Weighted k-medoids in Oklab space.
    Returns (medoid_rgb (k,3), labels (C,)).
    """
    lab  = _rgb_to_oklab(colors)
    rng  = np.random.default_rng(seed)
    # Init: weighted random sample without replacement
    prob = weights.astype(np.float64)
    prob /= prob.sum()
    medoid_idx = rng.choice(len(colors), size=min(k, len(colors)),
                             replace=False, p=prob)
    medoids    = lab[medoid_idx].copy()

    for _ in range(max_iter):
        # Assign each color to nearest medoid
        sq   = _sq_dists(lab, medoids)
        labels = sq.argmin(axis=1)

        new_medoids = medoids.copy()
        for j in range(k):
            mask = labels == j
            if not mask.any():
                continue
            # Best medoid = color in cluster with lowest weighted sum of distances
            cluster_lab = lab[mask]
            cluster_w   = weights[mask].astype(np.float64)
            sq_in       = _sq_dists(cluster_lab, cluster_lab)
            cost        = (sq_in * cluster_w[np.newaxis, :]).sum(axis=1)
            best        = int(np.argmin(cost))
            new_medoids[j] = cluster_lab[best]

        if np.allclose(new_medoids, medoids, atol=1e-6):
            break
        medoids = new_medoids

    sq     = _sq_dists(lab, medoids)
    labels = sq.argmin(axis=1)
    # Convert medoids back to RGB (find nearest actual color in each cluster)
    medoid_rgb = np.zeros((k, 3), dtype=np.uint8)
    for j in range(k):
        mask = labels == j
        if mask.any():
            # Pick the most-frequent color in this cluster as the representative
            best = int(np.argmax(weights * mask))
            medoid_rgb[j] = colors[best]
        else:
            medoid_rgb[j] = _oklab_to_rgb(medoids[j:j+1])[0]
    return medoid_rgb, labels


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pixel remapping
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _remap_to_palette(
    img_rgba:  np.ndarray,    # (H,W,4) uint8
    palette:   np.ndarray,    # (K,3)   uint8 RGB
    transp_idx: int = 0,
) -> Image.Image:
    """Remap every opaque pixel to nearest Oklab palette entry. Returns indexed PNG."""
    H, W  = img_rgba.shape[:2]
    alpha = img_rgba[:,:,3]
    rgb   = img_rgba[:,:,:3].reshape(-1, 3).astype(np.uint8)
    opaque_mask = alpha.flatten() >= 128

    pal_lab = _rgb_to_oklab(palette)
    indices = np.full(H * W, transp_idx, dtype=np.uint8)

    if opaque_mask.any():
        px_lab = _rgb_to_oklab(rgb[opaque_mask])
        chunk  = 2048
        nearest = np.empty(px_lab.shape[0], dtype=np.int32)
        for s in range(0, len(px_lab), chunk):
            e = min(s + chunk, len(px_lab))
            nearest[s:e] = _sq_dists(px_lab[s:e], pal_lab).argmin(axis=1)
        indices[opaque_mask] = nearest.astype(np.uint8)

    out = Image.fromarray(indices.reshape(H, W), mode="P")
    flat_pal = []
    for r,g,b in palette:
        flat_pal += [int(r), int(g), int(b)]
    flat_pal += [0] * (768 - len(flat_pal))
    out.putpalette(flat_pal)
    return out


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Routes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/load")
async def load_8bpp(file: UploadFile = File(...)):
    """Load palette from JASC-PAL or 8bpp indexed PNG."""
    data     = await file.read()
    filename = file.filename or ""
    ext      = Path(filename).suffix.lower()
    colors: list[tuple[int,int,int]] = []

    if ext == ".pal":
        try:
            colors = _parse_jasc_pal(data.decode("utf-8", errors="replace"))
        except Exception as e:
            raise HTTPException(400, f"Could not parse PAL: {e}")
        if not colors:
            raise HTTPException(400, "PAL has no colors")
        colors = colors[:256]
    elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif"):
        try:
            img = Image.open(io.BytesIO(data)); img.load()
        except Exception as e:
            raise HTTPException(400, f"Could not read image: {e}")
        if img.mode != "P":
            raise HTTPException(400, "not-indexed")
        pal      = img.getpalette() or []
        n_colors = len(pal) // 3
        if not n_colors:
            raise HTTPException(400, "Image has no palette")
        colors = [(pal[i*3], pal[i*3+1], pal[i*3+2]) for i in range(min(n_colors, 256))]
    else:
        raise HTTPException(400, f"Unsupported type '{ext}'")

    return _banks_response(colors, Path(filename).stem)


@router.post("/shrink")
async def shrink_8bpp(
    file:      UploadFile = File(...),
    threshold: float      = Form(default=0.05),
    max_colors: int       = Form(default=256),
):
    """
    Mode A — shrink an 8bpp indexed PNG palette.
    1. Greedy merge near-identical colors (Oklab dist < threshold).
    2. If still > max_colors, reduce with weighted k-medoids.
    Returns: image_b64, palette banks, metrics.
    """
    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data)); img.load()
    except Exception as e:
        raise HTTPException(400, f"Could not read image: {e}")
    if img.mode != "P":
        raise HTTPException(400, "Image must be an 8bpp indexed PNG")

    pal_raw  = img.getpalette() or []
    n        = min(len(pal_raw) // 3, 256)
    palette  = np.array([(pal_raw[i*3], pal_raw[i*3+1], pal_raw[i*3+2])
                          for i in range(n)], dtype=np.uint8)
    pixels   = np.array(img, dtype=np.uint8).flatten()
    original_count = int(len(np.unique(pixels)))

    # Step 1 — greedy merge
    pixels, palette = _greedy_merge(pixels, palette, threshold=threshold)
    after_merge = int(len(np.unique(pixels)))

    # Step 2 — k-medoids if still over budget
    if after_merge > max_colors:
        unique_cols, counts = np.unique(pixels, return_counts=True)
        col_rgb  = palette[unique_cols]
        med_rgb, med_labels = _kmedoids(col_rgb, counts, k=max_colors)
        # Remap pixels: color index → medoid index
        old_to_new = np.zeros(len(palette), dtype=np.uint8)
        for new_j, old_i in enumerate(unique_cols):
            old_to_new[old_i] = int(med_labels[new_j])
        pixels  = old_to_new[pixels]
        palette = med_rgb

    after_reduce = int(len(np.unique(pixels)))
    H, W = img.size[1], img.size[0]
    new_img = _remap_to_palette(
        np.dstack([
            palette[pixels.reshape(H,W)],
            np.full((H,W), 255, dtype=np.uint8)
        ]),
        palette,
    )

    colors_list = [tuple(int(x) for x in c) for c in palette]
    return {
        **_banks_response(colors_list, Path(file.filename or "image").stem),
        "image_b64": _img_to_b64(new_img),
        "metrics": {
            "original":     original_count,
            "after_merge":  after_merge,
            "after_reduce": after_reduce,
        },
    }


@router.post("/create")
async def create_8bpp(
    file:       UploadFile = File(...),
    n_colors:   int        = Form(default=255),
    bg_color:   str        = Form(default="#000000"),
    threshold:  float      = Form(default=0.05),
):
    """
    Mode B — create an 8bpp palette from any image.
    1. Greedy merge unique colors below threshold.
    2. If > n_colors, reduce with weighted k-medoids.
    Returns: quantized image_b64, palette banks, metrics.
    """
    if not 1 <= n_colors <= 255:
        raise HTTPException(400, "n_colors must be 1–255")

    h = bg_color.lstrip("#")
    bg_rgb = np.array([int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)], dtype=np.uint8)

    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception as e:
        raise HTTPException(400, f"Could not open image: {e}")

    img_arr  = np.array(img, dtype=np.uint8)
    H, W     = img_arr.shape[:2]
    alpha    = img_arr[:,:,3].flatten()
    rgb_flat = img_arr[:,:,:3].reshape(-1,3)
    opaque   = alpha >= 128

    sprite_px = rgb_flat[opaque]
    original_count = len(np.unique(sprite_px, axis=0)) if len(sprite_px) else 0

    if len(sprite_px) == 0:
        palette = np.array([bg_rgb], dtype=np.uint8)
        after_merge = after_reduce = 1
    else:
        # Build index image over unique colors
        unique_cols, inv = np.unique(sprite_px, axis=0, return_inverse=True)
        freq = np.bincount(inv, minlength=len(unique_cols)).astype(np.int64)

        # Step 1 — greedy merge on unique colors
        pixels_idx, palette = _greedy_merge(
            inv.astype(np.uint8), unique_cols.astype(np.uint8), threshold
        )
        after_merge = int(len(np.unique(pixels_idx)))

        # Step 2 — k-medoids if still over budget
        if after_merge > n_colors:
            u2, c2 = np.unique(pixels_idx, return_counts=True)
            med_rgb, med_labels = _kmedoids(palette[u2], c2, k=n_colors)
            remap = np.zeros(len(palette), dtype=np.uint8)
            for nj, oi in enumerate(u2):
                remap[oi] = int(med_labels[nj])
            pixels_idx = remap[pixels_idx]
            palette    = med_rgb

        after_reduce = int(len(np.unique(pixels_idx)))

        # Reconstruct full opaque palette for remapping
        # (bg_color goes in slot 0)
        palette = np.vstack([bg_rgb[np.newaxis,:], palette])

    # Remap full image (transparent → slot 0 = bg)
    out_img = _remap_to_palette(img_arr, palette, transp_idx=0)
    colors_list = [tuple(int(x) for x in c) for c in palette]

    return {
        **_banks_response(colors_list, Path(file.filename or "image").stem),
        "image_b64": _img_to_b64(out_img),
        "metrics": {
            "original":     original_count,
            "after_merge":  after_merge,
            "after_reduce": after_reduce,
        },
    }


@router.post("/export-bank")
async def export_bank(
    file:        UploadFile = File(...),
    bank_index:  int        = Form(...),
    name:        str        = Form(default=""),
    colors_json: str        = Form(default=""),
):
    """Export one 16-color bank as JASC-PAL."""
    if not 0 <= bank_index <= 15:
        raise HTTPException(400, f"bank_index must be 0–15")
    colors: list[tuple[int,int,int]] = []
    if colors_json:
        try:
            for h in _json.loads(colors_json):
                h = h.lstrip("#")
                colors.append((int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)))
        except Exception as e:
            raise HTTPException(400, f"Invalid colors_json: {e}")
    else:
        data = await file.read()
        ext  = Path(file.filename or "").suffix.lower()
        if ext == ".pal":
            colors = _parse_jasc_pal(data.decode("utf-8", errors="replace"))
        elif ext in (".png",".jpg",".jpeg",".bmp"):
            img = Image.open(io.BytesIO(data))
            if img.mode != "P":
                raise HTTPException(400, "Not indexed")
            pal = img.getpalette()
            colors = [(pal[i*3],pal[i*3+1],pal[i*3+2]) for i in range(min(len(pal)//3,256))]
        else:
            raise HTTPException(400, f"Unsupported: {ext}")

    padded = (list(colors) + [(0,0,0)]*256)[:256]
    bank   = padded[bank_index*16 : bank_index*16+16]
    stem   = name or f"bank{bank_index}"
    lines  = ["JASC-PAL","0100","16"] + [f"{r} {g} {b}" for r,g,b in bank]
    return StreamingResponse(
        io.BytesIO(("\n".join(lines)+"\n").encode()),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{stem}.pal"'},
    )