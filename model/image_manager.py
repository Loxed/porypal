from PyQt5.QtGui import QImage, QColor
from PyQt5.QtWidgets import QMessageBox
from pathlib import Path
import logging, os
from PIL import Image

from model.palette_manager import Palette

class ImageManager:
    """
    Handles image processing and palette conversion operations.
    
    Constants:
        SUPPORTED_FORMATS (list): ['.png', '.jpg', '.jpeg', '.gif', '.bmp']
    
    Attributes:
        config (dict): Configuration settings
        _original_image (QImage): Currently loaded image
        _color_distance_cache (dict): Cache for color distance calculations
        _transparent_color (QColor): Detected transparent color of current image
        converted_images (list): Stores converted images and their metrics
    """
    
    SUPPORTED_FORMATS = ['.png', '.jpg', '.jpeg', '.gif', '.bmp']
    
    def __init__(self, config: dict):
        self.config = config
        self._current_image_path = None
        self._original_image = None
        self._color_distance_cache = {}
        self._transparent_color = None
        self.converted_images = []
        
    # ------------ LOAD IMAGE ------------ #
    def load_image(self, image_path: str) -> QImage:
        """Load image and detect transparent color"""
        self._current_image_path = Path(image_path)
        if self._current_image_path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported image format. Supported formats: {', '.join(self.SUPPORTED_FORMATS)}")
            
        # Load image in its original format
        image = QImage(image_path)
        if image.isNull():
            raise ValueError("Failed to load image")
            
        logging.debug(f"Loaded image: {image_path} ({image.width()}x{image.height()})")
        
        self._original_image = image
        self._detect_transparent_color(image)
        return image
        
    def _detect_transparent_color(self, image: QImage) -> None:
        """Detect transparent color using multiple methods"""
        # First pass: look for any pixel with alpha < 255
        for y in range(image.height()):
            for x in range(image.width()):
                color = QColor(image.pixel(x, y))
                if color.alpha() < 255:
                    # Store the exact RGB values found
                    self._transparent_color = color
                    logging.debug(f"Found transparent color (alpha): RGB({color.red()}, {color.green()}, {color.blue()})")
                    return

        # Second pass: edge detection if no transparency found
        edges = []
        # Get colors from edges
        for x in range(image.width()):
            edges.append(QColor(image.pixel(x, 0)))
            edges.append(QColor(image.pixel(x, image.height()-1)))
        for y in range(image.height()):
            edges.append(QColor(image.pixel(0, y)))
            edges.append(QColor(image.pixel(image.width()-1, y)))
            
        # Find most common edge color
        color_count = {}
        for color in edges:
            # Use the exact RGB values as key
            rgb = (color.red(), color.green(), color.blue())
            color_count[rgb] = color_count.get(rgb, 0) + 1
            
        if color_count:
            most_common_rgb = max(color_count.items(), key=lambda x: x[1])[0]
            self._transparent_color = QColor(*most_common_rgb)
            logging.debug(f"Found transparent color (edges): RGB{most_common_rgb}")
        
    # ------------ PROCESS IMAGE ------------ #
    def process_all_palettes(self, palettes: list[Palette]) -> dict:
        """Process image with all palettes and return results dictionary"""
        if not self._original_image:
            raise ValueError("No image loaded")
            
        results = {
            'images': [],
            'labels': [],
            'highlights': {'best_indices': []}
        }
        
        max_colors = -1
        best_indices = []
        
        for i, palette in enumerate(palettes):
            converted, used_colors = self._convert_to_palette(self._original_image, palette)
            results['images'].append(converted)
            results['labels'].append(f"{palette.get_name()}\n({used_colors} colors used)")
            
            # Track best conversions based on color usage
            if used_colors > max_colors:
                max_colors = used_colors
                best_indices = [i]
            elif used_colors == max_colors:
                best_indices.append(i)
                
        results['highlights']['best_indices'] = best_indices

        self.converted_images = results['images']
        return results
        
    def _convert_to_palette(self, image: QImage, palette: Palette) -> tuple[QImage, int]:
        """Convert image using palette colors"""
        width = image.width()
        height = image.height()
        converted = QImage(width, height, QImage.Format_RGB32)
        
        # Get palette colors
        transparent_color = palette.get_colors()[0]
        available_colors = palette.get_colors()[1:] if len(palette.get_colors()) > 1 else []
        used_colors = set()
        
        for y in range(height):
            for x in range(width):
                pixel_color = image.pixelColor(x, y)
                
                if pixel_color.alpha() < 255 or pixel_color == transparent_color:
                    converted_color = transparent_color
                else:
                    if available_colors:
                        closest = min(available_colors,
                                    key=lambda c: self._color_distance(pixel_color, c))
                        converted_color = closest
                    else:
                        converted_color = pixel_color
                        
                converted.setPixelColor(x, y, converted_color)
                used_colors.add((
                    converted_color.red(),
                    converted_color.green(),
                    converted_color.blue()
                ))
                
        return converted, len(used_colors)
    
    # ------------ COLOR CONVERSION ------------ #
        
    def _find_closest_color(self, target_color: QColor, palette_colors: list[QColor]) -> QColor:
        """Find closest matching color in palette using RGB distance"""
        if not palette_colors:
            return target_color
            
        min_distance = float('inf')
        closest_color = None
        
        target_rgb = (target_color.red(), target_color.green(), target_color.blue())
        
        for color in palette_colors:
            cache_key = (target_color.rgb(), color.rgb())
            if cache_key in self._color_distance_cache:
                distance = self._color_distance_cache[cache_key]
            else:
                color_rgb = (color.red(), color.green(), color.blue())
                distance = sum((a - b) ** 2 for a, b in zip(target_rgb, color_rgb))
                self._color_distance_cache[cache_key] = distance
                
            if distance < min_distance:
                min_distance = distance
                closest_color = color
                
        return closest_color


    def _color_distance(self, c1: QColor, c2: QColor) -> int:
        """Calculate RGB distance between two colors"""
        return (c1.red() - c2.red())**2 + (c1.green() - c2.green())**2 + (c1.blue() - c2.blue())**2
     

    # ------------ SAVE IMAGE ------------ #

    def save_image(self, image: QImage, output_path: str, palette: Palette) -> bool:
        logging.debug(f"Attempting to save image. Image is None: {image is None}")
        if image is None:
            return False
        try:
            # Get palette colors in correct order
            palette_colors = palette.get_colors()
            palette_order = [(c.red(), c.green(), c.blue()) for c in palette_colors]
            color_to_index = {rgb: idx for idx, rgb in enumerate(palette_order)}

            # Convert QImage to indices
            width = image.width()
            height = image.height()
            indices = []
            for y in range(height):
                for x in range(width):
                    color = image.pixelColor(x, y)
                    rgb = (color.red(), color.green(), color.blue())
                    indices.append(color_to_index[rgb])

            # Create indexed PNG
            with Image.new("P", (width, height)) as im:
                # Set up palette data (RGB triplets)
                palette_data = []
                for color in palette_colors:
                    palette_data.extend([color.red(), color.green(), color.blue()])
                # Pad to 256 colors (768 bytes)
                palette_data.extend([0] * (768 - len(palette_data)))
                
                im.putpalette(palette_data)
                im.info["transparency"] = 0  # First color is transparent
                im.putdata(indices)
                
                # Save as 4-bit PNG
                im.save(output_path, format="PNG", bits=4, optimize=True)

            return True

        except Exception as e:
            logging.error(f"Failed to save image: {e}")
            return False

    # ------------ EXTRACT PALETTE ------------ #
    def extract_palette(self) -> None:
        """ 
        Takes the _original_ image and creates a palette (JASC-PAL) from it.
        Warns if more than 16 colors are detected.
        """
        try:
            # Convert QImage to PIL Image
            buffer = self._original_image.constBits()
            buffer.setsize(self._original_image.byteCount())
            pil_img = Image.frombytes(
                "RGBA" if self._original_image.hasAlphaChannel() else "RGB",
                (self._original_image.width(), self._original_image.height()),
                buffer,
                'raw',
                'BGRA' if self._original_image.hasAlphaChannel() else 'BGR'
            )
            
            # Convert to RGB mode
            pil_img = pil_img.convert("RGB")
            
            # Get the palette through PIL's quantization
            quantized = pil_img.convert("P", palette=Image.ADAPTIVE, colors=16)
            palette = quantized.getpalette()[:48]  # First 16 RGB triplets (16 * 3)
            
            # Convert to list of RGB tuples
            colors = [(palette[i], palette[i+1], palette[i+2]) 
                    for i in range(0, len(palette), 3)
                    if palette[i] + palette[i+1] + palette[i+2] > 0]  # Skip black/empty colors

            if len(colors) > 16:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setText(f"Image contains {len(colors)} colors. Maximum allowed is 16.")
                msg.setInformativeText("Please use an image with 16 or fewer colors.")
                msg.setWindowTitle("Too Many Colors")
                msg.exec_()
                return

            # Create palette filename using Path
            palette_name = self._current_image_path.stem + ".pal"
            palette_path = Path("palettes") / palette_name

            # Ensure palettes directory exists
            palette_path.parent.mkdir(exist_ok=True)

            # Create palette file
            with palette_path.open("w") as f:
                f.write("JASC-PAL\n0100\n16\n")
                for color in colors:
                    f.write(f"{color[0]:3} {color[1]:3} {color[2]:3}\n")

            logging.info(f"Palette created: {palette_path}")

        except Exception as e:
            logging.error(f"Error extracting palette: {e}")

    # ------------ GETTERS ------------ #

    def get_original_image(self) -> QImage:
        return self._original_image
    
    def get_image_at_index(self, index: int) -> QImage:
        logging.debug(f"Getting image at index {index}. Total images: {len(self.converted_images)}")
        if 0 <= index < len(self.converted_images):
            return self.converted_images[index]
        logging.warning(f"No image found at index {index}")
        return None

    
    def get_images(self) -> list[QImage]:
        """Get all converted images."""
        return self.converted_images
    
    def get_current_image_path(self) -> str:
        return self._current_image_path