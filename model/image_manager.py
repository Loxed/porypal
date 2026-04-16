"""
model/image_manager.py

Image loading, palette conversion, and saving. Pure Pillow — no Qt.

The conversion pipeline:
  1. Load any image → PIL RGBA
  2. Detect transparent color (alpha channel, explicit override, or edge detection)
  3. For each palette: remap every pixel to the nearest Color using Oklab distance
     — pixels matching the bg color are mapped directly to slot 0 (transparent)
  4. Save as indexed 4-bit PNG (GBA-compatible)
"""

from __future__ import annotations
import logging
from pathlib import Path

import numpy as np
from PIL import Image

from model.palette import Color, Palette
from model.palette_extractor import rgb_to_oklab


SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}


def detect_background_color(img: Image.Image) -> Color | None:
    """
    Detect the sprite's background/transparent color.

    Priority matches Apply Palette: first alpha-transparent pixel, otherwise the
    most common edge pixel.
    """
    pixels = np.array(img.convert("RGBA"))  # shape (H, W, 4)

    transparent_mask = pixels[:, :, 3] < 255
    if transparent_mask.any():
        y, x = np.argwhere(transparent_mask)[0]
        r, g, b, _ = pixels[y, x]
        c = Color(int(r), int(g), int(b))
        logging.debug(f"Transparent color (alpha): {c.to_hex()}")
        return c

    h, w = pixels.shape[:2]
    edges = np.concatenate([
        pixels[0, :, :3],
        pixels[-1, :, :3],
        pixels[:, 0, :3],
        pixels[:, -1, :3],
    ])
    unique, counts = np.unique(edges.reshape(-1, 3), axis=0, return_counts=True)
    most_common = unique[counts.argmax()]
    c = Color(int(most_common[0]), int(most_common[1]), int(most_common[2]))
    logging.debug(f"Transparent color (edge): {c.to_hex()}")
    return c


def build_background_mask(img: Image.Image, background_color: Color | None) -> np.ndarray:
    """
    Return a boolean mask for pixels treated as background by Apply Palette.

    Background is any alpha-transparent pixel plus any opaque pixel that exactly
    matches the detected/explicit background RGB color.
    """
    pixels = np.array(img.convert("RGBA"))  # shape (H, W, 4)
    rgb = pixels[:, :, :3]
    alpha = pixels[:, :, 3]

    bg_mask = alpha < 255
    if background_color is not None:
        tr, tg, tb = background_color.to_tuple()
        bg_mask = bg_mask | (
            (rgb[:, :, 0] == tr) &
            (rgb[:, :, 1] == tg) &
            (rgb[:, :, 2] == tb)
        )
    return bg_mask


class ConversionResult:
    """Holds one palette's conversion of the loaded image."""

    def __init__(self, image: Image.Image, palette: Palette, colors_used: int, used_indices: set = None):
        self.image = image          # PIL Image (mode "P", indexed)
        self.palette = palette
        self.colors_used = colors_used
        self.used_indices = used_indices or set()  # palette indices actually present in the image

    @property
    def label(self) -> str:
        return f"{self.palette.name} ({self.colors_used} colors used)"


