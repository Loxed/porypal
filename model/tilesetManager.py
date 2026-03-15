# model/tileset_manager.py
import os
import yaml
from PyQt5.QtGui import QPixmap, QImage, QPainter
from typing import List, Dict
from PyQt5.QtCore import Qt


class TilesetManager:
    """Handles tileset loading and processing based on configuration."""
    
    def __init__(self, _config: Dict):
        self.config = _config
        self.pixmap: Optional[QPixmap] = None
        self.sprites: List[QPixmap] = []
        self.processed_image: Optional[QImage] = None

    def load_tileset(self, file_path: str) -> bool:
        """Load and process tileset image."""
        self.pixmap = QPixmap(file_path)
        if self.pixmap.isNull():
            return False
            
        tileset_config = self.config['tileset']
        output_size = tileset_config['output_sprite_size']
        
        self._resize_tileset(tileset_config)
        self._extract_sprites(output_size)
        self._arrange_sprites()
        return True

    def _resize_tileset(self, config: Dict) -> None:
        """Resize tileset based on configuration rules."""
        matched_size = next((
            s for s in config['supported_sizes']
            if self.pixmap.width() == s['width'] and self.pixmap.height() == s['height']
        ), None)

        if matched_size:
            target_size = matched_size['resize_to']
        elif config['resize_tileset']:
            target_size = config['resize_to']
        else:
            return

        self.pixmap = self.pixmap.scaled(
            target_size, target_size,
            Qt.IgnoreAspectRatio, 
            Qt.FastTransformation
        )

    def _extract_sprites(self, sprite_size: Dict) -> None:
        """Extract individual sprites from tileset."""
        self.sprites.clear()
        width = sprite_size['width']
        height = sprite_size['height']
        
        for y in range(0, self.pixmap.height(), height):
            for x in range(0, self.pixmap.width(), width):
                sprite = self.pixmap.copy(x, y, width, height)
                if not sprite.isNull():
                    self.sprites.append(sprite)

    def _arrange_sprites(self) -> None:
        """Arrange sprites according to configured order."""
        order = self.config['tileset']['sprite_order']
        output_config = self.config['output']
        sprite_size = self.config['tileset']['output_sprite_size']
        
        output = QImage(
            output_config['output_width'],
            output_config['output_height'],
            QImage.Format_ARGB32
        )
        output.fill(Qt.transparent)
        
        painter = QPainter(output)
        for i, idx in enumerate(order):
            if idx < len(self.sprites):
                x_pos = i * sprite_size['width']
                painter.drawPixmap(x_pos, 0, self.sprites[idx])
        painter.end()
        
        self.processed_image = output