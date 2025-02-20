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
        return self.name
    
    def get_colors(self) -> list[QColor]:
        return self.colors
    
class PaletteManager:
    """Loads and manages palettes for image conversion"""

    def __init__(self, config: dict):
        self.config = config
        self._palettes: list[Palette] = []  # Fixed the initialization
        self._load_palettes()

    def _load_palettes(self) -> None:
        """Load palettes based on configuration"""
        palette_dir = Path("palettes")
        if not palette_dir.exists():
            logging.error("Missing palettes directory")
            return

        # Get config settings
        more_colors = self.config.get('palettes', {}).get('more_colors', False)
        npc_priority = self.config.get('palettes', {}).get('npc_priority', False)

        # Load appropriate palettes
        for pal_file in sorted(palette_dir.glob("*.pal")):
            # Skip non-NPC palettes if configured
            if not more_colors and npc_priority:
                if not pal_file.name.startswith("npc_"):
                    continue

            try:
                # Open palette file 
                with open(pal_file, 'r') as f:
                    lines = f.readlines()

                # Skip first 3 lines
                lines = lines[3:]

                # Get every color (r, g, b) into QColor list
                colors = []
                for line in lines:
                    r, g, b = line.split()
                    colors.append(QColor(int(r), int(g), int(b)))

                # Create palette object and append to the list
                self._palettes.append(Palette(pal_file.name, colors))  # Fixed append

            except Exception as e:
                logging.error(f"Failed to load palette {pal_file.name}: {e}")

        # Set number of active palettes
        self.num_palettes = (len(self._palettes) if more_colors else 
                           min(4, len(self._palettes)))

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
