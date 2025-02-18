# model/image_converter.py
from PyQt5.QtGui import QImage, QColor
from PyQt5.QtCore import Qt
from typing import List, Tuple, Optional
import os
import logging

class ImageManager:
    """Handles image conversion using QImage and palette data."""
    
    def __init__(self, _config: dict):
        self.config = _config
        self.target_image: Optional[QImage] = None
        self.current_file_path: str = ""
        self.converted_data: List[Tuple[QImage, int]] = []
        self.best_indices: List[int] = []

    def try_load_image(self, file_path: str) -> bool:
        """Load image file into QImage with ARGB32 format."""
        self.target_image = QImage(file_path)
        if self.target_image.isNull():
            logging.error(f"Failed to load image: {file_path}")
            return False
            
        if self.target_image.format() != QImage.Format_ARGB32:
            self.target_image = self.target_image.convertToFormat(QImage.Format_ARGB32)
            
        self.current_file_path = file_path
        return True

    def convert_all(self, palettes: List[dict], max_palettes: int) -> None:
        """Convert image using all specified palettes."""
        self.converted_data.clear()
        self.best_indices.clear()
        
        if not self.target_image or not palettes:
            return

        max_colors = -1
        for idx, palette in enumerate(palettes[:max_palettes]):
            converted_img, used_colors = self.convert_to_palette(palette)
            self.converted_data.append((converted_img, used_colors))
            
            if used_colors > max_colors:
                max_colors = used_colors
                self.best_indices = [idx]
            elif used_colors == max_colors:
                self.best_indices.append(idx)

    def convert_to_palette(self, palette: dict) -> Tuple[QImage, int]:
        """Convert image to use specified palette colors."""
        colors = palette['colors']
        transparent = colors[0]
        available_colors = colors[1:] if len(colors) > 1 else []
        
        # Create indexed image with palette
        converted = QImage(self.target_image.size(), QImage.Format_Indexed8)
        color_table = [color.rgb() for color in colors]
        converted.setColorTable(color_table)
        
        used_indices = set()
        
        for y in range(self.target_image.height()):
            for x in range(self.target_image.width()):
                color = QColor(self.target_image.pixel(x, y))
                
                if color.alpha() < 255:
                    index = 0
                else:
                    index = self._find_closest_color_index(color, available_colors) + 1
                
                converted.setPixel(x, y, index)
                if index != 0:
                    used_indices.add(index)
        
        return converted, len(used_indices)

    @staticmethod
    def _find_closest_color_index(color: QColor, palette: List[QColor]) -> int:
        """Find index of closest color in palette using squared distance."""
        min_dist = float('inf')
        best_index = 0
        
        for i, pc in enumerate(palette):
            dr = color.red() - pc.red()
            dg = color.green() - pc.green()
            db = color.blue() - pc.blue()
            dist = dr*dr + dg*dg + db*db
            
            if dist < min_dist:
                min_dist = dist
                best_index = i
        
        return best_index

    def generate_output_path(self, palette_name: str) -> str:
        """Generate output path preserving original directory structure."""
        base_dir = os.path.dirname(self.current_file_path)
        base_name = os.path.splitext(os.path.basename(self.current_file_path))[0]
        return os.path.join(base_dir, f"{base_name}_{palette_name}.png")

    def save_converted_image(self, index: int, palette: dict, output_path: str = None) -> bool:
        """Save converted image with appropriate palette settings."""
        if index >= len(self.converted_data):
            return False

        output_path = output_path or self.generate_output_path(palette['name'])
        converted_img, _ = self.converted_data[index]
        
        # Ensure correct color table
        color_table = [color.rgb() for color in palette['colors']]
        converted_img.setColorTable(color_table)
        
        return converted_img.save(output_path, 'PNG', 80)