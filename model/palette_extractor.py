"""
model/palette_extractor.py

Extract a GBA-compatible palette from any sprite using k-means clustering.
Supports two color spaces for clustering:
  - 'oklab'  (default) — perceptually uniform, groups colors as humans see them
  - 'rgb'              — raw euclidean distance in sRGB space

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


# ---------------------------------------------------------------------------
# Oklab conversion (vectorized numpy)
# Reference: https://bottosson.github.io/posts/oklab/
# ---------------------------------------------------------------------------

def _srgb_to_linear(c: np.ndarray) -> np.ndarray:
    """sRGB gamma → linear (in-place safe, float32 input expected, 0–1 range)."""
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(c: np.ndarray) -> np.ndarray:
    """Linear → sRGB gamma (0–1 range)."""
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1.0 / 2.4) - 0.055)


def rgb_to_oklab(pixels: np.ndarray) -> np.ndarray:
    """
    Convert (N, 3) uint8 RGB → (N, 3) float32 Oklab.
    L in ~[0, 1], a/b in ~[-0.5, 0.5].
    """
    rgb = pixels.astype(np.float32) / 255.0
    lin = _srgb_to_linear(rgb)

    # Linear RGB → LMS cone responses
    l = 0.4122214708 * lin[:, 0] + 0.5363325363 * lin[:, 1] + 0.0514459929 * lin[:, 2]
    m = 0.2119034982 * lin[:, 0] + 0.6806995451 * lin[:, 1] + 0.1073969566 * lin[:, 2]
    s = 0.0883024619 * lin[:, 0] + 0.2817188376 * lin[:, 1] + 0.6299787005 * lin[:, 2]

    # Cube root (avoid NaN on negatives, though values should be ≥ 0)
    l_ = np.cbrt(np.maximum(l, 0))
    m_ = np.cbrt(np.maximum(m, 0))
    s_ = np.cbrt(np.maximum(s, 0))

    L =  0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a =  1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b =  0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_

    return np.stack([L, a, b], axis=1).astype(np.float32)


def oklab_to_rgb(lab: np.ndarray) -> np.ndarray:
    """
    Convert (N, 3) float32 Oklab → (N, 3) uint8 RGB.
    Values are clamped to valid range.
    """
    L, a, b = lab[:, 0], lab[:, 1], lab[:, 2]

    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b

    l = l_ ** 3
    m = m_ ** 3
    s = s_ ** 3

    r =  4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    b_ = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s

    rgb = np.stack([r, g, b_], axis=1)
    rgb = _linear_to_srgb(np.clip(rgb, 0, 1))
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------

class PaletteExtractor:
    """
    Extract a palette from a sprite using k-means clustering.

    Slot 0 is always the explicit bg_color (the transparent color).
    n_colors refers to the number of *non-transparent* colors to cluster,
    so the final palette has n_colors + 1 entries total (max 16 for GBA).

    color_space controls the space in which distance is measured:
      'oklab'  — perceptually uniform (default, recommended)
      'rgb'    — raw sRGB euclidean distance
    """

    VALID_COLOR_SPACES = ("oklab", "rgb")

    def __init__(self, random_state: int = 42):
        self.random_state = random_state

    def extract(
        self,
        image_path: str | Path,
        n_colors: int = 15,
        bg_color: str = "#73C5A4",
        color_space: str = "oklab",
        name: str | None = None,
    ) -> Palette:
        """
        Extract a palette from image_path.

        Args:
            image_path:   Path to any image Pillow can open.
            n_colors:     Number of sprite colors to cluster (NOT including transparent).
                          Final palette size = n_colors + 1. Max 15 for GBA (16 total).
            bg_color:     Hex string for the transparent color forced into slot 0.
            color_space:  'oklab' (default) or 'rgb'.
            name:         Palette name. Defaults to the image filename stem.

        Returns:
            A Palette with (n_colors + 1) entries, index 0 = bg_color.
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

        if color_space not in self.VALID_COLOR_SPACES:
            raise ValueError(f"color_space must be one of {self.VALID_COLOR_SPACES}, got {color_space!r}")

        max_sprite_colors = Palette.MAX_COLORS - 1  # 15
        if n_colors < 1 or n_colors > max_sprite_colors:
            raise ValueError(f"n_colors must be 1–{max_sprite_colors}, got {n_colors}")

        transparent_color = self._parse_hex(bg_color)
        transparent_rgb = np.array(
            [transparent_color.r, transparent_color.g, transparent_color.b],
            dtype=np.float32,
        )

        img = Image.open(path).convert("RGBA")
        pixels = np.array(img)          # (H, W, 4)
        alpha = pixels[:, :, 3]
        rgb   = pixels[:, :, :3]

        # Collect fully opaque pixels, excluding the transparent color
        opaque_mask = alpha.flatten() >= 255
        flat_rgb = rgb.reshape(-1, 3)
        opaque_pixels = flat_rgb[opaque_mask].astype(np.float32)

        non_transparent_mask = ~np.all(opaque_pixels == transparent_rgb, axis=1)
        sprite_pixels_rgb = opaque_pixels[non_transparent_mask].astype(np.uint8)

        if len(sprite_pixels_rgb) == 0:
            logging.warning("Image has no sprite pixels — returning palette with transparent only")
            return Palette(name=name or path.stem, colors=[transparent_color])

        # Convert to clustering space
        if color_space == "oklab":
            cluster_pixels = rgb_to_oklab(sprite_pixels_rgb)
        else:
            cluster_pixels = sprite_pixels_rgb.astype(np.float32)

        unique_colors = len(np.unique(sprite_pixels_rgb, axis=0))
        actual_clusters = min(n_colors, unique_colors)

        kmeans = KMeans(
            n_clusters=actual_clusters,
            random_state=self.random_state,
            n_init="auto",
        )
        kmeans.fit(cluster_pixels)
        centers = kmeans.cluster_centers_   # float, in cluster space

        # Convert centroids back to uint8 RGB
        if color_space == "oklab":
            centers_rgb = oklab_to_rgb(centers.astype(np.float32))
        else:
            centers_rgb = np.clip(centers, 0, 255).astype(np.uint8)

        # Sort by cluster size (most-used color first)
        labels = kmeans.labels_
        cluster_sizes = np.bincount(labels, minlength=actual_clusters)
        order = np.argsort(-cluster_sizes)
        sorted_centers = centers_rgb[order]

        colors = [transparent_color] + [
            Color(int(c[0]), int(c[1]), int(c[2])) for c in sorted_centers
        ]

        palette = Palette(name=name or path.stem, colors=colors)
        logging.info(
            f"Extracted {len(colors)} colors from '{path.name}' "
            f"(space={color_space}, transparent={bg_color}, "
            f"{len(sprite_pixels_rgb)} sprite pixels, {actual_clusters} clusters)"
        )
        return palette

    def extract_batch(
        self,
        image_paths: list[Path],
        n_colors: int = 15,
        bg_color: str = "#73C5A4",
        color_space: str = "oklab",
    ) -> list[Palette]:
        """Extract palettes from a list of images. Returns one Palette per image."""
        results = []
        for path in image_paths:
            try:
                results.append(self.extract(path, n_colors=n_colors, bg_color=bg_color, color_space=color_space))
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