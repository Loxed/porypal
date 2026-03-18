"""
server/state.py

Shared application state — single instance imported by all routers.
Keeps PaletteManager, ImageManager, and PaletteExtractor alive across requests.
"""

from __future__ import annotations

from model.palette_manager import PaletteManager
from model.image_manager import ImageManager
from model.palette_extractor import PaletteExtractor


class AppState:
    def __init__(self):
        self.palette_manager = PaletteManager()
        self.image_manager = ImageManager()
        self.extractor = PaletteExtractor()


state = AppState()