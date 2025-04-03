"""
PaletteManager - Handles loading and management of .pal palette files
"""

import logging
from pathlib import Path
from PyQt5.QtGui import QColor

class Palette:
    def __init__(self, name: str, colors: list[QColor]):
        self._name = name
        self._colors = colors
    
    def get_name(self) -> str:
        return self._name
    
    def get_colors(self) -> list[QColor]:
        return self._colors
    
class PaletteManager:
    """Loads and manages palettes for image conversion"""

    def __init__(self, config: dict):
        self.config = config
        self._palettes: list[Palette] = []
        self._load_palettes()

    def _load_palettes(self) -> None:
        """Load palettes based on configuration."""
        palette_dir = Path("palettes")
        if not palette_dir.exists():
            logging.error("Missing palettes directory")
            return

        more_colors = self.config.get('palettes', {}).get('more_colors', False)
        npc_priority = self.config.get('palettes', {}).get('npc_priority', False)
        
        logging.debug(f"Loading palettes with settings - more_colors: {more_colors}, npc_priority: {npc_priority}")

        palette_files = sorted(palette_dir.glob("*.pal"))
        logging.debug(f"Found {len(palette_files)} total palette files")
        logging.debug(f"Initial palette files: {[p.name for p in palette_files]}")

        # Filter files based on settings
        if npc_priority:
            palette_files = [p for p in palette_files if p.name.startswith("npc_")]
            logging.debug(f"Filtered to NPC palettes: {[p.name for p in palette_files]}")
        
        # Limit to first 4 files if more_colors is False
        if not more_colors:
            palette_files = palette_files[:4]
            logging.debug(f"Limited to first 4 palettes: {[p.name for p in palette_files]}")

        # Attempt to load each palette file
        self._palettes = []  # Clear existing palettes
        for pal_file in palette_files:
            try:
                with open(pal_file, 'r') as f:
                    lines = f.readlines()[3:]  # Skip the first 3 lines

                colors = [QColor(*map(int, line.split())) for line in lines]
                self._palettes.append(Palette(pal_file.name, colors))
                logging.debug(f"Successfully loaded palette: {pal_file.name}")

            except Exception as e:
                logging.error(f"Failed to load palette {pal_file.name}: {e}")

        self.num_palettes = len(self._palettes)
        logging.debug(f"Final palette count: {self.num_palettes}")
        logging.debug(f"Final loaded palettes: {[p.get_name() for p in self._palettes]}")
        logging.info(f"Loaded {self.num_palettes} palettes")

    def get_palettes(self) -> list[Palette]:
        """Get currently active palettes"""
        return self._palettes

    def get_palette_by_index(self, index: int) -> Palette:
        """Get palette by index"""
        return self._palettes[index]
    
    def get_palette_by_name(self, name: str) -> Palette:
        """Get palette by name"""
        return next((p for p in self._palettes if p.get_name() == name), None)