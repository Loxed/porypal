"""
model/palette_extractor.py

Extract a GBA-compatible palette from any sprite using k-means clustering.
This is the v3 "Extract" pillar — the feature that was missing vs Pylette.

Usage:
    extractor = PaletteExtractor()
    palette = extractor.extract("my_sprite.png", n_colors=16, name="my_sprite")
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

    The first color slot is always reserved for the transparent/background color
    (detected automatically), so the actual cluster count is n_colors - 1.
    """

    def __init__(self, random_state: int = 42):
        self.random_state = random_state

    def extract(
        self,
        image_path: str | Path,
        n_colors: int = 16,
        name: str | None = None,
    ) -> Palette:
        """
        Extract a palette from image_path.

        Args:
            image_path: Path to any image Pillow can open.
            n_colors: Total palette size including transparent slot (max 16 for GBA).
            name: Palette name. Defaults to the image filename stem.

        Returns:
            A Palette with n_colors entries, index 0 = transparent color.
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
        if n_colors < 2 or n_colors > Palette.MAX_COLORS:
            raise ValueError(f"n_colors must be 2–{Palette.MAX_COLORS}, got {n_colors}")

        img = Image.open(path).convert("RGBA")
        pixels = np.array(img)          # (H, W, 4)
        alpha = pixels[:, :, 3]
        rgb = pixels[:, :, :3]

        # --- Transparent color: first fully-transparent or most common edge pixel ---
        transparent_color = self._detect_transparent(pixels)

        # --- Collect opaque pixels for clustering ---
        opaque_mask = alpha.flatten() >= 255
        opaque_pixels = rgb.reshape(-1, 3)[opaque_mask].astype(np.float32)

        n_clusters = n_colors - 1   # slot 0 is reserved for transparent

        if len(opaque_pixels) == 0:
            logging.warning("Image has no opaque pixels — returning palette with transparent only")
            return Palette(name=name or path.stem, colors=[transparent_color])

        # Clamp clusters to unique pixel count
        actual_clusters = min(n_clusters, len(np.unique(opaque_pixels, axis=0)))

        kmeans = KMeans(
            n_clusters=actual_clusters,
            random_state=self.random_state,
            n_init="auto",
        )
        kmeans.fit(opaque_pixels)
        centers = kmeans.cluster_centers_.astype(np.uint8)

        # Sort by cluster size (most prominent color first after transparent)
        labels = kmeans.labels_
        cluster_sizes = np.bincount(labels, minlength=actual_clusters)
        order = np.argsort(-cluster_sizes)  # descending
        sorted_centers = centers[order]

        colors = [transparent_color] + [
            Color(int(c[0]), int(c[1]), int(c[2])) for c in sorted_centers
        ]

        palette = Palette(name=name or path.stem, colors=colors)
        logging.info(
            f"Extracted {len(colors)} colors from '{path.name}' "
            f"({len(opaque_pixels)} opaque pixels, {actual_clusters} clusters)"
        )
        return palette

    def extract_batch(
        self,
        image_paths: list[Path],
        n_colors: int = 16,
    ) -> list[Palette]:
        """Extract palettes from a list of images. Returns one Palette per image."""
        results = []
        for path in image_paths:
            try:
                results.append(self.extract(path, n_colors=n_colors))
            except Exception as e:
                logging.error(f"Failed to extract palette from {path}: {e}")
        return results

    # ---------- Helpers ----------

    def _detect_transparent(self, pixels: np.ndarray) -> Color:
        alpha = pixels[:, :, 3]
        transparent_mask = alpha < 255
        if transparent_mask.any():
            y, x = np.argwhere(transparent_mask)[0]
            r, g, b, _ = pixels[y, x]
            return Color(int(r), int(g), int(b))

        # Fall back to most common edge pixel
        rgb = pixels[:, :, :3]
        h, w = rgb.shape[:2]
        edges = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
        unique, counts = np.unique(edges.reshape(-1, 3), axis=0, return_counts=True)
        most_common = unique[counts.argmax()]
        return Color(int(most_common[0]), int(most_common[1]), int(most_common[2]))
