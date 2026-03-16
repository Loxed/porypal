# __init__.py
```python
"""
PoryPal
A tool for managing and automating Pokemon game tileset and palette operations.
"""

__version__ = '2.0.0'
__author__ = 'Lox'
__license__ = 'MIT'

from . import controller
from . import view
from . import model

__all__ = [
    'controller',
    'view',
    'model'
]
```

----

# cli.py
```python
"""
cli.py

Porypal v3 CLI — palette toolchain for Gen 3 ROM hacking.

Commands:
    porypal convert   Remap a sprite to the nearest colors in a .pal file
    porypal extract   Extract a GBA palette from any sprite
    porypal batch     Apply a palette to every image in a folder
    porypal info      Inspect a .pal file

Install: pip install porypal[gui]   (GUI)
         pip install porypal        (CLI only)
"""

from __future__ import annotations
import logging
import sys
from pathlib import Path

import click
import yaml

from model.palette import Palette
from model.palette_manager import PaletteManager
from model.image_manager import ImageManager
from model.palette_extractor import PaletteExtractor


# ---------- CLI root ----------

@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging.")
def main(debug: bool):
    """Porypal — palette toolchain for Gen 3 Pokémon ROM hacking."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        format="[%(levelname)s] %(message)s",
    )


# ---------- convert ----------

@main.command()
@click.argument("image", type=click.Path(exists=True, path_type=Path))
@click.argument("palette", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None,
              help="Output path. Default: <image_stem>_<palette_stem>.png next to source.")
def convert(image: Path, palette: Path, output: Path | None):
    """Remap IMAGE pixels to the nearest colors in PALETTE (.pal file)."""
    pal = Palette.from_jasc_pal(palette)
    mgr = ImageManager(config={})
    mgr.load_image(image)
    results = mgr.process_all_palettes([pal])
    result = results[0]

    out_path = output or mgr.auto_output_path(result)
    if mgr.save_image(result, out_path):
        click.echo(f"Saved: {out_path}  ({result.colors_used} colors used)")
    else:
        click.echo("Error: failed to save image.", err=True)
        sys.exit(1)


# ---------- extract ----------

@main.command()
@click.argument("image", type=click.Path(exists=True, path_type=Path))
@click.option("-n", "--n-colors", default=16, show_default=True,
              help="Total palette size (including transparent slot). Max 16 for GBA.")
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None,
              help="Output .pal path. Default: <image_stem>.pal next to source.")
@click.option("--hex", "show_hex", is_flag=True, help="Print hex values to stdout as well.")
def extract(image: Path, n_colors: int, output: Path | None, show_hex: bool):
    """Extract a GBA-compatible palette from IMAGE using k-means clustering."""
    extractor = PaletteExtractor()
    palette = extractor.extract(image, n_colors=n_colors)

    out_path = output or image.parent / f"{image.stem}.pal"
    palette.to_jasc_pal(out_path)
    click.echo(f"Extracted {len(palette.colors)}-color palette → {out_path}")

    if show_hex:
        for i, color in enumerate(palette.colors):
            label = " (transparent)" if i == 0 else ""
            click.echo(f"  [{i:2d}] {color.to_hex()}{label}")


# ---------- batch ----------

@main.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("palette", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=None,
              help="Output directory. Default: same as input folder.")
@click.option("--report", is_flag=True, help="Print a summary table of colors used per file.")
def batch(folder: Path, palette: Path, output_dir: Path | None, report: bool):
    """Apply PALETTE to every PNG/JPG image in FOLDER."""
    pal = Palette.from_jasc_pal(palette)
    mgr = ImageManager(config={})
    out_dir = output_dir or folder
    out_dir.mkdir(parents=True, exist_ok=True)

    image_files = sorted(
        p for p in folder.iterdir()
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}
    )

    if not image_files:
        click.echo(f"No images found in {folder}")
        return

    rows = []
    for img_path in image_files:
        try:
            mgr.load_image(img_path)
            results = mgr.process_all_palettes([pal])
            result = results[0]
            out_path = out_dir / f"{img_path.stem}_{Path(palette).stem}.png"
            mgr.save_image(result, out_path)
            rows.append((img_path.name, result.colors_used, str(out_path.name)))
            click.echo(f"  ✓ {img_path.name} → {out_path.name} ({result.colors_used} colors)")
        except Exception as e:
            click.echo(f"  ✗ {img_path.name}: {e}", err=True)

    if report:
        click.echo(f"\n{'File':<30} {'Colors':>6}")
        click.echo("-" * 38)
        for name, colors, _ in rows:
            click.echo(f"{name:<30} {colors:>6}")
        click.echo(f"\nProcessed {len(rows)}/{len(image_files)} files.")


# ---------- info ----------

@main.command()
@click.argument("palette", type=click.Path(exists=True, path_type=Path))
def info(palette: Path):
    """Print details of a JASC-PAL file."""
    pal = Palette.from_jasc_pal(palette)
    click.echo(f"Palette: {pal.name}")
    click.echo(f"Colors:  {len(pal.colors)} / {Palette.MAX_COLORS}")
    click.echo(f"GBA compatible: {'yes' if pal.is_gba_compatible() else 'NO — too many colors'}")
    click.echo("")
    for i, color in enumerate(pal.colors):
        label = " ← transparent slot" if i == 0 else ""
        click.echo(f"  [{i:2d}] {color.to_hex()}  rgb({color.r}, {color.g}, {color.b}){label}")


if __name__ == "__main__":
    main()
```

----

# config.yaml
```yaml
dark_mode: dark
output:
  output_format: PNG
  output_height: 32
  output_width: 288
  transparent_bg: true
palettes:
  more_colors: false
  npc_priority: false
tileset:
  default_height: 128
  default_width: 128
  output_sprite_size:
    height: 32
    width: 32
  resize_tileset: true
  resize_to: 128
  sprite_order:
  - 0
  - 12
  - 4
  - 1
  - 3
  - 13
  - 15
  - 5
  - 7
  supported_sizes:
  - height: 256
    resize_to: 128
    width: 256
  - height: 128
    resize_to: 128
    width: 128
  - height: 512
    resize_to: 128
    width: 512
  - height: 1024
    resize_to: 128
    width: 1024
```

----

# controller/__init__.py
```python
"""
PoryPal Controller Package
This package contains the controllers for managing the PoryPal application's logic and data flow.
"""

from .automation_controller import AutomationController
from .palette_automation_controller import PaletteAutomationController
from .porypal_controller import PorypalController
from .tileset_editor_controller import TilesetEditorController

__all__ = [
    'AutomationController',
    'PaletteAutomationController',
    'PorypalController',
    'TilesetEditorController'
]

__version__ = '2.0.0'
```

----

# controller/automation_controller.py
```python
# controller/automation_controller.py
import os
import json
import glob
import logging
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QImage, QPen, QBrush, QColor, QPainter
from PyQt5.QtCore import Qt

class AutomationController:
    """
    Controller for the automation feature that handles the automation process
    and communication between the view and the tileset editor.
    """
    
    def __init__(self, tileset_editor_controller):
        """
        Initialize the automation controller.
        
        Args:
            tileset_editor_controller: The controller for the tileset editor
        """
        self.tileset_editor = tileset_editor_controller
        self.view = None
    
    def set_view(self, view):
        """
        Set the view for this controller.
        
        Args:
            view: The automation view
        """
        self.view = view
    
    def start_automation(self, input_folder, preset_file, output_folder):
        """
        Start the automation process.
        
        Args:
            input_folder: Path to the folder containing input images
            preset_file: Path to the preset file
            output_folder: Path to the output folder
        """
        try:
            # Load the preset
            with open(preset_file, 'r') as f:
                preset_config = json.load(f)
                
            # Extract preset name from file path
            preset_name = os.path.basename(preset_file)
            if preset_name.endswith(".json"):
                preset_name = preset_name[:-5]  # Remove .json extension
                
            # Get required dimensions from preset
            required_width = preset_config.get("input_width", 0)
            required_height = preset_config.get("input_height", 0)
            
            # Get supported image extensions
            image_extensions = ["*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp"]
            image_files = []
            
            for ext in image_extensions:
                image_files.extend(glob.glob(os.path.join(input_folder, ext)))
                
            if not image_files:
                QMessageBox.warning(self.view, "Warning", "No image files found in the selected folder.")
                return
                
            # Process each image
            success_count = 0
            error_count = 0
            
            for image_path in image_files:
                try:
                    # Load the image
                    temp_image = QImage(image_path)
                    
                    if temp_image.isNull():
                        logging.error(f"Failed to load image: {image_path}")
                        error_count += 1
                        continue
                        
                    # Check dimensions
                    if temp_image.width() != required_width or temp_image.height() != required_height:
                        logging.warning(f"Skipping {os.path.basename(image_path)}: Dimensions don't match. Required: {required_width}x{required_height}, Got: {temp_image.width()}x{temp_image.height()}")
                        error_count += 1
                        continue
                        
                    # Store the current state
                    original_input_image = self.tileset_editor.input_image
                    original_output_matrix = self.tileset_editor.output_matrix
                    
                    # Set the input image
                    self.tileset_editor.input_image = temp_image
                    
                    # Set spin box values from preset
                    self.tileset_editor.view.spin_tile_width.setValue(preset_config.get("tile_width", 32))
                    self.tileset_editor.view.spin_tile_height.setValue(preset_config.get("tile_height", 32))
                    self.tileset_editor.view.spin_columns.setValue(preset_config.get("columns", 1))
                    self.tileset_editor.view.spin_rows.setValue(preset_config.get("rows", 1))
                    self.tileset_editor.view.spin_scale.setValue(preset_config.get("scale", 100))
                    
                    # Apply grid and create layout
                    self.tileset_editor.apply_grid()
                    self.tileset_editor.create_output_layout()
                    
                    # Restore tile positions
                    for tile_data in preset_config.get("output_matrix", []):
                        row = tile_data.get("row", 0)
                        col = tile_data.get("col", 0)
                        original_x = tile_data.get("original_x", 0)
                        original_y = tile_data.get("original_y", 0)
                        
                        # Find the tile in the input image
                        for item in self.tileset_editor.grid_items:
                            item_pos = item.data(0)  # Get stored position
                            if item_pos == (original_x, original_y):
                                # Select this tile
                                self.tileset_editor.selected_tiles = [(original_x, original_y)]
                                item.setPen(QPen(QColor(0, 255, 0, 200)))
                                item.setBrush(QBrush(QColor(0, 255, 0, 50)))
                                
                                # Place it in the output matrix
                                self.tileset_editor.place_tile_in_output(row, col)
                                break
                    
                    # Save the output image
                    output_filename = os.path.basename(image_path)
                    output_path = os.path.join(output_folder, output_filename)
                    
                    # Get layout dimensions and scaled tile size
                    rows, cols = len(self.tileset_editor.output_matrix), len(self.tileset_editor.output_matrix[0])
                    tile_width, tile_height = self.tileset_editor.view.output_scene.tile_size
                    
                    # Create output image with the scaled dimensions
                    output_image = QImage(cols * tile_width, rows * tile_height, QImage.Format_RGBA8888)
                    output_image.fill(Qt.transparent)
                    
                    # Draw all tiles from the matrix
                    painter = QPainter(output_image)
                    for row in range(rows):
                        for col in range(cols):
                            tile_data = self.tileset_editor.output_matrix[row][col]
                            if tile_data is not None:
                                # Get the scaled tile image
                                scaled_image = tile_data['scaled_image']
                                
                                # Draw the scaled tile at its position
                                painter.drawImage(
                                    col * tile_width,
                                    row * tile_height,
                                    scaled_image
                                )
                    painter.end()
                    
                    # Save the image
                    output_image.save(output_path)
                    
                    # Restore the original state
                    self.tileset_editor.input_image = original_input_image
                    self.tileset_editor.output_matrix = original_output_matrix
                    
                    # Update the view
                    if self.tileset_editor.input_image:
                        self.tileset_editor.show_image(self.tileset_editor.input_image, self.tileset_editor.view.input_scene, self.tileset_editor.view.input_view)
                    
                    success_count += 1
                    
                except Exception as e:
                    logging.error(f"Error processing {os.path.basename(image_path)}: {e}")
                    error_count += 1
                    
            # Show results
            QMessageBox.information(
                self.view, 
                "Automation Complete", 
                f"Processed {len(image_files)} images.\n"
                f"Successfully processed: {success_count}\n"
                f"Errors/Skipped: {error_count}"
            )
            
        except Exception as e:
            logging.error(f"Failed to automate preset application: {e}")
            QMessageBox.critical(self.view, "Error", f"Failed to automate preset application: {e}")
    
    def return_to_editor(self):
        """Return to the tileset editor."""
        if self.view:
            self.view.close() ```

----

