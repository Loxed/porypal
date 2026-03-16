"""
model/palette_manager.py

Loads and manages .pal palette files. Pure Python, no Qt.
"""

from __future__ import annotations
import logging
from pathlib import Path

from model.palette import Palette


class PaletteManager:
    """Loads and manages palettes from a directory of JASC-PAL files."""

    def __init__(self, config: dict):
        self.config = config
        self._palettes: list[Palette] = []
        self._load_palettes()

    def _load_palettes(self) -> None:
        palette_dir = Path("palettes")
        if not palette_dir.exists():
            logging.error("Missing palettes directory")
            return

        more_colors = self.config.get("palettes", {}).get("more_colors", False)
        npc_priority = self.config.get("palettes", {}).get("npc_priority", False)

        palette_files = sorted(palette_dir.glob("*.pal"))

        if npc_priority:
            palette_files = [p for p in palette_files if p.name.startswith("npc_")]

        if not more_colors:
            palette_files = palette_files[:4]

        self._palettes = []
        for pal_file in palette_files:
            try:
                self._palettes.append(Palette.from_jasc_pal(pal_file))
                logging.debug(f"Loaded palette: {pal_file.name}")
            except Exception as e:
                logging.error(f"Failed to load palette {pal_file.name}: {e}")

        logging.info(f"Loaded {len(self._palettes)} palettes")

    def get_palettes(self) -> list[Palette]:
        return self._palettes

    def get_palette_by_index(self, index: int) -> Palette:
        return self._palettes[index]

    def get_palette_by_name(self, name: str) -> Palette | None:
        return next((p for p in self._palettes if p.name == name), None)

    def reload(self) -> None:
        """Reload palettes from disk — useful when user adds new .pal files."""
        self._load_palettes()
