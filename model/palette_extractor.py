"""
model/palette_extractor.py

Extract a GBA-compatible palette from any sprite using k-means clustering.
Supports two color spaces for clustering:
  - 'oklab'  (default) — perceptually uniform, groups colors as humans see them
  - 'rgb'              — raw euclidean distance in sRGB space

Oklab matrix coefficients are loaded from oklab_weights.json (same directory).

Usage:
    extractor = PaletteExtractor()
    palette = extractor.extract("my_sprite.png", n_colors=15, bg_color="#73C5A4")
    palette.to_jasc_pal(Path("palettes/my_sprite.pal"))
"""

from __future__ import annotations
import json
import logging
from pathlib import Path

import numpy as np
from PIL import Image

from model.palette import Color, Palette


# ---------------------------------------------------------------------------
# Oklab weights (loaded once at import time)
# ---------------------------------------------------------------------------

_WEIGHTS_PATH = Path(__file__).parent / "data" / "oklab_weights.json"

def _load_weights() -> dict[str, np.ndarray]:
    with open(_WEIGHTS_PATH, "r") as f:
        raw = json.load(f)
    return {
        k: np.array(v, dtype=np.float32)
        for k, v in raw.items()
        if not k.startswith("_")
    }

_W = _load_weights()


# ---------------------------------------------------------------------------
# sRGB gamma helpers
# ---------------------------------------------------------------------------

def _srgb_to_linear(c: np.ndarray) -> np.ndarray:
    """sRGB gamma → linear (float32, 0–1 range)."""
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(c: np.ndarray) -> np.ndarray:
    """Linear → sRGB gamma (0–1 range)."""
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1.0 / 2.4) - 0.055)


# ---------------------------------------------------------------------------
# Oklab conversion (vectorized numpy, weights from JSON)
# ---------------------------------------------------------------------------

def rgb_to_oklab(pixels: np.ndarray) -> np.ndarray:
    """
    Convert (N, 3) uint8 RGB → (N, 3) float32 Oklab.
    L in ~[0, 1], a/b in ~[-0.5, 0.5].
    """
    lin = _srgb_to_linear(pixels.astype(np.float32) / 255.0)

    lms = np.cbrt(np.maximum(lin @ _W["rgb_to_lms"].T, 0))

    return (lms @ _W["lms_to_oklab"].T).astype(np.float32)


def oklab_to_rgb(lab: np.ndarray) -> np.ndarray:
    """
    Convert (N, 3) float32 Oklab → (N, 3) uint8 RGB.
    Values are clamped to valid range.
    """
    lms_ = lab @ _W["oklab_to_lms"].T
    lms  = lms_ ** 3

    rgb = _linear_to_srgb(np.clip(lms @ _W["lms_to_rgb"].T, 0.0, 1.0))
    return (rgb * 255.0 + 0.5).astype(np.uint8)


# ---------------------------------------------------------------------------
# K-means (pure numpy, no sklearn)
# ---------------------------------------------------------------------------