# controller/palette_automation_controller.py
```python
import os
import glob
import logging
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QImage

class PaletteAutomationController:
    """
    Controller for the palette automation feature that handles the automation process
    and communication between the view and the main palette application.
    """
    
    def __init__(self, porypal_controller):
        """
        Initialize the automation controller.
        
        Args:
            porypal_controller: The controller for the main palette application
        """
        self.porypal_controller = porypal_controller
        self.view = None
    
    def set_view(self, view):
        """
        Set the view for this controller.
        
        Args:
            view: The automation view
        """
        self.view = view
    
    def start_automation(self, input_folder, output_folder):
        """
        Start the automation process.
        
        Args:
            input_folder: Path to the folder containing input images
            output_folder: Path to the output folder
        """
        try:
            # Get supported image extensions
            image_extensions = ["*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp"]
            image_files = []
            
            for ext in image_extensions:
                image_files.extend(glob.glob(os.path.join(input_folder, ext)))
                
            if not image_files:
                QMessageBox.warning(self.view, "Warning", "No image files found in the selected folder.")
                return
                
            # Check if palettes are loaded
            palettes = self.porypal_controller.palette_manager.get_palettes()
            if not palettes:
                QMessageBox.warning(self.view, "Warning", "No palettes loaded. Please check the palettes directory.")
                return
                
            logging.info(f"Starting automation with {len(image_files)} images and {len(palettes)} palettes")
            
            # Process each image
            success_count = 0
            error_count = 0
            
            for image_path in image_files:
                try:
                    logging.info(f"Processing image: {image_path}")
                    
                    # Load the image
                    loaded_image = self.porypal_controller.image_manager.load_image(image_path)
                    
                    if loaded_image is None:
                        logging.error(f"Failed to load image: {image_path}")
                        error_count += 1
                        continue
                    
                    logging.info(f"Image loaded successfully: {image_path}")
                    
                    # Process with all palettes
                    results = self.porypal_controller.image_manager.process_all_palettes(palettes)
                    
                    # Get the best palette (first one with most colors)
                    best_indices = results['highlights'].get('best_indices', [])
                    best_index = best_indices[0] if best_indices else None
                    
                    if best_index is None:
                        logging.error(f"No suitable palette found for: {image_path}")
                        error_count += 1
                        continue
                    
                    # Get the best image and palette
                    best_image = results['images'][best_index]
                    best_palette = palettes[best_index]
                    
                    # Generate output path
                    original_name = os.path.splitext(os.path.basename(image_path))[0]
                    palette_name = os.path.splitext(best_palette.get_name())[0]  # Remove .pal if present
                    output_filename = f"{original_name}_{palette_name}.png"
                    output_path = os.path.join(output_folder, output_filename)
                    
                    logging.info(f"Saving image with palette {palette_name} to {output_path}")
                    
                    # Save the image
                    if not self.porypal_controller.image_manager.save_image(best_image, output_path, best_palette):
                        raise RuntimeError("Failed to save image")
                    
                    success_count += 1
                    logging.info(f"Successfully processed: {image_path}")
                    
                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    logging.error(f"Error processing {os.path.basename(image_path)}: {str(e)}\n{error_details}")
                    error_count += 1
                    
            # Show results
            QMessageBox.information(
                self.view, 
                "Automation Complete", 
                f"Processed {len(image_files)} images.\n"
                f"Successfully processed: {success_count}\n"
                f"Errors/Skipped: {error_count}"
            )
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logging.error(f"Failed to automate palette application: {str(e)}\n{error_details}")
            QMessageBox.critical(self.view, "Error", f"Failed to automate palette application: {str(e)}")
    
    def return_to_main(self):
        """Close the automation view."""
        if self.view:
            self.view.close() ```

----

# controller/porypal_controller.py
```python
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
            self.view.notification.show_error(f"Failed to open automation view: {e}")```

----

