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
    def __init__(self, config: dict):
        self.config = config
        self._source: Optional[Image.Image] = None
        self._source_palette: Optional[list[int]] = None  # raw palette from original "P" image
        self._source_transparency: int | bytes | None = None
        self._was_4bpp: bool = False
        self._tiles: list[Image.Image] = []
        self._processed: Optional[Image.Image] = None

    def load(self, file_path: str | Path) -> bool:
        try:
            # Open once to capture palette metadata before any conversion
            original = Image.open(file_path)
            self._was_4bpp = False
            self._source_palette = None
            self._source_transparency = None
            if original.mode == "P":
                import numpy as np
                arr = np.array(original)
                n_used = int(arr.max()) + 1 if arr.size > 0 else 0
                if n_used <= 16:
                    self._was_4bpp = True
                    self._source_palette = original.getpalette()  # flat [R,G,B, ...] × 256
                    self._source_transparency = original.info.get("transparency")

            if self._was_4bpp:
                img = original.copy()
            else:
                img = original.convert("RGBA")
            self._source = self._resize(img)
            self._tiles = self._extract_tiles(self._source)
            self._processed = self._arrange(self._tiles)
            logging.debug(f"Tileset loaded: {file_path} → {len(self._tiles)} tiles (4bpp={self._was_4bpp})")
            return True
        except Exception as e:
            logging.error(f"Failed to load tileset: {e}")
            return False

    def get_tiles(self) -> list[Image.Image]:
        return self._tiles

    def get_processed(self) -> Optional[Image.Image]:
        return self._processed

    def get_source(self) -> Optional[Image.Image]:
        return self._source

    def was_4bpp(self) -> bool:
        return self._was_4bpp

    def get_source_palette(self) -> Optional[list[int]]:
        return self._source_palette

    def get_source_transparency(self) -> int | bytes | None:
        return self._source_transparency

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
        input_size = cfg.get("input_sprite_size") or cfg.get(
            "output_sprite_size", {"width": 32, "height": 32}
        )
        output_size = cfg.get("output_sprite_size", input_size)
        in_tw = input_size["width"]
        in_th = input_size["height"]
        out_tw = output_size["width"]
        out_th = output_size["height"]

        tiles = []
        for y in range(0, img.height, in_th):
            for x in range(0, img.width, in_tw):
                tile = img.crop((x, y, x + in_tw, y + in_th))
                if tile.size != (out_tw, out_th):
                    tile = tile.resize((out_tw, out_th), Image.NEAREST)
                tiles.append(tile)
        return tiles

    def _arrange(self, tiles: list[Image.Image]) -> Image.Image:
        cfg = self.config.get("tileset", {})
        order = cfg.get("sprite_order", list(range(len(tiles))))
        sprite_size = cfg.get("output_sprite_size", {"width": 32, "height": 32})
        out_cfg = self.config.get("output", {})

        out_w = out_cfg.get("output_width", sprite_size["width"] * len(order))
        out_h = out_cfg.get("output_height", sprite_size["height"])

        if self._was_4bpp and self._source_palette:
            output = Image.new("P", (out_w, out_h), 0)
            output.putpalette(self._source_palette)
            if self._source_transparency is not None:
                output.info["transparency"] = self._source_transparency
        else:
            output = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 0))

        cols = max(1, out_w // sprite_size["width"])
        for i, idx in enumerate(order):
            if idx is None or idx < 0 or idx >= len(tiles):
                continue
            x_pos = (i % cols) * sprite_size["width"]
            y_pos = (i // cols) * sprite_size["height"]
            output.paste(tiles[idx], (x_pos, y_pos))
        return output
