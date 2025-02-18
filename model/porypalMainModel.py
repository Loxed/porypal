# model/porypalMainModel.py
from model.ImageManager import ImageManager
from model.tilesetManager import TilesetManager
from model.paletteManager import PaletteManager

from PyQt5.QtGui import QImage

class PorypalMainModel:
    """Main model coordinating between specialized components."""
    
    def __init__(self, _config: dict) -> None:
        self.config = _config
        self.image_manager = ImageManager(self.config)
        self.tileset_manager = TilesetManager(self.config)
        self.palette_manager = PaletteManager(self.config)  


    def load_tileset(self, file_path: str) -> QImage:
        return self.tileset_manager.load_tileset(file_path)
    
    def load_image(self, file_path: str) -> QImage:
        return self.image_manager.target_image if self.image_manager.try_load_image(file_path) else None