# controller/tileset_editor_controller.py
```python
# controller/tileset_editor_controller.py

from PyQt5.QtGui import QImage, QPixmap, QPen, QColor, QPainter, QBrush
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QGraphicsPixmapItem, QGraphicsRectItem, QApplication
from PyQt5.QtCore import QObject, pyqtSlot, QRectF, Qt, QPoint
import logging
import os
import glob

from view.tileset_editor_view import TilesetEditorView
from controller.automation_controller import AutomationController
from view.automation_view import AutomationView

class TilesetEditorController(QObject):
    """
    Controller for the Tileset Editor, handling user interactions,
    managing data between model and view, and coordinating application logic.
    """
    
    def __init__(self, parent_controller=None):
        """Initialize controller with optional parent controller."""
        super().__init__()
        
        self.parent_controller = parent_controller
        self.input_image = None # contains the input tileset
        self.output_tileset = None # contains the output tileset
        self.tile_width = 32
        self.tile_height = 32
        self.grid_items = [] # list of grid rectangles
        self.selected_tiles = [] # list of selected tile positions (x, y)
        self.selection_start = None  # Store the starting point of rectangle selection
        self.output_matrix = None  # Matrix to store tiles in the output layout
        
        # Create our own view - don't accept one from the parent
        self.view = TilesetEditorView(self)
        
        # Connect view signals to controller methods
        self._connect_signals()
        
        # Add handling for when the view is closed
        self.view.closeEvent = self.handle_close_event
        logging.info("Tileset Editor Controller initialized")

    # ------------ INPUT WINDOW ------------ #
    def handle_grid_click(self, pos: QPoint):
        """Handle mouse click on the grid."""
        # Check if grid has been applied
        if not self.grid_items:
            self.view.notification.show_error("Please apply the grid first")
            return

        # Convert view coordinates to scene coordinates
        scene_pos = self.view.input_view.mapToScene(pos)

        # Calculate grid position
        x = (scene_pos.x() // self.tile_width) * self.tile_width
        y = (scene_pos.y() // self.tile_height) * self.tile_height

        # Find the corresponding original position
        for item in self.grid_items:
            if item.contains(scene_pos):
                original_pos = item.data(0)  # Get stored original position
                if original_pos[0] < self.input_image.width() and original_pos[1] < self.input_image.height():
                    self.clear_selection()
                    self.selected_tiles.append(original_pos)
                    item.setPen(QPen(QColor(0, 255, 0, 200)))
                    item.setBrush(QBrush(QColor(0, 255, 0, 50)))
                    self.selection_start = original_pos
                    # self.update_preview()
                    self.update_info_label()
                return

    # ------------ PREVIEW WINDOW ------------ #
    # def update_preview(self):
    #     """Update the preview scene with selected tiles."""
    #     self.view.preview_scene.clear()

    #     if not self.selected_tiles:
    #         return

    #     # Calculate bounds of selected tiles
    #     min_x = min(x for x, y in self.selected_tiles)
    #     min_y = min(y for x, y in self.selected_tiles)
    #     max_x = max(x + self.tile_width for x, y in self.selected_tiles)
    #     max_y = max(y + self.tile_height for x, y in self.selected_tiles)

    #     # Create output image with the right dimensions
    #     output_image = QImage(int(max_x - min_x), int(max_y - min_y), QImage.Format_RGBA8888)
    #     output_image.fill(Qt.transparent)

    #     # Draw selected tiles
    #     painter = QPainter(output_image)
    #     for x, y in self.selected_tiles:
    #         # Copy the tile from the input image
    #         tile = self.input_image.copy(int(x), int(y), self.tile_width, self.tile_height)
    #         painter.drawImage(QRectF(x - min_x, y - min_y, self.tile_width, self.tile_height), tile)
    #     painter.end()

    #     # Add to preview scene
    #     self.view.preview_scene.addPixmap(QPixmap.fromImage(output_image))
    #     self.view.preview_view.centerOn(self.view.preview_scene.itemsBoundingRect().center())

    #     # Update notification
    #     # self.view.notification.show_notification(f"Selected {len(self.selected_tiles)} tiles")

    # ------------ OUTPUT WINDOW ------------ #
    def handle_output_click(self, pos: QPoint):
        """
            If the user has defined an output layout, and selected a tile,
            copy the tile to the output layout at the clicked grid position.
            Right-clicking on a tile will clear it, regardless of selection.
        """
        # Check if output layout has been created
        if not hasattr(self.view.output_scene, 'grid_size') or self.output_matrix is None:
            self.view.notification.show_error("Please create a layout first")
            return

        # Get the clicked grid position
        scene_pos = self.view.output_view.mapToScene(pos)

        # Get tile dimensions
        tile_width, tile_height = self.view.output_scene.tile_size
        print(f"DEBUG - Output Scene Tile Size: {tile_width}x{tile_height}")

        # Calculate grid position
        x = (scene_pos.x() // tile_width) * tile_width
        y = (scene_pos.y() // tile_height) * tile_height

        # Get output layout dimensions
        columns, rows = self.view.output_scene.grid_size
        print(f"DEBUG - Output Grid Size: {columns}x{rows}")

        # Check if click is within output layout bounds
        if x >= columns * tile_width or y >= rows * tile_height:
            self.view.notification.show_error("Click within the layout grid")
            return

        # Calculate grid indices
        col = int(x // tile_width)
        row = int(y // tile_height)

        # Handle right-click to clear tile
        if QApplication.mouseButtons() & Qt.RightButton:
            # Remove any existing tile at this position from the scene
            for item in self.view.output_scene.items():
                if isinstance(item, QGraphicsPixmapItem):
                    if item.pos().x() == x and item.pos().y() == y:
                        self.view.output_scene.removeItem(item)
                        # Clear the matrix entry
                        self.output_matrix[row][col] = None
                        # self.view.notification.show_notification(f"Cleared tile at position ({col}, {row})")
                        
                        # Check if there are any tiles left in the output matrix
                        has_tiles = False
                        for r in self.output_matrix:
                            for tile in r:
                                if tile is not None:
                                    has_tiles = True
                                    break
                            if has_tiles:
                                break
                                
                        # Disable save preset button if no tiles are left
                        if not has_tiles:
                            self.view.btn_save_preset.setEnabled(False)
                            
                        self.update_info_label()
                        return
            return  # Return early for right-click even if no tile was found

        # Handle left-click to place tile
        if not self.selected_tiles:
            self.view.notification.show_error("Please select a tile first")
            return

        # Get the top-left tile from selection
        min_x = min(x for x, y in self.selected_tiles)
        min_y = min(y for x, y in self.selected_tiles)
        top_left_tile = (min_x, min_y)

        # Create a new image for the single tile at original size
        temp_image = QImage(self.tile_width, self.tile_height, QImage.Format_RGBA8888)
        temp_image.fill(Qt.transparent)

        # Draw the single tile to temporary image
        painter = QPainter(temp_image)
        tile = self.input_image.copy(int(top_left_tile[0]), int(top_left_tile[1]), self.tile_width, self.tile_height)
        painter.drawImage(QRectF(0, 0, self.tile_width, self.tile_height), tile)
        painter.end()

        # Create scaled version of the tile for display using nearest neighbor
        scaled_image = temp_image.scaled(tile_width, tile_height, Qt.KeepAspectRatio, Qt.FastTransformation)
        print(f"DEBUG - Scaled Image Size: {scaled_image.width()}x{scaled_image.height()}")

        # Remove any existing tile at this position from the scene
        for item in self.view.output_scene.items():
            if isinstance(item, QGraphicsPixmapItem):
                if item.pos().x() == x and item.pos().y() == y:
                    self.view.output_scene.removeItem(item)
                    break

        # Add the new tile to the scene
        pixmap = QPixmap.fromImage(scaled_image)
        item = QGraphicsPixmapItem(pixmap)
        item.setPos(x, y)
        self.view.output_scene.addItem(item)

        # Update the matrix with both original and scaled images
        self.output_matrix[row][col] = {
            'image': temp_image,  # Store original image
            'scaled_image': scaled_image,  # Store scaled image
            'position': (x, y),
            'size': (tile_width, tile_height),  # Store scaled size
            'original_pos': top_left_tile  # Store original position
        }

        # Enable save preset button
        self.view.btn_save_preset.setEnabled(True)

        # Update notification
        # self.view.notification.show_notification(f"Copied tile to position ({col}, {row})")

        # Update the output scene and info label
        self.view.output_scene.update()
        self.update_info_label()

    # ------------ TILE MANAGEMENT ------------ #
    def clear_selection(self):
        """Clear all selected tiles."""
        for x, y in self.selected_tiles:
            # Find and update the grid item
            for item in self.grid_items:
                item_pos = item.data(0)  # Get stored position
                if item_pos == (x, y):
                    item.setPen(QPen(QColor(255, 0, 0, 100)))
                    item.setBrush(QBrush(Qt.NoBrush))
                    break
        self.selected_tiles.clear()
        # self.update_preview()

    def select_rectangle(self, start_x, start_y, end_x, end_y):
        """Select all tiles within the rectangle defined by start and end points."""
        # Ensure start coordinates are less than end coordinates
        min_x = min(start_x, end_x)
        max_x = max(start_x, end_x)
        min_y = min(start_y, end_y)
        max_y = max(start_y, end_y)

        # Calculate grid positions
        start_col = int(min_x // self.tile_width)
        end_col = int(max_x // self.tile_width)
        start_row = int(min_y // self.tile_height)
        end_row = int(max_y // self.tile_height)

        # Select all tiles in the rectangle
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                x = col * self.tile_width
                y = row * self.tile_height

                # Check if tile is within image bounds
                if x < self.input_image.width() and y < self.input_image.height():
                    tile_pos = (x, y)
                    if tile_pos not in self.selected_tiles:
                        self.selected_tiles.append(tile_pos)
                        # Update grid item appearance
                        for item in self.grid_items:
                            item_pos = item.data(0)  # Get stored position
                            if item_pos == tile_pos:
                                item.setPen(QPen(QColor(0, 255, 0, 200)))
                                item.setBrush(QBrush(QColor(0, 255, 0, 50)))
                                break
    # ------------ UI ACTIONS ------------ #
    @pyqtSlot()
    def show_help(self):
        """Show help dialog."""
        help_text = (
            "<h3>Tileset Editor Help</h3>"
            "<p><b>Loading a Tileset:</b> Click 'Load Tileset' to select an image file.</p>"
            "<p><b>Defining Tiles:</b> Set tile width and height, then click 'Apply Grid'.</p>"
            "<p><b>Creating Output Layout:</b> Set columns and rows, then click 'Create Layout'.</p>"
            "<p><b>Arranging Tiles:</b> Click on tiles in the input view to select them, then click in the output view to place them.</p>"
            "<p><b>Saving Tileset:</b> Click 'Save Tileset' to save the arranged tiles as a new image.</p>"
            "<p><b>Saving Layout:</b> Click 'Save Layout' to save the current layout configuration (tile positions) for use with other tilesets of the same dimensions. Layouts are saved in the 'presets' folder.</p>"
            "<p><b>Loading Layout:</b> Click 'Load Layout' to apply a saved layout configuration to the current tileset. The tileset must have the same dimensions as the one used to create the layout.</p>"
        )

        QMessageBox.information(self.view, "Tileset Editor Help", help_text)

    def handle_close_event(self, event):
        """Handle the view's close event to restore the main view."""
        if self.parent_controller and hasattr(self.parent_controller, 'restore_main_view'):
            self.parent_controller.restore_main_view()
        event.accept()

    # ------------ SIGNALS ------------ #
    def _connect_signals(self):
        """Connect view signals to controller methods."""
        self.view.btn_load_tileset.clicked.connect(self.load_tileset)
        self.view.btn_save_tileset.clicked.connect(self.save_tileset)
        self.view.btn_apply_grid.clicked.connect(self.apply_grid)
        self.view.btn_create_layout.clicked.connect(self.create_output_layout)
        self.view.btn_clear_layout.clicked.connect(self.clear_output_layout)
        self.view.btn_help.clicked.connect(self.show_help)
        self.view.spin_scale.valueChanged.connect(self.handle_scale_change)
        
        # Connect config save/load buttons
        self.view.btn_save_preset.clicked.connect(self.save_config)
        self.view.btn_load_preset.clicked.connect(self.load_config)
        
        # Connect automation button
        self.view.btn_automate.clicked.connect(self.automate_preset_application)
        
        # Connect mouse click events
        self.view.input_view.mousePressEvent = lambda e: self.handle_grid_click(e.pos())
        self.view.output_view.mousePressEvent = lambda e: self.handle_output_click(e.pos())

    def show_image(self, image, scene, view):
        """Display an image in a scene and fit the view."""
        # Clear the scene and add the image
        scene.clear()
        scene.addPixmap(QPixmap.fromImage(image))
        
        # Set the scene rect to match the image
        scene.setSceneRect(0, 0, image.width(), image.height())
        
        # Fit the view to the scene
        view.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)
        
        # Force view update
        view.viewport().update()

    @pyqtSlot()
    def load_tileset(self):
        """Load tileset image from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self.view, "Load Tileset", "", "Images (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        
        if not file_path:
            return

        try:
            self.input_image = QImage(file_path)
            if self.input_image.isNull():
                self.view.notification.show_error("Failed to load image")
                return
                
            # Store the input image path for config saving/loading
            self.input_image_path = file_path
                
            # Update view with the loaded image (no scaling for input)
            self.show_image(self.input_image, self.view.input_scene, self.view.input_view)
            
            # Update UI state
            self.view.btn_apply_grid.setEnabled(True)
            self.view.btn_create_layout.setEnabled(False)  # Disable until grid is applied
            self.view.btn_clear_layout.setEnabled(False)   # Disable until grid is applied
            self.view.btn_save_tileset.setEnabled(False)   # Disable until layout is created
            
            # Enable preset buttons
            self.view.btn_save_preset.setEnabled(False)  # Disable until layout is created
            self.view.btn_load_preset.setEnabled(True)   # Enable when image is loaded
            
            # Clear any existing grid and selection
            self.grid_items.clear()
            self.selected_tiles.clear()
            self.selection_start = None
            
            # Reset output matrix
            self.output_matrix = None
            
            # Update info label
            self.update_info_label()
                
        except Exception as e:
            logging.error(f"Failed to load tileset: {e}")
            QMessageBox.critical(self.view, "Error", f"Failed to load tileset: {e}")
            
    def handle_scale_change(self, value):
        """Handle changes to the scale factor."""
        pass  # We'll implement this later

    @pyqtSlot()
    def apply_grid(self):
        """Apply grid to input image based on tile dimensions."""
        if not self.input_image:
            return

        # Get tile dimensions from view
        self.tile_width = self.view.spin_tile_width.value()
        self.tile_height = self.view.spin_tile_height.value()

        # Calculate grid dimensions
        cols = self.input_image.width() // self.tile_width
        cols += 1 if self.input_image.width() % self.tile_width > 0 else 0

        rows = self.input_image.height() // self.tile_height
        rows += 1 if self.input_image.height() % self.tile_height > 0 else 0

        # Clear previous grid items and scene
        self.grid_items.clear()
        self.selected_tiles.clear()
        self.view.input_scene.clear()

        # Redraw the input image
        self.show_image(self.input_image, self.view.input_scene, self.view.input_view)

        # Set up the pen for grid drawing (transparent red, 1px width)
        pen = QPen(QColor(255, 0, 0, 100))
        pen.setWidth(1)

        # Draw grid at original size
        for row in range(rows):
            for col in range(cols):
                x = col * self.tile_width
                y = row * self.tile_height

                # Create grid cell
                grid_item = QGraphicsRectItem(x, y, self.tile_width, self.tile_height)
                grid_item.setPen(pen)
                grid_item.setData(0, (col * self.tile_width, row * self.tile_height))  # Store original position
                self.grid_items.append(grid_item)
                self.view.input_scene.addItem(grid_item)

        # Update UI state
        self.view.btn_create_layout.setEnabled(True)
        self.view.notification.show_notification(
            f"Grid applied: {cols}x{rows} tiles ({self.tile_width}x{self.tile_height} pixels each)"
        )
        
        # Update info label
        self.update_info_label()

    @pyqtSlot()
    def create_output_layout(self):
        """Create output layout with specified dimensions."""
        # Get layout dimensions
        columns = self.view.spin_columns.value()
        rows = self.view.spin_rows.value()

        # Get tile dimensions
        tile_width = self.view.spin_tile_width.value()
        tile_height = self.view.spin_tile_height.value()

        # Get scale factor
        scale_factor = self.view.spin_scale.value() / 100.0
        print(f"DEBUG - Scale Factor: {scale_factor}")
        print(f"DEBUG - Original Tile Size: {tile_width}x{tile_height}")

        # Calculate scaled dimensions for output
        scaled_tile_width = int(tile_width * scale_factor)
        scaled_tile_height = int(tile_height * scale_factor)
        scaled_width = columns * scaled_tile_width
        scaled_height = rows * scaled_tile_height
        print(f"DEBUG - Scaled Tile Size: {scaled_tile_width}x{scaled_tile_height}")
        print(f"DEBUG - Scaled Layout Size: {scaled_width}x{scaled_height}")

        # Create a blank image for the output layout at scaled size
        output_image = QImage(scaled_width, scaled_height, QImage.Format_RGBA8888)
        output_image.fill(Qt.transparent)

        # Setup output grid with scaled dimensions
        self.view.output_scene.setup_grid(columns, rows, scaled_tile_width, scaled_tile_height)
        
        # Initialize the output matrix
        self.output_matrix = [[None for _ in range(columns)] for _ in range(rows)]

        # Show the blank output image
        self.show_image(output_image, self.view.output_scene, self.view.output_view)

        # Draw grid using scaled dimensions (1px width)
        pen = QPen(QColor(200, 200, 200, 100))
        pen.setWidth(1)
        for x in range(0, scaled_width + 1, scaled_tile_width):
            self.view.output_scene.addLine(x, 0, x, scaled_height, pen)
        for y in range(0, scaled_height + 1, scaled_tile_height):
            self.view.output_scene.addLine(0, y, scaled_width, y, pen)

        # Update UI state
        self.view.btn_save_tileset.setEnabled(True)
        self.view.btn_clear_layout.setEnabled(True)
        self.view.btn_save_preset.setEnabled(True)  # Enable save preset button
        
        # Update info label
        self.update_info_label()

    @pyqtSlot()
    def clear_output_layout(self):
        """Clear the output layout."""
        # Get current layout dimensions
        columns, rows = self.view.output_scene.grid_size
        tile_width, tile_height = self.view.output_scene.tile_size

        # Clear the scene and matrix
        self.view.output_scene.clear()
        self.output_matrix = [[None for _ in range(columns)] for _ in range(rows)]

        # Redraw the grid
        width = columns * tile_width
        height = rows * tile_height

        from PyQt5.QtGui import QPen, QColor
        pen = QPen(QColor(200, 200, 200, 100))
        for x in range(0, width + 1, tile_width):
            self.view.output_scene.addLine(x, 0, x, height, pen)
        for y in range(0, height + 1, tile_height):
            self.view.output_scene.addLine(0, y, width, y, pen)

        # Update UI state
        self.view.btn_save_preset.setEnabled(False)  # Disable save preset button

        self.view.notification.show_notification("Output layout cleared")
        self.update_info_label()

    @pyqtSlot()
    def save_tileset(self):
        """Save the output tileset to a file."""
        # Check if there are tiles to save
        if not any(any(tile is not None for tile in row) for row in self.output_matrix):
            QMessageBox.warning(self.view, "Warning",
                                "No tiles to save. Please create a layout and arrange tiles first.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self.view, "Save Tileset", "", "PNG Image (*.png)"
        )

        if not file_path:
            return

        try:
            # Get layout dimensions and scaled tile size
            rows, cols = len(self.output_matrix), len(self.output_matrix[0])
            tile_width, tile_height = self.view.output_scene.tile_size
            
            # Create output image with the scaled dimensions
            output_image = QImage(cols * tile_width, rows * tile_height, QImage.Format_RGBA8888)
            output_image.fill(Qt.transparent)

            # Draw all tiles from the matrix
            painter = QPainter(output_image)
            for row in range(rows):
                for col in range(cols):
                    tile_data = self.output_matrix[row][col]
                    if tile_data is not None:
                        # Get the scaled tile image
                        scaled_image = tile_data['scaled_image']
                        
                        # Draw the scaled tile at its position
                        painter.drawImage(
                            col * tile_width,
                            row * tile_height,
                            scaled_image
                        )
            painter.end()

            # Save the image
            output_image.save(file_path)

            self.view.notification.show_notification(f"Tileset saved to: {file_path}")

        except Exception as e:
            logging.error(f"Failed to save tileset: {e}")
            QMessageBox.critical(self.view, "Error", f"Failed to save tileset: {e}")

    def update_info_label(self):
        """Update the info labels with current state information."""
        input_text = []
        output_text = []
        
        # Input image info
        if self.input_image:
            input_text.append(f"Input Image: {self.input_image.width()}x{self.input_image.height()} pixels")
            
            # Grid info - only show if grid exists
            if self.grid_items and len(self.grid_items) > 0:
                try:
                    cols = self.input_image.width() // self.tile_width
                    cols += 1 if self.input_image.width() % self.tile_width > 0 else 0
                    rows = self.input_image.height() // self.tile_height
                    rows += 1 if self.input_image.height() % self.tile_height > 0 else 0
                    input_text.append(f"Grid: {cols}x{rows} tiles")
                    input_text.append(f"Tile Size: {self.tile_width}x{self.tile_height} pixels")
                    
                    # Selected tile info - only show if tiles are selected
                    if self.selected_tiles and len(self.selected_tiles) > 0:
                        min_x = min(x for x, y in self.selected_tiles)
                        min_y = min(y for x, y in self.selected_tiles)
                        input_text.append(f"Selected Tile: ({min_x//self.tile_width}, {min_y//self.tile_height})")
                except Exception:
                    pass  # Skip grid info if there's an error
        
        # Output layout info - only show if layout exists
        if (hasattr(self.view.output_scene, 'grid_size') and 
            hasattr(self.view.output_scene, 'tile_size') and 
            self.output_matrix is not None):
            try:
                columns, rows = self.view.output_scene.grid_size
                tile_width, tile_height = self.view.output_scene.tile_size
                scale_factor = self.view.spin_scale.value() / 100.0
                
                # Calculate original and scaled dimensions
                original_width = columns * self.tile_width
                original_height = rows * self.tile_height
                scaled_width = columns * tile_width  # Use output scene tile width
                scaled_height = rows * tile_height   # Use output scene tile height
                
                output_text.append(f"Output Layout: {scaled_width}x{scaled_height} pixels")
                output_text.append(f"Scale: {scale_factor*100}%")
                output_text.append(f"Original Size: {original_width}x{original_height} pixels")
                output_text.append(f"Grid Size: {columns}x{rows} tiles")
                
                # Count placed tiles
                placed_tiles = sum(1 for row in self.output_matrix for tile in row if tile is not None)
                output_text.append(f"Placed Tiles: {placed_tiles}/{columns*rows}")
            except Exception:
                pass  # Skip layout info if there's an error
        
        # Update the labels
        self.view.text_info_label_input.setText("\n".join(input_text))
        self.view.text_info_label_output.setText("\n".join(output_text))

    # ------------ CONFIG SAVE/LOAD ------------ #
    def ensure_preset_folder_exists(self):
        """Ensure the preset folder exists, create it if it doesn't."""
        # Create preset folder in the application directory
        preset_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "presets")
        
        if not os.path.exists(preset_folder):
            os.makedirs(preset_folder)
            logging.info(f"Created preset folder at {preset_folder}")
            
        return preset_folder
    
    @pyqtSlot()
    def save_config(self):
        """Save the current configuration to a file."""
        if not self.input_image:
            self.view.notification.show_error("Please load a tileset first")
            return
            
        if not self.output_matrix:
            self.view.notification.show_error("Please create a layout first")
            return
            
        # Check if there are any tiles placed in the output matrix
        has_tiles = False
        for row in self.output_matrix:
            for tile in row:
                if tile is not None:
                    has_tiles = True
                    break
            if has_tiles:
                break
                
        if not has_tiles:
            self.view.notification.show_error("Please place at least one tile in the layout before saving")
            self.view.btn_save_preset.setEnabled(False)  # Disable save preset button
            return
            
        # Get the preset folder
        preset_folder = self.ensure_preset_folder_exists()
            
        file_path, _ = QFileDialog.getSaveFileName(
            self.view, "Save Configuration", preset_folder, "JSON Files (*.json)"
        )
        
        if not file_path:
            return
            
        # Ensure the file has a .json extension
        if not file_path.endswith(".json"):
            file_path += ".json"
            
        try:
            import json
            
            # Create config dictionary with only layout information
            config = {
                "tile_width": self.view.spin_tile_width.value(),
                "tile_height": self.view.spin_tile_height.value(),
                "columns": self.view.spin_columns.value(),
                "rows": self.view.spin_rows.value(),
                "scale": self.view.spin_scale.value(),
                "input_width": self.input_image.width(),
                "input_height": self.input_image.height(),
                "output_matrix": []
            }
            
            # Save only the positions from output matrix
            if self.output_matrix:
                for row in range(len(self.output_matrix)):
                    for col in range(len(self.output_matrix[row])):
                        tile_data = self.output_matrix[row][col]
                        if tile_data:
                            # Get the original position from the tile data
                            original_pos = tile_data.get('original_pos', (0, 0))
                            config["output_matrix"].append({
                                "row": row,
                                "col": col,
                                "original_x": original_pos[0],
                                "original_y": original_pos[1]
                            })
            
            # Write to file
            with open(file_path, 'w') as f:
                json.dump(config, f, indent=4)
                
            self.view.notification.show_notification(f"Configuration saved to {file_path}")
            
        except Exception as e:
            logging.error(f"Failed to save configuration: {e}")
            QMessageBox.critical(self.view, "Error", f"Failed to save configuration: {e}")
    
    @pyqtSlot()
    def load_config(self):
        """Load a configuration from a file."""
        # Get the preset folder
        preset_folder = self.ensure_preset_folder_exists()
        
        file_path, _ = QFileDialog.getOpenFileName(
            self.view, "Load Configuration", preset_folder, "JSON Files (*.json)"
        )
        
        if not file_path:
            return
            
        try:
            # Extract preset name from file path
            import os
            preset_name = os.path.basename(file_path)
            if preset_name.endswith(".json"):
                preset_name = preset_name[:-5]  # Remove .json extension
                
            # Load the preset
            self.load_preset_by_name(preset_name)
            
        except Exception as e:
            logging.error(f"Failed to load configuration: {e}")
            QMessageBox.critical(self.view, "Error", f"Failed to load configuration: {e}")
    
    def place_tile_in_output(self, row, col):
        """Place the currently selected tile in the output matrix at the specified position."""
        if not self.selected_tiles or not self.output_matrix:
            return
            
        # Get the top-left tile from selection
        min_x = min(x for x, y in self.selected_tiles)
        min_y = min(y for x, y in self.selected_tiles)
        top_left_tile = (min_x, min_y)
        
        # Get tile dimensions from output scene
        tile_width, tile_height = self.view.output_scene.tile_size
        
        # Create a new image for the single tile at original size
        temp_image = QImage(self.tile_width, self.tile_height, QImage.Format_RGBA8888)
        temp_image.fill(Qt.transparent)
        
        # Draw the single tile to temporary image
        painter = QPainter(temp_image)
        tile = self.input_image.copy(int(top_left_tile[0]), int(top_left_tile[1]), self.tile_width, self.tile_height)
        painter.drawImage(QRectF(0, 0, self.tile_width, self.tile_height), tile)
        painter.end()
        
        # Create scaled version of the tile for display using nearest neighbor
        scaled_image = temp_image.scaled(tile_width, tile_height, Qt.KeepAspectRatio, Qt.FastTransformation)
        
        # Calculate position in the output scene
        x = col * tile_width
        y = row * tile_height
        
        # Remove any existing tile at this position from the scene
        for item in self.view.output_scene.items():
            if isinstance(item, QGraphicsPixmapItem):
                if item.pos().x() == x and item.pos().y() == y:
                    self.view.output_scene.removeItem(item)
                    break
        
        # Add the new tile to the scene
        pixmap = QPixmap.fromImage(scaled_image)
        item = QGraphicsPixmapItem(pixmap)
        item.setPos(x, y)
        self.view.output_scene.addItem(item)
        
        # Update the matrix with both original and scaled images
        self.output_matrix[row][col] = {
            'image': temp_image,  # Store original image
            'scaled_image': scaled_image,  # Store scaled image
            'position': (x, y),
            'size': (tile_width, tile_height),  # Store scaled size
            'original_pos': top_left_tile  # Store original position
        }
        
        # Update the output scene and info label
        self.view.output_scene.update()
        self.update_info_label()

    def list_available_presets(self):
        """List all available presets in the preset folder."""
        import os
        import glob
        
        preset_folder = self.ensure_preset_folder_exists()
        preset_files = glob.glob(os.path.join(preset_folder, "*.json"))
        
        presets = []
        for file_path in preset_files:
            try:
                import json
                with open(file_path, 'r') as f:
                    config = json.load(f)
                    
                # Extract preset name from filename
                preset_name = os.path.basename(file_path)
                if preset_name.endswith(".json"):
                    preset_name = preset_name[:-5]  # Remove .json extension
                    
                # Get dimensions from config
                input_width = config.get("input_width", 0)
                input_height = config.get("input_height", 0)
                tile_width = config.get("tile_width", 32)
                tile_height = config.get("tile_height", 32)
                
                presets.append({
                    "name": preset_name,
                    "path": file_path,
                    "dimensions": f"{input_width}x{input_height}",
                    "tile_size": f"{tile_width}x{tile_height}"
                })
            except Exception as e:
                logging.error(f"Failed to load preset {file_path}: {e}")
                
        return presets

    def load_preset_by_name(self, preset_name):
        """Load a preset by its name."""
        import os
        
        preset_folder = self.ensure_preset_folder_exists()
        file_path = os.path.join(preset_folder, f"{preset_name}.json")
        
        if not os.path.exists(file_path):
            self.view.notification.show_error(f"Preset '{preset_name}' not found")
            return False
            
        try:
            import json
            
            # Read from file
            with open(file_path, 'r') as f:
                config = json.load(f)
            
            # Check if a tileset is loaded
            if not self.input_image:
                self.view.notification.show_error("Please load a tileset first")
                return False
                
            # Validate input dimensions
            input_width = config.get("input_width", 0)
            input_height = config.get("input_height", 0)
            
            if input_width != self.input_image.width() or input_height != self.input_image.height():
                QMessageBox.critical(
                    self.view, 
                    "Dimension Mismatch", 
                    f"Cannot apply this preset. The input tileset dimensions don't match.\n\n"
                    f"Preset requires: {input_width}x{input_height}\n"
                    f"Current tileset: {self.input_image.width()}x{self.input_image.height()}"
                )
                return False
            
            # Set spin box values
            self.view.spin_tile_width.setValue(config.get("tile_width", 32))
            self.view.spin_tile_height.setValue(config.get("tile_height", 32))
            self.view.spin_columns.setValue(config.get("columns", 1))
            self.view.spin_rows.setValue(config.get("rows", 1))
            self.view.spin_scale.setValue(config.get("scale", 100))
            
            # Apply grid and create layout
            self.apply_grid()
            self.create_output_layout()
            
            # Restore tile positions
            for tile_data in config.get("output_matrix", []):
                row = tile_data.get("row", 0)
                col = tile_data.get("col", 0)
                original_x = tile_data.get("original_x", 0)
                original_y = tile_data.get("original_y", 0)
                
                # Find the tile in the input image
                for item in self.grid_items:
                    item_pos = item.data(0)  # Get stored position
                    if item_pos == (original_x, original_y):
                        # Select this tile
                        self.selected_tiles = [(original_x, original_y)]
                        item.setPen(QPen(QColor(0, 255, 0, 200)))
                        item.setBrush(QBrush(QColor(0, 255, 0, 50)))
                        
                        # Place it in the output matrix
                        self.place_tile_in_output(row, col)
                        break
            
            self.view.notification.show_notification(f"Preset '{preset_name}' loaded successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to load preset '{preset_name}': {e}")
            QMessageBox.critical(self.view, "Error", f"Failed to load preset '{preset_name}': {e}")
            return False

    @pyqtSlot()
    def automate_preset_application(self):
        """Open the automation view to apply a preset to multiple images."""
        # Create automation controller and view
        self.automation_controller = AutomationController(self)
        self.automation_view = AutomationView(self.automation_controller)
        self.automation_controller.set_view(self.automation_view)
        
        # Show the automation view
        self.automation_view.show()
```

