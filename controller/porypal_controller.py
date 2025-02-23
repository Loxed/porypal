"""
PoryPal Controller - Manages application logic and state
Coordinates interactions between view and model components.
"""

import logging, os

from PyQt5.QtWidgets import QFileDialog, QApplication
from PyQt5.QtGui import QImage
from PyQt5.QtCore import QObject, pyqtSlot

from view.porypal_view import PorypalView
from model.palette_manager import PaletteManager
from model.image_manager import ImageManager
from view.porypal_theme import PorypalTheme

class PorypalController(QObject):
    """
    Main application controller coordinating UI actions with business logic.
    
    Attributes:
        _config (dict): Application configuration
        _app (QApplication): Qt application instance
        _theme (PorypalTheme): Theme manager
        palette_manager (PaletteManager): Handles palette loading and management
        image_manager (ImageManager): Handles image processing and conversion
        view (PorypalView): Main application view
    
    Public Methods:
        load_image() -> None: Load and process image
        save_image() -> None: Save currently selected converted image
        toggle_theme() -> None: Switch application theme
        load_tileset() -> None: (Not implemented) Load tileset image
    """
    def __init__(self, theme: PorypalTheme, app: QApplication, config: dict):
        """Initialize controller with required dependencies."""
        super().__init__()
        
        self._config = config
        self._app = app
        self._theme = theme
        
        # Initialize managers
        self.palette_manager = PaletteManager(config)
        self.image_manager = ImageManager(config)

        # logging.debug(f'\n\npalettes loaded (%d): %s\n\n', 
        #              len(self.palette_manager.get_palettes()), 
        #              ', '.join(p.get_name() for p in self.palette_manager.get_palettes()))
        
        # Create and setup view
        self.view = PorypalView(self.palette_manager.get_palettes())
        self._connect_signals()
        
        logging.debug("Controller initialized")

    def _connect_signals(self) -> None:
        """Connect view buttons to controller methods."""
        self.view.btn_load_image.clicked.connect(self.load_image)
        self.view.btn_load_tileset.clicked.connect(self.load_tileset)
        self.view.btn_save_image.clicked.connect(self.save_image)
        self.view.btn_toggle_theme.clicked.connect(self.toggle_theme)

    def _image_file_dialog(self, save: bool = False) -> str:
        """Open image file dialog for loading or saving."""
        try:
            dialog = QFileDialog()
            if save:
                return dialog.getSaveFileName(
                    self.view,
                    "Save Image",
                    "",
                    "PNG Image (*.png)")[0]
            else:
                dialog.setFileMode(QFileDialog.ExistingFile)
                dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.gif)")
                if dialog.exec_():
                    return dialog.selectedFiles()[0]
        except Exception as e:
            logging.error(f"Image file dialog failed: {e}")
            self.view.show_error("File Dialog Error", str(e))
        return ""
    
    @pyqtSlot()
    def load_image(self) -> None:
        """Load image and process with all palettes."""
        try:
            image_path = self._image_file_dialog()
            if not image_path:
                return
                
            logging.debug(f"Loading image: {image_path}")
            
            # Load and display original image
            loaded_image = self.image_manager.load_image(image_path)
            self.view.update_original_image(loaded_image)
            
            # Process with all palettes
            results = self.image_manager.process_all_palettes(
                self.palette_manager.get_palettes()
            )
            
            # Update view with converted images
            self.view.update_dynamic_images(
                results['images'],
                results['labels'],
                self.palette_manager.get_palettes(),
                results['highlights']
            )

            self.view.show_success("Image loaded successfully!")
            
        except Exception as e:
            logging.error(f"Error loading image: {e}")
            self.view.show_error("Image Loading Error"+ str(e))

    @pyqtSlot()
    def save_image(self) -> None:
        """Save currently selected converted image with auto-generated filename."""
        try:
            # Get selected index and corresponding data
            selected_index = self.view.get_selected_index()
            if selected_index is None:
                raise ValueError("No image selected")
                
            logging.debug(f"Selected index for save: {selected_index}")
            
            # Get current image and palette
            current_image = self.image_manager.get_image_at_index(selected_index)
            current_palette = self.palette_manager.get_palette_by_index(selected_index)
            
            if not current_image:
                raise ValueError("No image data available")
                
            # Generate output path from original image path and palette name
            original_path = self.image_manager.get_current_image_path()
            if not original_path:
                raise ValueError("No original image path available")
                
            # Create output path: same directory, original_name_palettename.png
            output_dir = os.path.dirname(original_path)
            original_name = os.path.splitext(os.path.basename(original_path))[0]
            palette_name = os.path.splitext(current_palette.get_name())[0]  # Remove .pal if present
            output_filename = f"{original_name}_{palette_name}.png"
            save_path = os.path.join(output_dir, output_filename)
                
            # Save image with palette data
            if not self.image_manager.save_image(current_image, save_path, current_palette):
                raise RuntimeError("Failed to save image")
                
            # Calculate the relative path from the project's root directory
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            relative_path = os.path.relpath(save_path, project_root)
            
            logging.debug(f"Image saved successfully: {relative_path}")
            self.view.show_success(f"Image saved successfully as '{relative_path}'")

        except Exception as e:
            logging.error(f"Error saving image: {e}")
            self.view.show_error(str(e))


    @pyqtSlot()
    def toggle_theme(self) -> None:
        """Toggle application theme."""
        self._theme.toggle_theme()

    @pyqtSlot()
    def load_tileset(self) -> None:
        """Load tileset image (not implemented)."""
        logging.warning("Tileset loading not implemented")
        pass