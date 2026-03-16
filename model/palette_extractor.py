"""
model/palette_extractor.py

Extract a GBA-compatible palette from any sprite using k-means clustering.
This is the v3 "Extract" pillar — the feature that was missing vs Pylette.

Usage:
    extractor = PaletteExtractor()
    palette = extractor.extract("my_sprite.png", n_colors=15, bg_color="#73C5A4")
    palette.to_jasc_pal(Path("palettes/my_sprite.pal"))
"""

from __future__ import annotations
import logging
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

from model.palette import Color, Palette


class PaletteExtractor:
    """
    Extract a palette from a sprite using k-means clustering.

    Slot 0 is always the explicit bg_color (the transparent color).
    n_colors refers to the number of *non-transparent* colors to cluster,
    so the final palette has n_colors + 1 entries total (max 16 for GBA).
    """

    def __init__(self, random_state: int = 42):
        self.random_state = random_state

    def extract(
        self,
        image_path: str | Path,
        n_colors: int = 15,
        bg_color: str = "#73C5A4",
        name: str | None = None,
    ) -> Palette:
        """
        Extract a palette from image_path.

        Args:
            image_path: Path to any image Pillow can open.
            n_colors:   Number of sprite colors to cluster (NOT including transparent).
                        Final palette size = n_colors + 1. Max 15 for GBA (16 total).
            bg_color:   Hex string for the transparent color forced into slot 0.
                        e.g. "#73C5A4" (GBA default) or whatever the user picked.
            name:       Palette name. Defaults to the image filename stem.

        Returns:
            A Palette with (n_colors + 1) entries, index 0 = bg_color.
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

        max_sprite_colors = Palette.MAX_COLORS - 1  # 15
        if n_colors < 1 or n_colors > max_sprite_colors:
            raise ValueError(f"n_colors must be 1–{max_sprite_colors}, got {n_colors}")

        transparent_color = self._parse_hex(bg_color)
        transparent_rgb = (transparent_color.r, transparent_color.g, transparent_color.b)

        img = Image.open(path).convert("RGBA")
        pixels = np.array(img)  # (H, W, 4)
        alpha = pixels[:, :, 3]
        rgb = pixels[:, :, :3]

        # Collect opaque pixels, excluding any that exactly match the transparent color
        opaque_mask = alpha.flatten() >= 255
        flat_rgb = rgb.reshape(-1, 3)
        opaque_pixels = flat_rgb[opaque_mask].astype(np.float32)

        # Remove pixels that are already the transparent color
        tr = np.array(transparent_rgb, dtype=np.float32)
        non_transparent_mask = ~np.all(opaque_pixels == tr, axis=1)
        sprite_pixels = opaque_pixels[non_transparent_mask]

        if len(sprite_pixels) == 0:
            logging.warning("Image has no sprite pixels — returning palette with transparent only")
            return Palette(name=name or path.stem, colors=[transparent_color])

        # Clamp clusters to number of unique colors actually present
        unique_colors = len(np.unique(sprite_pixels, axis=0))
        actual_clusters = min(n_colors, unique_colors)

        kmeans = KMeans(
            n_clusters=actual_clusters,
            random_state=self.random_state,
            n_init="auto",
        )
        kmeans.fit(sprite_pixels)
        centers = kmeans.cluster_centers_.astype(np.uint8)

        # Sort by cluster size (most prominent first)
        labels = kmeans.labels_
        cluster_sizes = np.bincount(labels, minlength=actual_clusters)
        order = np.argsort(-cluster_sizes)
        sorted_centers = centers[order]

        # Slot 0 = transparent, slots 1..n = clustered sprite colors
        colors = [transparent_color] + [
            Color(int(c[0]), int(c[1]), int(c[2])) for c in sorted_centers
        ]

        palette = Palette(name=name or path.stem, colors=colors)
        logging.info(
            f"Extracted {len(colors)} colors from '{path.name}' "
            f"(transparent={bg_color}, {len(sprite_pixels)} sprite pixels, {actual_clusters} clusters)"
        )
        return palette

    def extract_batch(
        self,
        image_paths: list[Path],
        n_colors: int = 15,
        bg_color: str = "#73C5A4",
    ) -> list[Palette]:
        """Extract palettes from a list of images. Returns one Palette per image."""
        results = []
        for path in image_paths:
            try:
                results.append(self.extract(path, n_colors=n_colors, bg_color=bg_color))
            except Exception as e:
                logging.error(f"Failed to extract palette from {path}: {e}")
        return results

    # ---------- Helpers ----------

    @staticmethod
    def _parse_hex(hex_color: str) -> Color:
        """Parse a hex color string like '#73C5A4' into a Color."""
        h = hex_color.lstrip("#")
        if len(h) != 6:
            raise ValueError(f"Invalid hex color: {hex_color!r}")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return Color(r, g, b)