----

# main.py
```python
#!/usr/bin/env python3
"""
PoryPal - Palette conversion tool for pokeemerald-expansion
Main application entry point.
"""

import sys
import logging
import os
from pathlib import Path
import yaml
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from controller.porypal_controller import PorypalController
from view.porypal_theme import PorypalTheme

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Application metadata
APP_METADATA = {
    'name': "PoryPal",
    'version': "1.1.0",
    'debug': False,
    'config_path': Path("config.yaml"),
    'icon_path': Path("ressources/porypal.ico"),
    'org_name': "prisonlox",
    'org_domain': "porypal"
}

def main() -> int:
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if APP_METADATA['debug'] else logging.INFO,
        format='[%(pathname)s:%(lineno)d] %(levelname)s - %(message)s'
    )
    logging.info(f"Starting {APP_METADATA['name']} v{APP_METADATA['version']}")

    # Initialize Qt application
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_METADATA['name'])
    app.setApplicationVersion(APP_METADATA['version'])
    app.setOrganizationName(APP_METADATA['org_name'])
    app.setOrganizationDomain(APP_METADATA['org_domain'])

    # Set icon if available
    if APP_METADATA['icon_path'].exists():
        app.setWindowIcon(QIcon(str(APP_METADATA['icon_path'])))

    # Windows-specific taskbar icon
    try:
        from ctypes import windll
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            f"{APP_METADATA['org_domain']}.{APP_METADATA['name']}.1"
        )
    except ImportError:
        pass

    # Load configuration
    config = {}
    try:
        if APP_METADATA['config_path'].exists():
            with open(APP_METADATA['config_path'], 'r') as file:
                config = yaml.safe_load(file) or {}
            logging.debug("Configuration loaded successfully")
        else:
            logging.warning(f"Config file not found: {APP_METADATA['config_path']}")
    except Exception as e:
        logging.error(f"Config load failed: {e}")

    # Initialize theme and controller
    theme = PorypalTheme(app, config)
    controller = PorypalController(theme, app, config)
    # controller.view.show()

    # Run application
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())```

----

# model/QNotificationWidget.py
```python
from PyQt5.QtWidgets import QDockWidget, QLabel, QApplication, QWidget, QVBoxLayout, QSizePolicy
from PyQt5.QtCore import Qt, QRect, QPropertyAnimation
from PyQt5.QtGui import QPalette
import sys
import json
from pathlib import Path
from view.porypal_theme import PorypalTheme

def warn(message: str):
    print("\n" + '\033[1m' + 'WARN:' + '\033[93m' + f' {message}' + '\033[0m')

class QNotificationWidget(QDockWidget):
    """Custom dock widget that displays a scrolling notification message."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)

        # Make dock background transparent
        self.setStyleSheet("background-color: transparent; border: 0; padding: 0; margin: 0;")

        self.setFixedHeight(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.message_label = QLabel(self)
        self.message_label.setAlignment(Qt.AlignCenter)
        self._update_style()
        self.message_label.setFixedHeight(self.message_label.sizeHint().height() + 10)

        # Scrolling text
        self.scroll_animation = QPropertyAnimation(self.message_label, b"geometry", self)
        self.scroll_animation.finished.connect(self.scroll_finished)

    def _update_style(self):
        """Update style using application palette colors"""
        palette = QApplication.instance().palette()
        
        # Use theme colors from palette
        bg_color = palette.color(QPalette.Base).name()
        text_color = palette.color(QPalette.Text).name()
        
        self.message_label.setStyleSheet(
            f"background-color: {bg_color};"
            f"color: {text_color};"
            "font-size: 20px;"
            "border: 0;"
            "padding: 0;"
            "margin: 0;"
        )

    def resizeEvent(self, event):
        """Ensure the widget takes the full width of the parent window."""
        if self.parent:
            self.setFixedWidth(self.parent.width())
        super().resizeEvent(event)

    def show_notification(self, message, speed=50):
        """Show the notification with a fixed scrolling speed (default 50 pixels per second)."""
        self._update_style()  # Update style before showing
        self.message_label.setText((message + 16 * " ") * 20)
        self.message_label.setFixedWidth(self.message_label.sizeHint().width())

        label_width, label_height = self.message_label.sizeHint().width(), self.message_label.sizeHint().height()
        self.setFixedHeight(label_height)

        # Calculate duration based on fixed speed

        self.scroll_animation.stop()
        self.scroll_animation.setDuration(5000)
        self.scroll_animation.setStartValue(QRect(0, 0, label_width, label_height))
        self.scroll_animation.setEndValue(QRect(-(int)(label_width/10), 0, label_width, label_height))
        self.scroll_animation.start()

        self.show()


    def hide_notification(self):
        self.scroll_animation.stop()
        self.setFixedHeight(0)
        self.hide()

    def scroll_finished(self):
        self.hide_notification()

    def notify(self, message, error=None):
        self.hide_notification()
        self.show_notification(message)
        if error:
            warn(f'{message}, {error}')


    def show_error(self, message: str):
        """Show error message in dialog."""
        self.notify(message, error=True)

    def show_success(self, message: str):
        """Show success message in dialog."""
        self.notify(message)

    def show_warning(self, message: str):
        """Show warning message in dialog."""
        self.notify("Warning: "+message, error=False)
```

----

