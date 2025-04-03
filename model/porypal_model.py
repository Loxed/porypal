# """
# PoryPal Main Model
# Coordinates image processing, tileset management, and palette operations.
# Acts as the central data and business logic coordinator.
# """

# from typing import Optional, List, Dict, Tuple
# from dataclasses import dataclass
# from PyQt5.QtGui import QImage
# import logging

# from model.image_manager import ImageManager
# from model.tileset_manager import TilesetManager
# from model.palette_manager import PaletteManager

# @dataclass
# class ConversionResult:
#     """Structured container for image conversion results"""
#     image: QImage
#     colors_used: int

# class PorypalMainModel:
#     """
#     Main model coordinating specialized components for image processing.
    
#     Responsibilities:
#     - Coordinates between specialized managers
#     - Maintains application state
#     - Handles data validation and processing
#     """
    
#     def __init__(self, config: Dict) -> None:
#         """
#         Initialize model with configuration and managers.
        
#         Args:
#             config: Application configuration dictionary
#         """
#         self.config = config
#         self._init_managers()
#         self._current_tileset: Optional[QImage] = None

#     def _init_managers(self) -> None:
#         """Initialize specialized manager components."""
#         try:
#             self.image_manager = ImageManager(self.config)
#             self.tileset_manager = TilesetManager(self.config)
#             self.palette_manager = PaletteManager(self.config)
#         except Exception as e:
#             logging.error(f"Failed to initialize managers: {e}")
#             raise RuntimeError("Model initialization failed")

#     def load_tileset(self, file_path: str) -> QImage:
#         """
#         Load and process a tileset image.
        
#         Args:
#             file_path: Path to tileset image file
            
#         Returns:
#             Processed tileset image
#         """
#         try:
#             self._current_tileset = self.tileset_manager.load_tileset(file_path)
#             return self._current_tileset
#         except Exception as e:
#             logging.error(f"Tileset load failed: {e}")
#             raise

#     def load_image(self, file_path: str) -> None:
#         """
#         Load target image and trigger conversion process.
        
#         Args:
#             file_path: Path to target image file
#         """
#         try:
#             self.image_manager.load_image(file_path)
#             self._process_conversions()
#         except Exception as e:
#             logging.error(f"Image load failed: {e}")
#             raise

#     def _process_conversions(self) -> None:
#         """Execute palette conversion process."""
#         active_palettes = self.palette_manager.get_active_palettes()
#         if not active_palettes:
#             logging.warning("No active palettes available")
#             return
        
#         self.image_manager.convert_all(
#             palettes=active_palettes,
#             max_palettes=self.palette_manager.num_palettes
#         )

#     def get_input_image(self) -> Optional[QImage]:
#         """
#         Retrieve current input image.
        
#         Returns:
#             Current input image or None if no image loaded
#         """
#         return self.image_manager.get_input_image()

#     def get_tileset_image(self) -> Optional[QImage]:
#         """
#         Retrieve current tileset image.
        
#         Returns:
#             Current tileset image or None if no tileset loaded
#         """
#         return self._current_tileset

#     def get_conversion_results(self) -> List[ConversionResult]:
#         """
#         Retrieve current conversion results.
        
#         Returns:
#             List of conversion results with images and metadata
#         """
#         converted_images = self.image_manager.get_converted_images()
#         return [
#             ConversionResult(image=img, colors_used=count)
#             for img, count in converted_images
#         ]

#     def get_best_conversions(self) -> List[int]:
#         """
#         Retrieve indices of best conversions.
        
#         Returns:
#             List of indices for conversions using most colors
#         """
#         return self.image_manager.best_indices