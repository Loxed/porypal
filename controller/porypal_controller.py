# controller/porypal_controller.py
import logging, os

from PyQt5.QtWidgets import QFileDialog, QApplication, QPushButton
from PyQt5.QtGui import QImage
from PyQt5.QtCore import QObject, pyqtSlot

from view.porypal_view import PorypalView
from model.palette_manager import PaletteManager
from model.image_manager import ImageManager
from view.porypal_theme import PorypalTheme
from controller.tileset_editor_controller import TilesetEditorController
from controller.palette_automation_controller import PaletteAutomationController
from view.palette_automation_view import PaletteAutomationView

class PorypalController(QObject):
    """
    Controller for the PoryPal application, handling user interactions, 
    managing data between model and view, and coordinating application logic.
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

        # Create and setup view
        self.view = PorypalView(self, self.palette_manager.get_palettes())
        self._connect_signals()
        
        logging.info("Controller initialized")

    def _connect_signals(self) -> None:
        """Connect view buttons to controller methods."""
        self.view.btn_load_image.clicked.connect(self.load_image)
        self.view.btn_load_tileset.clicked.connect(self.load_tileset)
        self.view.btn_save_image.clicked.connect(self.save_image)
        self.view.btn_extract_palette.clicked.connect(self.extract_palette)
        self.view.btn_toggle_theme.clicked.connect(self.toggle_theme)
        self.view.btn_automate.clicked.connect(self.open_automation)

    def _image_file_dialog(self, save: bool = False) -> str:
        """Open image file dialog for loading or saving."""
        dialog = QFileDialog()
        if save:
            return dialog.getSaveFileName(
                self.view, "Save Image", "", "PNG Image (*.png)")[0]
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.gif)")
        if dialog.exec_():
            return dialog.selectedFiles()[0]
        return ""
    
    # ------------ LOAD IMAGE ------------ #
    @pyqtSlot()
    def load_image(self) -> None:
        """Load image and process with all palettes."""
        image_path = self._image_file_dialog()
        if not image_path:
            return

        try:
            loaded_image = self.image_manager.load_image(image_path)
            self.view.update_original_image(loaded_image)

            results = self.image_manager.process_all_palettes(
                self.palette_manager.get_palettes()
            )

            self.view.update_dynamic_images(
                results['images'],
                results['labels'],
                self.palette_manager.get_palettes(),
                results['highlights']
            )

            self.view.btn_save_image.setEnabled(True)
            self.view.btn_extract_palette.setEnabled(True)

            self.view.notification.show_success("Image loaded successfully!")

        except Exception as e:
            logging.error(f"Error loading image: {e}")
            self.view.notification.show_error(f"Image Loading Error: {e}")

    # ------------ SAVE IMAGE ------------ #
    @pyqtSlot()
    def save_image(self) -> None:
        """Save currently selected converted image with auto-generated filename."""
        try:
            # Get selected index and corresponding data
            selected_index = self.view.get_selected_index()
            if selected_index is None:
                raise ValueError("No image selected")
            
            # Get current image and palette
            current_image = self.image_manager.get_image_at_index(selected_index)
            current_palette = self.palette_manager.get_palette_by_index(selected_index)
            
            # Generate output path from original image path and palette name
            original_path = self.image_manager.get_current_image_path()
            output_dir = os.path.dirname(original_path)
            original_name = os.path.splitext(os.path.basename(original_path))[0]
            palette_name = os.path.splitext(current_palette.get_name())[0]  # Remove .pal if present
            output_filename = f"{original_name}_{palette_name}.png"
            save_path = os.path.join(output_dir, output_filename)
            
            # Save image with palette data
            if not self.image_manager.save_image(current_image, save_path, current_palette):
                raise RuntimeError("Failed to save image")
            
            logging.debug(f"Image saved successfully: {save_path}")
            self.view.notification.show_success(f"Image saved successfully as '{save_path}'")

        except Exception as e:
            logging.error(f"Error saving image: {e}")
            self.view.notification.show_error(str(e))


    # ------------ PALETTE EXTRACTION ------------ #
    @pyqtSlot()
    def extract_palette(self) -> None:
        """Extract palette from the input image."""
        self.image_manager.extract_palette()
        self.view.notification.show_success("Palette extracted successfully!")

    # ------------ THEME TOGGLE ------------ #
    @pyqtSlot()
    def toggle_theme(self) -> None:
        """Toggle application theme."""
        self._theme.toggle_theme()

    # ------------ TILESET LOADING ------------ #

    @pyqtSlot()
    def load_tileset(self) -> None:
        """Open the tileset editor by replacing the current view with the tileset editor view."""
        try:
            # Store reference to the main view for restoration later
            self._main_view = self.view
            
            # Create tileset editor controller
            self.tileset_editor = TilesetEditorController(self)
            
            # Set up view swapping mechanism
            self.tileset_editor.view.btn_back = QPushButton("↩️ Return to Main View")
            self.tileset_editor.view.btn_back.setMinimumSize(136, 40)  # Set minimum size to 136x40px
            self.tileset_editor.view.btn_back.clicked.connect(self.restore_main_view)
            self.tileset_editor.view.toolbar_layout.addWidget(self.tileset_editor.view.btn_back)
            
            # Replace the current central widget with the tileset editor view
            self._app.setActiveWindow(self.tileset_editor.view)
            self._main_view.hide()
            self.tileset_editor.view.show()
            
            logging.info("Switched to tileset editor view")
        except Exception as e:
            logging.error(f"Error opening tileset editor: {e}")
            self.view.notification.show_error(f"Failed to open tileset editor: {e}")

    # Add a new method to restore the main view
    @pyqtSlot()
    def restore_main_view(self) -> None:
        """Restore the main view after closing the tileset editor."""
        try:
            if hasattr(self, 'tileset_editor') and self.tileset_editor:
                self.tileset_editor.view.hide()
                
            if hasattr(self, '_main_view') and self._main_view:
                self._main_view.show()
                self._app.setActiveWindow(self._main_view)
                
            logging.info("Restored main view")
        except Exception as e:
            logging.error(f"Error restoring main view: {e}")
            self.view.notification.show_error(f"Failed to restore main view: {e}")

    # ------------ AUTOMATION ------------ #
    
    @pyqtSlot()
    def open_automation(self) -> None:
        """Open the palette automation view."""
        try:
            # Create automation controller and view
            self.automation_controller = PaletteAutomationController(self)
            self.automation_view = PaletteAutomationView(self.automation_controller)
            
            # Set the view in the controller
            self.automation_controller.set_view(self.automation_view)
            
            # Show the automation view as a separate window
            self.automation_view.show()
            
            logging.info("Opened automation view")
        except Exception as e:
            logging.error(f"Error opening automation view: {e}")
            self.view.notification.show_error(f"Failed to open automation view: {e}")