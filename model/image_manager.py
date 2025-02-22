"""
ImageManager - Specialized image processor for pixel art palette conversion.
Handles transparency detection and palette-based color mapping.
"""

from typing import List, Tuple, Optional, Dict
import os
import logging
from dataclasses import dataclass
from PyQt5.QtGui import QImage, QColor, QPainter
from PyQt5.QtCore import Qt
from PIL import Image

@dataclass
class ColorCount:
    """Track unique colors and their usage in converted images"""
    colors: set
    count: int

class ImageManager:
    """
    Manages pixel art image processing operations:
    - Loads and validates input images
    - Detects transparency in pixel art
    - Converts images to target palettes
    - Saves processed images in indexed color format
    """
    
    def __init__(self, config: Dict):
        self._config = config
        self._input_image: Optional[QImage] = None
        self._current_path: str = ""
        self._transparent_color: Optional[QColor] = None
        self.converted_images: List[Tuple[QImage, int]] = []
        self.best_indices: List[int] = []

    def load_image(self, file_path: str) -> None:
        """Load and prepare image for processing."""
        try:
            image = QImage(file_path)
            if image.isNull():
                raise ValueError(f"Failed to load image: {file_path}")
                
            # Ensure consistent format
            self._input_image = (image if image.format() == QImage.Format_ARGB32 
                               else image.convertToFormat(QImage.Format_ARGB32))
            self._current_path = file_path
            
            # Detect transparency
            self._transparent_color = self._detect_transparency()
            logging.debug(f"Detected transparent color: {self._transparent_color.rgba() if self._transparent_color else 'None'}")
            
            # Reset state
            self.converted_images = []
            self.best_indices = []
            
        except Exception as e:
            logging.error(f"Image load failed: {e}")
            raise

    def _detect_transparency(self) -> Optional[QColor]:
        """
        Detect transparency in pixel art using two methods:
        1. Alpha channel transparency
        2. Corner color analysis
        """
        if not self._input_image or self._input_image.isNull():
            return None

        width = self._input_image.width()
        height = self._input_image.height()

        # Check for alpha transparency
        for y in range(height):
            for x in range(width):
                color = QColor(self._input_image.pixel(x, y))
                if color.alpha() < 255:
                    return QColor(0, 0, 0, 0)  # Use fully transparent

        # Check corners for consistent color
        corners = [
            QColor(self._input_image.pixel(0, 0)),
            QColor(self._input_image.pixel(width-1, 0)),
            QColor(self._input_image.pixel(0, height-1)),
            QColor(self._input_image.pixel(width-1, height-1))
        ]

        first_corner = corners[0]
        matching_corners = sum(1 for c in corners if self._colors_match(c, first_corner))
        
        if matching_corners >= 3:
            return first_corner

        return None

    def convert_all(self, palettes: List[Dict], max_palettes: int = 4) -> None:
        """Convert input image using provided palettes."""
        if not self._input_image or self._input_image.isNull():
            logging.error("No valid input image for conversion")
            return

        self.converted_images = []
        max_colors = -1
        self.best_indices = []

        for i, palette in enumerate(palettes[:max_palettes]):
            result = self._convert_to_palette(palette)
            self.converted_images.append(result)
            
            if result[1] > max_colors:
                max_colors = result[1]
                self.best_indices = [i]
            elif result[1] == max_colors:
                self.best_indices.append(i)

    def _convert_to_palette(self, palette: Dict) -> Tuple[QImage, int]:
        """Convert image to target palette colors."""
        width = self._input_image.width()
        height = self._input_image.height()
        
        result = QImage(width, height, QImage.Format_ARGB32)
        result.fill(Qt.transparent)
        
        # Setup palette colors
        palette_transparent = QColor(*palette['colors'][0])
        available_colors = [QColor(*rgb) for rgb in palette['colors'][1:]]
        unique_colors = set()
        
        painter = QPainter(result)
        try:
            for y in range(height):
                for x in range(width):
                    src_color = QColor(self._input_image.pixel(x, y))
                    
                    # Apply transparency rules
                    if (self._transparent_color and 
                        self._colors_match(src_color, self._transparent_color)):
                        target_color = palette_transparent
                    else:
                        idx = self._find_closest_color(src_color, available_colors)
                        target_color = available_colors[idx]
                    
                    painter.setPen(target_color)
                    painter.drawPoint(x, y)
                    unique_colors.add(target_color.rgb())
                    
        finally:
            painter.end()
            
        return result, len(unique_colors)

    def _colors_match(self, c1: QColor, c2: QColor) -> bool:
        """Compare colors, considering alpha for transparency."""
        if c1.alpha() < 255 or c2.alpha() < 255:
            return c1.alpha() < 255 and c2.alpha() < 255
        return c1.rgb() == c2.rgb()

    def _find_closest_color(self, target: QColor, palette: List[QColor]) -> int:
        """Find closest palette color using RGB distance."""
        min_dist = float('inf')
        best_idx = 0
        
        tr, tg, tb = target.red(), target.green(), target.blue()
        
        for i, color in enumerate(palette):
            dr = tr - color.red()
            dg = tg - color.green()
            db = tb - color.blue()
            dist = dr*dr + dg*dg + db*db
            
            if dist < min_dist:
                min_dist = dist
                best_idx = i
                if dist == 0:  # Exact match
                    break
                    
        return best_idx

    def save_image(self, image: QImage, palette: Dict, suffix: str = "_converted") -> None:
        """Save as indexed color PNG with palette."""
        if image.isNull() or not self._current_path:
            raise ValueError("Invalid image or path")

        try:
            output_path = f"{os.path.splitext(self._current_path)[0]}{suffix}.png"
            
            with Image.new("P", (image.width(), image.height())) as im:
                # Setup palette
                palette_data = []
                for rgb in palette['colors']:
                    palette_data.extend(rgb)
                # Pad to 256 colors
                palette_data.extend([0] * (768 - len(palette_data)))
                im.putpalette(palette_data)
                
                # Convert pixels
                pixels = []
                for y in range(image.height()):
                    for x in range(image.width()):
                        color = QColor(image.pixel(x, y))
                        idx = self._find_closest_color(
                            color,
                            [QColor(*rgb) for rgb in palette['colors']]
                        )
                        pixels.append(idx)
                
                im.putdata(pixels)
                im.info["transparency"] = 0
                im.save(output_path, format="PNG", bits=4, optimize=True)
            
            logging.info(f"Saved to: {output_path}")
            
        except Exception as e:
            logging.error(f"Save failed: {e}")
            raise

    # Getter methods
    def get_input_image(self) -> Optional[QImage]:
        return self._input_image

    def get_converted_images(self) -> List[Tuple[QImage, int]]:
        return self.converted_images

    def get_best_indices(self) -> List[int]:
        return self.best_indices