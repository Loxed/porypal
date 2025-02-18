from PyQt5.QtWidgets import QFileDialog, QGridLayout, QLabel, QGraphicsView, QGraphicsScene, QGraphicsView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter
from model.porypalMainModel import PorypalMainModel
from view.porypalView import porypalMainView
from typing import Optional, Tuple
import logging

class PorypalMainController:
    """Coordinates interactions between view components and data model."""
    
    DEBUG = True  # Class-level configuration constant
    
    def __init__(self, theme_controller, app, config):
        self.config = config
        self.model = PorypalMainModel(self.config)
        self.view = porypalMainView() # Main application view instance
        self._theme = theme_controller # Theme controller instance
        self._configure_logging() # Set up basic logging configuration
        self._connect_signals() # Connect UI signals to controller methods

        
    def _configure_logging(self) -> None:
        """Set up basic logging configuration based on debug mode."""
        level = logging.DEBUG if self.DEBUG else logging.INFO
        logging.basicConfig(format='%(message)s', level=level)

    # --- Signal Handlers --- #
    def _connect_signals(self) -> None:
        """Connect UI signals to controller methods using a clean mapping."""
        signal_map = {
            self.view.btn_target.clicked: self.load_image,
            self.view.btn_tileset.clicked: self.load_tileset,
            self.view.btn_save.clicked: self.save_converted_image,
            self.view.btn_toggle_theme.clicked: self.toggle_theme
        }
        for signal, handler in signal_map.items():
            signal.connect(handler)

    def file_dialog_window(self, title: str, filter: str) -> Optional[str]:
        """Show file dialog and return selected path."""
        path, _ = QFileDialog.getOpenFileName(
            parent=self.view,
            caption=title,
            filter=filter
        )
        return path if path else None

    # --- Controller Methods --- #

    # Load an image and process it, then display the result
    def load_image(self) -> None:
        """Load and process target conversion image."""
        logging.debug("Initiating target image load")
        if path := self.file_dialog_window("Open Target Sprite", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"):
            self.view.update_preview(self.model.load_image(path))
            self.convert_img_to_pal_imgs()
    
    # Open a tileset
    def load_tileset(self) -> None:
        """Load and process tileset image."""
        logging.debug("Initiating tileset load")
        if path := self.file_dialog_window("Select Tileset Image", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"):
            self.model.load_tileset(path)
            self.view.update_preview(self.model.load_image)


    # Convert image based on the available palettes and display all results
    def convert_img_to_pal_imgs(self) -> None:
        """Convert image using all active palettes and display results."""
        # Get available palettes from manager
        active_palettes = self.model.palette_manager.get_active_palettes()
        
        if not active_palettes:
            logging.warning("No palettes available for conversion")
            self.view.show_error("Conversion Error", "No valid palettes loaded")
            return

        # Perform conversion using all palettes
        self.model.image_manager.convert_all(
            palettes=active_palettes,
            max_palettes=self.model.palette_manager.num_palettes
        )

        # Extract results for display
        converted_images = [img for img, _ in self.model.image_manager.converted_data]
        palette_labels = [palette['name'] for palette in active_palettes]

        # Update UI with conversions
        self.view.update_converted_images(converted_images, palette_labels)
        
        # Highlight best matches if available
        if self.model.image_manager.best_indices:
            self.model.image_manager.convert_to_palette(active_palettes[self.model.image_manager.best_indices[0]])
    
    # Save converted image
    def save_converted_image(self) -> None:
        """Save currently selected converted image."""
        # if not self.view.selected_index:
        #     logging.warning("No conversion selected for saving")
        #     return

        # selected_idx = self.view.selected_index
        # output_path = self.model.generate_output_path(
        #     self.model.palettes[selected_idx]['name']
        # )
        # self.model.save_converted_image(
        #     self.model.converted_data[selected_idx],
        #     self.model.palettes[selected_idx],
        #     output_path
        # )

    # Toggle the theme
    def toggle_theme(self) -> None:
        """Switch application color theme."""
        self._theme.toggle_theme()
        logging.debug(f"Theme toggled to {'dark' if self._theme.is_dark_theme else 'light'} mode")