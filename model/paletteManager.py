# model/paletteManager.py
from typing import List, Dict, Optional
import os
import logging
from PyQt5.QtGui import QColor

class PaletteManager:
    """Manages palette loading and configuration with proper error handling and type safety."""
    
    def __init__(self, _config: Dict):
        self.config = _config
        self.palettes: List[Dict] = []
        self.num_palettes = self.calculate_num_palettes()
        self._load_palettes()

    def calculate_num_palettes(self) -> int:
        """Determine maximum number of palettes based on configuration."""
        try:
            if self.config.get('palettes', {}).get('more_colors', False):
                return len(self._find_palette_files())
            return 4
        except KeyError as e:
            logging.error(f"Configuration error: {e}")
            return 4

    def _find_palette_files(self) -> List[str]:
        """Locate valid palette files in the palette directory."""
        palette_dir = os.path.join(os.path.dirname(__file__), "palettes")
        try:
            return [
                f for f in os.listdir(palette_dir)
                if f.endswith('.pal') and os.path.isfile(os.path.join(palette_dir, f))
            ]
        except FileNotFoundError:
            logging.error(f"Palette directory not found: {palette_dir}")
            return []

    def _load_palettes(self) -> None:
        """Load and validate palettes from disk based on configuration."""
        palette_dir = os.path.join(os.getcwd(), "palettes")
        if not os.path.exists(palette_dir):
            logging.critical(f"Missing palette directory: {palette_dir}")
            return

        npc_filter = self._create_npc_filter()
        palette_files = sorted(f for f in os.listdir(palette_dir) if f.endswith(".pal"))

        for filename in palette_files:
            if npc_filter and filename not in npc_filter:
                continue
            self._load_palette_file(palette_dir, filename)

    def _create_npc_filter(self) -> Optional[List[str]]:
        """Create filename filter based on NPC priority setting."""
        if not self.config.get('palettes', {}).get('npc_priority', False):
            return None
        return {f"npc_{i}.pal" for i in range(1, 5)}

    def _load_palette_file(self, directory: str, filename: str) -> None:
        """Load and validate a single palette file."""
        try:
            with open(os.path.join(directory, filename), 'r') as f:
                lines = [line.strip() for line in f if line.strip()]

            if not self._validate_palette_header(lines):
                return

            color_count = int(lines[2])
            colors = self._parse_colors(lines[3:3+color_count])
            
            if colors:
                self.palettes.append({
                    'name': filename[:-4],
                    'colors': colors,
                    'transparent': colors[0]
                })

        except Exception as e:
            logging.error(f"Error loading palette {filename}: {str(e)}")

    def _validate_palette_header(self, lines: List[str]) -> bool:
        """Verify palette file format validity."""
        return len(lines) >= 3 and lines[0] == "JASC-PAL" and lines[1] == "0100"

    def _parse_colors(self, color_lines: List[str]) -> List[QColor]:
        """Convert text lines to QColor objects with error handling."""
        colors = []
        for line in color_lines:
            try:
                components = list(map(int, line.split()))
                if len(components) == 3:
                    colors.append(QColor(*components))
            except ValueError:
                logging.warning(f"Invalid color format: {line}")
        return colors

    def get_active_palettes(self) -> List[Dict]:
        """Retrieve available palettes based on configuration limits."""
        return self.palettes[:self.num_palettes]
    