# model/__init__.py
```python
"""
PoryPal Model Package
This package contains the data models and business logic for the PoryPal application.
"""

from .image_manager import ImageManager
from .tilesetManager import TilesetManager
from .tile_drop_area import TileDropArea
from .palette_manager import PaletteManager, Palette
from .QNotificationWidget import QNotificationWidget

__all__ = [
    'ImageManager',
    'TilesetManager',
    'TileDropArea',
    'PaletteManager',
    'Palette',
    'QNotificationWidget'
]

__version__ = '2.0.0'
```

----

# model/image_manager.py
```python
"""
model/image_manager.py

Image loading, palette conversion, and saving. Pure Pillow — no Qt.

The conversion pipeline:
  1. Load any image → PIL RGBA
  2. Detect transparent color (alpha channel or edge detection)
  3. For each palette: remap every pixel to the nearest Color using RGB distance
  4. Save as indexed 4-bit PNG (GBA-compatible)
"""

from __future__ import annotations
import logging
from pathlib import Path

import numpy as np
from PIL import Image

from model.palette import Color, Palette


SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}


class ConversionResult:
    """Holds one palette's conversion of the loaded image."""

    def __init__(self, image: Image.Image, palette: Palette, colors_used: int):
        self.image = image          # PIL Image (mode "P", indexed)
        self.palette = palette
        self.colors_used = colors_used

    @property
    def label(self) -> str:
        return f"{self.palette.name} ({self.colors_used} colors used)"


class ImageManager:
    """Handles image loading, conversion, and saving. No Qt dependency."""

    def __init__(self, config: dict):
        self.config = config
        self._current_image_path: Path | None = None
        self._original_rgba: Image.Image | None = None      # PIL RGBA source
        self._transparent_color: Color | None = None
        self._conversion_cache: dict[tuple, Color] = {}     # (pixel_rgb, palette_name) → Color
        self.results: list[ConversionResult] = []

    # ---------- Load ----------

    def load_image(self, image_path: str | Path) -> Image.Image:
        """Load image and return PIL RGBA. Raises on unsupported format or bad file."""
        path = Path(image_path)
        if path.suffix.lower() not in SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format '{path.suffix}'. Supported: {', '.join(SUPPORTED_FORMATS)}"
            )

        img = Image.open(path).convert("RGBA")
        self._current_image_path = path
        self._original_rgba = img
        self._transparent_color = self._detect_transparent_color(img)
        self._conversion_cache.clear()
        logging.debug(f"Loaded {path.name} ({img.width}×{img.height})")
        return img

    def _detect_transparent_color(self, img: Image.Image) -> Color | None:
        """
        Find the background/transparent color.
        Priority: alpha channel first, then most common edge pixel.
        """
        pixels = np.array(img)  # shape (H, W, 4)

        # 1. Any pixel with alpha < 255?
        transparent_mask = pixels[:, :, 3] < 255
        if transparent_mask.any():
            y, x = np.argwhere(transparent_mask)[0]
            r, g, b, _ = pixels[y, x]
            c = Color(int(r), int(g), int(b))
            logging.debug(f"Transparent color (alpha): {c.to_hex()}")
            return c

        # 2. Most common edge pixel
        h, w = pixels.shape[:2]
        edges = np.concatenate([
            pixels[0, :, :3],       # top row
            pixels[-1, :, :3],      # bottom row
            pixels[:, 0, :3],       # left col
            pixels[:, -1, :3],      # right col
        ])
        unique, counts = np.unique(edges.reshape(-1, 3), axis=0, return_counts=True)
        most_common = unique[counts.argmax()]
        c = Color(int(most_common[0]), int(most_common[1]), int(most_common[2]))
        logging.debug(f"Transparent color (edge): {c.to_hex()}")
        return c

    # ---------- Convert ----------

    def process_all_palettes(self, palettes: list[Palette]) -> list[ConversionResult]:
        """Convert the loaded image against every palette. Returns sorted results."""
        if self._original_rgba is None:
            raise ValueError("No image loaded — call load_image() first")

        self.results = [
            self._convert_to_palette(self._original_rgba, palette)
            for palette in palettes
        ]
        return self.results

    def _convert_to_palette(self, img: Image.Image, palette: Palette) -> ConversionResult:
        """
        Remap every pixel in img to the nearest color in palette.
        Transparent pixels → palette.transparent_color (index 0).
        Returns an indexed PIL Image (mode "P").
        """
        pixels = np.array(img)  # (H, W, 4)
        h, w = pixels.shape[:2]

        transparent = palette.transparent_color
        opaque = palette.opaque_colors

        if not opaque:
            # Edge case: palette only has one color
            opaque = palette.colors

        # Build lookup arrays for vectorised nearest-colour search
        palette_rgb = np.array([c.to_tuple() for c in opaque], dtype=np.int32)  # (N, 3)

        rgb = pixels[:, :, :3].astype(np.int32)          # (H, W, 3)
        alpha = pixels[:, :, 3]                           # (H, W)

        # For each pixel, find index of nearest opaque palette color
        # Expand dims for broadcasting: (H, W, 1, 3) vs (N, 3)
        diff = rgb[:, :, np.newaxis, :] - palette_rgb[np.newaxis, np.newaxis, :, :]
        dist_sq = (diff ** 2).sum(axis=3)                 # (H, W, N)
        nearest_idx = dist_sq.argmin(axis=2)              # (H, W)

        # Build output index array
        # Index 0 = transparent, index i+1 = opaque[i]
        index_map = nearest_idx + 1                       # shift by 1 (0 reserved for transparent)
        index_map[alpha < 255] = 0                        # transparent pixels → index 0

        # Count distinct palette indices actually used
        used = set(np.unique(index_map).tolist())
        colors_used = len(used)

        # Build PIL indexed image
        out = Image.new("P", (w, h))
        pal_data = []
        if transparent:
            pal_data += list(transparent.to_tuple())
        for c in opaque:
            pal_data += list(c.to_tuple())
        # Pad to 256 colours (768 bytes)
        pal_data += [0] * (768 - len(pal_data))
        out.putpalette(pal_data)
        out.putdata(index_map.flatten().tolist())

        return ConversionResult(image=out, palette=palette, colors_used=colors_used)

    # ---------- Save ----------

    def save_image(self, result: ConversionResult, output_path: str | Path) -> bool:
        """Save a ConversionResult as a 4-bit indexed PNG."""
        try:
            out_path = Path(output_path)
            result.image.save(out_path, format="PNG", bits=4, optimize=True)
            logging.debug(f"Saved: {out_path}")
            return True
        except Exception as e:
            logging.error(f"Failed to save image: {e}")
            return False

    def auto_output_path(self, result: ConversionResult) -> Path:
        """Generate <original_stem>_<palette_stem>.png next to the source image."""
        if not self._current_image_path:
            raise ValueError("No image loaded")
        stem = self._current_image_path.stem
        pal_stem = Path(result.palette.name).stem
        return self._current_image_path.parent / f"{stem}_{pal_stem}.png"

    # ---------- Getters ----------

    def get_result_at_index(self, index: int) -> ConversionResult | None:
        if 0 <= index < len(self.results):
            return self.results[index]
        return None

    def get_best_indices(self) -> list[int]:
        """Indices of results with the highest colors_used count."""
        if not self.results:
            return []
        max_colors = max(r.colors_used for r in self.results)
        return [i for i, r in enumerate(self.results) if r.colors_used == max_colors]

    @property
    def current_image_path(self) -> Path | None:
        return self._current_image_path
```

----

# model/palette.py
```python
"""
model/palette.py

Pure-Python palette types — no Qt dependency.
The view layer is responsible for converting Color → QColor / any other UI color type.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import logging


@dataclass(frozen=True)
class Color:
    """Immutable RGB color. No Qt, no GUI dependency."""
    r: int
    g: int
    b: int

    def __post_init__(self):
        for ch, v in (("r", self.r), ("g", self.g), ("b", self.b)):
            if not 0 <= v <= 255:
                raise ValueError(f"Color channel {ch}={v} out of range [0, 255]")

    def to_tuple(self) -> tuple[int, int, int]:
        return (self.r, self.g, self.b)

    def to_hex(self) -> str:
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}"

    def distance_sq(self, other: "Color") -> int:
        """Squared Euclidean distance in RGB space. No sqrt needed for comparisons."""
        return (self.r - other.r) ** 2 + (self.g - other.g) ** 2 + (self.b - other.b) ** 2

    @classmethod
    def from_hex(cls, hex_str: str) -> "Color":
        hex_str = hex_str.lstrip("#")
        return cls(int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))


@dataclass
class Palette:
    """
    A named list of up to 16 Colors.
    Index 0 is always the transparent/background color by GBA convention.
    """
    name: str
    colors: list[Color] = field(default_factory=list)

    MAX_COLORS = 16

    def __post_init__(self):
        if len(self.colors) > self.MAX_COLORS:
            raise ValueError(
                f"Palette '{self.name}' has {len(self.colors)} colors — GBA max is {self.MAX_COLORS}"
            )

    @property
    def transparent_color(self) -> Color | None:
        return self.colors[0] if self.colors else None

    @property
    def opaque_colors(self) -> list[Color]:
        """All colors except index 0 (transparent)."""
        return self.colors[1:]

    def is_gba_compatible(self) -> bool:
        return len(self.colors) <= self.MAX_COLORS

    # ---------- Serialisation ----------

    @classmethod
    def from_jasc_pal(cls, path: Path) -> "Palette":
        """
        Load from a JASC-PAL file.
        Format:
            JASC-PAL
            0100
            16
            R G B
            ...
        """
        lines = path.read_text(encoding="utf-8").splitlines()
        # Skip the 3-line JASC header
        color_lines = [l.strip() for l in lines[3:] if l.strip()]
        colors = []
        for line in color_lines:
            parts = line.split()
            if len(parts) >= 3:
                try:
                    colors.append(Color(int(parts[0]), int(parts[1]), int(parts[2])))
                except ValueError as e:
                    logging.warning(f"Skipping malformed color line '{line}' in {path.name}: {e}")
        return cls(name=path.name, colors=colors)

    def to_jasc_pal(self, path: Path) -> None:
        """Write palette back to JASC-PAL format."""
        lines = ["JASC-PAL", "0100", str(len(self.colors))]
        lines += [f"{c.r} {c.g} {c.b}" for c in self.colors]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def to_hex_list(self) -> list[str]:
        return [c.to_hex() for c in self.colors]
```

----

# model/palette_extractor.py
```python
"""
model/palette_extractor.py

Extract a GBA-compatible palette from any sprite using k-means clustering.
This is the v3 "Extract" pillar — the feature that was missing vs Pylette.

Usage:
    extractor = PaletteExtractor()
    palette = extractor.extract("my_sprite.png", n_colors=16, name="my_sprite")
    palette.to_jasc_pal(Path("palettes/my_sprite.pal"))
"""

from __future__ import annotations
import logging
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

from model.palette import Color, Palette


class PaletteExtractor:
    """
    Extract a palette from a sprite using k-means clustering.

    The first color slot is always reserved for the transparent/background color
    (detected automatically), so the actual cluster count is n_colors - 1.
    """

    def __init__(self, random_state: int = 42):
        self.random_state = random_state

    def extract(
        self,
        image_path: str | Path,
        n_colors: int = 16,
        name: str | None = None,
    ) -> Palette:
        """
        Extract a palette from image_path.

        Args:
            image_path: Path to any image Pillow can open.
            n_colors: Total palette size including transparent slot (max 16 for GBA).
            name: Palette name. Defaults to the image filename stem.

        Returns:
            A Palette with n_colors entries, index 0 = transparent color.
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
        if n_colors < 2 or n_colors > Palette.MAX_COLORS:
            raise ValueError(f"n_colors must be 2–{Palette.MAX_COLORS}, got {n_colors}")

        img = Image.open(path).convert("RGBA")
        pixels = np.array(img)          # (H, W, 4)
        alpha = pixels[:, :, 3]
        rgb = pixels[:, :, :3]

        # --- Transparent color: first fully-transparent or most common edge pixel ---
        transparent_color = self._detect_transparent(pixels)

        # --- Collect opaque pixels for clustering ---
        opaque_mask = alpha.flatten() >= 255
        opaque_pixels = rgb.reshape(-1, 3)[opaque_mask].astype(np.float32)

        n_clusters = n_colors - 1   # slot 0 is reserved for transparent

        if len(opaque_pixels) == 0:
            logging.warning("Image has no opaque pixels — returning palette with transparent only")
            return Palette(name=name or path.stem, colors=[transparent_color])

        # Clamp clusters to unique pixel count
        actual_clusters = min(n_clusters, len(np.unique(opaque_pixels, axis=0)))

        kmeans = KMeans(
            n_clusters=actual_clusters,
            random_state=self.random_state,
            n_init="auto",
        )
        kmeans.fit(opaque_pixels)
        centers = kmeans.cluster_centers_.astype(np.uint8)

        # Sort by cluster size (most prominent color first after transparent)
        labels = kmeans.labels_
        cluster_sizes = np.bincount(labels, minlength=actual_clusters)
        order = np.argsort(-cluster_sizes)  # descending
        sorted_centers = centers[order]

        colors = [transparent_color] + [
            Color(int(c[0]), int(c[1]), int(c[2])) for c in sorted_centers
        ]

        palette = Palette(name=name or path.stem, colors=colors)
        logging.info(
            f"Extracted {len(colors)} colors from '{path.name}' "
            f"({len(opaque_pixels)} opaque pixels, {actual_clusters} clusters)"
        )
        return palette

    def extract_batch(
        self,
        image_paths: list[Path],
        n_colors: int = 16,
    ) -> list[Palette]:
        """Extract palettes from a list of images. Returns one Palette per image."""
        results = []
        for path in image_paths:
            try:
                results.append(self.extract(path, n_colors=n_colors))
            except Exception as e:
                logging.error(f"Failed to extract palette from {path}: {e}")
        return results

    # ---------- Helpers ----------

    def _detect_transparent(self, pixels: np.ndarray) -> Color:
        alpha = pixels[:, :, 3]
        transparent_mask = alpha < 255
        if transparent_mask.any():
            y, x = np.argwhere(transparent_mask)[0]
            r, g, b, _ = pixels[y, x]
            return Color(int(r), int(g), int(b))

        # Fall back to most common edge pixel
        rgb = pixels[:, :, :3]
        h, w = rgb.shape[:2]
        edges = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
        unique, counts = np.unique(edges.reshape(-1, 3), axis=0, return_counts=True)
        most_common = unique[counts.argmax()]
        return Color(int(most_common[0]), int(most_common[1]), int(most_common[2]))
```

