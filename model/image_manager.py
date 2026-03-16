"""
model/image_manager.py

Image loading, palette conversion, and saving. Pure Pillow — no Qt.

The conversion pipeline:
  1. Load any image → PIL RGBA
  2. Detect transparent color (alpha channel or edge detection)
  3. For each palette: remap every pixel to the nearest Color using RGB distance
  4. Save as indexed 4-bit PNG (GBA-compatible)
"""

from __future__ import annotations
import logging
from pathlib import Path

import numpy as np
from PIL import Image

from model.palette import Color, Palette


SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}


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

    def __init__(self, config: dict):
        self.config = config
        self._current_image_path: Path | None = None
        self._original_rgba: Image.Image | None = None      # PIL RGBA source
        self._transparent_color: Color | None = None
        self._conversion_cache: dict[tuple, Color] = {}     # (pixel_rgb, palette_name) → Color
        self.results: list[ConversionResult] = []

    # ---------- Load ----------

    def load_image(self, image_path: str | Path) -> Image.Image:
        """Load image and return PIL RGBA. Raises on unsupported format or bad file."""
        path = Path(image_path)
        if path.suffix.lower() not in SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format '{path.suffix}'. Supported: {', '.join(SUPPORTED_FORMATS)}"
            )

        img = Image.open(path).convert("RGBA")
        self._current_image_path = path
        self._original_rgba = img
        self._transparent_color = self._detect_transparent_color(img)
        self._conversion_cache.clear()
        logging.debug(f"Loaded {path.name} ({img.width}×{img.height})")
        return img

    def _detect_transparent_color(self, img: Image.Image) -> Color | None:
        """
        Find the background/transparent color.
        Priority: alpha channel first, then most common edge pixel.
        """
        pixels = np.array(img)  # shape (H, W, 4)

        # 1. Any pixel with alpha < 255?
        transparent_mask = pixels[:, :, 3] < 255
        if transparent_mask.any():
            y, x = np.argwhere(transparent_mask)[0]
            r, g, b, _ = pixels[y, x]
            c = Color(int(r), int(g), int(b))
            logging.debug(f"Transparent color (alpha): {c.to_hex()}")
            return c

        # 2. Most common edge pixel
        h, w = pixels.shape[:2]
        edges = np.concatenate([
            pixels[0, :, :3],       # top row
            pixels[-1, :, :3],      # bottom row
            pixels[:, 0, :3],       # left col
            pixels[:, -1, :3],      # right col
        ])
        unique, counts = np.unique(edges.reshape(-1, 3), axis=0, return_counts=True)
        most_common = unique[counts.argmax()]
        c = Color(int(most_common[0]), int(most_common[1]), int(most_common[2]))
        logging.debug(f"Transparent color (edge): {c.to_hex()}")
        return c

    # ---------- Convert ----------

    def process_all_palettes(self, palettes: list[Palette]) -> list[ConversionResult]:
        """Convert the loaded image against every palette. Returns sorted results."""
        if self._original_rgba is None:
            raise ValueError("No image loaded — call load_image() first")

        self.results = [
            self._convert_to_palette(self._original_rgba, palette)
            for palette in palettes
        ]
        return self.results

    def _convert_to_palette(self, img: Image.Image, palette: Palette) -> ConversionResult:
        """
        Remap every pixel in img to the nearest color in palette.
        Transparent pixels → palette.transparent_color (index 0).
        Returns an indexed PIL Image (mode "P").
        """
        pixels = np.array(img)  # (H, W, 4)
        h, w = pixels.shape[:2]

        transparent = palette.transparent_color
        opaque = palette.opaque_colors

        if not opaque:
            # Edge case: palette only has one color
            opaque = palette.colors

        # Build lookup arrays for vectorised nearest-colour search
        palette_rgb = np.array([c.to_tuple() for c in opaque], dtype=np.int32)  # (N, 3)

        rgb = pixels[:, :, :3].astype(np.int32)          # (H, W, 3)
        alpha = pixels[:, :, 3]                           # (H, W)

        # For each pixel, find index of nearest opaque palette color
        # Expand dims for broadcasting: (H, W, 1, 3) vs (N, 3)
        diff = rgb[:, :, np.newaxis, :] - palette_rgb[np.newaxis, np.newaxis, :, :]
        dist_sq = (diff ** 2).sum(axis=3)                 # (H, W, N)
        nearest_idx = dist_sq.argmin(axis=2)              # (H, W)

        # Build output index array
        # Index 0 = transparent, index i+1 = opaque[i]
        index_map = nearest_idx + 1                       # shift by 1 (0 reserved for transparent)
        index_map[alpha < 255] = 0                        # transparent pixels → index 0

        # Count distinct palette indices actually used
        used = set(np.unique(index_map).tolist())
        colors_used = len(used)

        # Build PIL indexed image
        out = Image.new("P", (w, h))
        pal_data = []
        if transparent:
            pal_data += list(transparent.to_tuple())
        for c in opaque:
            pal_data += list(c.to_tuple())
        # Pad to 256 colours (768 bytes)
        pal_data += [0] * (768 - len(pal_data))
        out.putpalette(pal_data)
        out.putdata(index_map.flatten().tolist())

        return ConversionResult(image=out, palette=palette, colors_used=colors_used, used_indices=used)

    # ---------- Save ----------

    def save_image(self, result: ConversionResult, output_path: str | Path) -> bool:
        """Save a ConversionResult as a 4-bit indexed PNG."""
        try:
            out_path = Path(output_path)
            result.image.save(out_path, format="PNG", bits=4, optimize=True)
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