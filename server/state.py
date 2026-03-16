"""
server/state.py

Shared application state — single instance imported by all routers.
Keeps PaletteManager, ImageManager, and PaletteExtractor alive across requests.
"""

from __future__ import annotations
from pathlib import Path

from model.palette_manager import PaletteManager
from model.image_manager import ImageManager
from model.palette_extractor import PaletteExtractor


def _load_config() -> dict:
    cfg_path = Path("config.yaml")
    if cfg_path.exists():
        import yaml
        return yaml.safe_load(cfg_path.read_text()) or {}
    return {}


class AppState:
    def __init__(self):
        self.config = _load_config()
        self.palette_manager = PaletteManager(self.config)
        self.image_manager = ImageManager(self.config)
        self.extractor = PaletteExtractor()


state = AppState()