----

# model/palette_manager.py
```python
"""
model/palette_manager.py

Loads and manages .pal palette files. Pure Python, no Qt.
"""

from __future__ import annotations
import logging
from pathlib import Path

from model.palette import Palette


class PaletteManager:
    """Loads and manages palettes from a directory of JASC-PAL files."""

    def __init__(self, config: dict):
        self.config = config
        self._palettes: list[Palette] = []
        self._load_palettes()

    def _load_palettes(self) -> None:
        palette_dir = Path("palettes")
        if not palette_dir.exists():
            logging.error("Missing palettes directory")
            return

        more_colors = self.config.get("palettes", {}).get("more_colors", False)
        npc_priority = self.config.get("palettes", {}).get("npc_priority", False)

        palette_files = sorted(palette_dir.glob("*.pal"))

        if npc_priority:
            palette_files = [p for p in palette_files if p.name.startswith("npc_")]

        if not more_colors:
            palette_files = palette_files[:4]

        self._palettes = []
        for pal_file in palette_files:
            try:
                self._palettes.append(Palette.from_jasc_pal(pal_file))
                logging.debug(f"Loaded palette: {pal_file.name}")
            except Exception as e:
                logging.error(f"Failed to load palette {pal_file.name}: {e}")

        logging.info(f"Loaded {len(self._palettes)} palettes")

    def get_palettes(self) -> list[Palette]:
        return self._palettes

    def get_palette_by_index(self, index: int) -> Palette:
        return self._palettes[index]

    def get_palette_by_name(self, name: str) -> Palette | None:
        return next((p for p in self._palettes if p.name == name), None)

    def reload(self) -> None:
        """Reload palettes from disk — useful when user adds new .pal files."""
        self._load_palettes()
```

----

# model/tile_drop_area.py
```python
#model/tile_drop_area.py
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGraphicsScene

class TileDropArea(QGraphicsScene):
    """
    Graphics scene that handles tile placement in a grid.
    Manages the arrangement of tiles in the output tileset.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid_size = (0, 0)
        self.tile_size = (32, 32)
        self.tiles = {}  # Position -> Tile mapping
        
    def setup_grid(self, columns, rows, tile_width, tile_height):
        """Setup grid with specified dimensions."""
        self.grid_size = (columns, rows)
        self.tile_size = (tile_width, tile_height)
        
        # Create new scene with proper size
        width = columns * tile_width
        height = rows * tile_height
        self.setSceneRect(0, 0, width, height)
        
        # Clear existing tiles
        self.clear()
        self.tiles.clear()
        
        return width, height
        
    def place_tile(self, pixmap, tile_id, grid_x, grid_y):
        """Place a tile at the specified grid position."""
        # Calculate pixel position
        x = grid_x * self.tile_size[0]
        y = grid_y * self.tile_size[1]
        
        # Remove existing tile at this position if any
        position = (grid_x, grid_y)
        if position in self.tiles:
            self.removeItem(self.tiles[position])
        
        # Create new tile and position it
        new_tile = DraggableTile(pixmap, tile_id)
        new_tile.setPos(x, y)
        self.addItem(new_tile)
        
        # Store reference to the tile
        self.tiles[position] = new_tile
        
        return new_tile
        
    def get_output_image(self):
        """Generate a QImage from the arranged tiles."""
        from PyQt5.QtGui import QImage, QPainter
        
        columns, rows = self.grid_size
        tile_width, tile_height = self.tile_size
        
        # Create image with the right dimensions
        output_image = QImage(
            columns * tile_width,
            rows * tile_height,
            QImage.Format_ARGB32
        )
        output_image.fill(Qt.transparent)
        
        # Draw tiles onto the image
        painter = QPainter(output_image)
        
        for (col, row), tile in self.tiles.items():
            # Get source rectangle in original tileset
            pixmap = tile.pixmap()
            painter.drawPixmap(
                col * tile_width,
                row * tile_height,
                pixmap
            )
            
        painter.end()
        return output_image```

----

# model/tilesetManager.py
```python
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
        
        self.processed_image = output```

----

# presets/ow_sprite.json
```json
{
    "tile_width": 64,
    "tile_height": 64,
    "columns": 9,
    "rows": 1,
    "scale": 50,
    "input_width": 256,
    "input_height": 256,
    "output_matrix": [
        {
            "row": 0,
            "col": 0,
            "original_x": 0,
            "original_y": 0
        },
        {
            "row": 0,
            "col": 1,
            "original_x": 0,
            "original_y": 192
        },
        {
            "row": 0,
            "col": 2,
            "original_x": 0,
            "original_y": 64
        },
        {
            "row": 0,
            "col": 3,
            "original_x": 64,
            "original_y": 0
        },
        {
            "row": 0,
            "col": 4,
            "original_x": 192,
            "original_y": 0
        },
        {
            "row": 0,
            "col": 5,
            "original_x": 64,
            "original_y": 192
        },
        {
            "row": 0,
            "col": 6,
            "original_x": 192,
            "original_y": 192
        },
        {
            "row": 0,
            "col": 7,
            "original_x": 64,
            "original_y": 64
        },
        {
            "row": 0,
            "col": 8,
            "original_x": 192,
            "original_y": 64
        }
    ]
}```

----

# setup.sh
```sh
#!/bin/bash

# Define the virtual environment directory
VENV_DIR="venv"

# Step 1: Create a virtual environment
python3 -m venv $VENV_DIR

# Step 2: Determine the path to the Python interpreter in the virtual environment
PYTHON_BIN="$VENV_DIR/bin/python"

# Step 3: Activate the virtual environment
source $VENV_DIR/bin/activate

# Step 4: Install requirements.txt if it exists
REQUIREMENTS_FILE="requirements.txt"

if [[ -f "$REQUIREMENTS_FILE" ]]; then
    if pip install -r "$REQUIREMENTS_FILE"; then
        echo "Requirements installed successfully."
    else
        echo "Failed to install requirements from $REQUIREMENTS_FILE."
        exit 1
    fi
else
    echo "No requirements.txt file found."
fi

echo ""
echo "Virtual environment created and requirements installed."
echo "You can now run your script using the Python interpreter in the virtual environment."
echo ""
echo "To launch the Python interpreter in the virtual environment, run: source $VENV_DIR/bin/activate"
echo "To deactivate the virtual environment, run: deactivate"```

----

# tests/test_model.py
```python
"""
tests/test_model.py

Tests for the Qt-free model layer.
Run with: pytest tests/
"""

import pytest
from pathlib import Path
from model.palette import Color, Palette
from model.image_manager import ImageManager
from model.palette_extractor import PaletteExtractor


# ---------- Color ----------

class TestColor:
    def test_round_trip_hex(self):
        c = Color(255, 128, 0)
        assert Color.from_hex(c.to_hex()) == c

    def test_distance_sq_self(self):
        c = Color(100, 100, 100)
        assert c.distance_sq(c) == 0

    def test_distance_sq_known(self):
        a = Color(0, 0, 0)
        b = Color(1, 0, 0)
        assert a.distance_sq(b) == 1

    def test_invalid_channel(self):
        with pytest.raises(ValueError):
            Color(256, 0, 0)


# ---------- Palette ----------

class TestPalette:
    def test_max_colors(self):
        colors = [Color(i, i, i) for i in range(17)]
        with pytest.raises(ValueError):
            Palette("too_many", colors)

    def test_transparent_color(self):
        colors = [Color(255, 0, 255), Color(0, 0, 0)]
        p = Palette("test", colors)
        assert p.transparent_color == Color(255, 0, 255)

    def test_opaque_colors(self):
        colors = [Color(255, 0, 255), Color(1, 2, 3), Color(4, 5, 6)]
        p = Palette("test", colors)
        assert p.opaque_colors == [Color(1, 2, 3), Color(4, 5, 6)]

    def test_jasc_round_trip(self, tmp_path):
        colors = [Color(255, 0, 255)] + [Color(i * 10, i * 5, i * 2) for i in range(1, 10)]
        p = Palette("round_trip", colors)
        pal_path = tmp_path / "test.pal"
        p.to_jasc_pal(pal_path)
        loaded = Palette.from_jasc_pal(pal_path)
        assert loaded.colors == p.colors

    def test_is_gba_compatible(self):
        p16 = Palette("ok", [Color(i, 0, 0) for i in range(16)])
        assert p16.is_gba_compatible()


# ---------- ImageManager ----------

class TestImageManager:
    @pytest.fixture
    def simple_palette(self):
        return Palette("test", [
            Color(255, 0, 255),   # transparent (magenta)
            Color(255, 255, 255), # white
            Color(0, 0, 0),       # black
            Color(255, 0, 0),     # red
        ])

    @pytest.fixture
    def simple_png(self, tmp_path):
        """Create a tiny 4x4 RGBA PNG with known colors."""
        from PIL import Image
        img = Image.new("RGBA", (4, 4), (255, 255, 255, 255))
        # Make top-left pixel transparent
        img.putpixel((0, 0), (255, 0, 255, 0))
        img.putpixel((1, 1), (0, 0, 0, 255))
        path = tmp_path / "test.png"
        img.save(path)
        return path

    def test_load_image(self, simple_png):
        mgr = ImageManager({})
        img = mgr.load_image(simple_png)
        assert img.width == 4
        assert img.height == 4

    def test_unsupported_format(self, tmp_path):
        fake = tmp_path / "file.xyz"
        fake.write_bytes(b"")
        mgr = ImageManager({})
        with pytest.raises(ValueError, match="Unsupported format"):
            mgr.load_image(fake)

    def test_process_all_palettes(self, simple_png, simple_palette):
        mgr = ImageManager({})
        mgr.load_image(simple_png)
        results = mgr.process_all_palettes([simple_palette])
        assert len(results) == 1
        r = results[0]
        assert r.palette is simple_palette
        assert r.colors_used >= 1

    def test_save_and_reload(self, simple_png, simple_palette, tmp_path):
        mgr = ImageManager({})
        mgr.load_image(simple_png)
        results = mgr.process_all_palettes([simple_palette])
        out = tmp_path / "out.png"
        assert mgr.save_image(results[0], out)
        assert out.exists()

    def test_get_best_indices(self, simple_png, simple_palette):
        mgr = ImageManager({})
        mgr.load_image(simple_png)
        mgr.process_all_palettes([simple_palette])
        best = mgr.get_best_indices()
        assert isinstance(best, list)
        assert 0 in best


# ---------- PaletteExtractor ----------

class TestPaletteExtractor:
    @pytest.fixture
    def gradient_png(self, tmp_path):
        """Create a gradient PNG with more than 16 colors."""
        from PIL import Image
        import numpy as np
        arr = np.zeros((16, 16, 4), dtype=np.uint8)
        for i in range(16):
            arr[i, :, 0] = i * 16   # R gradient
            arr[i, :, 1] = 128
            arr[i, :, 2] = 255
            arr[i, :, 3] = 255
        arr[0, 0, 3] = 0            # one transparent pixel
        img = Image.fromarray(arr, "RGBA")
        path = tmp_path / "gradient.png"
        img.save(path)
        return path

    def test_extract_count(self, gradient_png):
        ext = PaletteExtractor()
        p = ext.extract(gradient_png, n_colors=16)
        assert 1 <= len(p.colors) <= 16

    def test_extract_gba_compatible(self, gradient_png):
        ext = PaletteExtractor()
        p = ext.extract(gradient_png, n_colors=16)
        assert p.is_gba_compatible()

    def test_extract_invalid_n_colors(self, gradient_png):
        ext = PaletteExtractor()
        with pytest.raises(ValueError):
            ext.extract(gradient_png, n_colors=17)

    def test_extract_saves_pal(self, gradient_png, tmp_path):
        ext = PaletteExtractor()
        p = ext.extract(gradient_png)
        out = tmp_path / "out.pal"
        p.to_jasc_pal(out)
        assert out.exists()
        loaded = Palette.from_jasc_pal(out)
        assert loaded.colors == p.colors
```

----

# view/__init__.py
```python
"""
PoryPal View Package
This package contains the view components for the PoryPal application's user interface.
"""

from .automation_view import AutomationView
from .palette_automation_view import PaletteAutomationView
from .porypal_view import PorypalView
from .tileset_editor_view import TilesetEditorView
from .zoomable_graphics_view import ZoomableGraphicsView
from .palette_display import PaletteDisplay
from .porypal_theme import PorypalTheme

__all__ = [
    'AutomationView',
    'PaletteAutomationView',
    'PorypalView',
    'TilesetEditorView',
    'ZoomableGraphicsView',
    'PaletteDisplay',
    'PorypalTheme'
]

__version__ = '2.0.0'
```

----

