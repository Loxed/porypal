"""
PoryPal Controller - Manages application logic and state
Coordinates interactions between view and model components.
"""

import logging

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
    Handles user interactions and maintains application state.
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

        logging.debug(f'\n\npalettes loaded (%d): %s\n\n', len(self.palette_manager.get_palettes()), ', '.join(p.get_name() for p in self.palette_manager.get_palettes()))
        
        # Create and setup view
        self.view = PorypalView(self.palette_manager.get_palettes())
        self._connect_signals()
        
        # Track state
        logging.debug("Controller initialized")

    def _connect_signals(self) -> None:
        """Connect view buttons to controller methods."""
        self.view.btn_load_image.clicked.connect(self.load_image)
        self.view.btn_load_tileset.clicked.connect(self.load_tileset)
        self.view.btn_save_image.clicked.connect(self.save_image)
        self.view.btn_toggle_theme.clicked.connect(self.toggle_theme)

    def _image_file_dialog(self) -> str:
        """Open image selection file dialog and return selected image path to load."""
        try:
            dialog = QFileDialog()
            dialog.setFileMode(QFileDialog.ExistingFile)
            dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.gif)")
            if dialog.exec_():
                return dialog.selectedFiles()[0]
        except Exception as e:
            logging.error(f"Image file dialog failed: {e}")
        raise RuntimeError("Image file dialog failed")
    
    @pyqtSlot()
    def load_image(self) -> None:
        """Load image from file and trigger conversion process."""
        image_path = self._image_file_dialog()
        if image_path:
            logging.debug(f"Loading image: {image_path}")
            self.view.update_original_image(QImage(image_path))

    @pyqtSlot()
    def toggle_theme(self) -> None:
        self._theme.toggle_theme()

    @pyqtSlot()
    def load_tileset(self) -> None:
        pass

    @pyqtSlot()
    def save_image(self) -> None:
        pass