class ImageManager:
    """Handles image loading, conversion, and saving. No Qt dependency."""

    def __init__(self):
        self._current_image_path: Path | None = None
        self._original_rgba: Image.Image | None = None
        self._transparent_color: Color | None = None
        self._conversion_cache: dict[tuple, Color] = {}
        self.results: list[ConversionResult] = []

    # ---------- Load ----------

    def load_image(self, image_path: str | Path, bg_color: str | None = None) -> Image.Image:
        """
        Load image and return PIL RGBA.
        bg_color: optional hex string (e.g. '#73C5A4') to override transparent color detection.
        """
        path = Path(image_path)
        if path.suffix.lower() not in SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format '{path.suffix}'. Supported: {', '.join(SUPPORTED_FORMATS)}"
            )

        img = Image.open(path).convert("RGBA")
        self._current_image_path = path
        self._original_rgba = img
        self._conversion_cache.clear()

        if bg_color:
            h = bg_color.lstrip('#')
            self._transparent_color = Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            logging.debug(f"Transparent color (explicit): {bg_color}")
        else:
            self._transparent_color = self._detect_transparent_color(img)

        logging.debug(f"Loaded {path.name} ({img.width}×{img.height})")
        return img

    def _detect_transparent_color(self, img: Image.Image) -> Color | None:
        """
        Find the background/transparent color.
        Priority: alpha channel first, then most common edge pixel.
        """
        return detect_background_color(img)

    # ---------- Convert ----------

    def process_all_palettes(self, palettes: list[Palette]) -> list[ConversionResult]:
        """Convert the loaded image against every palette."""
        if self._original_rgba is None:
            raise ValueError("No image loaded — call load_image() first")

        self.results = [
            self._convert_to_palette(self._original_rgba, palette)
            for palette in palettes
        ]
        return self.results

    def _convert_to_palette(self, img: Image.Image, palette: Palette) -> ConversionResult:
        """
        Remap every pixel to the nearest palette color in Oklab space.
        Pixels matching the image's bg color → slot 0 (transparent), skipped from Oklab matching.
        """
        pixels = np.array(img)  # (H, W, 4)
        h, w = pixels.shape[:2]

        transparent = palette.transparent_color
        opaque = palette.opaque_colors or palette.colors

        rgb = pixels[:, :, :3]   # (H, W, 3)

        bg_mask = build_background_mask(img, self._transparent_color)

        # Convert palette opaque colors to Oklab
        palette_rgb = np.array([c.to_tuple() for c in opaque], dtype=np.uint8)  # (N, 3)
        palette_lab = rgb_to_oklab(palette_rgb)                                   # (N, 3)

        # Convert all image pixels to Oklab
        flat_lab = rgb_to_oklab(rgb.reshape(-1, 3).astype(np.uint8))  # (H*W, 3)

        # Nearest neighbor in Oklab space
        diff = flat_lab[:, np.newaxis, :] - palette_lab[np.newaxis, :, :]  # (H*W, N, 3)
        dist_sq = (diff ** 2).sum(axis=2)                                   # (H*W, N)
        nearest_idx = dist_sq.argmin(axis=1).reshape(h, w)                 # (H, W)

        # Index 0 = transparent slot, opaque colors start at 1
        index_map = nearest_idx + 1
        index_map[bg_mask] = 0  # bg pixels → slot 0, no Oklab matching

        used = set(np.unique(index_map).tolist())

        # Build PIL indexed image
        out = Image.new("P", (w, h))
        pal_data = list(transparent.to_tuple()) if transparent else [0, 0, 0]
        for c in opaque:
            pal_data += list(c.to_tuple())
        pal_data += [0] * (768 - len(pal_data))
        out.putpalette(pal_data)
        out.putdata(index_map.flatten().tolist())
        out.info["transparency"] = 0

        return ConversionResult(image=out, palette=palette, colors_used=len(used), used_indices=used)

    # ---------- Save ----------

    def save_image(self, result: ConversionResult, output_path: str | Path) -> bool:
        """Save a ConversionResult as a 4-bit indexed PNG."""
        try:
            out_path = Path(output_path)
            from server.helpers import save_png

            out_path.write_bytes(save_png(result.image))
            logging.debug(f"Saved: {out_path}")
            return True
        except Exception as e:
            logging.error(f"Failed to save image: {e}")
            return False

    def auto_output_path(self, result: ConversionResult) -> Path:
        """Generate <original_stem>_<palette_stem>.png next to the source image."""
        if not self._current_image_path:
            raise ValueError("No image loaded")
        stem = self._current_image_path.stem
        pal_stem = Path(result.palette.name).stem
        return self._current_image_path.parent / f"{stem}_{pal_stem}.png"

    # ---------- Getters ----------

    def get_result_at_index(self, index: int) -> ConversionResult | None:
        if 0 <= index < len(self.results):
            return self.results[index]
        return None

    def get_best_indices(self) -> list[int]:
        """Indices of results with the highest colors_used count."""
        if not self.results:
            return []
        max_colors = max(r.colors_used for r in self.results)
        return [i for i, r in enumerate(self.results) if r.colors_used == max_colors]

    @property
    def current_image_path(self) -> Path | None:
        return self._current_image_path