# view/automation_view.py
```python
# view/automation_view.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog
from PyQt5.QtCore import Qt
import os

class AutomationView(QWidget):
    """
    View for the automation feature that allows users to select input folder,
    preset file, output folder, and return to the tileset editor.
    """
    
    def __init__(self, controller):
        super().__init__()
        
        self.controller = controller
        
        # Set window properties
        self.setWindowTitle("PoryPal - Automation")
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self.setMinimumWidth(400)
        self.setMinimumHeight(250)
        
        # Create layout
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        # Add title
        self.title_label = QLabel("Automation")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title_label)
        
        # Add description
        self.description_label = QLabel("Apply a preset to multiple images in a folder")
        self.description_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.description_label)
        
        # Add status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.status_label)
        
        # Add buttons
        self.btn_input_folder = QPushButton("📁 Select Input Folder")
        self.btn_input_folder.setMinimumSize(136, 40)
        self.btn_input_folder.clicked.connect(self.select_input_folder)
        self.layout.addWidget(self.btn_input_folder)
        
        self.btn_preset = QPushButton("📋 Select Preset")
        self.btn_preset.setMinimumSize(136, 40)
        self.btn_preset.clicked.connect(self.select_preset)
        self.layout.addWidget(self.btn_preset)
        
        self.btn_output_folder = QPushButton("📂 Select Output Folder")
        self.btn_output_folder.setMinimumSize(136, 40)
        self.btn_output_folder.clicked.connect(self.select_output_folder)
        self.layout.addWidget(self.btn_output_folder)
        
        self.btn_start = QPushButton("▶️ Start Automation")
        self.btn_start.setMinimumSize(136, 40)
        self.btn_start.clicked.connect(self.start_automation)
        self.btn_start.setEnabled(False)
        self.layout.addWidget(self.btn_start)
        
        self.btn_return = QPushButton("↩️ Return to Tileset Editor")
        self.btn_return.setMinimumSize(136, 40)
        self.btn_return.clicked.connect(self.return_to_editor)
        self.layout.addWidget(self.btn_return)
        
        # Add stretch to push everything to the top
        self.layout.addStretch()
        
        # Initialize state
        self.input_folder = ""
        self.preset_file = ""
        self.output_folder = ""
        
        # Update status
        self.update_status()
    
    def select_input_folder(self):
        """Open dialog to select input folder."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Input Folder with Images", ""
        )
        
        if folder:
            self.input_folder = folder
            self.update_status()
    
    def select_preset(self):
        """Open dialog to select preset file."""
        preset_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "presets")
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Preset File", preset_folder, "JSON Files (*.json)"
        )
        
        if file_path:
            self.preset_file = file_path
            self.update_status()
    
    def select_output_folder(self):
        """Open dialog to select output folder."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", ""
        )
        
        if folder:
            self.output_folder = folder
            self.update_status()
    
    def update_status(self):
        """Update the status label and enable/disable the start button."""
        status_parts = []
        
        if self.input_folder:
            status_parts.append(f"Input: {os.path.basename(self.input_folder)}")
        else:
            status_parts.append("Input: Not selected")
            
        if self.preset_file:
            status_parts.append(f"Preset: {os.path.basename(self.preset_file)}")
        else:
            status_parts.append("Preset: Not selected")
            
        if self.output_folder:
            status_parts.append(f"Output: {os.path.basename(self.output_folder)}")
        else:
            status_parts.append("Output: Not selected")
            
        self.status_label.setText(" | ".join(status_parts))
        
        # Enable start button only if all selections are made
        self.btn_start.setEnabled(
            bool(self.input_folder) and 
            bool(self.preset_file) and 
            bool(self.output_folder)
        )
    
    def start_automation(self):
        """Start the automation process."""
        self.controller.start_automation(
            self.input_folder,
            self.preset_file,
            self.output_folder
        )
    
    def return_to_editor(self):
        """Return to the tileset editor."""
        self.controller.return_to_editor() ```

----

# view/palette_automation_view.py
```python
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog
from PyQt5.QtCore import Qt
import os

class PaletteAutomationView(QWidget):
    """
    View for the palette automation feature that allows users to select input folder,
    output folder, and return to the main palette application.
    """
    
    def __init__(self, controller):
        super().__init__()
        
        self.controller = controller
        
        # Set window properties
        self.setWindowTitle("PoryPal - Palette Automation")
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self.setMinimumWidth(400)
        self.setMinimumHeight(250)
        
        # Create layout
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        # Add title
        self.title_label = QLabel("Palette Automation")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title_label)
        
        # Add description
        self.description_label = QLabel("Process multiple images with the best matching palette")
        self.description_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.description_label)
        
        # Add status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.status_label)
        
        # Add buttons
        self.btn_input_folder = QPushButton("📁 Select Input Folder")
        self.btn_input_folder.setMinimumSize(136, 40)
        self.btn_input_folder.clicked.connect(self.select_input_folder)
        self.layout.addWidget(self.btn_input_folder)
        
        self.btn_output_folder = QPushButton("📂 Select Output Folder")
        self.btn_output_folder.setMinimumSize(136, 40)
        self.btn_output_folder.clicked.connect(self.select_output_folder)
        self.layout.addWidget(self.btn_output_folder)
        
        self.btn_start = QPushButton("▶️ Start Automation")
        self.btn_start.setMinimumSize(136, 40)
        self.btn_start.clicked.connect(self.start_automation)
        self.btn_start.setEnabled(False)
        self.layout.addWidget(self.btn_start)
        
        self.btn_return = QPushButton("↩️ Return to Main View")
        self.btn_return.setMinimumSize(136, 40)
        self.btn_return.clicked.connect(self.return_to_main)
        self.layout.addWidget(self.btn_return)
        
        # Add stretch to push everything to the top
        self.layout.addStretch()
        
        # Initialize state
        self.input_folder = ""
        self.output_folder = ""
        
        # Update status
        self.update_status()
    
    def select_input_folder(self):
        """Open dialog to select input folder."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Input Folder with Images", ""
        )
        
        if folder:
            self.input_folder = folder
            self.update_status()
    
    def select_output_folder(self):
        """Open dialog to select output folder."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", ""
        )
        
        if folder:
            self.output_folder = folder
            self.update_status()
    
    def update_status(self):
        """Update the status label and enable/disable the start button."""
        status_parts = []
        
        if self.input_folder:
            status_parts.append(f"Input: {os.path.basename(self.input_folder)}")
        else:
            status_parts.append("Input: Not selected")
            
        if self.output_folder:
            status_parts.append(f"Output: {os.path.basename(self.output_folder)}")
        else:
            status_parts.append("Output: Not selected")
            
        self.status_label.setText(" | ".join(status_parts))
        
        # Enable start button only if all selections are made
        self.btn_start.setEnabled(
            bool(self.input_folder) and 
            bool(self.output_folder)
        )
    
    def start_automation(self):
        """Start the automation process."""
        self.controller.start_automation(
            self.input_folder,
            self.output_folder
        )
    
    def return_to_main(self):
        """Return to the main palette application."""
        self.controller.return_to_main() ```

----

# view/palette_display.py
```python
from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtCore import Qt, QSize

class PaletteDisplay(QWidget):
    """Widget to display a 4x4 grid of palette colors with height-based scaling."""

    def __init__(self, colors=None, parent=None):
        super().__init__(parent)
        self.colors = colors or []
        
        # Set minimum size and size policy for height-based scaling
        self.setMinimumSize(40, 40)
        self.setMaximumSize(80, 80)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)
        self.setVisible(bool(self.colors))


    def paintEvent(self, event):
        """Paint the 4x4 grid of colors based on widget height."""
        if not self.colors:
            return

        painter = QPainter(self)

        # Calculate cell size based on the widget's height
        cell_size = self.height() // 4

        # Draw grid based on height
        for i in range(16):
            row, col = divmod(i, 4)
            x, y = col * cell_size, row * cell_size

            # Draw color if available, otherwise draw empty cell
            if i < len(self.colors):
                color = self.colors[i]
                if isinstance(color, QColor):
                    painter.fillRect(x, y, cell_size, cell_size, color)
                else:
                    painter.fillRect(x, y, cell_size, cell_size, QColor(*color))
            else:
                painter.setPen(Qt.gray)
                painter.drawRect(x, y, cell_size, cell_size)

            painter.setPen(Qt.black)
            painter.drawRect(x, y, cell_size, cell_size)

    def set_palette(self, colors):
        """Update the palette colors."""
        self.colors = colors or []
        self.setVisible(bool(self.colors))
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(80, 80)  # preferred size

    def minimumSizeHint(self) -> QSize:
        return QSize(40, 40)  # minimum size

    def resizeEvent(self, event):
        # Keep the widget square
        size = min(event.size().width(), event.size().height())
        self.setBaseSize(QSize(size, size))
        super().resizeEvent(event)  ```

----

# view/porypal_theme.py
```python
from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication
import yaml

class PorypalTheme:
    def __init__(self, app: QApplication, config: dict):
        self.app = app
        self.config = config
        self.app.setStyle('Fusion')  # OS agnostic style
        self._dark_mode = self.config.get('dark_mode')
        self.apply_theme()

    def set_dark_theme(self):
        self._dark_mode = True
        self.apply_theme()

    def set_light_theme(self):
        self._dark_mode = False
        self.apply_theme()

    def toggle_theme(self):
        self._dark_mode = not self._dark_mode
        self.apply_theme()

    def _hex_to_QColor(self, hex: str) -> QColor:
        return QColor(hex)

    def apply_theme(self):
        palette = QPalette()
        theme = dark_theme if self._dark_mode else light_theme

        for item in theme:
            if len(item) == 2:
                # Standard color setting
                palette.setColor(item[0], self._hex_to_QColor(item[1]))
            elif len(item) == 3:
                # Disabled state color setting (ColorGroup first, then ColorRole)
                palette.setColor(item[1], item[0], self._hex_to_QColor(item[2]))

        self.app.setPalette(palette)
        self.config['dark_mode'] = 'dark' if self._dark_mode else 'light'

        with open('config.yaml', 'w') as file:
            yaml.dump(self.config, file, default_flow_style=False)

# ----- THEMES ----- #
dark_theme = [
    (QPalette.Window, "#22272e"),
    (QPalette.WindowText, "#e6edf3"),
    (QPalette.Base, "#2d333b"),
    (QPalette.Text, "#cdd6e0"),
    (QPalette.Button, "#373e47"),
    (QPalette.ButtonText, "#e6edf3"),
    # Disabled state
    (QPalette.Button, QPalette.Disabled, "#2d3238"),
    (QPalette.ButtonText, QPalette.Disabled, "#abbfd0"),
]

light_theme = [
    (QPalette.Window, "#eae9f3"),
    (QPalette.WindowText, "#2b304b"),
    (QPalette.Base, "#ffffff"),
    (QPalette.Text, "#353549"),
    (QPalette.Button, "#dcdfec"),
    (QPalette.ButtonText, "#2b304b"),
    # Disabled state
    (QPalette.Button, QPalette.Disabled, "#a5acc8"),
    (QPalette.ButtonText, QPalette.Disabled, "#252839"),
]
```

----