def _kmeans(
    pixels: np.ndarray,
    n_clusters: int,
    n_init: int = 3,
    max_iter: int = 100,
    random_state: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """
    K-means clustering with k-means++ initialisation.

    Args:
        pixels:      (N, D) float32 array of data points.
        n_clusters:  Number of clusters k.
        n_init:      Number of independent restarts; best inertia wins.
        max_iter:    Maximum iterations per run.
        random_state: Seed for reproducibility.

    Returns:
        centers: (k, D) float32 cluster centroids.
        labels:  (N,)  int32  cluster index per point.
    """
    rng = np.random.default_rng(random_state)
    N = len(pixels)

    best_inertia = np.inf
    best_centers: np.ndarray | None = None
    best_labels:  np.ndarray | None = None

    for _ in range(n_init):
        # --- k-means++ init ---
        first = int(rng.integers(N))
        chosen = [first]

        for _ in range(1, n_clusters):
            # Distance from each point to its nearest chosen center
            dists = np.min(
                np.sum((pixels[:, None, :] - pixels[chosen][None, :, :]) ** 2, axis=2),
                axis=1,
            )
            probs = dists / dists.sum()
            chosen.append(int(rng.choice(N, p=probs)))

        centers = pixels[chosen].copy()

        # --- Lloyd iterations ---
        labels = np.empty(N, dtype=np.int32)
        for _ in range(max_iter):
            # Assignment step: (N, k) squared distances
            dists_sq = np.sum(
                (pixels[:, None, :] - centers[None, :, :]) ** 2, axis=2
            )
            new_labels = np.argmin(dists_sq, axis=1).astype(np.int32)

            if np.array_equal(new_labels, labels):
                break
            labels = new_labels

            # Update step
            for k in range(n_clusters):
                members = pixels[labels == k]
                if len(members):
                    centers[k] = members.mean(axis=0)
                # Empty cluster: leave centroid unchanged (rare with k-means++)

        inertia = float(np.sum((pixels - centers[labels]) ** 2))
        if inertia < best_inertia:
            best_inertia = inertia
            best_centers = centers.copy()
            best_labels  = labels.copy()

    return best_centers, best_labels  # type: ignore[return-value]


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
    ) -> tuple[Palette, str]:
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
            A tuple of (Palette, method) where method is 'embedded' or 'kmeans'.
            Palette has (n_colors + 1) entries, index 0 = bg_color.
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

        if color_space not in self.VALID_COLOR_SPACES:
            raise ValueError(
                f"color_space must be one of {self.VALID_COLOR_SPACES}, got {color_space!r}"
            )

        max_sprite_colors = Palette.MAX_COLORS - 1  # 15
        if n_colors < 1 or n_colors > max_sprite_colors:
            raise ValueError(f"n_colors must be 1–{max_sprite_colors}, got {n_colors}")

        transparent_color = self._parse_hex(bg_color)
        transparent_rgb   = np.array(
            [transparent_color.r, transparent_color.g, transparent_color.b],
            dtype=np.float32,
        )

        img = Image.open(path)

        # --- Fast path: embedded 4bpp palette (≤16 colors) ---
        embedded = self._extract_embedded_palette(img, transparent_color, name or path.stem)
        if embedded is not None:
            return embedded, "embedded"

        # --- Slow path: k-means clustering ---
        img    = img.convert("RGBA")
        pixels = np.array(img)       # (H, W, 4)
        alpha  = pixels[:, :, 3]
        rgb    = pixels[:, :, :3]

        # Collect fully opaque pixels, excluding the transparent color
        opaque_mask    = alpha.flatten() >= 255
        flat_rgb       = rgb.reshape(-1, 3)
        opaque_pixels  = flat_rgb[opaque_mask].astype(np.float32)

        non_transparent_mask = ~np.all(opaque_pixels == transparent_rgb, axis=1)
        sprite_pixels_rgb    = opaque_pixels[non_transparent_mask].astype(np.uint8)

        if len(sprite_pixels_rgb) == 0:
            logging.warning("Image has no sprite pixels — returning palette with transparent only")
            return Palette(name=name or path.stem, colors=[transparent_color]), "kmeans"

        # Convert to clustering space
        if color_space == "oklab":
            cluster_pixels = rgb_to_oklab(sprite_pixels_rgb)
        else:
            cluster_pixels = sprite_pixels_rgb.astype(np.float32)

        unique_colors   = len(np.unique(sprite_pixels_rgb, axis=0))
        actual_clusters = min(n_colors, unique_colors)

        centers, labels = _kmeans(
            cluster_pixels,
            n_clusters=actual_clusters,
            random_state=self.random_state,
        )

        # Convert centroids back to uint8 RGB
        if color_space == "oklab":
            centers_rgb = oklab_to_rgb(centers.astype(np.float32))
        else:
            centers_rgb = np.clip(centers, 0, 255).astype(np.uint8)

        # Sort by cluster size (most-used color first)
        cluster_sizes = np.bincount(labels, minlength=actual_clusters)
        order         = np.argsort(-cluster_sizes)
        sorted_centers = centers_rgb[order]

        colors = [transparent_color] + [
            Color(int(c[0]), int(c[1]), int(c[2])) for c in sorted_centers
        ]

        palette = Palette(name=name or path.stem, colors=colors)
        logging.info(
            f"Extracted {len(colors)} colors from '{path.name}' via k-means "
            f"(space={color_space}, transparent={bg_color}, "
            f"{len(sprite_pixels_rgb)} sprite pixels, {actual_clusters} clusters)"
        )
        return palette, "kmeans"

    def _extract_embedded_palette(
        self,
        img: Image.Image,
        transparent_color: Color,
        name: str,
    ) -> Palette | None:
        """
        Extract the embedded palette from a paletted PNG (mode 'P') if it has
        ≤16 colors (4bpp). Returns None if the image is not 4bpp-paletted,
        falling through to k-means.

        The transparent index (from img.info['transparency']) is always placed
        in slot 0, replaced by bg_color. All other entries preserve their
        original palette order.
        """
        if img.mode != "P":
            return None

        indices = np.array(img)                  # (H, W) uint8 palette indices
        used_indices = np.unique(indices)

        if used_indices.max() > 15:
            logging.info(
                f"'{name}': paletted PNG has {used_indices.max() + 1} colors — "
                "falling back to k-means"
            )
            return None

        raw = img.getpalette()                   # flat [R,G,B, ...] × up to 256
        pal = np.array(raw, dtype=np.uint8).reshape(-1, 3)

        transparent_index = img.info.get("transparency")

        # Build colors in index order; slot 0 = transparent_color
        colors: list[Color] = [transparent_color]
        for idx in used_indices:
            if isinstance(transparent_index, int) and idx == transparent_index:
                continue                         # skip — already in slot 0
            r, g, b = int(pal[idx][0]), int(pal[idx][1]), int(pal[idx][2])
            if r == transparent_color.r and g == transparent_color.g and b == transparent_color.b:
                continue                         # same color as bg, skip duplicate
            colors.append(Color(r, g, b))

        logging.info(
            f"Extracted {len(colors)} colors from '{name}' via embedded palette "
            f"(transparent index={transparent_index})"
        )
        return Palette(name=name, colors=colors)

    def extract_batch(
        self,
        image_paths: list[Path],
        n_colors: int = 15,
        bg_color: str = "#73C5A4",
        color_space: str = "oklab",
    ) -> list[tuple[Palette, str]]:
        """Extract palettes from a list of images. Returns one (Palette, method) per image."""
        results = []
        for path in image_paths:
            try:
                results.append(
                    self.extract(path, n_colors=n_colors, bg_color=bg_color, color_space=color_space)
                )
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