"""
model/tileset_manager.py

Tileset loading, slicing, reordering — pure Pillow, no Qt.
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional

from PIL import Image


class TilesetManager:
    """
    Loads a spritesheet, slices it into tiles, reorders them
    according to config, and produces a processed output image.
    """

    def __init__(self, config: dict):
        self.config = config
        self._source: Optional[Image.Image] = None
        self._tiles: list[Image.Image] = []
        self._processed: Optional[Image.Image] = None

    # ---------- public ----------

    def load(self, file_path: str | Path) -> bool:
        """Load, resize, slice and arrange. Returns True on success."""
        try:
            img = Image.open(file_path).convert("RGBA")
            self._source = self._resize(img)
            self._tiles = self._extract_tiles(self._source)
            self._processed = self._arrange(self._tiles)
            logging.debug(f"Tileset loaded: {file_path} → {len(self._tiles)} tiles")
            return True
        except Exception as e:
            logging.error(f"Failed to load tileset: {e}")
            return False

    def get_tiles(self) -> list[Image.Image]:
        """Return individual tile images."""
        return self._tiles

    def get_processed(self) -> Optional[Image.Image]:
        """Return the arranged output image."""
        return self._processed

    def get_source(self) -> Optional[Image.Image]:
        """Return the (possibly resized) source image."""
        return self._source

    # ---------- pipeline steps ----------

    def _resize(self, img: Image.Image) -> Image.Image:
        cfg = self.config.get("tileset", {})
        supported = cfg.get("supported_sizes", [])

        matched = next(
            (s for s in supported if img.width == s["width"] and img.height == s["height"]),
            None,
        )
        if matched:
            target = matched["resize_to"]
        elif cfg.get("resize_tileset", False):
            target = cfg.get("resize_to", img.width)
        else:
            return img

        return img.resize((target, target), Image.NEAREST)

    def _extract_tiles(self, img: Image.Image) -> list[Image.Image]:
        cfg = self.config.get("tileset", {})
        sprite_size = cfg.get("output_sprite_size", {"width": 32, "height": 32})
        tw = sprite_size["width"]
        th = sprite_size["height"]

        tiles = []
        for y in range(0, img.height, th):
            for x in range(0, img.width, tw):
                tile = img.crop((x, y, x + tw, y + th))
                tiles.append(tile)
        return tiles

    def _arrange(self, tiles: list[Image.Image]) -> Image.Image:
        cfg = self.config.get("tileset", {})
        order = cfg.get("sprite_order", list(range(len(tiles))))
        sprite_size = cfg.get("output_sprite_size", {"width": 32, "height": 32})
        out_cfg = self.config.get("output", {})

        out_w = out_cfg.get("output_width", sprite_size["width"] * len(order))
        out_h = out_cfg.get("output_height", sprite_size["height"])

        output = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 0))
        for i, idx in enumerate(order):
            if idx < len(tiles):
                x_pos = i * sprite_size["width"]
                output.paste(tiles[idx], (x_pos, 0))
        return output