# view/porypal_view.py
```python
# view/porypal_view.py
from PyQt5.QtCore import Qt, QRectF, QEvent
from PyQt5.QtGui import QPixmap, QScreen, QCursor
from PyQt5.QtWidgets import (
    QGraphicsScene, QGraphicsView, QLabel, QWidget, 
    QMessageBox, QHBoxLayout, QSizePolicy, 
    QApplication, QPushButton
)
from PyQt5 import uic
from model.palette_manager import Palette
from model.QNotificationWidget import QNotificationWidget

from view.palette_display import PaletteDisplay
from view.zoomable_graphics_view import ZoomableGraphicsView

import logging
import os
import sys

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class PorypalView(QWidget):
    """Main application view with dynamic resizing support."""

    CONFIRM_ON_EXIT = True
    MIN_WIDTH = 540
    MIN_HEIGHT = 600

    def __init__(self, parent, palettes: list[Palette]):
        super().__init__()
        ui_file = resource_path("view/porypalette.ui")
        uic.loadUi(ui_file, self)

        self.parent = parent

        self.notification = QNotificationWidget(self)
        
        # Add automation button
        self.btn_automate = QPushButton("⚙️ Automate", self)
        self.btn_automate.setMinimumSize(136, 40)
        self.btn_automate.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.processing_layout.addWidget(self.btn_automate)
        
        self.selected_index = None
        self.best_indices = []
        self.dynamic_views = []
        self.dynamic_labels = []
        self.dynamic_frames = []

        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)
        # self.setFixedSize(self.MIN_WIDTH, self.MIN_HEIGHT)

        # Get the screen where the mouse cursor is located
        cursor_pos = QCursor.pos()
        cursor_screen = QApplication.screenAt(cursor_pos)
        
        if cursor_screen:
            # Get the screen geometry
            screen_geometry = cursor_screen.availableGeometry()
            
            # Set window geometry to match the screen
            self.setGeometry(screen_geometry)
            
            # Position window at the top-left corner of the screen
            self.move(screen_geometry.x(), screen_geometry.y())
        else:
            # Fallback to primary screen if cursor screen can't be determined
            screen = QApplication.primaryScreen()
            screen_size = screen.availableGeometry()
            self.setGeometry(screen_size)
            self.move(cursor_pos.x(), cursor_pos.y())

        self._setup_original_view()
        self._setup_dynamic_views(palettes)

        self.content_layout.setStretch(0, 1)
        self.content_layout.setStretch(1, 1)


        self.show()

    def _setup_original_view(self):
        """Replace original QGraphicsView with a ZoomableGraphicsView."""
        layout = self.original_image_layout
        index = layout.indexOf(self.original_view)

        layout.removeWidget(self.original_view)
        self.original_view.hide()
        self.original_view.deleteLater()

        self.original_view = ZoomableGraphicsView(view=self)
        self.original_view.setMinimumWidth((int)(self.MIN_WIDTH*0.4))
        self.original_view.setMinimumHeight((int)(self.MIN_HEIGHT*0.3))
        self.original_view.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred
        )

        # self.original_view.setBorder(Qt.black, 1)

        layout.insertWidget(index, self.original_view, 1)

    def _setup_dynamic_views(self, palettes: list[Palette]):
        """Setup dynamic content with proper resizing behavior."""
        while self.dynamic_layout.count():
            item = self.dynamic_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()

        # # add label
        # label_output = QLabel("Output Images", self)
        # label_instruction = QLabel("🟢 = Selected Image\n🔵 = Recommended Image(s)",self)

        # self.dynamic_layout.addWidget(label_output)
        # self.dynamic_layout.addWidget(label_instruction)

        for palette in palettes:
            container = QWidget(self)
            container.setSizePolicy(
                QSizePolicy.Minimum, QSizePolicy.Minimum
            )
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(5, 5, 5, 5)
            container_layout.setSpacing(10)

            # Label: Only as wide as its text needs
            text = f"{palette.get_name()} ({len(palette.get_colors())} colors)"
            label = QLabel(text, container)
            preferred_width = self._get_text_width(text, label)
            label.setMaximumWidth(preferred_width)
            label.setMinimumWidth(min(60, preferred_width))
            label.setWordWrap(True)
            label.setSizePolicy(
                QSizePolicy.MinimumExpanding, QSizePolicy.Preferred
            )

            # Palette display: Square that maintains minimum size
            palette_4x4 = PaletteDisplay(palette.get_colors(), container)

            
            # View: Takes remaining horizontal space
            output_view = ZoomableGraphicsView(container, self, palettes.index(palette))
            # output_view.setMinimumWidth(int(self.MIN_HEIGHT * 0.2))
            # output_view.setMinimumHeight(int(self.MIN_HEIGHT * 0.2))
            # output_view.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
            # output_view.clicked.connect(lambda: self._handle_view_click(len(self.dynamic_views)))

            # Define frame to put view into
            frame = QWidget(container)
            frame.setStyleSheet("border: 1px solid transparent;")
            frame.setMaximumWidth((int)(self.width() * 0.4)) if self.width() == self.MIN_WIDTH else frame.setMaximumWidth((int)(self.width() * 0.6))
            frame.setMaximumHeight((int)(self.height()/len(palettes) * 0.6)) if self.height() == self.MIN_HEIGHT else frame.setMaximumHeight((int)(self.height() * 0.4))
            frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            frame_layout = QHBoxLayout(frame)
            frame_layout.addWidget(output_view)
            frame_layout.setContentsMargins(0, 0, 0, 0)
            # set 1px transparent border
            frame_layout.setSpacing(0)


            # Add widgets to layout
            container_layout.addWidget(label, 0)       # No stretch
            container_layout.addWidget(palette_4x4, 0) # No stretch
            # container_layout.addWidget(output_view, 1) # Takes remaining space
            container_layout.addWidget(frame, 1)

            self.dynamic_frames.append(frame)
            self.dynamic_views.append(output_view)
            self.dynamic_labels.append(label)
            self.dynamic_layout.addWidget(container)

    def _get_text_width(self, text: str, label: QLabel) -> int:
        return label.fontMetrics().boundingRect(text).width()

    def update_original_image(self, image):
        """Update the main preview image."""
        if image and not image.isNull():
            pixmap = QPixmap.fromImage(image)
            scene = QGraphicsScene(self.original_view)
            self.original_view.setScene(scene)
            scene.addPixmap(pixmap)
            scene.setSceneRect(QRectF(pixmap.rect()))

            self.original_view.resetTransform()
            self.original_view.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
            self.original_view.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)

    def update_dynamic_images(self, images, labels, palettes, highlights):
        """Update conversion results."""
        if not images:
            return

        max_colors = -1
        self.best_indices = []

        # Find images with most colors
        for i, label in enumerate(labels):
            color_count = int(label.split('(')[1].split(' ')[0])
            if color_count > max_colors:
                max_colors = color_count
                self.best_indices = [i]
            elif color_count == max_colors:
                self.best_indices.append(i)

        # Set selected index to first best index
        self.selected_index = self.best_indices[0] if self.best_indices else None

        # Update images and labels
        for i, (image, label, palette) in enumerate(zip(images, labels, palettes)):
            if i >= len(self.dynamic_views):
                break

            view = self.dynamic_views[i]
            pixmap = QPixmap.fromImage(image)
            
            scene = QGraphicsScene(view)
            view.setScene(scene)
            scene.addPixmap(pixmap)
            scene.setSceneRect(QRectF(pixmap.rect()))
            
            view.resetTransform()
            view.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
            view.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)

            self.dynamic_labels[i].setText(label)

        # Update highlights
        self._update_highlights()

    def _update_highlights(self):
        """Update view highlighting."""
        for i, view in enumerate(self.dynamic_frames):
            style = ""
            if i == self.selected_index:
                # style = "background-color: #458447; QGraphicsView {background-color: #22272e}" if self.parent._config.get('dark_mode') == "dark" \
                # else    "background-color: #7ebc80; QGraphicsView {background-color: #f2f2f2}"
                style = "border: 1px solid #458447"
            elif i in self.best_indices:
                style = "border: 1px solid #2196F3"  # Blue for best alternatives

            view.setStyleSheet(style)

    def _handle_view_click(self, index: int):
        """Handle click on a view."""
        if index is not None and self.parent.image_manager.get_original_image() is not None:
            self.selected_index = index
            self._update_highlights()

    # ------------ EVENT HANDLERS ------------ #
    def eventFilter(self, source, event):
        if event.type() == QEvent.MouseButtonPress:
            logging.debug("Event filter triggered")
            if source in self.dynamic_layout:
                index = self.dynamic_layout.index(source)
                logging.debug(f'View clicked: {index}')
                self._handle_view_click(index)
                return True
        return super().eventFilter(source, event)
    
    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() == Qt.Key_Escape:
            # Instead of showing the dialog here, just call close()
            # The confirmation will be handled by closeEvent
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Handle window close events."""
        if self.CONFIRM_ON_EXIT:
            reply = QMessageBox.question(
                self,
                'Confirm Exit',
                'Are you sure you want to exit?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
    # ------------ GETTERS ------------ #

    def get_selected_index(self) -> int:
        """Return currently selected view index."""
        return self.selected_index

```

----

# view/tileset_editor_view.py
```python
# view/tileset_editor_view.py
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtWidgets import QWidget, QGraphicsScene, QApplication, QMessageBox
from PyQt5.QtGui import QPixmap, QCursor
from PyQt5 import uic
import logging
import os
import sys
# from model.draggable_tile import DraggableTile
from model.tile_drop_area import TileDropArea
from model.QNotificationWidget import QNotificationWidget

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class TilesetEditorView(QWidget):
    """
    View for the tileset editor that displays the UI using the existing UI file.
    """
    CONFIRM_ON_EXIT = True
    
    def __init__(self, controller):
        super().__init__()
        
        # Load UI from file
        ui_file = resource_path("view/tileset_editor.ui")
        uic.loadUi(ui_file, self)
        
        self.controller = controller

        # Initialize scenes
        self.input_scene = QGraphicsScene(self)
        self.input_view.setScene(self.input_scene)
        
        # Replace output view's scene with TileDropArea
        self.output_scene = TileDropArea(self)
        self.output_view.setScene(self.output_scene)
        self.output_view.setAcceptDrops(True)
        
        # Initial state
        self.btn_save_tileset.setEnabled(False)
        self.btn_apply_grid.setEnabled(False)
        self.btn_create_layout.setEnabled(False)
        self.btn_clear_layout.setEnabled(False)

        # Initialize notifications        
        self.notification = QNotificationWidget(self)

        # Set window title
        self.setWindowTitle("PoryPal - Tileset Editor")
        
        # Get the screen where the mouse cursor is located
        cursor_pos = QCursor.pos()
        cursor_screen = QApplication.screenAt(cursor_pos)
        
        if cursor_screen:
            # Get the screen geometry
            screen_geometry = cursor_screen.availableGeometry()
            
            # Set window geometry to match the screen
            self.setGeometry(screen_geometry)
            
            # Position window at the top-left corner of the screen
            self.move(screen_geometry.x(), screen_geometry.y())
        else:
            # Fallback to primary screen if cursor screen can't be determined
            screen = QApplication.primaryScreen()
            screen_size = screen.availableGeometry()
            self.setGeometry(screen_size)
            self.move(cursor_pos.x(), cursor_pos.y())

    # ------------ DISPLAY HELPERS ------------ #
    def show_image(self, image, scene, view):
        """ Show image using Pixmap / fit in view"""
        try:
            pixmap = QPixmap.fromImage(image)
            scene.clear()
            scene.addPixmap(pixmap)
            scene.setSceneRect(QRectF(pixmap.rect()))
            view.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)
        except Exception as e:
            logging.error(f"Failed to load image: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load image: {e}")
            self.notification.show_error(f"Failed to load image: {e}")

    def update_preview_scene(self):
        """Updates the preview scene to display the selected tiles."""
        self.preview_scene.clear()  # Clear the preview scene before adding selected tiles

        for tile in self.controller.selected_tiles:
            # Add the selected tile to the preview scene (make sure the tile is visible)
            self.preview_scene.addPixmap(tile.pixmap()).setPos(tile.x(), tile.y())
    
    # ------------ EVENT HANDLERS ------------ #
    def resizeEvent(self, event):
        """Handle window resize."""
        super().resizeEvent(event)
        
        # Adjust views to maintain aspect ratio
        if not self.input_scene.sceneRect().isEmpty():
            self.input_view.fitInView(self.input_scene.sceneRect(), Qt.KeepAspectRatio)
            self.input_view.setProperty('canResizeHorizontally', True)

            
        if not self.output_scene.sceneRect().isEmpty():
            self.output_view.fitInView(self.output_scene.sceneRect(), Qt.KeepAspectRatio)
    
    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() == Qt.Key_Escape:
            if self.CONFIRM_ON_EXIT:
                reply = QMessageBox.question(
                    self,
                    'Confirm Exit',
                    'Are you sure you want to exit the tileset editor?',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    event.accept()
                    self.close()
                else:
                    event.ignore()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)```

----

# view/zoomable_graphics_view.py
```python
from PyQt5.QtWidgets import QGraphicsView, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QMouseEvent
import logging

class ZoomableGraphicsView(QGraphicsView):
    def __init__(self, parent=None, view=None, index=None):
        super().__init__(parent)
        self.clicked = QMouseEvent


        self.parent_view = view
        self.index = index

        # Disable antialiasing for sharp pixel edges
        self.setRenderHint(QPainter.Antialiasing, False)
        self.setRenderHint(QPainter.SmoothPixmapTransform, False)
        self.setRenderHint(QPainter.TextAntialiasing, False)
        
        # Set transform anchor to keep pixel alignment
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # Disable scrollbar animation for precise movement
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        
        # Set drag mode
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        
        # Initialize zoom parameters
        self.zoom_factor = 2.0  # Changed to 2.0 for pixel-perfect scaling
        self.current_zoom = 1.0
        
        # Create reset button
        self.reset_button = QPushButton("Reset View", self)
        self.reset_button.clicked.connect(self.reset_view)
        self.reset_button.setFixedSize(80, 30)
        self.reset_button.hide()  # Initially hidden
        
        # Store initial transform
        self.initial_transform = self.transform()
        
        # Initialize pan parameters
        self.panning = False
        self.last_pos = None
        
        # Set viewport update mode
        self.setViewportUpdateMode(QGraphicsView.MinimalViewportUpdate)

    def check_reset_button_visibility(self):
        """Check if the view needs the reset button."""
        if not self.scene():
            return

        # Check if we're zoomed
        is_default = abs(self.current_zoom - 1.0) < 0.001
        
        # Show/hide reset button accordingly
        self.reset_button.setVisible(not is_default)

    # ---- EVENTS ----- #

    def resizeEvent(self, event):
        super().resizeEvent(event)
        button_x = self.width() - self.reset_button.width() - 10
        self.reset_button.move(button_x, 10)
        # self.reset_view() # caused glitch due to false-positive with selection border

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            old_pos = self.mapToScene(event.pos())

            # Zoom in or out with power of 2 scaling
            if event.angleDelta().y() > 0:
                zoom_factor = self.zoom_factor
            else:
                zoom_factor = 1 / self.zoom_factor

            self.scale(zoom_factor, zoom_factor)
            self.current_zoom *= zoom_factor

            new_pos = self.mapToScene(event.pos())
            delta = new_pos - old_pos
            self.translate(delta.x(), delta.y())
            
            self.check_reset_button_visibility()
            event.accept()
        else:
            super().wheelEvent(event)

    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.panning = True
            self.last_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            logging.debug("Selected index: %s", self.index)
            self.parent_view._handle_view_click(self.index) if self.parent_view else None
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        # Check if panning is enabled
        if self.panning and self.last_pos is not None:
            # Calculate the delta between the current and last mouse positions
            delta = event.pos() - self.last_pos
            
            # Update the scroll bars to move the view by the delta
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y())
            
            # Update the last mouse position
            self.last_pos = event.pos()
            
            # Accept the event to prevent further processing
            event.accept()

    def reset_view(self):
        self.setTransform(self.initial_transform)
        self.current_zoom = 1.0
        
        if self.scene():
            self.setSceneRect(self.scene().itemsBoundingRect())
            self.fitInView(self.scene().itemsBoundingRect(), Qt.KeepAspectRatio)
        
        self.check_reset_button_visibility()
        self.update()

    def setScene(self, scene):
        super().setScene(scene)
        if scene:
            self.setSceneRect(scene.itemsBoundingRect())
            self.fitInView(scene.itemsBoundingRect(), Qt.KeepAspectRatio)
            self.initial_transform = self.transform()
            self.check_reset_button_visibility()
```

----

