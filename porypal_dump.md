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
__version__ = '3.0.0'
```

----

# controller/automation_controller.py
```python
# controller/automation_controller.py
import os
import json
import glob
import logging
from PySide6.QtWidgets import QMessageBox
from PySide6.QtGui import QImage, QPen, QBrush, QColor, QPainter
from PySide6.QtCore import Qt

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
from PySide6.QtWidgets import QMessageBox
from PySide6.QtGui import QImage

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

from PySide6.QtWidgets import QFileDialog, QApplication, QPushButton
from PySide6.QtGui import QImage
from PySide6.QtCore import QObject, Slot

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
        if dialog.exec():
            return dialog.selectedFiles()[0]
        return ""
    
    # ------------ LOAD IMAGE ------------ #
    @Slot()
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
    @Slot()
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
    @Slot()
    def extract_palette(self) -> None:
        """Extract palette from the input image."""
        self.image_manager.extract_palette()
        self.view.notification.show_success("Palette extracted successfully!")

    # ------------ THEME TOGGLE ------------ #
    @Slot()
    def toggle_theme(self) -> None:
        """Toggle application theme."""
        self._theme.toggle_theme()

    # ------------ TILESET LOADING ------------ #

    @Slot()
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
    @Slot()
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
    
    @Slot()
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

from PySide6.QtGui import QImage, QPixmap, QPen, QColor, QPainter, QBrush
from PySide6.QtWidgets import QFileDialog, QMessageBox, QGraphicsPixmapItem, QGraphicsRectItem, QApplication
from PySide6.QtCore import QObject, Slot, QRectF, Qt, QPoint
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
    @Slot()
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

    @Slot()
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

    @Slot()
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

    @Slot()
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

    @Slot()
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

        from PySide6.QtGui import QPen, QColor
        pen = QPen(QColor(200, 200, 200, 100))
        for x in range(0, width + 1, tile_width):
            self.view.output_scene.addLine(x, 0, x, height, pen)
        for y in range(0, height + 1, tile_height):
            self.view.output_scene.addLine(0, y, width, y, pen)

        # Update UI state
        self.view.btn_save_preset.setEnabled(False)  # Disable save preset button

        self.view.notification.show_notification("Output layout cleared")
        self.update_info_label()

    @Slot()
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
    
    @Slot()
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
    
    @Slot()
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

    @Slot()
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

# frontend/node_modules/.package-lock.json
```json
{
  "name": "porypal-frontend",
  "version": "3.0.0",
  "lockfileVersion": 3,
  "requires": true,
  "packages": {
    "node_modules/@babel/code-frame": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/code-frame/-/code-frame-7.29.0.tgz",
      "integrity": "sha512-9NhCeYjq9+3uxgdtp20LSiJXJvN0FeCtNGpJxuMFZ1Kv3cWUNb6DOhJwUvcVCzKGR66cw4njwM6hrJLqgOwbcw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/helper-validator-identifier": "^7.28.5",
        "js-tokens": "^4.0.0",
        "picocolors": "^1.1.1"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/compat-data": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/compat-data/-/compat-data-7.29.0.tgz",
      "integrity": "sha512-T1NCJqT/j9+cn8fvkt7jtwbLBfLC/1y1c7NtCeXFRgzGTsafi68MRv8yzkYSapBnFA6L3U2VSc02ciDzoAJhJg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/core": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/core/-/core-7.29.0.tgz",
      "integrity": "sha512-CGOfOJqWjg2qW/Mb6zNsDm+u5vFQ8DxXfbM09z69p5Z6+mE1ikP2jUXw+j42Pf1XTYED2Rni5f95npYeuwMDQA==",
      "dev": true,
      "license": "MIT",
      "peer": true,
      "dependencies": {
        "@babel/code-frame": "^7.29.0",
        "@babel/generator": "^7.29.0",
        "@babel/helper-compilation-targets": "^7.28.6",
        "@babel/helper-module-transforms": "^7.28.6",
        "@babel/helpers": "^7.28.6",
        "@babel/parser": "^7.29.0",
        "@babel/template": "^7.28.6",
        "@babel/traverse": "^7.29.0",
        "@babel/types": "^7.29.0",
        "@jridgewell/remapping": "^2.3.5",
        "convert-source-map": "^2.0.0",
        "debug": "^4.1.0",
        "gensync": "^1.0.0-beta.2",
        "json5": "^2.2.3",
        "semver": "^6.3.1"
      },
      "engines": {
        "node": ">=6.9.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/babel"
      }
    },
    "node_modules/@babel/generator": {
      "version": "7.29.1",
      "resolved": "https://registry.npmjs.org/@babel/generator/-/generator-7.29.1.tgz",
      "integrity": "sha512-qsaF+9Qcm2Qv8SRIMMscAvG4O3lJ0F1GuMo5HR/Bp02LopNgnZBC/EkbevHFeGs4ls/oPz9v+Bsmzbkbe+0dUw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/parser": "^7.29.0",
        "@babel/types": "^7.29.0",
        "@jridgewell/gen-mapping": "^0.3.12",
        "@jridgewell/trace-mapping": "^0.3.28",
        "jsesc": "^3.0.2"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-compilation-targets": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/helper-compilation-targets/-/helper-compilation-targets-7.28.6.tgz",
      "integrity": "sha512-JYtls3hqi15fcx5GaSNL7SCTJ2MNmjrkHXg4FSpOA/grxK8KwyZ5bubHsCq8FXCkua6xhuaaBit+3b7+VZRfcA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/compat-data": "^7.28.6",
        "@babel/helper-validator-option": "^7.27.1",
        "browserslist": "^4.24.0",
        "lru-cache": "^5.1.1",
        "semver": "^6.3.1"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-globals": {
      "version": "7.28.0",
      "resolved": "https://registry.npmjs.org/@babel/helper-globals/-/helper-globals-7.28.0.tgz",
      "integrity": "sha512-+W6cISkXFa1jXsDEdYA8HeevQT/FULhxzR99pxphltZcVaugps53THCeiWA8SguxxpSp3gKPiuYfSWopkLQ4hw==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-module-imports": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/helper-module-imports/-/helper-module-imports-7.28.6.tgz",
      "integrity": "sha512-l5XkZK7r7wa9LucGw9LwZyyCUscb4x37JWTPz7swwFE/0FMQAGpiWUZn8u9DzkSBWEcK25jmvubfpw2dnAMdbw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/traverse": "^7.28.6",
        "@babel/types": "^7.28.6"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-module-transforms": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/helper-module-transforms/-/helper-module-transforms-7.28.6.tgz",
      "integrity": "sha512-67oXFAYr2cDLDVGLXTEABjdBJZ6drElUSI7WKp70NrpyISso3plG9SAGEF6y7zbha/wOzUByWWTJvEDVNIUGcA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/helper-module-imports": "^7.28.6",
        "@babel/helper-validator-identifier": "^7.28.5",
        "@babel/traverse": "^7.28.6"
      },
      "engines": {
        "node": ">=6.9.0"
      },
      "peerDependencies": {
        "@babel/core": "^7.0.0"
      }
    },
    "node_modules/@babel/helper-plugin-utils": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/helper-plugin-utils/-/helper-plugin-utils-7.28.6.tgz",
      "integrity": "sha512-S9gzZ/bz83GRysI7gAD4wPT/AI3uCnY+9xn+Mx/KPs2JwHJIz1W8PZkg2cqyt3RNOBM8ejcXhV6y8Og7ly/Dug==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-string-parser": {
      "version": "7.27.1",
      "resolved": "https://registry.npmjs.org/@babel/helper-string-parser/-/helper-string-parser-7.27.1.tgz",
      "integrity": "sha512-qMlSxKbpRlAridDExk92nSobyDdpPijUq2DW6oDnUqd0iOGxmQjyqhMIihI9+zv4LPyZdRje2cavWPbCbWm3eA==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-validator-identifier": {
      "version": "7.28.5",
      "resolved": "https://registry.npmjs.org/@babel/helper-validator-identifier/-/helper-validator-identifier-7.28.5.tgz",
      "integrity": "sha512-qSs4ifwzKJSV39ucNjsvc6WVHs6b7S03sOh2OcHF9UHfVPqWWALUsNUVzhSBiItjRZoLHx7nIarVjqKVusUZ1Q==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-validator-option": {
      "version": "7.27.1",
      "resolved": "https://registry.npmjs.org/@babel/helper-validator-option/-/helper-validator-option-7.27.1.tgz",
      "integrity": "sha512-YvjJow9FxbhFFKDSuFnVCe2WxXk1zWc22fFePVNEaWJEu8IrZVlda6N0uHwzZrUM1il7NC9Mlp4MaJYbYd9JSg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helpers": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/helpers/-/helpers-7.28.6.tgz",
      "integrity": "sha512-xOBvwq86HHdB7WUDTfKfT/Vuxh7gElQ+Sfti2Cy6yIWNW05P8iUslOVcZ4/sKbE+/jQaukQAdz/gf3724kYdqw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/template": "^7.28.6",
        "@babel/types": "^7.28.6"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/parser": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/parser/-/parser-7.29.0.tgz",
      "integrity": "sha512-IyDgFV5GeDUVX4YdF/3CPULtVGSXXMLh1xVIgdCgxApktqnQV0r7/8Nqthg+8YLGaAtdyIlo2qIdZrbCv4+7ww==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/types": "^7.29.0"
      },
      "bin": {
        "parser": "bin/babel-parser.js"
      },
      "engines": {
        "node": ">=6.0.0"
      }
    },
    "node_modules/@babel/plugin-transform-react-jsx-self": {
      "version": "7.27.1",
      "resolved": "https://registry.npmjs.org/@babel/plugin-transform-react-jsx-self/-/plugin-transform-react-jsx-self-7.27.1.tgz",
      "integrity": "sha512-6UzkCs+ejGdZ5mFFC/OCUrv028ab2fp1znZmCZjAOBKiBK2jXD1O+BPSfX8X2qjJ75fZBMSnQn3Rq2mrBJK2mw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/helper-plugin-utils": "^7.27.1"
      },
      "engines": {
        "node": ">=6.9.0"
      },
      "peerDependencies": {
        "@babel/core": "^7.0.0-0"
      }
    },
    "node_modules/@babel/plugin-transform-react-jsx-source": {
      "version": "7.27.1",
      "resolved": "https://registry.npmjs.org/@babel/plugin-transform-react-jsx-source/-/plugin-transform-react-jsx-source-7.27.1.tgz",
      "integrity": "sha512-zbwoTsBruTeKB9hSq73ha66iFeJHuaFkUbwvqElnygoNbj/jHRsSeokowZFN3CZ64IvEqcmmkVe89OPXc7ldAw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/helper-plugin-utils": "^7.27.1"
      },
      "engines": {
        "node": ">=6.9.0"
      },
      "peerDependencies": {
        "@babel/core": "^7.0.0-0"
      }
    },
    "node_modules/@babel/template": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/template/-/template-7.28.6.tgz",
      "integrity": "sha512-YA6Ma2KsCdGb+WC6UpBVFJGXL58MDA6oyONbjyF/+5sBgxY/dwkhLogbMT2GXXyU84/IhRw/2D1Os1B/giz+BQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/code-frame": "^7.28.6",
        "@babel/parser": "^7.28.6",
        "@babel/types": "^7.28.6"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/traverse": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/traverse/-/traverse-7.29.0.tgz",
      "integrity": "sha512-4HPiQr0X7+waHfyXPZpWPfWL/J7dcN1mx9gL6WdQVMbPnF3+ZhSMs8tCxN7oHddJE9fhNE7+lxdnlyemKfJRuA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/code-frame": "^7.29.0",
        "@babel/generator": "^7.29.0",
        "@babel/helper-globals": "^7.28.0",
        "@babel/parser": "^7.29.0",
        "@babel/template": "^7.28.6",
        "@babel/types": "^7.29.0",
        "debug": "^4.3.1"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/types": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/types/-/types-7.29.0.tgz",
      "integrity": "sha512-LwdZHpScM4Qz8Xw2iKSzS+cfglZzJGvofQICy7W7v4caru4EaAmyUuO6BGrbyQ2mYV11W0U8j5mBhd14dd3B0A==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/helper-string-parser": "^7.27.1",
        "@babel/helper-validator-identifier": "^7.28.5"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@esbuild/win32-x64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/win32-x64/-/win32-x64-0.21.5.tgz",
      "integrity": "sha512-tQd/1efJuzPC6rCFwEvLtci/xNFcTZknmXs98FYDfGE4wP9ClFV98nyKrzJKVPMhdDnjzLhdUyMX4PsQAPjwIw==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@jridgewell/gen-mapping": {
      "version": "0.3.13",
      "resolved": "https://registry.npmjs.org/@jridgewell/gen-mapping/-/gen-mapping-0.3.13.tgz",
      "integrity": "sha512-2kkt/7niJ6MgEPxF0bYdQ6etZaA+fQvDcLKckhy1yIQOzaoKjBBjSj63/aLVjYE3qhRt5dvM+uUyfCg6UKCBbA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@jridgewell/sourcemap-codec": "^1.5.0",
        "@jridgewell/trace-mapping": "^0.3.24"
      }
    },
    "node_modules/@jridgewell/remapping": {
      "version": "2.3.5",
      "resolved": "https://registry.npmjs.org/@jridgewell/remapping/-/remapping-2.3.5.tgz",
      "integrity": "sha512-LI9u/+laYG4Ds1TDKSJW2YPrIlcVYOwi2fUC6xB43lueCjgxV4lffOCZCtYFiH6TNOX+tQKXx97T4IKHbhyHEQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@jridgewell/gen-mapping": "^0.3.5",
        "@jridgewell/trace-mapping": "^0.3.24"
      }
    },
    "node_modules/@jridgewell/resolve-uri": {
      "version": "3.1.2",
      "resolved": "https://registry.npmjs.org/@jridgewell/resolve-uri/-/resolve-uri-3.1.2.tgz",
      "integrity": "sha512-bRISgCIjP20/tbWSPWMEi54QVPRZExkuD9lJL+UIxUKtwVJA8wW1Trb1jMs1RFXo1CBTNZ/5hpC9QvmKWdopKw==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.0.0"
      }
    },
    "node_modules/@jridgewell/sourcemap-codec": {
      "version": "1.5.5",
      "resolved": "https://registry.npmjs.org/@jridgewell/sourcemap-codec/-/sourcemap-codec-1.5.5.tgz",
      "integrity": "sha512-cYQ9310grqxueWbl+WuIUIaiUaDcj7WOq5fVhEljNVgRfOUhY9fy2zTvfoqWsnebh8Sl70VScFbICvJnLKB0Og==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@jridgewell/trace-mapping": {
      "version": "0.3.31",
      "resolved": "https://registry.npmjs.org/@jridgewell/trace-mapping/-/trace-mapping-0.3.31.tgz",
      "integrity": "sha512-zzNR+SdQSDJzc8joaeP8QQoCQr8NuYx2dIIytl1QeBEZHJ9uW6hebsrYgbz8hJwUQao3TWCMtmfV8Nu1twOLAw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@jridgewell/resolve-uri": "^3.1.0",
        "@jridgewell/sourcemap-codec": "^1.4.14"
      }
    },
    "node_modules/@rolldown/pluginutils": {
      "version": "1.0.0-beta.27",
      "resolved": "https://registry.npmjs.org/@rolldown/pluginutils/-/pluginutils-1.0.0-beta.27.tgz",
      "integrity": "sha512-+d0F4MKMCbeVUJwG96uQ4SgAznZNSq93I3V+9NHA4OpvqG8mRCpGdKmK8l/dl02h2CCDHwW2FqilnTyDcAnqjA==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@rollup/rollup-win32-x64-gnu": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-win32-x64-gnu/-/rollup-win32-x64-gnu-4.59.0.tgz",
      "integrity": "sha512-laBkYlSS1n2L8fSo1thDNGrCTQMmxjYY5G0WFWjFFYZkKPjsMBsgJfGf4TLxXrF6RyhI60L8TMOjBMvXiTcxeA==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ]
    },
    "node_modules/@rollup/rollup-win32-x64-msvc": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-win32-x64-msvc/-/rollup-win32-x64-msvc-4.59.0.tgz",
      "integrity": "sha512-2HRCml6OztYXyJXAvdDXPKcawukWY2GpR5/nxKp4iBgiO3wcoEGkAaqctIbZcNB6KlUQBIqt8VYkNSj2397EfA==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ]
    },
    "node_modules/@types/babel__core": {
      "version": "7.20.5",
      "resolved": "https://registry.npmjs.org/@types/babel__core/-/babel__core-7.20.5.tgz",
      "integrity": "sha512-qoQprZvz5wQFJwMDqeseRXWv3rqMvhgpbXFfVyWhbx9X47POIA6i/+dXefEmZKoAgOaTdaIgNSMqMIU61yRyzA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/parser": "^7.20.7",
        "@babel/types": "^7.20.7",
        "@types/babel__generator": "*",
        "@types/babel__template": "*",
        "@types/babel__traverse": "*"
      }
    },
    "node_modules/@types/babel__generator": {
      "version": "7.27.0",
      "resolved": "https://registry.npmjs.org/@types/babel__generator/-/babel__generator-7.27.0.tgz",
      "integrity": "sha512-ufFd2Xi92OAVPYsy+P4n7/U7e68fex0+Ee8gSG9KX7eo084CWiQ4sdxktvdl0bOPupXtVJPY19zk6EwWqUQ8lg==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/types": "^7.0.0"
      }
    },
    "node_modules/@types/babel__template": {
      "version": "7.4.4",
      "resolved": "https://registry.npmjs.org/@types/babel__template/-/babel__template-7.4.4.tgz",
      "integrity": "sha512-h/NUaSyG5EyxBIp8YRxo4RMe2/qQgvyowRwVMzhYhBCONbW8PUsg4lkFMrhgZhUe5z3L3MiLDuvyJ/CaPa2A8A==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/parser": "^7.1.0",
        "@babel/types": "^7.0.0"
      }
    },
    "node_modules/@types/babel__traverse": {
      "version": "7.28.0",
      "resolved": "https://registry.npmjs.org/@types/babel__traverse/-/babel__traverse-7.28.0.tgz",
      "integrity": "sha512-8PvcXf70gTDZBgt9ptxJ8elBeBjcLOAcOtoO/mPJjtji1+CdGbHgm77om1GrsPxsiE+uXIpNSK64UYaIwQXd4Q==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/types": "^7.28.2"
      }
    },
    "node_modules/@types/estree": {
      "version": "1.0.8",
      "resolved": "https://registry.npmjs.org/@types/estree/-/estree-1.0.8.tgz",
      "integrity": "sha512-dWHzHa2WqEXI/O1E9OjrocMTKJl2mSrEolh1Iomrv6U+JuNwaHXsXx9bLu5gG7BUWFIN0skIQJQ/L1rIex4X6w==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@types/prop-types": {
      "version": "15.7.15",
      "resolved": "https://registry.npmjs.org/@types/prop-types/-/prop-types-15.7.15.tgz",
      "integrity": "sha512-F6bEyamV9jKGAFBEmlQnesRPGOQqS2+Uwi0Em15xenOxHaf2hv6L8YCVn3rPdPJOiJfPiCnLIRyvwVaqMY3MIw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@types/react": {
      "version": "18.3.28",
      "resolved": "https://registry.npmjs.org/@types/react/-/react-18.3.28.tgz",
      "integrity": "sha512-z9VXpC7MWrhfWipitjNdgCauoMLRdIILQsAEV+ZesIzBq/oUlxk0m3ApZuMFCXdnS4U7KrI+l3WRUEGQ8K1QKw==",
      "dev": true,
      "license": "MIT",
      "peer": true,
      "dependencies": {
        "@types/prop-types": "*",
        "csstype": "^3.2.2"
      }
    },
    "node_modules/@types/react-dom": {
      "version": "18.3.7",
      "resolved": "https://registry.npmjs.org/@types/react-dom/-/react-dom-18.3.7.tgz",
      "integrity": "sha512-MEe3UeoENYVFXzoXEWsvcpg6ZvlrFNlOQ7EOsvhI3CfAXwzPfO8Qwuxd40nepsYKqyyVQnTdEfv68q91yLcKrQ==",
      "dev": true,
      "license": "MIT",
      "peerDependencies": {
        "@types/react": "^18.0.0"
      }
    },
    "node_modules/@vitejs/plugin-react": {
      "version": "4.7.0",
      "resolved": "https://registry.npmjs.org/@vitejs/plugin-react/-/plugin-react-4.7.0.tgz",
      "integrity": "sha512-gUu9hwfWvvEDBBmgtAowQCojwZmJ5mcLn3aufeCsitijs3+f2NsrPtlAWIR6OPiqljl96GVCUbLe0HyqIpVaoA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/core": "^7.28.0",
        "@babel/plugin-transform-react-jsx-self": "^7.27.1",
        "@babel/plugin-transform-react-jsx-source": "^7.27.1",
        "@rolldown/pluginutils": "1.0.0-beta.27",
        "@types/babel__core": "^7.20.5",
        "react-refresh": "^0.17.0"
      },
      "engines": {
        "node": "^14.18.0 || >=16.0.0"
      },
      "peerDependencies": {
        "vite": "^4.2.0 || ^5.0.0 || ^6.0.0 || ^7.0.0"
      }
    },
    "node_modules/baseline-browser-mapping": {
      "version": "2.10.8",
      "resolved": "https://registry.npmjs.org/baseline-browser-mapping/-/baseline-browser-mapping-2.10.8.tgz",
      "integrity": "sha512-PCLz/LXGBsNTErbtB6i5u4eLpHeMfi93aUv5duMmj6caNu6IphS4q6UevDnL36sZQv9lrP11dbPKGMaXPwMKfQ==",
      "dev": true,
      "license": "Apache-2.0",
      "bin": {
        "baseline-browser-mapping": "dist/cli.cjs"
      },
      "engines": {
        "node": ">=6.0.0"
      }
    },
    "node_modules/browserslist": {
      "version": "4.28.1",
      "resolved": "https://registry.npmjs.org/browserslist/-/browserslist-4.28.1.tgz",
      "integrity": "sha512-ZC5Bd0LgJXgwGqUknZY/vkUQ04r8NXnJZ3yYi4vDmSiZmC/pdSN0NbNRPxZpbtO4uAfDUAFffO8IZoM3Gj8IkA==",
      "dev": true,
      "funding": [
        {
          "type": "opencollective",
          "url": "https://opencollective.com/browserslist"
        },
        {
          "type": "tidelift",
          "url": "https://tidelift.com/funding/github/npm/browserslist"
        },
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "MIT",
      "peer": true,
      "dependencies": {
        "baseline-browser-mapping": "^2.9.0",
        "caniuse-lite": "^1.0.30001759",
        "electron-to-chromium": "^1.5.263",
        "node-releases": "^2.0.27",
        "update-browserslist-db": "^1.2.0"
      },
      "bin": {
        "browserslist": "cli.js"
      },
      "engines": {
        "node": "^6 || ^7 || ^8 || ^9 || ^10 || ^11 || ^12 || >=13.7"
      }
    },
    "node_modules/caniuse-lite": {
      "version": "1.0.30001779",
      "resolved": "https://registry.npmjs.org/caniuse-lite/-/caniuse-lite-1.0.30001779.tgz",
      "integrity": "sha512-U5og2PN7V4DMgF50YPNtnZJGWVLFjjsN3zb6uMT5VGYIewieDj1upwfuVNXf4Kor+89c3iCRJnSzMD5LmTvsfA==",
      "dev": true,
      "funding": [
        {
          "type": "opencollective",
          "url": "https://opencollective.com/browserslist"
        },
        {
          "type": "tidelift",
          "url": "https://tidelift.com/funding/github/npm/caniuse-lite"
        },
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "CC-BY-4.0"
    },
    "node_modules/convert-source-map": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/convert-source-map/-/convert-source-map-2.0.0.tgz",
      "integrity": "sha512-Kvp459HrV2FEJ1CAsi1Ku+MY3kasH19TFykTz2xWmMeq6bk2NU3XXvfJ+Q61m0xktWwt+1HSYf3JZsTms3aRJg==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/csstype": {
      "version": "3.2.3",
      "resolved": "https://registry.npmjs.org/csstype/-/csstype-3.2.3.tgz",
      "integrity": "sha512-z1HGKcYy2xA8AGQfwrn0PAy+PB7X/GSj3UVJW9qKyn43xWa+gl5nXmU4qqLMRzWVLFC8KusUX8T/0kCiOYpAIQ==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/debug": {
      "version": "4.4.3",
      "resolved": "https://registry.npmjs.org/debug/-/debug-4.4.3.tgz",
      "integrity": "sha512-RGwwWnwQvkVfavKVt22FGLw+xYSdzARwm0ru6DhTVA3umU5hZc28V3kO4stgYryrTlLpuvgI9GiijltAjNbcqA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "ms": "^2.1.3"
      },
      "engines": {
        "node": ">=6.0"
      },
      "peerDependenciesMeta": {
        "supports-color": {
          "optional": true
        }
      }
    },
    "node_modules/electron-to-chromium": {
      "version": "1.5.313",
      "resolved": "https://registry.npmjs.org/electron-to-chromium/-/electron-to-chromium-1.5.313.tgz",
      "integrity": "sha512-QBMrTWEf00GXZmJyx2lbYD45jpI3TUFnNIzJ5BBc8piGUDwMPa1GV6HJWTZVvY/eiN3fSopl7NRbgGp9sZ9LTA==",
      "dev": true,
      "license": "ISC"
    },
    "node_modules/esbuild": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/esbuild/-/esbuild-0.21.5.tgz",
      "integrity": "sha512-mg3OPMV4hXywwpoDxu3Qda5xCKQi+vCTZq8S9J/EpkhB2HzKXq4SNFZE3+NK93JYxc8VMSep+lOUSC/RVKaBqw==",
      "dev": true,
      "hasInstallScript": true,
      "license": "MIT",
      "bin": {
        "esbuild": "bin/esbuild"
      },
      "engines": {
        "node": ">=12"
      },
      "optionalDependencies": {
        "@esbuild/aix-ppc64": "0.21.5",
        "@esbuild/android-arm": "0.21.5",
        "@esbuild/android-arm64": "0.21.5",
        "@esbuild/android-x64": "0.21.5",
        "@esbuild/darwin-arm64": "0.21.5",
        "@esbuild/darwin-x64": "0.21.5",
        "@esbuild/freebsd-arm64": "0.21.5",
        "@esbuild/freebsd-x64": "0.21.5",
        "@esbuild/linux-arm": "0.21.5",
        "@esbuild/linux-arm64": "0.21.5",
        "@esbuild/linux-ia32": "0.21.5",
        "@esbuild/linux-loong64": "0.21.5",
        "@esbuild/linux-mips64el": "0.21.5",
        "@esbuild/linux-ppc64": "0.21.5",
        "@esbuild/linux-riscv64": "0.21.5",
        "@esbuild/linux-s390x": "0.21.5",
        "@esbuild/linux-x64": "0.21.5",
        "@esbuild/netbsd-x64": "0.21.5",
        "@esbuild/openbsd-x64": "0.21.5",
        "@esbuild/sunos-x64": "0.21.5",
        "@esbuild/win32-arm64": "0.21.5",
        "@esbuild/win32-ia32": "0.21.5",
        "@esbuild/win32-x64": "0.21.5"
      }
    },
    "node_modules/escalade": {
      "version": "3.2.0",
      "resolved": "https://registry.npmjs.org/escalade/-/escalade-3.2.0.tgz",
      "integrity": "sha512-WUj2qlxaQtO4g6Pq5c29GTcWGDyd8itL8zTlipgECz3JesAiiOKotd8JU6otB3PACgG6xkJUyVhboMS+bje/jA==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6"
      }
    },
    "node_modules/gensync": {
      "version": "1.0.0-beta.2",
      "resolved": "https://registry.npmjs.org/gensync/-/gensync-1.0.0-beta.2.tgz",
      "integrity": "sha512-3hN7NaskYvMDLQY55gnW3NQ+mesEAepTqlg+VEbj7zzqEMBVNhzcGYYeqFo/TlYz6eQiFcp1HcsCZO+nGgS8zg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/js-tokens": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/js-tokens/-/js-tokens-4.0.0.tgz",
      "integrity": "sha512-RdJUflcE3cUzKiMqQgsCu06FPu9UdIJO0beYbPhHN4k6apgJtifcoCtT9bcxOpYBtpD2kCM6Sbzg4CausW/PKQ==",
      "license": "MIT"
    },
    "node_modules/jsesc": {
      "version": "3.1.0",
      "resolved": "https://registry.npmjs.org/jsesc/-/jsesc-3.1.0.tgz",
      "integrity": "sha512-/sM3dO2FOzXjKQhJuo0Q173wf2KOo8t4I8vHy6lF9poUp7bKT0/NHE8fPX23PwfhnykfqnC2xRxOnVw5XuGIaA==",
      "dev": true,
      "license": "MIT",
      "bin": {
        "jsesc": "bin/jsesc"
      },
      "engines": {
        "node": ">=6"
      }
    },
    "node_modules/json5": {
      "version": "2.2.3",
      "resolved": "https://registry.npmjs.org/json5/-/json5-2.2.3.tgz",
      "integrity": "sha512-XmOWe7eyHYH14cLdVPoyg+GOH3rYX++KpzrylJwSW98t3Nk+U8XOl8FWKOgwtzdb8lXGf6zYwDUzeHMWfxasyg==",
      "dev": true,
      "license": "MIT",
      "bin": {
        "json5": "lib/cli.js"
      },
      "engines": {
        "node": ">=6"
      }
    },
    "node_modules/loose-envify": {
      "version": "1.4.0",
      "resolved": "https://registry.npmjs.org/loose-envify/-/loose-envify-1.4.0.tgz",
      "integrity": "sha512-lyuxPGr/Wfhrlem2CL/UcnUc1zcqKAImBDzukY7Y5F/yQiNdko6+fRLevlw1HgMySw7f611UIY408EtxRSoK3Q==",
      "license": "MIT",
      "dependencies": {
        "js-tokens": "^3.0.0 || ^4.0.0"
      },
      "bin": {
        "loose-envify": "cli.js"
      }
    },
    "node_modules/lru-cache": {
      "version": "5.1.1",
      "resolved": "https://registry.npmjs.org/lru-cache/-/lru-cache-5.1.1.tgz",
      "integrity": "sha512-KpNARQA3Iwv+jTA0utUVVbrh+Jlrr1Fv0e56GGzAFOXN7dk/FviaDW8LHmK52DlcH4WP2n6gI8vN1aesBFgo9w==",
      "dev": true,
      "license": "ISC",
      "dependencies": {
        "yallist": "^3.0.2"
      }
    },
    "node_modules/lucide-react": {
      "version": "0.577.0",
      "resolved": "https://registry.npmjs.org/lucide-react/-/lucide-react-0.577.0.tgz",
      "integrity": "sha512-4LjoFv2eEPwYDPg/CUdBJQSDfPyzXCRrVW1X7jrx/trgxnxkHFjnVZINbzvzxjN70dxychOfg+FTYwBiS3pQ5A==",
      "license": "ISC",
      "peerDependencies": {
        "react": "^16.5.1 || ^17.0.0 || ^18.0.0 || ^19.0.0"
      }
    },
    "node_modules/ms": {
      "version": "2.1.3",
      "resolved": "https://registry.npmjs.org/ms/-/ms-2.1.3.tgz",
      "integrity": "sha512-6FlzubTLZG3J2a/NVCAleEhjzq5oxgHyaCU9yYXvcLsvoVaHJq/s5xXI6/XXP6tz7R9xAOtHnSO/tXtF3WRTlA==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/nanoid": {
      "version": "3.3.11",
      "resolved": "https://registry.npmjs.org/nanoid/-/nanoid-3.3.11.tgz",
      "integrity": "sha512-N8SpfPUnUp1bK+PMYW8qSWdl9U+wwNWI4QKxOYDy9JAro3WMX7p2OeVRF9v+347pnakNevPmiHhNmZ2HbFA76w==",
      "dev": true,
      "funding": [
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "MIT",
      "bin": {
        "nanoid": "bin/nanoid.cjs"
      },
      "engines": {
        "node": "^10 || ^12 || ^13.7 || ^14 || >=15.0.1"
      }
    },
    "node_modules/node-releases": {
      "version": "2.0.36",
      "resolved": "https://registry.npmjs.org/node-releases/-/node-releases-2.0.36.tgz",
      "integrity": "sha512-TdC8FSgHz8Mwtw9g5L4gR/Sh9XhSP/0DEkQxfEFXOpiul5IiHgHan2VhYYb6agDSfp4KuvltmGApc8HMgUrIkA==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/picocolors": {
      "version": "1.1.1",
      "resolved": "https://registry.npmjs.org/picocolors/-/picocolors-1.1.1.tgz",
      "integrity": "sha512-xceH2snhtb5M9liqDsmEw56le376mTZkEX/jEb/RxNFyegNul7eNslCXP9FDj/Lcu0X8KEyMceP2ntpaHrDEVA==",
      "dev": true,
      "license": "ISC"
    },
    "node_modules/postcss": {
      "version": "8.5.8",
      "resolved": "https://registry.npmjs.org/postcss/-/postcss-8.5.8.tgz",
      "integrity": "sha512-OW/rX8O/jXnm82Ey1k44pObPtdblfiuWnrd8X7GJ7emImCOstunGbXUpp7HdBrFQX6rJzn3sPT397Wp5aCwCHg==",
      "dev": true,
      "funding": [
        {
          "type": "opencollective",
          "url": "https://opencollective.com/postcss/"
        },
        {
          "type": "tidelift",
          "url": "https://tidelift.com/funding/github/npm/postcss"
        },
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "MIT",
      "dependencies": {
        "nanoid": "^3.3.11",
        "picocolors": "^1.1.1",
        "source-map-js": "^1.2.1"
      },
      "engines": {
        "node": "^10 || ^12 || >=14"
      }
    },
    "node_modules/react": {
      "version": "18.3.1",
      "resolved": "https://registry.npmjs.org/react/-/react-18.3.1.tgz",
      "integrity": "sha512-wS+hAgJShR0KhEvPJArfuPVN1+Hz1t0Y6n5jLrGQbkb4urgPE/0Rve+1kMB1v/oWgHgm4WIcV+i7F2pTVj+2iQ==",
      "license": "MIT",
      "peer": true,
      "dependencies": {
        "loose-envify": "^1.1.0"
      },
      "engines": {
        "node": ">=0.10.0"
      }
    },
    "node_modules/react-dom": {
      "version": "18.3.1",
      "resolved": "https://registry.npmjs.org/react-dom/-/react-dom-18.3.1.tgz",
      "integrity": "sha512-5m4nQKp+rZRb09LNH59GM4BxTh9251/ylbKIbpe7TpGxfJ+9kv6BLkLBXIjjspbgbnIBNqlI23tRnTWT0snUIw==",
      "license": "MIT",
      "dependencies": {
        "loose-envify": "^1.1.0",
        "scheduler": "^0.23.2"
      },
      "peerDependencies": {
        "react": "^18.3.1"
      }
    },
    "node_modules/react-refresh": {
      "version": "0.17.0",
      "resolved": "https://registry.npmjs.org/react-refresh/-/react-refresh-0.17.0.tgz",
      "integrity": "sha512-z6F7K9bV85EfseRCp2bzrpyQ0Gkw1uLoCel9XBVWPg/TjRj94SkJzUTGfOa4bs7iJvBWtQG0Wq7wnI0syw3EBQ==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=0.10.0"
      }
    },
    "node_modules/rollup": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/rollup/-/rollup-4.59.0.tgz",
      "integrity": "sha512-2oMpl67a3zCH9H79LeMcbDhXW/UmWG/y2zuqnF2jQq5uq9TbM9TVyXvA4+t+ne2IIkBdrLpAaRQAvo7YI/Yyeg==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@types/estree": "1.0.8"
      },
      "bin": {
        "rollup": "dist/bin/rollup"
      },
      "engines": {
        "node": ">=18.0.0",
        "npm": ">=8.0.0"
      },
      "optionalDependencies": {
        "@rollup/rollup-android-arm-eabi": "4.59.0",
        "@rollup/rollup-android-arm64": "4.59.0",
        "@rollup/rollup-darwin-arm64": "4.59.0",
        "@rollup/rollup-darwin-x64": "4.59.0",
        "@rollup/rollup-freebsd-arm64": "4.59.0",
        "@rollup/rollup-freebsd-x64": "4.59.0",
        "@rollup/rollup-linux-arm-gnueabihf": "4.59.0",
        "@rollup/rollup-linux-arm-musleabihf": "4.59.0",
        "@rollup/rollup-linux-arm64-gnu": "4.59.0",
        "@rollup/rollup-linux-arm64-musl": "4.59.0",
        "@rollup/rollup-linux-loong64-gnu": "4.59.0",
        "@rollup/rollup-linux-loong64-musl": "4.59.0",
        "@rollup/rollup-linux-ppc64-gnu": "4.59.0",
        "@rollup/rollup-linux-ppc64-musl": "4.59.0",
        "@rollup/rollup-linux-riscv64-gnu": "4.59.0",
        "@rollup/rollup-linux-riscv64-musl": "4.59.0",
        "@rollup/rollup-linux-s390x-gnu": "4.59.0",
        "@rollup/rollup-linux-x64-gnu": "4.59.0",
        "@rollup/rollup-linux-x64-musl": "4.59.0",
        "@rollup/rollup-openbsd-x64": "4.59.0",
        "@rollup/rollup-openharmony-arm64": "4.59.0",
        "@rollup/rollup-win32-arm64-msvc": "4.59.0",
        "@rollup/rollup-win32-ia32-msvc": "4.59.0",
        "@rollup/rollup-win32-x64-gnu": "4.59.0",
        "@rollup/rollup-win32-x64-msvc": "4.59.0",
        "fsevents": "~2.3.2"
      }
    },
    "node_modules/scheduler": {
      "version": "0.23.2",
      "resolved": "https://registry.npmjs.org/scheduler/-/scheduler-0.23.2.tgz",
      "integrity": "sha512-UOShsPwz7NrMUqhR6t0hWjFduvOzbtv7toDH1/hIrfRNIDBnnBWd0CwJTGvTpngVlmwGCdP9/Zl/tVrDqcuYzQ==",
      "license": "MIT",
      "dependencies": {
        "loose-envify": "^1.1.0"
      }
    },
    "node_modules/semver": {
      "version": "6.3.1",
      "resolved": "https://registry.npmjs.org/semver/-/semver-6.3.1.tgz",
      "integrity": "sha512-BR7VvDCVHO+q2xBEWskxS6DJE1qRnb7DxzUrogb71CWoSficBxYsiAGd+Kl0mmq/MprG9yArRkyrQxTO6XjMzA==",
      "dev": true,
      "license": "ISC",
      "bin": {
        "semver": "bin/semver.js"
      }
    },
    "node_modules/source-map-js": {
      "version": "1.2.1",
      "resolved": "https://registry.npmjs.org/source-map-js/-/source-map-js-1.2.1.tgz",
      "integrity": "sha512-UXWMKhLOwVKb728IUtQPXxfYU+usdybtUrK/8uGE8CQMvrhOpwvzDBwj0QhSL7MQc7vIsISBG8VQ8+IDQxpfQA==",
      "dev": true,
      "license": "BSD-3-Clause",
      "engines": {
        "node": ">=0.10.0"
      }
    },
    "node_modules/update-browserslist-db": {
      "version": "1.2.3",
      "resolved": "https://registry.npmjs.org/update-browserslist-db/-/update-browserslist-db-1.2.3.tgz",
      "integrity": "sha512-Js0m9cx+qOgDxo0eMiFGEueWztz+d4+M3rGlmKPT+T4IS/jP4ylw3Nwpu6cpTTP8R1MAC1kF4VbdLt3ARf209w==",
      "dev": true,
      "funding": [
        {
          "type": "opencollective",
          "url": "https://opencollective.com/browserslist"
        },
        {
          "type": "tidelift",
          "url": "https://tidelift.com/funding/github/npm/browserslist"
        },
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "MIT",
      "dependencies": {
        "escalade": "^3.2.0",
        "picocolors": "^1.1.1"
      },
      "bin": {
        "update-browserslist-db": "cli.js"
      },
      "peerDependencies": {
        "browserslist": ">= 4.21.0"
      }
    },
    "node_modules/vite": {
      "version": "5.4.21",
      "resolved": "https://registry.npmjs.org/vite/-/vite-5.4.21.tgz",
      "integrity": "sha512-o5a9xKjbtuhY6Bi5S3+HvbRERmouabWbyUcpXXUA1u+GNUKoROi9byOJ8M0nHbHYHkYICiMlqxkg1KkYmm25Sw==",
      "dev": true,
      "license": "MIT",
      "peer": true,
      "dependencies": {
        "esbuild": "^0.21.3",
        "postcss": "^8.4.43",
        "rollup": "^4.20.0"
      },
      "bin": {
        "vite": "bin/vite.js"
      },
      "engines": {
        "node": "^18.0.0 || >=20.0.0"
      },
      "funding": {
        "url": "https://github.com/vitejs/vite?sponsor=1"
      },
      "optionalDependencies": {
        "fsevents": "~2.3.3"
      },
      "peerDependencies": {
        "@types/node": "^18.0.0 || >=20.0.0",
        "less": "*",
        "lightningcss": "^1.21.0",
        "sass": "*",
        "sass-embedded": "*",
        "stylus": "*",
        "sugarss": "*",
        "terser": "^5.4.0"
      },
      "peerDependenciesMeta": {
        "@types/node": {
          "optional": true
        },
        "less": {
          "optional": true
        },
        "lightningcss": {
          "optional": true
        },
        "sass": {
          "optional": true
        },
        "sass-embedded": {
          "optional": true
        },
        "stylus": {
          "optional": true
        },
        "sugarss": {
          "optional": true
        },
        "terser": {
          "optional": true
        }
      }
    },
    "node_modules/yallist": {
      "version": "3.1.1",
      "resolved": "https://registry.npmjs.org/yallist/-/yallist-3.1.1.tgz",
      "integrity": "sha512-a4UGQaWPH59mOXUYnAG2ewncQS4i4F43Tv3JoAM+s2VDAmS9NsK8GpDMLrCHPksFT7h3K6TOoUNn2pb7RoXx4g==",
      "dev": true,
      "license": "ISC"
    }
  }
}
```

----

# frontend/node_modules/.vite/deps/_metadata.json
```json
{
  "hash": "9b32e4bb",
  "configHash": "491ba9fa",
  "lockfileHash": "6265b5aa",
  "browserHash": "d4bbff97",
  "optimized": {
    "react": {
      "src": "../../react/index.js",
      "file": "react.js",
      "fileHash": "ede471c1",
      "needsInterop": true
    },
    "react-dom": {
      "src": "../../react-dom/index.js",
      "file": "react-dom.js",
      "fileHash": "6a46a16c",
      "needsInterop": true
    },
    "react/jsx-dev-runtime": {
      "src": "../../react/jsx-dev-runtime.js",
      "file": "react_jsx-dev-runtime.js",
      "fileHash": "35a6f313",
      "needsInterop": true
    },
    "react/jsx-runtime": {
      "src": "../../react/jsx-runtime.js",
      "file": "react_jsx-runtime.js",
      "fileHash": "3a50951b",
      "needsInterop": true
    },
    "lucide-react": {
      "src": "../../lucide-react/dist/esm/lucide-react.js",
      "file": "lucide-react.js",
      "fileHash": "7ddb15e0",
      "needsInterop": false
    },
    "react-dom/client": {
      "src": "../../react-dom/client.js",
      "file": "react-dom_client.js",
      "fileHash": "d148a8de",
      "needsInterop": true
    }
  },
  "chunks": {
    "chunk-BCXODTBQ": {
      "file": "chunk-BCXODTBQ.js"
    },
    "chunk-2YIMICFJ": {
      "file": "chunk-2YIMICFJ.js"
    }
  }
}```

----

# frontend/node_modules/.vite/deps/package.json
```json
{
  "type": "module"
}
```

----

# frontend/node_modules/@babel/code-frame/package.json
```json
{
  "name": "@babel/code-frame",
  "version": "7.29.0",
  "description": "Generate errors that contain a code frame that point to source locations.",
  "author": "The Babel Team (https://babel.dev/team)",
  "homepage": "https://babel.dev/docs/en/next/babel-code-frame",
  "bugs": "https://github.com/babel/babel/issues?utf8=%E2%9C%93&q=is%3Aissue+is%3Aopen",
  "license": "MIT",
  "publishConfig": {
    "access": "public"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/babel/babel.git",
    "directory": "packages/babel-code-frame"
  },
  "main": "./lib/index.js",
  "dependencies": {
    "@babel/helper-validator-identifier": "^7.28.5",
    "js-tokens": "^4.0.0",
    "picocolors": "^1.1.1"
  },
  "devDependencies": {
    "charcodes": "^0.2.0",
    "import-meta-resolve": "^4.1.0",
    "strip-ansi": "^4.0.0"
  },
  "engines": {
    "node": ">=6.9.0"
  },
  "type": "commonjs"
}```

----

# frontend/node_modules/@babel/compat-data/data/corejs2-built-ins.json
```json
{
  "es6.array.copy-within": {
    "chrome": "45",
    "opera": "32",
    "edge": "12",
    "firefox": "32",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "5",
    "rhino": "1.7.13",
    "opera_mobile": "32",
    "electron": "0.31"
  },
  "es6.array.every": {
    "chrome": "5",
    "opera": "10.10",
    "edge": "12",
    "firefox": "2",
    "safari": "3.1",
    "node": "0.4",
    "deno": "1",
    "ie": "9",
    "android": "4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "10.1",
    "electron": "0.20"
  },
  "es6.array.fill": {
    "chrome": "45",
    "opera": "32",
    "edge": "12",
    "firefox": "31",
    "safari": "7.1",
    "node": "4",
    "deno": "1",
    "ios": "8",
    "samsung": "5",
    "rhino": "1.7.13",
    "opera_mobile": "32",
    "electron": "0.31"
  },
  "es6.array.filter": {
    "chrome": "51",
    "opera": "38",
    "edge": "13",
    "firefox": "48",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es6.array.find": {
    "chrome": "45",
    "opera": "32",
    "edge": "12",
    "firefox": "25",
    "safari": "7.1",
    "node": "4",
    "deno": "1",
    "ios": "8",
    "samsung": "5",
    "rhino": "1.7.13",
    "opera_mobile": "32",
    "electron": "0.31"
  },
  "es6.array.find-index": {
    "chrome": "45",
    "opera": "32",
    "edge": "12",
    "firefox": "25",
    "safari": "7.1",
    "node": "4",
    "deno": "1",
    "ios": "8",
    "samsung": "5",
    "rhino": "1.7.13",
    "opera_mobile": "32",
    "electron": "0.31"
  },
  "es7.array.flat-map": {
    "chrome": "69",
    "opera": "56",
    "edge": "79",
    "firefox": "62",
    "safari": "12",
    "node": "11",
    "deno": "1",
    "ios": "12",
    "samsung": "10",
    "rhino": "1.7.15",
    "opera_mobile": "48",
    "electron": "4.0"
  },
  "es6.array.for-each": {
    "chrome": "5",
    "opera": "10.10",
    "edge": "12",
    "firefox": "2",
    "safari": "3.1",
    "node": "0.4",
    "deno": "1",
    "ie": "9",
    "android": "4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "10.1",
    "electron": "0.20"
  },
  "es6.array.from": {
    "chrome": "51",
    "opera": "38",
    "edge": "15",
    "firefox": "36",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.7.15",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es7.array.includes": {
    "chrome": "47",
    "opera": "34",
    "edge": "14",
    "firefox": "102",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.8",
    "opera_mobile": "34",
    "electron": "0.36"
  },
  "es6.array.index-of": {
    "chrome": "5",
    "opera": "10.10",
    "edge": "12",
    "firefox": "2",
    "safari": "3.1",
    "node": "0.4",
    "deno": "1",
    "ie": "9",
    "android": "4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "10.1",
    "electron": "0.20"
  },
  "es6.array.is-array": {
    "chrome": "5",
    "opera": "10.50",
    "edge": "12",
    "firefox": "4",
    "safari": "4",
    "node": "0.4",
    "deno": "1",
    "ie": "9",
    "android": "4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "10.1",
    "electron": "0.20"
  },
  "es6.array.iterator": {
    "chrome": "66",
    "opera": "53",
    "edge": "12",
    "firefox": "60",
    "safari": "9",
    "node": "10",
    "deno": "1",
    "ios": "9",
    "samsung": "9",
    "rhino": "1.7.13",
    "opera_mobile": "47",
    "electron": "3.0"
  },
  "es6.array.last-index-of": {
    "chrome": "5",
    "opera": "10.10",
    "edge": "12",
    "firefox": "2",
    "safari": "3.1",
    "node": "0.4",
    "deno": "1",
    "ie": "9",
    "android": "4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "10.1",
    "electron": "0.20"
  },
  "es6.array.map": {
    "chrome": "51",
    "opera": "38",
    "edge": "13",
    "firefox": "48",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es6.array.of": {
    "chrome": "45",
    "opera": "32",
    "edge": "12",
    "firefox": "25",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "5",
    "rhino": "1.7.13",
    "opera_mobile": "32",
    "electron": "0.31"
  },
  "es6.array.reduce": {
    "chrome": "5",
    "opera": "10.50",
    "edge": "12",
    "firefox": "3",
    "safari": "4",
    "node": "0.4",
    "deno": "1",
    "ie": "9",
    "android": "4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "10.1",
    "electron": "0.20"
  },
  "es6.array.reduce-right": {
    "chrome": "5",
    "opera": "10.50",
    "edge": "12",
    "firefox": "3",
    "safari": "4",
    "node": "0.4",
    "deno": "1",
    "ie": "9",
    "android": "4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "10.1",
    "electron": "0.20"
  },
  "es6.array.slice": {
    "chrome": "51",
    "opera": "38",
    "edge": "13",
    "firefox": "48",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es6.array.some": {
    "chrome": "5",
    "opera": "10.10",
    "edge": "12",
    "firefox": "2",
    "safari": "3.1",
    "node": "0.4",
    "deno": "1",
    "ie": "9",
    "android": "4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "10.1",
    "electron": "0.20"
  },
  "es6.array.sort": {
    "chrome": "63",
    "opera": "50",
    "edge": "12",
    "firefox": "5",
    "safari": "12",
    "node": "10",
    "deno": "1",
    "ie": "9",
    "ios": "12",
    "samsung": "8",
    "rhino": "1.7.13",
    "opera_mobile": "46",
    "electron": "3.0"
  },
  "es6.array.species": {
    "chrome": "51",
    "opera": "38",
    "edge": "13",
    "firefox": "48",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.7.15",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es6.date.now": {
    "chrome": "5",
    "opera": "10.50",
    "edge": "12",
    "firefox": "2",
    "safari": "4",
    "node": "0.4",
    "deno": "1",
    "ie": "9",
    "android": "4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "10.1",
    "electron": "0.20"
  },
  "es6.date.to-iso-string": {
    "chrome": "5",
    "opera": "10.50",
    "edge": "12",
    "firefox": "3.5",
    "safari": "4",
    "node": "0.4",
    "deno": "1",
    "ie": "9",
    "android": "4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "10.1",
    "electron": "0.20"
  },
  "es6.date.to-json": {
    "chrome": "5",
    "opera": "12.10",
    "edge": "12",
    "firefox": "4",
    "safari": "10",
    "node": "0.4",
    "deno": "1",
    "ie": "9",
    "android": "4",
    "ios": "10",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "12.1",
    "electron": "0.20"
  },
  "es6.date.to-primitive": {
    "chrome": "47",
    "opera": "34",
    "edge": "15",
    "firefox": "44",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.8",
    "opera_mobile": "34",
    "electron": "0.36"
  },
  "es6.date.to-string": {
    "chrome": "5",
    "opera": "10.50",
    "edge": "12",
    "firefox": "2",
    "safari": "3.1",
    "node": "0.4",
    "deno": "1",
    "ie": "10",
    "android": "4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "10.1",
    "electron": "0.20"
  },
  "es6.function.bind": {
    "chrome": "7",
    "opera": "12",
    "edge": "12",
    "firefox": "4",
    "safari": "5.1",
    "node": "0.4",
    "deno": "1",
    "ie": "9",
    "android": "4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "12",
    "electron": "0.20"
  },
  "es6.function.has-instance": {
    "chrome": "51",
    "opera": "38",
    "edge": "15",
    "firefox": "50",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es6.function.name": {
    "chrome": "5",
    "opera": "10.50",
    "edge": "14",
    "firefox": "2",
    "safari": "4",
    "node": "0.4",
    "deno": "1",
    "android": "4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "10.1",
    "electron": "0.20"
  },
  "es6.map": {
    "chrome": "51",
    "opera": "38",
    "edge": "15",
    "firefox": "53",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es6.math.acosh": {
    "chrome": "38",
    "opera": "25",
    "edge": "12",
    "firefox": "25",
    "safari": "7.1",
    "node": "0.12",
    "deno": "1",
    "ios": "8",
    "samsung": "3",
    "rhino": "1.7.13",
    "opera_mobile": "25",
    "electron": "0.20"
  },
  "es6.math.asinh": {
    "chrome": "38",
    "opera": "25",
    "edge": "12",
    "firefox": "25",
    "safari": "7.1",
    "node": "0.12",
    "deno": "1",
    "ios": "8",
    "samsung": "3",
    "rhino": "1.7.13",
    "opera_mobile": "25",
    "electron": "0.20"
  },
  "es6.math.atanh": {
    "chrome": "38",
    "opera": "25",
    "edge": "12",
    "firefox": "25",
    "safari": "7.1",
    "node": "0.12",
    "deno": "1",
    "ios": "8",
    "samsung": "3",
    "rhino": "1.7.13",
    "opera_mobile": "25",
    "electron": "0.20"
  },
  "es6.math.cbrt": {
    "chrome": "38",
    "opera": "25",
    "edge": "12",
    "firefox": "25",
    "safari": "7.1",
    "node": "0.12",
    "deno": "1",
    "ios": "8",
    "samsung": "3",
    "rhino": "1.7.13",
    "opera_mobile": "25",
    "electron": "0.20"
  },
  "es6.math.clz32": {
    "chrome": "38",
    "opera": "25",
    "edge": "12",
    "firefox": "31",
    "safari": "9",
    "node": "0.12",
    "deno": "1",
    "ios": "9",
    "samsung": "3",
    "rhino": "1.7.13",
    "opera_mobile": "25",
    "electron": "0.20"
  },
  "es6.math.cosh": {
    "chrome": "38",
    "opera": "25",
    "edge": "12",
    "firefox": "25",
    "safari": "7.1",
    "node": "0.12",
    "deno": "1",
    "ios": "8",
    "samsung": "3",
    "rhino": "1.7.13",
    "opera_mobile": "25",
    "electron": "0.20"
  },
  "es6.math.expm1": {
    "chrome": "38",
    "opera": "25",
    "edge": "12",
    "firefox": "25",
    "safari": "7.1",
    "node": "0.12",
    "deno": "1",
    "ios": "8",
    "samsung": "3",
    "rhino": "1.7.13",
    "opera_mobile": "25",
    "electron": "0.20"
  },
  "es6.math.fround": {
    "chrome": "38",
    "opera": "25",
    "edge": "12",
    "firefox": "26",
    "safari": "7.1",
    "node": "0.12",
    "deno": "1",
    "ios": "8",
    "samsung": "3",
    "rhino": "1.7.13",
    "opera_mobile": "25",
    "electron": "0.20"
  },
  "es6.math.hypot": {
    "chrome": "38",
    "opera": "25",
    "edge": "12",
    "firefox": "27",
    "safari": "7.1",
    "node": "0.12",
    "deno": "1",
    "ios": "8",
    "samsung": "3",
    "rhino": "1.7.13",
    "opera_mobile": "25",
    "electron": "0.20"
  },
  "es6.math.imul": {
    "chrome": "30",
    "opera": "17",
    "edge": "12",
    "firefox": "23",
    "safari": "7",
    "node": "0.12",
    "deno": "1",
    "android": "4.4",
    "ios": "7",
    "samsung": "2",
    "rhino": "1.7.13",
    "opera_mobile": "18",
    "electron": "0.20"
  },
  "es6.math.log1p": {
    "chrome": "38",
    "opera": "25",
    "edge": "12",
    "firefox": "25",
    "safari": "7.1",
    "node": "0.12",
    "deno": "1",
    "ios": "8",
    "samsung": "3",
    "rhino": "1.7.13",
    "opera_mobile": "25",
    "electron": "0.20"
  },
  "es6.math.log10": {
    "chrome": "38",
    "opera": "25",
    "edge": "12",
    "firefox": "25",
    "safari": "7.1",
    "node": "0.12",
    "deno": "1",
    "ios": "8",
    "samsung": "3",
    "rhino": "1.7.13",
    "opera_mobile": "25",
    "electron": "0.20"
  },
  "es6.math.log2": {
    "chrome": "38",
    "opera": "25",
    "edge": "12",
    "firefox": "25",
    "safari": "7.1",
    "node": "0.12",
    "deno": "1",
    "ios": "8",
    "samsung": "3",
    "rhino": "1.7.13",
    "opera_mobile": "25",
    "electron": "0.20"
  },
  "es6.math.sign": {
    "chrome": "38",
    "opera": "25",
    "edge": "12",
    "firefox": "25",
    "safari": "9",
    "node": "0.12",
    "deno": "1",
    "ios": "9",
    "samsung": "3",
    "rhino": "1.7.13",
    "opera_mobile": "25",
    "electron": "0.20"
  },
  "es6.math.sinh": {
    "chrome": "38",
    "opera": "25",
    "edge": "12",
    "firefox": "25",
    "safari": "7.1",
    "node": "0.12",
    "deno": "1",
    "ios": "8",
    "samsung": "3",
    "rhino": "1.7.13",
    "opera_mobile": "25",
    "electron": "0.20"
  },
  "es6.math.tanh": {
    "chrome": "38",
    "opera": "25",
    "edge": "12",
    "firefox": "25",
    "safari": "7.1",
    "node": "0.12",
    "deno": "1",
    "ios": "8",
    "samsung": "3",
    "rhino": "1.7.13",
    "opera_mobile": "25",
    "electron": "0.20"
  },
  "es6.math.trunc": {
    "chrome": "38",
    "opera": "25",
    "edge": "12",
    "firefox": "25",
    "safari": "7.1",
    "node": "0.12",
    "deno": "1",
    "ios": "8",
    "samsung": "3",
    "rhino": "1.7.13",
    "opera_mobile": "25",
    "electron": "0.20"
  },
  "es6.number.constructor": {
    "chrome": "41",
    "opera": "28",
    "edge": "12",
    "firefox": "36",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "3.4",
    "rhino": "1.7.13",
    "opera_mobile": "28",
    "electron": "0.21"
  },
  "es6.number.epsilon": {
    "chrome": "34",
    "opera": "21",
    "edge": "12",
    "firefox": "25",
    "safari": "9",
    "node": "0.12",
    "deno": "1",
    "ios": "9",
    "samsung": "2",
    "rhino": "1.7.14",
    "opera_mobile": "21",
    "electron": "0.20"
  },
  "es6.number.is-finite": {
    "chrome": "19",
    "opera": "15",
    "edge": "12",
    "firefox": "16",
    "safari": "9",
    "node": "0.8",
    "deno": "1",
    "android": "4.1",
    "ios": "9",
    "samsung": "1.5",
    "rhino": "1.7.13",
    "opera_mobile": "14",
    "electron": "0.20"
  },
  "es6.number.is-integer": {
    "chrome": "34",
    "opera": "21",
    "edge": "12",
    "firefox": "16",
    "safari": "9",
    "node": "0.12",
    "deno": "1",
    "ios": "9",
    "samsung": "2",
    "rhino": "1.7.13",
    "opera_mobile": "21",
    "electron": "0.20"
  },
  "es6.number.is-nan": {
    "chrome": "19",
    "opera": "15",
    "edge": "12",
    "firefox": "15",
    "safari": "9",
    "node": "0.8",
    "deno": "1",
    "android": "4.1",
    "ios": "9",
    "samsung": "1.5",
    "rhino": "1.7.13",
    "opera_mobile": "14",
    "electron": "0.20"
  },
  "es6.number.is-safe-integer": {
    "chrome": "34",
    "opera": "21",
    "edge": "12",
    "firefox": "32",
    "safari": "9",
    "node": "0.12",
    "deno": "1",
    "ios": "9",
    "samsung": "2",
    "rhino": "1.7.13",
    "opera_mobile": "21",
    "electron": "0.20"
  },
  "es6.number.max-safe-integer": {
    "chrome": "34",
    "opera": "21",
    "edge": "12",
    "firefox": "31",
    "safari": "9",
    "node": "0.12",
    "deno": "1",
    "ios": "9",
    "samsung": "2",
    "rhino": "1.7.13",
    "opera_mobile": "21",
    "electron": "0.20"
  },
  "es6.number.min-safe-integer": {
    "chrome": "34",
    "opera": "21",
    "edge": "12",
    "firefox": "31",
    "safari": "9",
    "node": "0.12",
    "deno": "1",
    "ios": "9",
    "samsung": "2",
    "rhino": "1.7.13",
    "opera_mobile": "21",
    "electron": "0.20"
  },
  "es6.number.parse-float": {
    "chrome": "34",
    "opera": "21",
    "edge": "12",
    "firefox": "25",
    "safari": "9",
    "node": "0.12",
    "deno": "1",
    "ios": "9",
    "samsung": "2",
    "rhino": "1.7.14",
    "opera_mobile": "21",
    "electron": "0.20"
  },
  "es6.number.parse-int": {
    "chrome": "34",
    "opera": "21",
    "edge": "12",
    "firefox": "25",
    "safari": "9",
    "node": "0.12",
    "deno": "1",
    "ios": "9",
    "samsung": "2",
    "rhino": "1.7.14",
    "opera_mobile": "21",
    "electron": "0.20"
  },
  "es6.object.assign": {
    "chrome": "49",
    "opera": "36",
    "edge": "13",
    "firefox": "36",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.8",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "es6.object.create": {
    "chrome": "5",
    "opera": "12",
    "edge": "12",
    "firefox": "4",
    "safari": "4",
    "node": "0.4",
    "deno": "1",
    "ie": "9",
    "android": "4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "12",
    "electron": "0.20"
  },
  "es7.object.define-getter": {
    "chrome": "62",
    "opera": "49",
    "edge": "16",
    "firefox": "48",
    "safari": "9",
    "node": "8.10",
    "deno": "1",
    "ios": "9",
    "samsung": "8",
    "opera_mobile": "46",
    "electron": "3.0"
  },
  "es7.object.define-setter": {
    "chrome": "62",
    "opera": "49",
    "edge": "16",
    "firefox": "48",
    "safari": "9",
    "node": "8.10",
    "deno": "1",
    "ios": "9",
    "samsung": "8",
    "opera_mobile": "46",
    "electron": "3.0"
  },
  "es6.object.define-property": {
    "chrome": "5",
    "opera": "12",
    "edge": "12",
    "firefox": "4",
    "safari": "5.1",
    "node": "0.4",
    "deno": "1",
    "ie": "9",
    "android": "4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "12",
    "electron": "0.20"
  },
  "es6.object.define-properties": {
    "chrome": "5",
    "opera": "12",
    "edge": "12",
    "firefox": "4",
    "safari": "4",
    "node": "0.4",
    "deno": "1",
    "ie": "9",
    "android": "4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "12",
    "electron": "0.20"
  },
  "es7.object.entries": {
    "chrome": "54",
    "opera": "41",
    "edge": "14",
    "firefox": "47",
    "safari": "10.1",
    "node": "7",
    "deno": "1",
    "ios": "10.3",
    "samsung": "6",
    "rhino": "1.7.14",
    "opera_mobile": "41",
    "electron": "1.4"
  },
  "es6.object.freeze": {
    "chrome": "44",
    "opera": "31",
    "edge": "12",
    "firefox": "35",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "4",
    "rhino": "1.7.13",
    "opera_mobile": "32",
    "electron": "0.30"
  },
  "es6.object.get-own-property-descriptor": {
    "chrome": "44",
    "opera": "31",
    "edge": "12",
    "firefox": "35",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "4",
    "rhino": "1.7.13",
    "opera_mobile": "32",
    "electron": "0.30"
  },
  "es7.object.get-own-property-descriptors": {
    "chrome": "54",
    "opera": "41",
    "edge": "15",
    "firefox": "50",
    "safari": "10.1",
    "node": "7",
    "deno": "1",
    "ios": "10.3",
    "samsung": "6",
    "rhino": "1.8",
    "opera_mobile": "41",
    "electron": "1.4"
  },
  "es6.object.get-own-property-names": {
    "chrome": "40",
    "opera": "27",
    "edge": "12",
    "firefox": "33",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "3.4",
    "rhino": "1.7.13",
    "opera_mobile": "27",
    "electron": "0.21"
  },
  "es6.object.get-prototype-of": {
    "chrome": "44",
    "opera": "31",
    "edge": "12",
    "firefox": "35",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "4",
    "rhino": "1.7.13",
    "opera_mobile": "32",
    "electron": "0.30"
  },
  "es7.object.lookup-getter": {
    "chrome": "62",
    "opera": "49",
    "edge": "79",
    "firefox": "36",
    "safari": "9",
    "node": "8.10",
    "deno": "1",
    "ios": "9",
    "samsung": "8",
    "opera_mobile": "46",
    "electron": "3.0"
  },
  "es7.object.lookup-setter": {
    "chrome": "62",
    "opera": "49",
    "edge": "79",
    "firefox": "36",
    "safari": "9",
    "node": "8.10",
    "deno": "1",
    "ios": "9",
    "samsung": "8",
    "opera_mobile": "46",
    "electron": "3.0"
  },
  "es6.object.prevent-extensions": {
    "chrome": "44",
    "opera": "31",
    "edge": "12",
    "firefox": "35",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "4",
    "rhino": "1.7.13",
    "opera_mobile": "32",
    "electron": "0.30"
  },
  "es6.object.to-string": {
    "chrome": "57",
    "opera": "44",
    "edge": "15",
    "firefox": "51",
    "safari": "10",
    "node": "8",
    "deno": "1",
    "ios": "10",
    "samsung": "7",
    "opera_mobile": "43",
    "electron": "1.7"
  },
  "es6.object.is": {
    "chrome": "19",
    "opera": "15",
    "edge": "12",
    "firefox": "22",
    "safari": "9",
    "node": "0.8",
    "deno": "1",
    "android": "4.1",
    "ios": "9",
    "samsung": "1.5",
    "rhino": "1.7.13",
    "opera_mobile": "14",
    "electron": "0.20"
  },
  "es6.object.is-frozen": {
    "chrome": "44",
    "opera": "31",
    "edge": "12",
    "firefox": "35",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "4",
    "rhino": "1.7.13",
    "opera_mobile": "32",
    "electron": "0.30"
  },
  "es6.object.is-sealed": {
    "chrome": "44",
    "opera": "31",
    "edge": "12",
    "firefox": "35",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "4",
    "rhino": "1.7.13",
    "opera_mobile": "32",
    "electron": "0.30"
  },
  "es6.object.is-extensible": {
    "chrome": "44",
    "opera": "31",
    "edge": "12",
    "firefox": "35",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "4",
    "rhino": "1.7.13",
    "opera_mobile": "32",
    "electron": "0.30"
  },
  "es6.object.keys": {
    "chrome": "40",
    "opera": "27",
    "edge": "12",
    "firefox": "35",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "3.4",
    "rhino": "1.7.13",
    "opera_mobile": "27",
    "electron": "0.21"
  },
  "es6.object.seal": {
    "chrome": "44",
    "opera": "31",
    "edge": "12",
    "firefox": "35",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "4",
    "rhino": "1.7.13",
    "opera_mobile": "32",
    "electron": "0.30"
  },
  "es6.object.set-prototype-of": {
    "chrome": "34",
    "opera": "21",
    "edge": "12",
    "firefox": "31",
    "safari": "9",
    "node": "0.12",
    "deno": "1",
    "ie": "11",
    "ios": "9",
    "samsung": "2",
    "rhino": "1.7.13",
    "opera_mobile": "21",
    "electron": "0.20"
  },
  "es7.object.values": {
    "chrome": "54",
    "opera": "41",
    "edge": "14",
    "firefox": "47",
    "safari": "10.1",
    "node": "7",
    "deno": "1",
    "ios": "10.3",
    "samsung": "6",
    "rhino": "1.7.14",
    "opera_mobile": "41",
    "electron": "1.4"
  },
  "es6.promise": {
    "chrome": "51",
    "opera": "38",
    "edge": "14",
    "firefox": "45",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.7.15",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es7.promise.finally": {
    "chrome": "63",
    "opera": "50",
    "edge": "18",
    "firefox": "58",
    "safari": "11.1",
    "node": "10",
    "deno": "1",
    "ios": "11.3",
    "samsung": "8",
    "rhino": "1.7.15",
    "opera_mobile": "46",
    "electron": "3.0"
  },
  "es6.reflect.apply": {
    "chrome": "49",
    "opera": "36",
    "edge": "12",
    "firefox": "42",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.8",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "es6.reflect.construct": {
    "chrome": "49",
    "opera": "36",
    "edge": "13",
    "firefox": "49",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "es6.reflect.define-property": {
    "chrome": "49",
    "opera": "36",
    "edge": "13",
    "firefox": "42",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.8",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "es6.reflect.delete-property": {
    "chrome": "49",
    "opera": "36",
    "edge": "12",
    "firefox": "42",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.8",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "es6.reflect.get": {
    "chrome": "49",
    "opera": "36",
    "edge": "12",
    "firefox": "42",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.8",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "es6.reflect.get-own-property-descriptor": {
    "chrome": "49",
    "opera": "36",
    "edge": "12",
    "firefox": "42",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.8",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "es6.reflect.get-prototype-of": {
    "chrome": "49",
    "opera": "36",
    "edge": "12",
    "firefox": "42",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.8",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "es6.reflect.has": {
    "chrome": "49",
    "opera": "36",
    "edge": "12",
    "firefox": "42",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.8",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "es6.reflect.is-extensible": {
    "chrome": "49",
    "opera": "36",
    "edge": "12",
    "firefox": "42",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.8",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "es6.reflect.own-keys": {
    "chrome": "49",
    "opera": "36",
    "edge": "12",
    "firefox": "42",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.8",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "es6.reflect.prevent-extensions": {
    "chrome": "49",
    "opera": "36",
    "edge": "12",
    "firefox": "42",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.8",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "es6.reflect.set": {
    "chrome": "49",
    "opera": "36",
    "edge": "12",
    "firefox": "42",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.8",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "es6.reflect.set-prototype-of": {
    "chrome": "49",
    "opera": "36",
    "edge": "12",
    "firefox": "42",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.8",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "es6.regexp.constructor": {
    "chrome": "50",
    "opera": "37",
    "edge": "79",
    "firefox": "40",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "37",
    "electron": "1.1"
  },
  "es6.regexp.flags": {
    "chrome": "49",
    "opera": "36",
    "edge": "79",
    "firefox": "37",
    "safari": "9",
    "node": "6",
    "deno": "1",
    "ios": "9",
    "samsung": "5",
    "rhino": "1.7.15",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "es6.regexp.match": {
    "chrome": "50",
    "opera": "37",
    "edge": "79",
    "firefox": "49",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.7.13",
    "opera_mobile": "37",
    "electron": "1.1"
  },
  "es6.regexp.replace": {
    "chrome": "50",
    "opera": "37",
    "edge": "79",
    "firefox": "49",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "37",
    "electron": "1.1"
  },
  "es6.regexp.split": {
    "chrome": "50",
    "opera": "37",
    "edge": "79",
    "firefox": "49",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "37",
    "electron": "1.1"
  },
  "es6.regexp.search": {
    "chrome": "50",
    "opera": "37",
    "edge": "79",
    "firefox": "49",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.7.13",
    "opera_mobile": "37",
    "electron": "1.1"
  },
  "es6.regexp.to-string": {
    "chrome": "50",
    "opera": "37",
    "edge": "79",
    "firefox": "39",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.7.15",
    "opera_mobile": "37",
    "electron": "1.1"
  },
  "es6.set": {
    "chrome": "51",
    "opera": "38",
    "edge": "15",
    "firefox": "53",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es6.symbol": {
    "chrome": "51",
    "opera": "38",
    "edge": "79",
    "firefox": "51",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es7.symbol.async-iterator": {
    "chrome": "63",
    "opera": "50",
    "edge": "79",
    "firefox": "57",
    "safari": "12",
    "node": "10",
    "deno": "1",
    "ios": "12",
    "samsung": "8",
    "opera_mobile": "46",
    "electron": "3.0"
  },
  "es6.string.anchor": {
    "chrome": "5",
    "opera": "15",
    "edge": "12",
    "firefox": "17",
    "safari": "6",
    "node": "0.4",
    "deno": "1",
    "android": "4",
    "ios": "7",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.14",
    "opera_mobile": "14",
    "electron": "0.20"
  },
  "es6.string.big": {
    "chrome": "5",
    "opera": "15",
    "edge": "12",
    "firefox": "17",
    "safari": "6",
    "node": "0.4",
    "deno": "1",
    "android": "4",
    "ios": "7",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.14",
    "opera_mobile": "14",
    "electron": "0.20"
  },
  "es6.string.blink": {
    "chrome": "5",
    "opera": "15",
    "edge": "12",
    "firefox": "17",
    "safari": "6",
    "node": "0.4",
    "deno": "1",
    "android": "4",
    "ios": "7",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.14",
    "opera_mobile": "14",
    "electron": "0.20"
  },
  "es6.string.bold": {
    "chrome": "5",
    "opera": "15",
    "edge": "12",
    "firefox": "17",
    "safari": "6",
    "node": "0.4",
    "deno": "1",
    "android": "4",
    "ios": "7",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.14",
    "opera_mobile": "14",
    "electron": "0.20"
  },
  "es6.string.code-point-at": {
    "chrome": "41",
    "opera": "28",
    "edge": "12",
    "firefox": "29",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "3.4",
    "rhino": "1.7.13",
    "opera_mobile": "28",
    "electron": "0.21"
  },
  "es6.string.ends-with": {
    "chrome": "41",
    "opera": "28",
    "edge": "12",
    "firefox": "29",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "3.4",
    "rhino": "1.7.13",
    "opera_mobile": "28",
    "electron": "0.21"
  },
  "es6.string.fixed": {
    "chrome": "5",
    "opera": "15",
    "edge": "12",
    "firefox": "17",
    "safari": "6",
    "node": "0.4",
    "deno": "1",
    "android": "4",
    "ios": "7",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.14",
    "opera_mobile": "14",
    "electron": "0.20"
  },
  "es6.string.fontcolor": {
    "chrome": "5",
    "opera": "15",
    "edge": "12",
    "firefox": "17",
    "safari": "6",
    "node": "0.4",
    "deno": "1",
    "android": "4",
    "ios": "7",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.14",
    "opera_mobile": "14",
    "electron": "0.20"
  },
  "es6.string.fontsize": {
    "chrome": "5",
    "opera": "15",
    "edge": "12",
    "firefox": "17",
    "safari": "6",
    "node": "0.4",
    "deno": "1",
    "android": "4",
    "ios": "7",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.14",
    "opera_mobile": "14",
    "electron": "0.20"
  },
  "es6.string.from-code-point": {
    "chrome": "41",
    "opera": "28",
    "edge": "12",
    "firefox": "29",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "3.4",
    "rhino": "1.7.13",
    "opera_mobile": "28",
    "electron": "0.21"
  },
  "es6.string.includes": {
    "chrome": "41",
    "opera": "28",
    "edge": "12",
    "firefox": "40",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "3.4",
    "rhino": "1.7.13",
    "opera_mobile": "28",
    "electron": "0.21"
  },
  "es6.string.italics": {
    "chrome": "5",
    "opera": "15",
    "edge": "12",
    "firefox": "17",
    "safari": "6",
    "node": "0.4",
    "deno": "1",
    "android": "4",
    "ios": "7",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.14",
    "opera_mobile": "14",
    "electron": "0.20"
  },
  "es6.string.iterator": {
    "chrome": "38",
    "opera": "25",
    "edge": "12",
    "firefox": "36",
    "safari": "9",
    "node": "0.12",
    "deno": "1",
    "ios": "9",
    "samsung": "3",
    "rhino": "1.7.13",
    "opera_mobile": "25",
    "electron": "0.20"
  },
  "es6.string.link": {
    "chrome": "5",
    "opera": "15",
    "edge": "12",
    "firefox": "17",
    "safari": "6",
    "node": "0.4",
    "deno": "1",
    "android": "4",
    "ios": "7",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.14",
    "opera_mobile": "14",
    "electron": "0.20"
  },
  "es7.string.pad-start": {
    "chrome": "57",
    "opera": "44",
    "edge": "15",
    "firefox": "48",
    "safari": "10",
    "node": "8",
    "deno": "1",
    "ios": "10",
    "samsung": "7",
    "rhino": "1.7.13",
    "opera_mobile": "43",
    "electron": "1.7"
  },
  "es7.string.pad-end": {
    "chrome": "57",
    "opera": "44",
    "edge": "15",
    "firefox": "48",
    "safari": "10",
    "node": "8",
    "deno": "1",
    "ios": "10",
    "samsung": "7",
    "rhino": "1.7.13",
    "opera_mobile": "43",
    "electron": "1.7"
  },
  "es6.string.raw": {
    "chrome": "41",
    "opera": "28",
    "edge": "12",
    "firefox": "34",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "3.4",
    "rhino": "1.7.14",
    "opera_mobile": "28",
    "electron": "0.21"
  },
  "es6.string.repeat": {
    "chrome": "41",
    "opera": "28",
    "edge": "12",
    "firefox": "24",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "3.4",
    "rhino": "1.7.13",
    "opera_mobile": "28",
    "electron": "0.21"
  },
  "es6.string.small": {
    "chrome": "5",
    "opera": "15",
    "edge": "12",
    "firefox": "17",
    "safari": "6",
    "node": "0.4",
    "deno": "1",
    "android": "4",
    "ios": "7",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.14",
    "opera_mobile": "14",
    "electron": "0.20"
  },
  "es6.string.starts-with": {
    "chrome": "41",
    "opera": "28",
    "edge": "12",
    "firefox": "29",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "3.4",
    "rhino": "1.7.13",
    "opera_mobile": "28",
    "electron": "0.21"
  },
  "es6.string.strike": {
    "chrome": "5",
    "opera": "15",
    "edge": "12",
    "firefox": "17",
    "safari": "6",
    "node": "0.4",
    "deno": "1",
    "android": "4",
    "ios": "7",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.14",
    "opera_mobile": "14",
    "electron": "0.20"
  },
  "es6.string.sub": {
    "chrome": "5",
    "opera": "15",
    "edge": "12",
    "firefox": "17",
    "safari": "6",
    "node": "0.4",
    "deno": "1",
    "android": "4",
    "ios": "7",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.14",
    "opera_mobile": "14",
    "electron": "0.20"
  },
  "es6.string.sup": {
    "chrome": "5",
    "opera": "15",
    "edge": "12",
    "firefox": "17",
    "safari": "6",
    "node": "0.4",
    "deno": "1",
    "android": "4",
    "ios": "7",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.14",
    "opera_mobile": "14",
    "electron": "0.20"
  },
  "es6.string.trim": {
    "chrome": "5",
    "opera": "10.50",
    "edge": "12",
    "firefox": "3.5",
    "safari": "4",
    "node": "0.4",
    "deno": "1",
    "ie": "9",
    "android": "4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "10.1",
    "electron": "0.20"
  },
  "es7.string.trim-left": {
    "chrome": "66",
    "opera": "53",
    "edge": "79",
    "firefox": "61",
    "safari": "12",
    "node": "10",
    "deno": "1",
    "ios": "12",
    "samsung": "9",
    "rhino": "1.7.13",
    "opera_mobile": "47",
    "electron": "3.0"
  },
  "es7.string.trim-right": {
    "chrome": "66",
    "opera": "53",
    "edge": "79",
    "firefox": "61",
    "safari": "12",
    "node": "10",
    "deno": "1",
    "ios": "12",
    "samsung": "9",
    "rhino": "1.7.13",
    "opera_mobile": "47",
    "electron": "3.0"
  },
  "es6.typed.array-buffer": {
    "chrome": "51",
    "opera": "38",
    "edge": "13",
    "firefox": "48",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es6.typed.data-view": {
    "chrome": "5",
    "opera": "12",
    "edge": "12",
    "firefox": "15",
    "safari": "5.1",
    "node": "0.4",
    "deno": "1",
    "ie": "10",
    "android": "4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "12",
    "electron": "0.20"
  },
  "es6.typed.int8-array": {
    "chrome": "51",
    "opera": "38",
    "edge": "13",
    "firefox": "48",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es6.typed.uint8-array": {
    "chrome": "51",
    "opera": "38",
    "edge": "13",
    "firefox": "48",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es6.typed.uint8-clamped-array": {
    "chrome": "51",
    "opera": "38",
    "edge": "13",
    "firefox": "48",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es6.typed.int16-array": {
    "chrome": "51",
    "opera": "38",
    "edge": "13",
    "firefox": "48",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es6.typed.uint16-array": {
    "chrome": "51",
    "opera": "38",
    "edge": "13",
    "firefox": "48",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es6.typed.int32-array": {
    "chrome": "51",
    "opera": "38",
    "edge": "13",
    "firefox": "48",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es6.typed.uint32-array": {
    "chrome": "51",
    "opera": "38",
    "edge": "13",
    "firefox": "48",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es6.typed.float32-array": {
    "chrome": "51",
    "opera": "38",
    "edge": "13",
    "firefox": "48",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es6.typed.float64-array": {
    "chrome": "51",
    "opera": "38",
    "edge": "13",
    "firefox": "48",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es6.weak-map": {
    "chrome": "51",
    "opera": "38",
    "edge": "15",
    "firefox": "53",
    "safari": "9",
    "node": "6.5",
    "deno": "1",
    "ios": "9",
    "samsung": "5",
    "rhino": "1.7.15",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "es6.weak-set": {
    "chrome": "51",
    "opera": "38",
    "edge": "15",
    "firefox": "53",
    "safari": "9",
    "node": "6.5",
    "deno": "1",
    "ios": "9",
    "samsung": "5",
    "rhino": "1.7.15",
    "opera_mobile": "41",
    "electron": "1.2"
  }
}
```

----

# frontend/node_modules/@babel/compat-data/data/corejs3-shipped-proposals.json
```json
[
  "esnext.promise.all-settled",
  "esnext.string.match-all",
  "esnext.global-this"
]
```

----

# frontend/node_modules/@babel/compat-data/data/native-modules.json
```json
{
  "es6.module": {
    "chrome": "61",
    "and_chr": "61",
    "edge": "16",
    "firefox": "60",
    "and_ff": "60",
    "node": "13.2.0",
    "opera": "48",
    "op_mob": "45",
    "safari": "10.1",
    "ios": "10.3",
    "samsung": "8.2",
    "android": "61",
    "electron": "2.0",
    "ios_saf": "10.3"
  }
}
```

----

# frontend/node_modules/@babel/compat-data/data/overlapping-plugins.json
```json
{
  "transform-async-to-generator": [
    "bugfix/transform-async-arrows-in-class"
  ],
  "transform-parameters": [
    "bugfix/transform-edge-default-parameters",
    "bugfix/transform-safari-id-destructuring-collision-in-function-expression"
  ],
  "transform-function-name": [
    "bugfix/transform-edge-function-name"
  ],
  "transform-block-scoping": [
    "bugfix/transform-safari-block-shadowing",
    "bugfix/transform-safari-for-shadowing"
  ],
  "transform-template-literals": [
    "bugfix/transform-tagged-template-caching"
  ],
  "transform-optional-chaining": [
    "bugfix/transform-v8-spread-parameters-in-optional-chaining"
  ],
  "proposal-optional-chaining": [
    "bugfix/transform-v8-spread-parameters-in-optional-chaining"
  ],
  "transform-class-properties": [
    "bugfix/transform-v8-static-class-fields-redefine-readonly",
    "bugfix/transform-firefox-class-in-computed-class-key",
    "bugfix/transform-safari-class-field-initializer-scope"
  ],
  "proposal-class-properties": [
    "bugfix/transform-v8-static-class-fields-redefine-readonly",
    "bugfix/transform-firefox-class-in-computed-class-key",
    "bugfix/transform-safari-class-field-initializer-scope"
  ]
}
```

----

# frontend/node_modules/@babel/compat-data/data/plugin-bugfixes.json
```json
{
  "bugfix/transform-async-arrows-in-class": {
    "chrome": "55",
    "opera": "42",
    "edge": "15",
    "firefox": "52",
    "safari": "11",
    "node": "7.6",
    "deno": "1",
    "ios": "11",
    "samsung": "6",
    "opera_mobile": "42",
    "electron": "1.6"
  },
  "bugfix/transform-edge-default-parameters": {
    "chrome": "49",
    "opera": "36",
    "edge": "18",
    "firefox": "52",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "bugfix/transform-edge-function-name": {
    "chrome": "51",
    "opera": "38",
    "edge": "79",
    "firefox": "53",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "bugfix/transform-safari-block-shadowing": {
    "chrome": "49",
    "opera": "36",
    "edge": "12",
    "firefox": "44",
    "safari": "11",
    "node": "6",
    "deno": "1",
    "ie": "11",
    "ios": "11",
    "samsung": "5",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "bugfix/transform-safari-for-shadowing": {
    "chrome": "49",
    "opera": "36",
    "edge": "12",
    "firefox": "4",
    "safari": "11",
    "node": "6",
    "deno": "1",
    "ie": "11",
    "ios": "11",
    "samsung": "5",
    "rhino": "1.7.13",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "bugfix/transform-safari-id-destructuring-collision-in-function-expression": {
    "chrome": "49",
    "opera": "36",
    "edge": "14",
    "firefox": "2",
    "safari": "16.3",
    "node": "6",
    "deno": "1",
    "ios": "16.3",
    "samsung": "5",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "bugfix/transform-tagged-template-caching": {
    "chrome": "41",
    "opera": "28",
    "edge": "12",
    "firefox": "34",
    "safari": "13",
    "node": "4",
    "deno": "1",
    "ios": "13",
    "samsung": "3.4",
    "rhino": "1.7.14",
    "opera_mobile": "28",
    "electron": "0.21"
  },
  "bugfix/transform-v8-spread-parameters-in-optional-chaining": {
    "chrome": "91",
    "opera": "77",
    "edge": "91",
    "firefox": "74",
    "safari": "13.1",
    "node": "16.9",
    "deno": "1.9",
    "ios": "13.4",
    "samsung": "16",
    "opera_mobile": "64",
    "electron": "13.0"
  },
  "transform-optional-chaining": {
    "chrome": "80",
    "opera": "67",
    "edge": "80",
    "firefox": "74",
    "safari": "13.1",
    "node": "14",
    "deno": "1",
    "ios": "13.4",
    "samsung": "13",
    "rhino": "1.8",
    "opera_mobile": "57",
    "electron": "8.0"
  },
  "proposal-optional-chaining": {
    "chrome": "80",
    "opera": "67",
    "edge": "80",
    "firefox": "74",
    "safari": "13.1",
    "node": "14",
    "deno": "1",
    "ios": "13.4",
    "samsung": "13",
    "rhino": "1.8",
    "opera_mobile": "57",
    "electron": "8.0"
  },
  "transform-parameters": {
    "chrome": "49",
    "opera": "36",
    "edge": "15",
    "firefox": "52",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "transform-async-to-generator": {
    "chrome": "55",
    "opera": "42",
    "edge": "15",
    "firefox": "52",
    "safari": "10.1",
    "node": "7.6",
    "deno": "1",
    "ios": "10.3",
    "samsung": "6",
    "opera_mobile": "42",
    "electron": "1.6"
  },
  "transform-template-literals": {
    "chrome": "41",
    "opera": "28",
    "edge": "13",
    "firefox": "34",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "3.4",
    "opera_mobile": "28",
    "electron": "0.21"
  },
  "transform-function-name": {
    "chrome": "51",
    "opera": "38",
    "edge": "14",
    "firefox": "53",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "transform-block-scoping": {
    "chrome": "50",
    "opera": "37",
    "edge": "14",
    "firefox": "53",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "37",
    "electron": "1.1"
  }
}
```

----

# frontend/node_modules/@babel/compat-data/data/plugins.json
```json
{
  "transform-explicit-resource-management": {
    "chrome": "134",
    "edge": "134",
    "firefox": "141",
    "node": "24",
    "electron": "35.0"
  },
  "transform-duplicate-named-capturing-groups-regex": {
    "chrome": "126",
    "opera": "112",
    "edge": "126",
    "firefox": "129",
    "safari": "17.4",
    "node": "23",
    "ios": "17.4",
    "electron": "31.0"
  },
  "transform-regexp-modifiers": {
    "chrome": "125",
    "opera": "111",
    "edge": "125",
    "firefox": "132",
    "node": "23",
    "samsung": "27",
    "electron": "31.0"
  },
  "transform-unicode-sets-regex": {
    "chrome": "112",
    "opera": "98",
    "edge": "112",
    "firefox": "116",
    "safari": "17",
    "node": "20",
    "deno": "1.32",
    "ios": "17",
    "samsung": "23",
    "opera_mobile": "75",
    "electron": "24.0"
  },
  "bugfix/transform-v8-static-class-fields-redefine-readonly": {
    "chrome": "98",
    "opera": "84",
    "edge": "98",
    "firefox": "75",
    "safari": "15",
    "node": "12",
    "deno": "1.18",
    "ios": "15",
    "samsung": "11",
    "opera_mobile": "52",
    "electron": "17.0"
  },
  "bugfix/transform-firefox-class-in-computed-class-key": {
    "chrome": "74",
    "opera": "62",
    "edge": "79",
    "firefox": "126",
    "safari": "16",
    "node": "12",
    "deno": "1",
    "ios": "16",
    "samsung": "11",
    "opera_mobile": "53",
    "electron": "6.0"
  },
  "bugfix/transform-safari-class-field-initializer-scope": {
    "chrome": "74",
    "opera": "62",
    "edge": "79",
    "firefox": "69",
    "safari": "16",
    "node": "12",
    "deno": "1",
    "ios": "16",
    "samsung": "11",
    "opera_mobile": "53",
    "electron": "6.0"
  },
  "transform-class-static-block": {
    "chrome": "94",
    "opera": "80",
    "edge": "94",
    "firefox": "93",
    "safari": "16.4",
    "node": "16.11",
    "deno": "1.14",
    "ios": "16.4",
    "samsung": "17",
    "opera_mobile": "66",
    "electron": "15.0"
  },
  "proposal-class-static-block": {
    "chrome": "94",
    "opera": "80",
    "edge": "94",
    "firefox": "93",
    "safari": "16.4",
    "node": "16.11",
    "deno": "1.14",
    "ios": "16.4",
    "samsung": "17",
    "opera_mobile": "66",
    "electron": "15.0"
  },
  "transform-private-property-in-object": {
    "chrome": "91",
    "opera": "77",
    "edge": "91",
    "firefox": "90",
    "safari": "15",
    "node": "16.9",
    "deno": "1.9",
    "ios": "15",
    "samsung": "16",
    "opera_mobile": "64",
    "electron": "13.0"
  },
  "proposal-private-property-in-object": {
    "chrome": "91",
    "opera": "77",
    "edge": "91",
    "firefox": "90",
    "safari": "15",
    "node": "16.9",
    "deno": "1.9",
    "ios": "15",
    "samsung": "16",
    "opera_mobile": "64",
    "electron": "13.0"
  },
  "transform-class-properties": {
    "chrome": "74",
    "opera": "62",
    "edge": "79",
    "firefox": "90",
    "safari": "14.1",
    "node": "12",
    "deno": "1",
    "ios": "14.5",
    "samsung": "11",
    "opera_mobile": "53",
    "electron": "6.0"
  },
  "proposal-class-properties": {
    "chrome": "74",
    "opera": "62",
    "edge": "79",
    "firefox": "90",
    "safari": "14.1",
    "node": "12",
    "deno": "1",
    "ios": "14.5",
    "samsung": "11",
    "opera_mobile": "53",
    "electron": "6.0"
  },
  "transform-private-methods": {
    "chrome": "84",
    "opera": "70",
    "edge": "84",
    "firefox": "90",
    "safari": "15",
    "node": "14.6",
    "deno": "1",
    "ios": "15",
    "samsung": "14",
    "opera_mobile": "60",
    "electron": "10.0"
  },
  "proposal-private-methods": {
    "chrome": "84",
    "opera": "70",
    "edge": "84",
    "firefox": "90",
    "safari": "15",
    "node": "14.6",
    "deno": "1",
    "ios": "15",
    "samsung": "14",
    "opera_mobile": "60",
    "electron": "10.0"
  },
  "transform-numeric-separator": {
    "chrome": "75",
    "opera": "62",
    "edge": "79",
    "firefox": "70",
    "safari": "13",
    "node": "12.5",
    "deno": "1",
    "ios": "13",
    "samsung": "11",
    "rhino": "1.7.14",
    "opera_mobile": "54",
    "electron": "6.0"
  },
  "proposal-numeric-separator": {
    "chrome": "75",
    "opera": "62",
    "edge": "79",
    "firefox": "70",
    "safari": "13",
    "node": "12.5",
    "deno": "1",
    "ios": "13",
    "samsung": "11",
    "rhino": "1.7.14",
    "opera_mobile": "54",
    "electron": "6.0"
  },
  "transform-logical-assignment-operators": {
    "chrome": "85",
    "opera": "71",
    "edge": "85",
    "firefox": "79",
    "safari": "14",
    "node": "15",
    "deno": "1.2",
    "ios": "14",
    "samsung": "14",
    "opera_mobile": "60",
    "electron": "10.0"
  },
  "proposal-logical-assignment-operators": {
    "chrome": "85",
    "opera": "71",
    "edge": "85",
    "firefox": "79",
    "safari": "14",
    "node": "15",
    "deno": "1.2",
    "ios": "14",
    "samsung": "14",
    "opera_mobile": "60",
    "electron": "10.0"
  },
  "transform-nullish-coalescing-operator": {
    "chrome": "80",
    "opera": "67",
    "edge": "80",
    "firefox": "72",
    "safari": "13.1",
    "node": "14",
    "deno": "1",
    "ios": "13.4",
    "samsung": "13",
    "rhino": "1.8",
    "opera_mobile": "57",
    "electron": "8.0"
  },
  "proposal-nullish-coalescing-operator": {
    "chrome": "80",
    "opera": "67",
    "edge": "80",
    "firefox": "72",
    "safari": "13.1",
    "node": "14",
    "deno": "1",
    "ios": "13.4",
    "samsung": "13",
    "rhino": "1.8",
    "opera_mobile": "57",
    "electron": "8.0"
  },
  "transform-optional-chaining": {
    "chrome": "91",
    "opera": "77",
    "edge": "91",
    "firefox": "74",
    "safari": "13.1",
    "node": "16.9",
    "deno": "1.9",
    "ios": "13.4",
    "samsung": "16",
    "opera_mobile": "64",
    "electron": "13.0"
  },
  "proposal-optional-chaining": {
    "chrome": "91",
    "opera": "77",
    "edge": "91",
    "firefox": "74",
    "safari": "13.1",
    "node": "16.9",
    "deno": "1.9",
    "ios": "13.4",
    "samsung": "16",
    "opera_mobile": "64",
    "electron": "13.0"
  },
  "transform-json-strings": {
    "chrome": "66",
    "opera": "53",
    "edge": "79",
    "firefox": "62",
    "safari": "12",
    "node": "10",
    "deno": "1",
    "ios": "12",
    "samsung": "9",
    "rhino": "1.7.14",
    "opera_mobile": "47",
    "electron": "3.0"
  },
  "proposal-json-strings": {
    "chrome": "66",
    "opera": "53",
    "edge": "79",
    "firefox": "62",
    "safari": "12",
    "node": "10",
    "deno": "1",
    "ios": "12",
    "samsung": "9",
    "rhino": "1.7.14",
    "opera_mobile": "47",
    "electron": "3.0"
  },
  "transform-optional-catch-binding": {
    "chrome": "66",
    "opera": "53",
    "edge": "79",
    "firefox": "58",
    "safari": "11.1",
    "node": "10",
    "deno": "1",
    "ios": "11.3",
    "samsung": "9",
    "opera_mobile": "47",
    "electron": "3.0"
  },
  "proposal-optional-catch-binding": {
    "chrome": "66",
    "opera": "53",
    "edge": "79",
    "firefox": "58",
    "safari": "11.1",
    "node": "10",
    "deno": "1",
    "ios": "11.3",
    "samsung": "9",
    "opera_mobile": "47",
    "electron": "3.0"
  },
  "transform-parameters": {
    "chrome": "49",
    "opera": "36",
    "edge": "18",
    "firefox": "52",
    "safari": "16.3",
    "node": "6",
    "deno": "1",
    "ios": "16.3",
    "samsung": "5",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "transform-async-generator-functions": {
    "chrome": "63",
    "opera": "50",
    "edge": "79",
    "firefox": "57",
    "safari": "12",
    "node": "10",
    "deno": "1",
    "ios": "12",
    "samsung": "8",
    "opera_mobile": "46",
    "electron": "3.0"
  },
  "proposal-async-generator-functions": {
    "chrome": "63",
    "opera": "50",
    "edge": "79",
    "firefox": "57",
    "safari": "12",
    "node": "10",
    "deno": "1",
    "ios": "12",
    "samsung": "8",
    "opera_mobile": "46",
    "electron": "3.0"
  },
  "transform-object-rest-spread": {
    "chrome": "60",
    "opera": "47",
    "edge": "79",
    "firefox": "55",
    "safari": "11.1",
    "node": "8.3",
    "deno": "1",
    "ios": "11.3",
    "samsung": "8",
    "opera_mobile": "44",
    "electron": "2.0"
  },
  "proposal-object-rest-spread": {
    "chrome": "60",
    "opera": "47",
    "edge": "79",
    "firefox": "55",
    "safari": "11.1",
    "node": "8.3",
    "deno": "1",
    "ios": "11.3",
    "samsung": "8",
    "opera_mobile": "44",
    "electron": "2.0"
  },
  "transform-dotall-regex": {
    "chrome": "62",
    "opera": "49",
    "edge": "79",
    "firefox": "78",
    "safari": "11.1",
    "node": "8.10",
    "deno": "1",
    "ios": "11.3",
    "samsung": "8",
    "rhino": "1.7.15",
    "opera_mobile": "46",
    "electron": "3.0"
  },
  "transform-unicode-property-regex": {
    "chrome": "64",
    "opera": "51",
    "edge": "79",
    "firefox": "78",
    "safari": "11.1",
    "node": "10",
    "deno": "1",
    "ios": "11.3",
    "samsung": "9",
    "opera_mobile": "47",
    "electron": "3.0"
  },
  "proposal-unicode-property-regex": {
    "chrome": "64",
    "opera": "51",
    "edge": "79",
    "firefox": "78",
    "safari": "11.1",
    "node": "10",
    "deno": "1",
    "ios": "11.3",
    "samsung": "9",
    "opera_mobile": "47",
    "electron": "3.0"
  },
  "transform-named-capturing-groups-regex": {
    "chrome": "64",
    "opera": "51",
    "edge": "79",
    "firefox": "78",
    "safari": "11.1",
    "node": "10",
    "deno": "1",
    "ios": "11.3",
    "samsung": "9",
    "opera_mobile": "47",
    "electron": "3.0"
  },
  "transform-async-to-generator": {
    "chrome": "55",
    "opera": "42",
    "edge": "15",
    "firefox": "52",
    "safari": "11",
    "node": "7.6",
    "deno": "1",
    "ios": "11",
    "samsung": "6",
    "opera_mobile": "42",
    "electron": "1.6"
  },
  "transform-exponentiation-operator": {
    "chrome": "52",
    "opera": "39",
    "edge": "14",
    "firefox": "52",
    "safari": "10.1",
    "node": "7",
    "deno": "1",
    "ios": "10.3",
    "samsung": "6",
    "rhino": "1.7.14",
    "opera_mobile": "41",
    "electron": "1.3"
  },
  "transform-template-literals": {
    "chrome": "41",
    "opera": "28",
    "edge": "13",
    "firefox": "34",
    "safari": "13",
    "node": "4",
    "deno": "1",
    "ios": "13",
    "samsung": "3.4",
    "opera_mobile": "28",
    "electron": "0.21"
  },
  "transform-literals": {
    "chrome": "44",
    "opera": "31",
    "edge": "12",
    "firefox": "53",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "4",
    "rhino": "1.7.15",
    "opera_mobile": "32",
    "electron": "0.30"
  },
  "transform-function-name": {
    "chrome": "51",
    "opera": "38",
    "edge": "79",
    "firefox": "53",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "transform-arrow-functions": {
    "chrome": "47",
    "opera": "34",
    "edge": "13",
    "firefox": "43",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.7.13",
    "opera_mobile": "34",
    "electron": "0.36"
  },
  "transform-block-scoped-functions": {
    "chrome": "41",
    "opera": "28",
    "edge": "12",
    "firefox": "46",
    "safari": "10",
    "node": "4",
    "deno": "1",
    "ie": "11",
    "ios": "10",
    "samsung": "3.4",
    "opera_mobile": "28",
    "electron": "0.21"
  },
  "transform-classes": {
    "chrome": "46",
    "opera": "33",
    "edge": "13",
    "firefox": "45",
    "safari": "10",
    "node": "5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "33",
    "electron": "0.36"
  },
  "transform-object-super": {
    "chrome": "46",
    "opera": "33",
    "edge": "13",
    "firefox": "45",
    "safari": "10",
    "node": "5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "33",
    "electron": "0.36"
  },
  "transform-shorthand-properties": {
    "chrome": "43",
    "opera": "30",
    "edge": "12",
    "firefox": "33",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "4",
    "rhino": "1.7.14",
    "opera_mobile": "30",
    "electron": "0.27"
  },
  "transform-duplicate-keys": {
    "chrome": "42",
    "opera": "29",
    "edge": "12",
    "firefox": "34",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "3.4",
    "opera_mobile": "29",
    "electron": "0.25"
  },
  "transform-computed-properties": {
    "chrome": "44",
    "opera": "31",
    "edge": "12",
    "firefox": "34",
    "safari": "7.1",
    "node": "4",
    "deno": "1",
    "ios": "8",
    "samsung": "4",
    "rhino": "1.8",
    "opera_mobile": "32",
    "electron": "0.30"
  },
  "transform-for-of": {
    "chrome": "51",
    "opera": "38",
    "edge": "15",
    "firefox": "53",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "transform-sticky-regex": {
    "chrome": "49",
    "opera": "36",
    "edge": "13",
    "firefox": "3",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "rhino": "1.7.15",
    "opera_mobile": "36",
    "electron": "0.37"
  },
  "transform-unicode-escapes": {
    "chrome": "44",
    "opera": "31",
    "edge": "12",
    "firefox": "53",
    "safari": "9",
    "node": "4",
    "deno": "1",
    "ios": "9",
    "samsung": "4",
    "rhino": "1.7.15",
    "opera_mobile": "32",
    "electron": "0.30"
  },
  "transform-unicode-regex": {
    "chrome": "50",
    "opera": "37",
    "edge": "13",
    "firefox": "46",
    "safari": "12",
    "node": "6",
    "deno": "1",
    "ios": "12",
    "samsung": "5",
    "opera_mobile": "37",
    "electron": "1.1"
  },
  "transform-spread": {
    "chrome": "46",
    "opera": "33",
    "edge": "13",
    "firefox": "45",
    "safari": "10",
    "node": "5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "33",
    "electron": "0.36"
  },
  "transform-destructuring": {
    "chrome": "51",
    "opera": "38",
    "edge": "15",
    "firefox": "53",
    "safari": "10",
    "node": "6.5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "41",
    "electron": "1.2"
  },
  "transform-block-scoping": {
    "chrome": "50",
    "opera": "37",
    "edge": "14",
    "firefox": "53",
    "safari": "11",
    "node": "6",
    "deno": "1",
    "ios": "11",
    "samsung": "5",
    "opera_mobile": "37",
    "electron": "1.1"
  },
  "transform-typeof-symbol": {
    "chrome": "48",
    "opera": "35",
    "edge": "12",
    "firefox": "36",
    "safari": "9",
    "node": "6",
    "deno": "1",
    "ios": "9",
    "samsung": "5",
    "rhino": "1.8",
    "opera_mobile": "35",
    "electron": "0.37"
  },
  "transform-new-target": {
    "chrome": "46",
    "opera": "33",
    "edge": "14",
    "firefox": "41",
    "safari": "10",
    "node": "5",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "33",
    "electron": "0.36"
  },
  "transform-regenerator": {
    "chrome": "50",
    "opera": "37",
    "edge": "13",
    "firefox": "53",
    "safari": "10",
    "node": "6",
    "deno": "1",
    "ios": "10",
    "samsung": "5",
    "opera_mobile": "37",
    "electron": "1.1"
  },
  "transform-member-expression-literals": {
    "chrome": "7",
    "opera": "12",
    "edge": "12",
    "firefox": "2",
    "safari": "5.1",
    "node": "0.4",
    "deno": "1",
    "ie": "9",
    "android": "4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "12",
    "electron": "0.20"
  },
  "transform-property-literals": {
    "chrome": "7",
    "opera": "12",
    "edge": "12",
    "firefox": "2",
    "safari": "5.1",
    "node": "0.4",
    "deno": "1",
    "ie": "9",
    "android": "4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "12",
    "electron": "0.20"
  },
  "transform-reserved-words": {
    "chrome": "13",
    "opera": "10.50",
    "edge": "12",
    "firefox": "2",
    "safari": "3.1",
    "node": "0.6",
    "deno": "1",
    "ie": "9",
    "android": "4.4",
    "ios": "6",
    "phantom": "1.9",
    "samsung": "1",
    "rhino": "1.7.13",
    "opera_mobile": "10.1",
    "electron": "0.20"
  },
  "transform-export-namespace-from": {
    "chrome": "72",
    "deno": "1.0",
    "edge": "79",
    "firefox": "80",
    "node": "13.2.0",
    "opera": "60",
    "opera_mobile": "51",
    "safari": "14.1",
    "ios": "14.5",
    "samsung": "11.0",
    "android": "72",
    "electron": "5.0"
  },
  "proposal-export-namespace-from": {
    "chrome": "72",
    "deno": "1.0",
    "edge": "79",
    "firefox": "80",
    "node": "13.2.0",
    "opera": "60",
    "opera_mobile": "51",
    "safari": "14.1",
    "ios": "14.5",
    "samsung": "11.0",
    "android": "72",
    "electron": "5.0"
  }
}
```

----

# frontend/node_modules/@babel/compat-data/package.json
```json
{
  "name": "@babel/compat-data",
  "version": "7.29.0",
  "author": "The Babel Team (https://babel.dev/team)",
  "license": "MIT",
  "description": "The compat-data to determine required Babel plugins",
  "repository": {
    "type": "git",
    "url": "https://github.com/babel/babel.git",
    "directory": "packages/babel-compat-data"
  },
  "publishConfig": {
    "access": "public"
  },
  "exports": {
    "./plugins": "./plugins.js",
    "./native-modules": "./native-modules.js",
    "./corejs2-built-ins": "./corejs2-built-ins.js",
    "./corejs3-shipped-proposals": "./corejs3-shipped-proposals.js",
    "./overlapping-plugins": "./overlapping-plugins.js",
    "./plugin-bugfixes": "./plugin-bugfixes.js"
  },
  "scripts": {
    "build-data": "./scripts/download-compat-table.sh && node ./scripts/build-data.mjs && node ./scripts/build-modules-support.mjs && node ./scripts/build-bugfixes-targets.mjs"
  },
  "keywords": [
    "babel",
    "compat-table",
    "compat-data"
  ],
  "devDependencies": {
    "@mdn/browser-compat-data": "^6.0.8",
    "core-js-compat": "^3.48.0",
    "electron-to-chromium": "^1.5.278"
  },
  "engines": {
    "node": ">=6.9.0"
  },
  "type": "commonjs"
}```

----

# frontend/node_modules/@babel/core/package.json
```json
{
  "name": "@babel/core",
  "version": "7.29.0",
  "description": "Babel compiler core.",
  "main": "./lib/index.js",
  "author": "The Babel Team (https://babel.dev/team)",
  "license": "MIT",
  "publishConfig": {
    "access": "public"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/babel/babel.git",
    "directory": "packages/babel-core"
  },
  "homepage": "https://babel.dev/docs/en/next/babel-core",
  "bugs": "https://github.com/babel/babel/issues?utf8=%E2%9C%93&q=is%3Aissue+label%3A%22pkg%3A%20core%22+is%3Aopen",
  "keywords": [
    "6to5",
    "babel",
    "classes",
    "const",
    "es6",
    "harmony",
    "let",
    "modules",
    "transpile",
    "transpiler",
    "var",
    "babel-core",
    "compiler"
  ],
  "engines": {
    "node": ">=6.9.0"
  },
  "funding": {
    "type": "opencollective",
    "url": "https://opencollective.com/babel"
  },
  "browser": {
    "./lib/config/files/index.js": "./lib/config/files/index-browser.js",
    "./lib/config/resolve-targets.js": "./lib/config/resolve-targets-browser.js",
    "./lib/transform-file.js": "./lib/transform-file-browser.js",
    "./src/config/files/index.ts": "./src/config/files/index-browser.ts",
    "./src/config/resolve-targets.ts": "./src/config/resolve-targets-browser.ts",
    "./src/transform-file.ts": "./src/transform-file-browser.ts"
  },
  "dependencies": {
    "@babel/code-frame": "^7.29.0",
    "@babel/generator": "^7.29.0",
    "@babel/helper-compilation-targets": "^7.28.6",
    "@babel/helper-module-transforms": "^7.28.6",
    "@babel/helpers": "^7.28.6",
    "@babel/parser": "^7.29.0",
    "@babel/template": "^7.28.6",
    "@babel/traverse": "^7.29.0",
    "@babel/types": "^7.29.0",
    "@jridgewell/remapping": "^2.3.5",
    "convert-source-map": "^2.0.0",
    "debug": "^4.1.0",
    "gensync": "^1.0.0-beta.2",
    "json5": "^2.2.3",
    "semver": "^6.3.1"
  },
  "devDependencies": {
    "@babel/helper-transform-fixture-test-runner": "^7.28.6",
    "@babel/plugin-syntax-flow": "^7.28.6",
    "@babel/plugin-transform-flow-strip-types": "^7.27.1",
    "@babel/plugin-transform-modules-commonjs": "^7.28.6",
    "@babel/preset-env": "^7.29.0",
    "@babel/preset-typescript": "^7.28.5",
    "@jridgewell/trace-mapping": "^0.3.28",
    "@types/convert-source-map": "^2.0.0",
    "@types/debug": "^4.1.0",
    "@types/resolve": "^1.3.2",
    "@types/semver": "^5.4.0",
    "rimraf": "^3.0.0",
    "ts-node": "^11.0.0-beta.1",
    "tsx": "^4.20.3"
  },
  "type": "commonjs"
}```

----

# frontend/node_modules/@babel/generator/package.json
```json
{
  "name": "@babel/generator",
  "version": "7.29.1",
  "description": "Turns an AST into code.",
  "author": "The Babel Team (https://babel.dev/team)",
  "license": "MIT",
  "publishConfig": {
    "access": "public"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/babel/babel.git",
    "directory": "packages/babel-generator"
  },
  "homepage": "https://babel.dev/docs/en/next/babel-generator",
  "bugs": "https://github.com/babel/babel/issues?utf8=%E2%9C%93&q=is%3Aissue+label%3A%22pkg%3A%20generator%22+is%3Aopen",
  "main": "./lib/index.js",
  "files": [
    "lib"
  ],
  "dependencies": {
    "@babel/parser": "^7.29.0",
    "@babel/types": "^7.29.0",
    "@jridgewell/gen-mapping": "^0.3.12",
    "@jridgewell/trace-mapping": "^0.3.28",
    "jsesc": "^3.0.2"
  },
  "devDependencies": {
    "@babel/core": "^7.29.0",
    "@babel/helper-fixtures": "^7.28.6",
    "@babel/plugin-transform-typescript": "^7.28.6",
    "@jridgewell/sourcemap-codec": "^1.5.3",
    "charcodes": "^0.2.0"
  },
  "engines": {
    "node": ">=6.9.0"
  },
  "type": "commonjs"
}```

----

# frontend/node_modules/@babel/helper-compilation-targets/package.json
```json
{
  "name": "@babel/helper-compilation-targets",
  "version": "7.28.6",
  "author": "The Babel Team (https://babel.dev/team)",
  "license": "MIT",
  "description": "Helper functions on Babel compilation targets",
  "repository": {
    "type": "git",
    "url": "https://github.com/babel/babel.git",
    "directory": "packages/babel-helper-compilation-targets"
  },
  "main": "./lib/index.js",
  "exports": {
    ".": {
      "types": "./lib/index.d.ts",
      "default": "./lib/index.js"
    },
    "./package.json": "./package.json"
  },
  "publishConfig": {
    "access": "public"
  },
  "keywords": [
    "babel",
    "babel-plugin"
  ],
  "dependencies": {
    "@babel/compat-data": "^7.28.6",
    "@babel/helper-validator-option": "^7.27.1",
    "browserslist": "^4.24.0",
    "lru-cache": "^5.1.1",
    "semver": "^6.3.1"
  },
  "devDependencies": {
    "@babel/helper-plugin-test-runner": "^7.27.1",
    "@types/lru-cache": "^5.1.1",
    "@types/semver": "^5.5.0"
  },
  "engines": {
    "node": ">=6.9.0"
  },
  "type": "commonjs"
}```

----

# frontend/node_modules/@babel/helper-globals/data/browser-upper.json
```json
[
  "AbortController",
  "AbortSignal",
  "AbsoluteOrientationSensor",
  "AbstractRange",
  "Accelerometer",
  "AI",
  "AICreateMonitor",
  "AITextSession",
  "AnalyserNode",
  "Animation",
  "AnimationEffect",
  "AnimationEvent",
  "AnimationPlaybackEvent",
  "AnimationTimeline",
  "AsyncDisposableStack",
  "Attr",
  "Audio",
  "AudioBuffer",
  "AudioBufferSourceNode",
  "AudioContext",
  "AudioData",
  "AudioDecoder",
  "AudioDestinationNode",
  "AudioEncoder",
  "AudioListener",
  "AudioNode",
  "AudioParam",
  "AudioParamMap",
  "AudioProcessingEvent",
  "AudioScheduledSourceNode",
  "AudioSinkInfo",
  "AudioWorklet",
  "AudioWorkletGlobalScope",
  "AudioWorkletNode",
  "AudioWorkletProcessor",
  "AuthenticatorAssertionResponse",
  "AuthenticatorAttestationResponse",
  "AuthenticatorResponse",
  "BackgroundFetchManager",
  "BackgroundFetchRecord",
  "BackgroundFetchRegistration",
  "BarcodeDetector",
  "BarProp",
  "BaseAudioContext",
  "BatteryManager",
  "BeforeUnloadEvent",
  "BiquadFilterNode",
  "Blob",
  "BlobEvent",
  "Bluetooth",
  "BluetoothCharacteristicProperties",
  "BluetoothDevice",
  "BluetoothRemoteGATTCharacteristic",
  "BluetoothRemoteGATTDescriptor",
  "BluetoothRemoteGATTServer",
  "BluetoothRemoteGATTService",
  "BluetoothUUID",
  "BroadcastChannel",
  "BrowserCaptureMediaStreamTrack",
  "ByteLengthQueuingStrategy",
  "Cache",
  "CacheStorage",
  "CanvasCaptureMediaStream",
  "CanvasCaptureMediaStreamTrack",
  "CanvasGradient",
  "CanvasPattern",
  "CanvasRenderingContext2D",
  "CaptureController",
  "CaretPosition",
  "CDATASection",
  "ChannelMergerNode",
  "ChannelSplitterNode",
  "ChapterInformation",
  "CharacterBoundsUpdateEvent",
  "CharacterData",
  "Clipboard",
  "ClipboardEvent",
  "ClipboardItem",
  "CloseEvent",
  "CloseWatcher",
  "CommandEvent",
  "Comment",
  "CompositionEvent",
  "CompressionStream",
  "ConstantSourceNode",
  "ContentVisibilityAutoStateChangeEvent",
  "ConvolverNode",
  "CookieChangeEvent",
  "CookieDeprecationLabel",
  "CookieStore",
  "CookieStoreManager",
  "CountQueuingStrategy",
  "Credential",
  "CredentialsContainer",
  "CropTarget",
  "Crypto",
  "CryptoKey",
  "CSPViolationReportBody",
  "CSS",
  "CSSAnimation",
  "CSSConditionRule",
  "CSSContainerRule",
  "CSSCounterStyleRule",
  "CSSFontFaceRule",
  "CSSFontFeatureValuesRule",
  "CSSFontPaletteValuesRule",
  "CSSGroupingRule",
  "CSSImageValue",
  "CSSImportRule",
  "CSSKeyframeRule",
  "CSSKeyframesRule",
  "CSSKeywordValue",
  "CSSLayerBlockRule",
  "CSSLayerStatementRule",
  "CSSMarginRule",
  "CSSMathClamp",
  "CSSMathInvert",
  "CSSMathMax",
  "CSSMathMin",
  "CSSMathNegate",
  "CSSMathProduct",
  "CSSMathSum",
  "CSSMathValue",
  "CSSMatrixComponent",
  "CSSMediaRule",
  "CSSNamespaceRule",
  "CSSNestedDeclarations",
  "CSSNumericArray",
  "CSSNumericValue",
  "CSSPageDescriptors",
  "CSSPageRule",
  "CSSPerspective",
  "CSSPositionTryDescriptors",
  "CSSPositionTryRule",
  "CSSPositionValue",
  "CSSPropertyRule",
  "CSSRotate",
  "CSSRule",
  "CSSRuleList",
  "CSSScale",
  "CSSScopeRule",
  "CSSSkew",
  "CSSSkewX",
  "CSSSkewY",
  "CSSStartingStyleRule",
  "CSSStyleDeclaration",
  "CSSStyleRule",
  "CSSStyleSheet",
  "CSSStyleValue",
  "CSSSupportsRule",
  "CSSTransformComponent",
  "CSSTransformValue",
  "CSSTransition",
  "CSSTranslate",
  "CSSUnitValue",
  "CSSUnparsedValue",
  "CSSVariableReferenceValue",
  "CSSViewTransitionRule",
  "CustomElementRegistry",
  "CustomEvent",
  "CustomStateSet",
  "DataTransfer",
  "DataTransferItem",
  "DataTransferItemList",
  "DecompressionStream",
  "DelayNode",
  "DelegatedInkTrailPresenter",
  "DeviceMotionEvent",
  "DeviceMotionEventAcceleration",
  "DeviceMotionEventRotationRate",
  "DeviceOrientationEvent",
  "DevicePosture",
  "DisposableStack",
  "Document",
  "DocumentFragment",
  "DocumentPictureInPicture",
  "DocumentPictureInPictureEvent",
  "DocumentTimeline",
  "DocumentType",
  "DOMError",
  "DOMException",
  "DOMImplementation",
  "DOMMatrix",
  "DOMMatrixReadOnly",
  "DOMParser",
  "DOMPoint",
  "DOMPointReadOnly",
  "DOMQuad",
  "DOMRect",
  "DOMRectList",
  "DOMRectReadOnly",
  "DOMStringList",
  "DOMStringMap",
  "DOMTokenList",
  "DragEvent",
  "DynamicsCompressorNode",
  "EditContext",
  "Element",
  "ElementInternals",
  "EncodedAudioChunk",
  "EncodedVideoChunk",
  "ErrorEvent",
  "Event",
  "EventCounts",
  "EventSource",
  "EventTarget",
  "External",
  "EyeDropper",
  "FeaturePolicy",
  "FederatedCredential",
  "Fence",
  "FencedFrameConfig",
  "FetchLaterResult",
  "File",
  "FileList",
  "FileReader",
  "FileSystem",
  "FileSystemDirectoryEntry",
  "FileSystemDirectoryHandle",
  "FileSystemDirectoryReader",
  "FileSystemEntry",
  "FileSystemFileEntry",
  "FileSystemFileHandle",
  "FileSystemHandle",
  "FileSystemObserver",
  "FileSystemWritableFileStream",
  "FocusEvent",
  "FontData",
  "FontFace",
  "FontFaceSet",
  "FontFaceSetLoadEvent",
  "FormData",
  "FormDataEvent",
  "FragmentDirective",
  "GainNode",
  "Gamepad",
  "GamepadAxisMoveEvent",
  "GamepadButton",
  "GamepadButtonEvent",
  "GamepadEvent",
  "GamepadHapticActuator",
  "GamepadPose",
  "Geolocation",
  "GeolocationCoordinates",
  "GeolocationPosition",
  "GeolocationPositionError",
  "GPU",
  "GPUAdapter",
  "GPUAdapterInfo",
  "GPUBindGroup",
  "GPUBindGroupLayout",
  "GPUBuffer",
  "GPUBufferUsage",
  "GPUCanvasContext",
  "GPUColorWrite",
  "GPUCommandBuffer",
  "GPUCommandEncoder",
  "GPUCompilationInfo",
  "GPUCompilationMessage",
  "GPUComputePassEncoder",
  "GPUComputePipeline",
  "GPUDevice",
  "GPUDeviceLostInfo",
  "GPUError",
  "GPUExternalTexture",
  "GPUInternalError",
  "GPUMapMode",
  "GPUOutOfMemoryError",
  "GPUPipelineError",
  "GPUPipelineLayout",
  "GPUQuerySet",
  "GPUQueue",
  "GPURenderBundle",
  "GPURenderBundleEncoder",
  "GPURenderPassEncoder",
  "GPURenderPipeline",
  "GPUSampler",
  "GPUShaderModule",
  "GPUShaderStage",
  "GPUSupportedFeatures",
  "GPUSupportedLimits",
  "GPUTexture",
  "GPUTextureUsage",
  "GPUTextureView",
  "GPUUncapturedErrorEvent",
  "GPUValidationError",
  "GravitySensor",
  "Gyroscope",
  "HashChangeEvent",
  "Headers",
  "HID",
  "HIDConnectionEvent",
  "HIDDevice",
  "HIDInputReportEvent",
  "Highlight",
  "HighlightRegistry",
  "History",
  "HTMLAllCollection",
  "HTMLAnchorElement",
  "HTMLAreaElement",
  "HTMLAudioElement",
  "HTMLBaseElement",
  "HTMLBodyElement",
  "HTMLBRElement",
  "HTMLButtonElement",
  "HTMLCanvasElement",
  "HTMLCollection",
  "HTMLDataElement",
  "HTMLDataListElement",
  "HTMLDetailsElement",
  "HTMLDialogElement",
  "HTMLDirectoryElement",
  "HTMLDivElement",
  "HTMLDListElement",
  "HTMLDocument",
  "HTMLElement",
  "HTMLEmbedElement",
  "HTMLFencedFrameElement",
  "HTMLFieldSetElement",
  "HTMLFontElement",
  "HTMLFormControlsCollection",
  "HTMLFormElement",
  "HTMLFrameElement",
  "HTMLFrameSetElement",
  "HTMLHeadElement",
  "HTMLHeadingElement",
  "HTMLHRElement",
  "HTMLHtmlElement",
  "HTMLIFrameElement",
  "HTMLImageElement",
  "HTMLInputElement",
  "HTMLLabelElement",
  "HTMLLegendElement",
  "HTMLLIElement",
  "HTMLLinkElement",
  "HTMLMapElement",
  "HTMLMarqueeElement",
  "HTMLMediaElement",
  "HTMLMenuElement",
  "HTMLMetaElement",
  "HTMLMeterElement",
  "HTMLModElement",
  "HTMLObjectElement",
  "HTMLOListElement",
  "HTMLOptGroupElement",
  "HTMLOptionElement",
  "HTMLOptionsCollection",
  "HTMLOutputElement",
  "HTMLParagraphElement",
  "HTMLParamElement",
  "HTMLPictureElement",
  "HTMLPreElement",
  "HTMLProgressElement",
  "HTMLQuoteElement",
  "HTMLScriptElement",
  "HTMLSelectedContentElement",
  "HTMLSelectElement",
  "HTMLSlotElement",
  "HTMLSourceElement",
  "HTMLSpanElement",
  "HTMLStyleElement",
  "HTMLTableCaptionElement",
  "HTMLTableCellElement",
  "HTMLTableColElement",
  "HTMLTableElement",
  "HTMLTableRowElement",
  "HTMLTableSectionElement",
  "HTMLTemplateElement",
  "HTMLTextAreaElement",
  "HTMLTimeElement",
  "HTMLTitleElement",
  "HTMLTrackElement",
  "HTMLUListElement",
  "HTMLUnknownElement",
  "HTMLVideoElement",
  "IDBCursor",
  "IDBCursorWithValue",
  "IDBDatabase",
  "IDBFactory",
  "IDBIndex",
  "IDBKeyRange",
  "IDBObjectStore",
  "IDBOpenDBRequest",
  "IDBRequest",
  "IDBTransaction",
  "IDBVersionChangeEvent",
  "IdentityCredential",
  "IdentityCredentialError",
  "IdentityProvider",
  "IdleDeadline",
  "IdleDetector",
  "IIRFilterNode",
  "Image",
  "ImageBitmap",
  "ImageBitmapRenderingContext",
  "ImageCapture",
  "ImageData",
  "ImageDecoder",
  "ImageTrack",
  "ImageTrackList",
  "Ink",
  "InputDeviceCapabilities",
  "InputDeviceInfo",
  "InputEvent",
  "IntersectionObserver",
  "IntersectionObserverEntry",
  "Keyboard",
  "KeyboardEvent",
  "KeyboardLayoutMap",
  "KeyframeEffect",
  "LanguageDetector",
  "LargestContentfulPaint",
  "LaunchParams",
  "LaunchQueue",
  "LayoutShift",
  "LayoutShiftAttribution",
  "LinearAccelerationSensor",
  "Location",
  "Lock",
  "LockManager",
  "MathMLElement",
  "MediaCapabilities",
  "MediaCapabilitiesInfo",
  "MediaDeviceInfo",
  "MediaDevices",
  "MediaElementAudioSourceNode",
  "MediaEncryptedEvent",
  "MediaError",
  "MediaKeyError",
  "MediaKeyMessageEvent",
  "MediaKeys",
  "MediaKeySession",
  "MediaKeyStatusMap",
  "MediaKeySystemAccess",
  "MediaList",
  "MediaMetadata",
  "MediaQueryList",
  "MediaQueryListEvent",
  "MediaRecorder",
  "MediaRecorderErrorEvent",
  "MediaSession",
  "MediaSource",
  "MediaSourceHandle",
  "MediaStream",
  "MediaStreamAudioDestinationNode",
  "MediaStreamAudioSourceNode",
  "MediaStreamEvent",
  "MediaStreamTrack",
  "MediaStreamTrackAudioSourceNode",
  "MediaStreamTrackAudioStats",
  "MediaStreamTrackEvent",
  "MediaStreamTrackGenerator",
  "MediaStreamTrackProcessor",
  "MediaStreamTrackVideoStats",
  "MessageChannel",
  "MessageEvent",
  "MessagePort",
  "MIDIAccess",
  "MIDIConnectionEvent",
  "MIDIInput",
  "MIDIInputMap",
  "MIDIMessageEvent",
  "MIDIOutput",
  "MIDIOutputMap",
  "MIDIPort",
  "MimeType",
  "MimeTypeArray",
  "ModelGenericSession",
  "ModelManager",
  "MouseEvent",
  "MutationEvent",
  "MutationObserver",
  "MutationRecord",
  "NamedNodeMap",
  "NavigateEvent",
  "Navigation",
  "NavigationActivation",
  "NavigationCurrentEntryChangeEvent",
  "NavigationDestination",
  "NavigationHistoryEntry",
  "NavigationPreloadManager",
  "NavigationTransition",
  "Navigator",
  "NavigatorLogin",
  "NavigatorManagedData",
  "NavigatorUAData",
  "NetworkInformation",
  "Node",
  "NodeFilter",
  "NodeIterator",
  "NodeList",
  "Notification",
  "NotifyPaintEvent",
  "NotRestoredReasonDetails",
  "NotRestoredReasons",
  "Observable",
  "OfflineAudioCompletionEvent",
  "OfflineAudioContext",
  "OffscreenCanvas",
  "OffscreenCanvasRenderingContext2D",
  "Option",
  "OrientationSensor",
  "OscillatorNode",
  "OTPCredential",
  "OverconstrainedError",
  "PageRevealEvent",
  "PageSwapEvent",
  "PageTransitionEvent",
  "PannerNode",
  "PasswordCredential",
  "Path2D",
  "PaymentAddress",
  "PaymentManager",
  "PaymentMethodChangeEvent",
  "PaymentRequest",
  "PaymentRequestUpdateEvent",
  "PaymentResponse",
  "Performance",
  "PerformanceElementTiming",
  "PerformanceEntry",
  "PerformanceEventTiming",
  "PerformanceLongAnimationFrameTiming",
  "PerformanceLongTaskTiming",
  "PerformanceMark",
  "PerformanceMeasure",
  "PerformanceNavigation",
  "PerformanceNavigationTiming",
  "PerformanceObserver",
  "PerformanceObserverEntryList",
  "PerformancePaintTiming",
  "PerformanceResourceTiming",
  "PerformanceScriptTiming",
  "PerformanceServerTiming",
  "PerformanceTiming",
  "PeriodicSyncManager",
  "PeriodicWave",
  "Permissions",
  "PermissionStatus",
  "PERSISTENT",
  "PictureInPictureEvent",
  "PictureInPictureWindow",
  "Plugin",
  "PluginArray",
  "PointerEvent",
  "PopStateEvent",
  "Presentation",
  "PresentationAvailability",
  "PresentationConnection",
  "PresentationConnectionAvailableEvent",
  "PresentationConnectionCloseEvent",
  "PresentationConnectionList",
  "PresentationReceiver",
  "PresentationRequest",
  "PressureObserver",
  "PressureRecord",
  "ProcessingInstruction",
  "Profiler",
  "ProgressEvent",
  "PromiseRejectionEvent",
  "ProtectedAudience",
  "PublicKeyCredential",
  "PushManager",
  "PushSubscription",
  "PushSubscriptionOptions",
  "RadioNodeList",
  "Range",
  "ReadableByteStreamController",
  "ReadableStream",
  "ReadableStreamBYOBReader",
  "ReadableStreamBYOBRequest",
  "ReadableStreamDefaultController",
  "ReadableStreamDefaultReader",
  "RelativeOrientationSensor",
  "RemotePlayback",
  "ReportBody",
  "ReportingObserver",
  "Request",
  "ResizeObserver",
  "ResizeObserverEntry",
  "ResizeObserverSize",
  "Response",
  "RestrictionTarget",
  "RTCCertificate",
  "RTCDataChannel",
  "RTCDataChannelEvent",
  "RTCDtlsTransport",
  "RTCDTMFSender",
  "RTCDTMFToneChangeEvent",
  "RTCEncodedAudioFrame",
  "RTCEncodedVideoFrame",
  "RTCError",
  "RTCErrorEvent",
  "RTCIceCandidate",
  "RTCIceTransport",
  "RTCPeerConnection",
  "RTCPeerConnectionIceErrorEvent",
  "RTCPeerConnectionIceEvent",
  "RTCRtpReceiver",
  "RTCRtpScriptTransform",
  "RTCRtpSender",
  "RTCRtpTransceiver",
  "RTCSctpTransport",
  "RTCSessionDescription",
  "RTCStatsReport",
  "RTCTrackEvent",
  "Scheduler",
  "Scheduling",
  "Screen",
  "ScreenDetailed",
  "ScreenDetails",
  "ScreenOrientation",
  "ScriptProcessorNode",
  "ScrollTimeline",
  "SecurityPolicyViolationEvent",
  "Selection",
  "Sensor",
  "SensorErrorEvent",
  "Serial",
  "SerialPort",
  "ServiceWorker",
  "ServiceWorkerContainer",
  "ServiceWorkerRegistration",
  "ShadowRoot",
  "SharedStorage",
  "SharedStorageAppendMethod",
  "SharedStorageClearMethod",
  "SharedStorageDeleteMethod",
  "SharedStorageModifierMethod",
  "SharedStorageSetMethod",
  "SharedStorageWorklet",
  "SharedWorker",
  "SnapEvent",
  "SourceBuffer",
  "SourceBufferList",
  "SpeechSynthesis",
  "SpeechSynthesisErrorEvent",
  "SpeechSynthesisEvent",
  "SpeechSynthesisUtterance",
  "SpeechSynthesisVoice",
  "StaticRange",
  "StereoPannerNode",
  "Storage",
  "StorageBucket",
  "StorageBucketManager",
  "StorageEvent",
  "StorageManager",
  "StylePropertyMap",
  "StylePropertyMapReadOnly",
  "StyleSheet",
  "StyleSheetList",
  "SubmitEvent",
  "Subscriber",
  "SubtleCrypto",
  "SuppressedError",
  "SVGAElement",
  "SVGAngle",
  "SVGAnimatedAngle",
  "SVGAnimatedBoolean",
  "SVGAnimatedEnumeration",
  "SVGAnimatedInteger",
  "SVGAnimatedLength",
  "SVGAnimatedLengthList",
  "SVGAnimatedNumber",
  "SVGAnimatedNumberList",
  "SVGAnimatedPreserveAspectRatio",
  "SVGAnimatedRect",
  "SVGAnimatedString",
  "SVGAnimatedTransformList",
  "SVGAnimateElement",
  "SVGAnimateMotionElement",
  "SVGAnimateTransformElement",
  "SVGAnimationElement",
  "SVGCircleElement",
  "SVGClipPathElement",
  "SVGComponentTransferFunctionElement",
  "SVGDefsElement",
  "SVGDescElement",
  "SVGElement",
  "SVGEllipseElement",
  "SVGFEBlendElement",
  "SVGFEColorMatrixElement",
  "SVGFEComponentTransferElement",
  "SVGFECompositeElement",
  "SVGFEConvolveMatrixElement",
  "SVGFEDiffuseLightingElement",
  "SVGFEDisplacementMapElement",
  "SVGFEDistantLightElement",
  "SVGFEDropShadowElement",
  "SVGFEFloodElement",
  "SVGFEFuncAElement",
  "SVGFEFuncBElement",
  "SVGFEFuncGElement",
  "SVGFEFuncRElement",
  "SVGFEGaussianBlurElement",
  "SVGFEImageElement",
  "SVGFEMergeElement",
  "SVGFEMergeNodeElement",
  "SVGFEMorphologyElement",
  "SVGFEOffsetElement",
  "SVGFEPointLightElement",
  "SVGFESpecularLightingElement",
  "SVGFESpotLightElement",
  "SVGFETileElement",
  "SVGFETurbulenceElement",
  "SVGFilterElement",
  "SVGForeignObjectElement",
  "SVGGElement",
  "SVGGeometryElement",
  "SVGGradientElement",
  "SVGGraphicsElement",
  "SVGImageElement",
  "SVGLength",
  "SVGLengthList",
  "SVGLinearGradientElement",
  "SVGLineElement",
  "SVGMarkerElement",
  "SVGMaskElement",
  "SVGMatrix",
  "SVGMetadataElement",
  "SVGMPathElement",
  "SVGNumber",
  "SVGNumberList",
  "SVGPathElement",
  "SVGPatternElement",
  "SVGPoint",
  "SVGPointList",
  "SVGPolygonElement",
  "SVGPolylineElement",
  "SVGPreserveAspectRatio",
  "SVGRadialGradientElement",
  "SVGRect",
  "SVGRectElement",
  "SVGScriptElement",
  "SVGSetElement",
  "SVGStopElement",
  "SVGStringList",
  "SVGStyleElement",
  "SVGSVGElement",
  "SVGSwitchElement",
  "SVGSymbolElement",
  "SVGTextContentElement",
  "SVGTextElement",
  "SVGTextPathElement",
  "SVGTextPositioningElement",
  "SVGTitleElement",
  "SVGTransform",
  "SVGTransformList",
  "SVGTSpanElement",
  "SVGUnitTypes",
  "SVGUseElement",
  "SVGViewElement",
  "SyncManager",
  "TaskAttributionTiming",
  "TaskController",
  "TaskPriorityChangeEvent",
  "TaskSignal",
  "TEMPORARY",
  "Text",
  "TextDecoder",
  "TextDecoderStream",
  "TextEncoder",
  "TextEncoderStream",
  "TextEvent",
  "TextFormat",
  "TextFormatUpdateEvent",
  "TextMetrics",
  "TextTrack",
  "TextTrackCue",
  "TextTrackCueList",
  "TextTrackList",
  "TextUpdateEvent",
  "TimeEvent",
  "TimeRanges",
  "ToggleEvent",
  "Touch",
  "TouchEvent",
  "TouchList",
  "TrackEvent",
  "TransformStream",
  "TransformStreamDefaultController",
  "TransitionEvent",
  "TreeWalker",
  "TrustedHTML",
  "TrustedScript",
  "TrustedScriptURL",
  "TrustedTypePolicy",
  "TrustedTypePolicyFactory",
  "UIEvent",
  "URL",
  "URLPattern",
  "URLSearchParams",
  "USB",
  "USBAlternateInterface",
  "USBConfiguration",
  "USBConnectionEvent",
  "USBDevice",
  "USBEndpoint",
  "USBInterface",
  "USBInTransferResult",
  "USBIsochronousInTransferPacket",
  "USBIsochronousInTransferResult",
  "USBIsochronousOutTransferPacket",
  "USBIsochronousOutTransferResult",
  "USBOutTransferResult",
  "UserActivation",
  "ValidityState",
  "VideoColorSpace",
  "VideoDecoder",
  "VideoEncoder",
  "VideoFrame",
  "VideoPlaybackQuality",
  "ViewTimeline",
  "ViewTransition",
  "ViewTransitionTypeSet",
  "VirtualKeyboard",
  "VirtualKeyboardGeometryChangeEvent",
  "VisibilityStateEntry",
  "VisualViewport",
  "VTTCue",
  "VTTRegion",
  "WakeLock",
  "WakeLockSentinel",
  "WaveShaperNode",
  "WebAssembly",
  "WebGL2RenderingContext",
  "WebGLActiveInfo",
  "WebGLBuffer",
  "WebGLContextEvent",
  "WebGLFramebuffer",
  "WebGLObject",
  "WebGLProgram",
  "WebGLQuery",
  "WebGLRenderbuffer",
  "WebGLRenderingContext",
  "WebGLSampler",
  "WebGLShader",
  "WebGLShaderPrecisionFormat",
  "WebGLSync",
  "WebGLTexture",
  "WebGLTransformFeedback",
  "WebGLUniformLocation",
  "WebGLVertexArrayObject",
  "WebSocket",
  "WebSocketError",
  "WebSocketStream",
  "WebTransport",
  "WebTransportBidirectionalStream",
  "WebTransportDatagramDuplexStream",
  "WebTransportError",
  "WebTransportReceiveStream",
  "WebTransportSendStream",
  "WGSLLanguageFeatures",
  "WheelEvent",
  "Window",
  "WindowControlsOverlay",
  "WindowControlsOverlayGeometryChangeEvent",
  "Worker",
  "Worklet",
  "WorkletGlobalScope",
  "WritableStream",
  "WritableStreamDefaultController",
  "WritableStreamDefaultWriter",
  "XMLDocument",
  "XMLHttpRequest",
  "XMLHttpRequestEventTarget",
  "XMLHttpRequestUpload",
  "XMLSerializer",
  "XPathEvaluator",
  "XPathExpression",
  "XPathResult",
  "XRAnchor",
  "XRAnchorSet",
  "XRBoundedReferenceSpace",
  "XRCamera",
  "XRCPUDepthInformation",
  "XRDepthInformation",
  "XRDOMOverlayState",
  "XRFrame",
  "XRHand",
  "XRHitTestResult",
  "XRHitTestSource",
  "XRInputSource",
  "XRInputSourceArray",
  "XRInputSourceEvent",
  "XRInputSourcesChangeEvent",
  "XRJointPose",
  "XRJointSpace",
  "XRLayer",
  "XRLightEstimate",
  "XRLightProbe",
  "XRPose",
  "XRRay",
  "XRReferenceSpace",
  "XRReferenceSpaceEvent",
  "XRRenderState",
  "XRRigidTransform",
  "XRSession",
  "XRSessionEvent",
  "XRSpace",
  "XRSystem",
  "XRTransientInputHitTestResult",
  "XRTransientInputHitTestSource",
  "XRView",
  "XRViewerPose",
  "XRViewport",
  "XRWebGLBinding",
  "XRWebGLDepthInformation",
  "XRWebGLLayer",
  "XSLTProcessor"
]
```

----

# frontend/node_modules/@babel/helper-globals/data/builtin-lower.json
```json
[
  "decodeURI",
  "decodeURIComponent",
  "encodeURI",
  "encodeURIComponent",
  "escape",
  "eval",
  "globalThis",
  "isFinite",
  "isNaN",
  "parseFloat",
  "parseInt",
  "undefined",
  "unescape"
]
```

----

# frontend/node_modules/@babel/helper-globals/data/builtin-upper.json
```json
[
  "AggregateError",
  "Array",
  "ArrayBuffer",
  "Atomics",
  "BigInt",
  "BigInt64Array",
  "BigUint64Array",
  "Boolean",
  "DataView",
  "Date",
  "Error",
  "EvalError",
  "FinalizationRegistry",
  "Float16Array",
  "Float32Array",
  "Float64Array",
  "Function",
  "Infinity",
  "Int16Array",
  "Int32Array",
  "Int8Array",
  "Intl",
  "Iterator",
  "JSON",
  "Map",
  "Math",
  "NaN",
  "Number",
  "Object",
  "Promise",
  "Proxy",
  "RangeError",
  "ReferenceError",
  "Reflect",
  "RegExp",
  "Set",
  "SharedArrayBuffer",
  "String",
  "Symbol",
  "SyntaxError",
  "TypeError",
  "Uint16Array",
  "Uint32Array",
  "Uint8Array",
  "Uint8ClampedArray",
  "URIError",
  "WeakMap",
  "WeakRef",
  "WeakSet"
]
```

----

# frontend/node_modules/@babel/helper-globals/package.json
```json
{
  "name": "@babel/helper-globals",
  "version": "7.28.0",
  "author": "The Babel Team (https://babel.dev/team)",
  "license": "MIT",
  "description": "A collection of JavaScript globals for Babel internal usage",
  "repository": {
    "type": "git",
    "url": "https://github.com/babel/babel.git",
    "directory": "packages/babel-helper-globals"
  },
  "publishConfig": {
    "access": "public"
  },
  "exports": {
    "./data/browser-upper.json": "./data/browser-upper.json",
    "./data/builtin-lower.json": "./data/builtin-lower.json",
    "./data/builtin-upper.json": "./data/builtin-upper.json",
    "./package.json": "./package.json"
  },
  "keywords": [
    "babel",
    "globals"
  ],
  "devDependencies": {
    "globals": "^16.1.0"
  },
  "engines": {
    "node": ">=6.9.0"
  },
  "type": "commonjs"
}```

----

# frontend/node_modules/@babel/helper-module-imports/package.json
```json
{
  "name": "@babel/helper-module-imports",
  "version": "7.28.6",
  "description": "Babel helper functions for inserting module loads",
  "author": "The Babel Team (https://babel.dev/team)",
  "homepage": "https://babel.dev/docs/en/next/babel-helper-module-imports",
  "license": "MIT",
  "publishConfig": {
    "access": "public"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/babel/babel.git",
    "directory": "packages/babel-helper-module-imports"
  },
  "main": "./lib/index.js",
  "dependencies": {
    "@babel/traverse": "^7.28.6",
    "@babel/types": "^7.28.6"
  },
  "devDependencies": {
    "@babel/core": "^7.28.6"
  },
  "engines": {
    "node": ">=6.9.0"
  },
  "type": "commonjs"
}```

----

# frontend/node_modules/@babel/helper-module-transforms/package.json
```json
{
  "name": "@babel/helper-module-transforms",
  "version": "7.28.6",
  "description": "Babel helper functions for implementing ES6 module transformations",
  "author": "The Babel Team (https://babel.dev/team)",
  "homepage": "https://babel.dev/docs/en/next/babel-helper-module-transforms",
  "license": "MIT",
  "publishConfig": {
    "access": "public"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/babel/babel.git",
    "directory": "packages/babel-helper-module-transforms"
  },
  "main": "./lib/index.js",
  "dependencies": {
    "@babel/helper-module-imports": "^7.28.6",
    "@babel/helper-validator-identifier": "^7.28.5",
    "@babel/traverse": "^7.28.6"
  },
  "devDependencies": {
    "@babel/core": "^7.28.6"
  },
  "peerDependencies": {
    "@babel/core": "^7.0.0"
  },
  "engines": {
    "node": ">=6.9.0"
  },
  "type": "commonjs"
}```

----

# frontend/node_modules/@babel/helper-plugin-utils/package.json
```json
{
  "name": "@babel/helper-plugin-utils",
  "version": "7.28.6",
  "description": "General utilities for plugins to use",
  "author": "The Babel Team (https://babel.dev/team)",
  "homepage": "https://babel.dev/docs/en/next/babel-helper-plugin-utils",
  "license": "MIT",
  "publishConfig": {
    "access": "public"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/babel/babel.git",
    "directory": "packages/babel-helper-plugin-utils"
  },
  "main": "./lib/index.js",
  "engines": {
    "node": ">=6.9.0"
  },
  "devDependencies": {
    "@babel/core": "^7.28.6"
  },
  "type": "commonjs"
}```

----

# frontend/node_modules/@babel/helper-string-parser/package.json
```json
{
  "name": "@babel/helper-string-parser",
  "version": "7.27.1",
  "description": "A utility package to parse strings",
  "repository": {
    "type": "git",
    "url": "https://github.com/babel/babel.git",
    "directory": "packages/babel-helper-string-parser"
  },
  "homepage": "https://babel.dev/docs/en/next/babel-helper-string-parser",
  "license": "MIT",
  "publishConfig": {
    "access": "public"
  },
  "main": "./lib/index.js",
  "devDependencies": {
    "charcodes": "^0.2.0"
  },
  "engines": {
    "node": ">=6.9.0"
  },
  "author": "The Babel Team (https://babel.dev/team)",
  "exports": {
    ".": {
      "types": "./lib/index.d.ts",
      "default": "./lib/index.js"
    },
    "./package.json": "./package.json"
  },
  "type": "commonjs"
}```

----

# frontend/node_modules/@babel/helper-validator-identifier/package.json
```json
{
  "name": "@babel/helper-validator-identifier",
  "version": "7.28.5",
  "description": "Validate identifier/keywords name",
  "repository": {
    "type": "git",
    "url": "https://github.com/babel/babel.git",
    "directory": "packages/babel-helper-validator-identifier"
  },
  "license": "MIT",
  "publishConfig": {
    "access": "public"
  },
  "main": "./lib/index.js",
  "exports": {
    ".": {
      "types": "./lib/index.d.ts",
      "default": "./lib/index.js"
    },
    "./package.json": "./package.json"
  },
  "devDependencies": {
    "@unicode/unicode-17.0.0": "^1.6.10",
    "charcodes": "^0.2.0"
  },
  "engines": {
    "node": ">=6.9.0"
  },
  "author": "The Babel Team (https://babel.dev/team)",
  "type": "commonjs"
}```

----

# frontend/node_modules/@babel/helper-validator-option/package.json
```json
{
  "name": "@babel/helper-validator-option",
  "version": "7.27.1",
  "description": "Validate plugin/preset options",
  "repository": {
    "type": "git",
    "url": "https://github.com/babel/babel.git",
    "directory": "packages/babel-helper-validator-option"
  },
  "license": "MIT",
  "publishConfig": {
    "access": "public"
  },
  "main": "./lib/index.js",
  "exports": {
    ".": {
      "types": "./lib/index.d.ts",
      "default": "./lib/index.js"
    },
    "./package.json": "./package.json"
  },
  "engines": {
    "node": ">=6.9.0"
  },
  "author": "The Babel Team (https://babel.dev/team)",
  "type": "commonjs"
}```

----

# frontend/node_modules/@babel/helpers/package.json
```json
{
  "name": "@babel/helpers",
  "version": "7.28.6",
  "description": "Collection of helper functions used by Babel transforms.",
  "author": "The Babel Team (https://babel.dev/team)",
  "homepage": "https://babel.dev/docs/en/next/babel-helpers",
  "license": "MIT",
  "publishConfig": {
    "access": "public"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/babel/babel.git",
    "directory": "packages/babel-helpers"
  },
  "main": "./lib/index.js",
  "dependencies": {
    "@babel/template": "^7.28.6",
    "@babel/types": "^7.28.6"
  },
  "devDependencies": {
    "@babel/generator": "^7.28.6",
    "@babel/helper-plugin-test-runner": "^7.27.1",
    "@babel/parser": "^7.28.6",
    "regenerator-runtime": "^0.14.0"
  },
  "engines": {
    "node": ">=6.9.0"
  },
  "type": "commonjs"
}```

----

# frontend/node_modules/@babel/parser/package.json
```json
{
  "name": "@babel/parser",
  "version": "7.29.0",
  "description": "A JavaScript parser",
  "author": "The Babel Team (https://babel.dev/team)",
  "homepage": "https://babel.dev/docs/en/next/babel-parser",
  "bugs": "https://github.com/babel/babel/issues?utf8=%E2%9C%93&q=is%3Aissue+label%3A%22pkg%3A+parser+%28babylon%29%22+is%3Aopen",
  "license": "MIT",
  "publishConfig": {
    "access": "public"
  },
  "keywords": [
    "babel",
    "javascript",
    "parser",
    "tc39",
    "ecmascript",
    "@babel/parser"
  ],
  "repository": {
    "type": "git",
    "url": "https://github.com/babel/babel.git",
    "directory": "packages/babel-parser"
  },
  "main": "./lib/index.js",
  "types": "./typings/babel-parser.d.ts",
  "files": [
    "bin",
    "lib",
    "typings/babel-parser.d.ts",
    "index.cjs"
  ],
  "engines": {
    "node": ">=6.0.0"
  },
  "# dependencies": "This package doesn't actually have runtime dependencies. @babel/types is only needed for type definitions.",
  "dependencies": {
    "@babel/types": "^7.29.0"
  },
  "devDependencies": {
    "@babel/code-frame": "^7.29.0",
    "@babel/helper-check-duplicate-nodes": "^7.28.6",
    "@babel/helper-fixtures": "^7.28.6",
    "@babel/helper-string-parser": "^7.27.1",
    "@babel/helper-validator-identifier": "^7.28.5",
    "charcodes": "^0.2.0"
  },
  "bin": "./bin/babel-parser.js",
  "type": "commonjs"
}```

----

# frontend/node_modules/@babel/plugin-transform-react-jsx-self/package.json
```json
{
  "name": "@babel/plugin-transform-react-jsx-self",
  "version": "7.27.1",
  "description": "Add a __self prop to all JSX Elements",
  "repository": {
    "type": "git",
    "url": "https://github.com/babel/babel.git",
    "directory": "packages/babel-plugin-transform-react-jsx-self"
  },
  "homepage": "https://babel.dev/docs/en/next/babel-plugin-transform-react-jsx-self",
  "license": "MIT",
  "publishConfig": {
    "access": "public"
  },
  "main": "./lib/index.js",
  "keywords": [
    "babel-plugin"
  ],
  "dependencies": {
    "@babel/helper-plugin-utils": "^7.27.1"
  },
  "peerDependencies": {
    "@babel/core": "^7.0.0-0"
  },
  "devDependencies": {
    "@babel/core": "^7.27.1",
    "@babel/helper-plugin-test-runner": "^7.27.1",
    "@babel/plugin-syntax-jsx": "^7.27.1"
  },
  "engines": {
    "node": ">=6.9.0"
  },
  "author": "The Babel Team (https://babel.dev/team)",
  "type": "commonjs"
}```

----

# frontend/node_modules/@babel/plugin-transform-react-jsx-source/package.json
```json
{
  "name": "@babel/plugin-transform-react-jsx-source",
  "version": "7.27.1",
  "description": "Add a __source prop to all JSX Elements",
  "repository": {
    "type": "git",
    "url": "https://github.com/babel/babel.git",
    "directory": "packages/babel-plugin-transform-react-jsx-source"
  },
  "homepage": "https://babel.dev/docs/en/next/babel-plugin-transform-react-jsx-source",
  "license": "MIT",
  "publishConfig": {
    "access": "public"
  },
  "main": "./lib/index.js",
  "keywords": [
    "babel-plugin"
  ],
  "dependencies": {
    "@babel/helper-plugin-utils": "^7.27.1"
  },
  "peerDependencies": {
    "@babel/core": "^7.0.0-0"
  },
  "devDependencies": {
    "@babel/core": "^7.27.1",
    "@babel/helper-plugin-test-runner": "^7.27.1",
    "@babel/plugin-syntax-jsx": "^7.27.1"
  },
  "engines": {
    "node": ">=6.9.0"
  },
  "author": "The Babel Team (https://babel.dev/team)",
  "type": "commonjs"
}```

----

# frontend/node_modules/@babel/template/package.json
```json
{
  "name": "@babel/template",
  "version": "7.28.6",
  "description": "Generate an AST from a string template.",
  "author": "The Babel Team (https://babel.dev/team)",
  "homepage": "https://babel.dev/docs/en/next/babel-template",
  "bugs": "https://github.com/babel/babel/issues?utf8=%E2%9C%93&q=is%3Aissue+label%3A%22pkg%3A%20template%22+is%3Aopen",
  "license": "MIT",
  "publishConfig": {
    "access": "public"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/babel/babel.git",
    "directory": "packages/babel-template"
  },
  "main": "./lib/index.js",
  "dependencies": {
    "@babel/code-frame": "^7.28.6",
    "@babel/parser": "^7.28.6",
    "@babel/types": "^7.28.6"
  },
  "engines": {
    "node": ">=6.9.0"
  },
  "type": "commonjs"
}```

----

# frontend/node_modules/@babel/traverse/package.json
```json
{
  "name": "@babel/traverse",
  "version": "7.29.0",
  "description": "The Babel Traverse module maintains the overall tree state, and is responsible for replacing, removing, and adding nodes",
  "author": "The Babel Team (https://babel.dev/team)",
  "homepage": "https://babel.dev/docs/en/next/babel-traverse",
  "bugs": "https://github.com/babel/babel/issues?utf8=%E2%9C%93&q=is%3Aissue+label%3A%22pkg%3A%20traverse%22+is%3Aopen",
  "license": "MIT",
  "publishConfig": {
    "access": "public"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/babel/babel.git",
    "directory": "packages/babel-traverse"
  },
  "main": "./lib/index.js",
  "dependencies": {
    "@babel/code-frame": "^7.29.0",
    "@babel/generator": "^7.29.0",
    "@babel/helper-globals": "^7.28.0",
    "@babel/parser": "^7.29.0",
    "@babel/template": "^7.28.6",
    "@babel/types": "^7.29.0",
    "debug": "^4.3.1"
  },
  "devDependencies": {
    "@babel/core": "^7.29.0",
    "@babel/helper-plugin-test-runner": "^7.27.1"
  },
  "engines": {
    "node": ">=6.9.0"
  },
  "type": "commonjs"
}```

----

# frontend/node_modules/@babel/traverse/tsconfig.overrides.json
```json
{
  "compilerOptions": {
    "strictNullChecks": true,
    "strictPropertyInitialization": true
  }
}```

----

# frontend/node_modules/@babel/types/package.json
```json
{
  "name": "@babel/types",
  "version": "7.29.0",
  "description": "Babel Types is a Lodash-esque utility library for AST nodes",
  "author": "The Babel Team (https://babel.dev/team)",
  "homepage": "https://babel.dev/docs/en/next/babel-types",
  "bugs": "https://github.com/babel/babel/issues?utf8=%E2%9C%93&q=is%3Aissue+label%3A%22pkg%3A%20types%22+is%3Aopen",
  "license": "MIT",
  "publishConfig": {
    "access": "public"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/babel/babel.git",
    "directory": "packages/babel-types"
  },
  "main": "./lib/index.js",
  "dependencies": {
    "@babel/helper-string-parser": "^7.27.1",
    "@babel/helper-validator-identifier": "^7.28.5"
  },
  "devDependencies": {
    "@babel/generator": "^7.29.0",
    "@babel/helper-fixtures": "^7.28.6",
    "@babel/parser": "^7.29.0"
  },
  "engines": {
    "node": ">=6.9.0"
  },
  "type": "commonjs",
  "types": "./lib/index-legacy.d.ts",
  "typesVersions": {
    ">=4.1": {
      "lib/index-legacy.d.ts": [
        "lib/index.d.ts"
      ]
    }
  }
}```

----

# frontend/node_modules/@jridgewell/gen-mapping/package.json
```json
{
  "name": "@jridgewell/gen-mapping",
  "version": "0.3.13",
  "description": "Generate source maps",
  "keywords": [
    "source",
    "map"
  ],
  "main": "dist/gen-mapping.umd.js",
  "module": "dist/gen-mapping.mjs",
  "types": "types/gen-mapping.d.cts",
  "files": [
    "dist",
    "src",
    "types"
  ],
  "exports": {
    ".": [
      {
        "import": {
          "types": "./types/gen-mapping.d.mts",
          "default": "./dist/gen-mapping.mjs"
        },
        "default": {
          "types": "./types/gen-mapping.d.cts",
          "default": "./dist/gen-mapping.umd.js"
        }
      },
      "./dist/gen-mapping.umd.js"
    ],
    "./package.json": "./package.json"
  },
  "scripts": {
    "benchmark": "run-s build:code benchmark:*",
    "benchmark:install": "cd benchmark && npm install",
    "benchmark:only": "node --expose-gc benchmark/index.js",
    "build": "run-s -n build:code build:types",
    "build:code": "node ../../esbuild.mjs gen-mapping.ts",
    "build:types": "run-s build:types:force build:types:emit build:types:mts",
    "build:types:force": "rimraf tsconfig.build.tsbuildinfo",
    "build:types:emit": "tsc --project tsconfig.build.json",
    "build:types:mts": "node ../../mts-types.mjs",
    "clean": "run-s -n clean:code clean:types",
    "clean:code": "tsc --build --clean tsconfig.build.json",
    "clean:types": "rimraf dist types",
    "test": "run-s -n test:types test:only test:format",
    "test:format": "prettier --check '{src,test}/**/*.ts'",
    "test:only": "mocha",
    "test:types": "eslint '{src,test}/**/*.ts'",
    "lint": "run-s -n lint:types lint:format",
    "lint:format": "npm run test:format -- --write",
    "lint:types": "npm run test:types -- --fix",
    "prepublishOnly": "npm run-s -n build test"
  },
  "homepage": "https://github.com/jridgewell/sourcemaps/tree/main/packages/gen-mapping",
  "repository": {
    "type": "git",
    "url": "git+https://github.com/jridgewell/sourcemaps.git",
    "directory": "packages/gen-mapping"
  },
  "author": "Justin Ridgewell <justin@ridgewell.name>",
  "license": "MIT",
  "dependencies": {
    "@jridgewell/sourcemap-codec": "^1.5.0",
    "@jridgewell/trace-mapping": "^0.3.24"
  }
}
```

----

# frontend/node_modules/@jridgewell/remapping/package.json
```json
{
  "name": "@jridgewell/remapping",
  "version": "2.3.5",
  "description": "Remap sequential sourcemaps through transformations to point at the original source code",
  "keywords": [
    "source",
    "map",
    "remap"
  ],
  "main": "dist/remapping.umd.js",
  "module": "dist/remapping.mjs",
  "types": "types/remapping.d.cts",
  "files": [
    "dist",
    "src",
    "types"
  ],
  "exports": {
    ".": [
      {
        "import": {
          "types": "./types/remapping.d.mts",
          "default": "./dist/remapping.mjs"
        },
        "default": {
          "types": "./types/remapping.d.cts",
          "default": "./dist/remapping.umd.js"
        }
      },
      "./dist/remapping.umd.js"
    ],
    "./package.json": "./package.json"
  },
  "scripts": {
    "benchmark": "run-s build:code benchmark:*",
    "benchmark:install": "cd benchmark && npm install",
    "benchmark:only": "node --expose-gc benchmark/index.js",
    "build": "run-s -n build:code build:types",
    "build:code": "node ../../esbuild.mjs remapping.ts",
    "build:types": "run-s build:types:force build:types:emit build:types:mts",
    "build:types:force": "rimraf tsconfig.build.tsbuildinfo",
    "build:types:emit": "tsc --project tsconfig.build.json",
    "build:types:mts": "node ../../mts-types.mjs",
    "clean": "run-s -n clean:code clean:types",
    "clean:code": "tsc --build --clean tsconfig.build.json",
    "clean:types": "rimraf dist types",
    "test": "run-s -n test:types test:only test:format",
    "test:format": "prettier --check '{src,test}/**/*.ts'",
    "test:only": "mocha",
    "test:types": "eslint '{src,test}/**/*.ts'",
    "lint": "run-s -n lint:types lint:format",
    "lint:format": "npm run test:format -- --write",
    "lint:types": "npm run test:types -- --fix",
    "prepublishOnly": "npm run-s -n build test"
  },
  "homepage": "https://github.com/jridgewell/sourcemaps/tree/main/packages/remapping",
  "repository": {
    "type": "git",
    "url": "git+https://github.com/jridgewell/sourcemaps.git",
    "directory": "packages/remapping"
  },
  "author": "Justin Ridgewell <justin@ridgewell.name>",
  "license": "MIT",
  "dependencies": {
    "@jridgewell/gen-mapping": "^0.3.5",
    "@jridgewell/trace-mapping": "^0.3.24"
  },
  "devDependencies": {
    "source-map": "0.6.1"
  }
}
```

----

# frontend/node_modules/@jridgewell/resolve-uri/package.json
```json
{
  "name": "@jridgewell/resolve-uri",
  "version": "3.1.2",
  "description": "Resolve a URI relative to an optional base URI",
  "keywords": [
    "resolve",
    "uri",
    "url",
    "path"
  ],
  "author": "Justin Ridgewell <justin@ridgewell.name>",
  "license": "MIT",
  "repository": "https://github.com/jridgewell/resolve-uri",
  "main": "dist/resolve-uri.umd.js",
  "module": "dist/resolve-uri.mjs",
  "types": "dist/types/resolve-uri.d.ts",
  "exports": {
    ".": [
      {
        "types": "./dist/types/resolve-uri.d.ts",
        "browser": "./dist/resolve-uri.umd.js",
        "require": "./dist/resolve-uri.umd.js",
        "import": "./dist/resolve-uri.mjs"
      },
      "./dist/resolve-uri.umd.js"
    ],
    "./package.json": "./package.json"
  },
  "files": [
    "dist"
  ],
  "engines": {
    "node": ">=6.0.0"
  },
  "scripts": {
    "prebuild": "rm -rf dist",
    "build": "run-s -n build:*",
    "build:rollup": "rollup -c rollup.config.js",
    "build:ts": "tsc --project tsconfig.build.json",
    "lint": "run-s -n lint:*",
    "lint:prettier": "npm run test:lint:prettier -- --write",
    "lint:ts": "npm run test:lint:ts -- --fix",
    "pretest": "run-s build:rollup",
    "test": "run-s -n test:lint test:only",
    "test:debug": "mocha --inspect-brk",
    "test:lint": "run-s -n test:lint:*",
    "test:lint:prettier": "prettier --check '{src,test}/**/*.ts'",
    "test:lint:ts": "eslint '{src,test}/**/*.ts'",
    "test:only": "mocha",
    "test:coverage": "c8 mocha",
    "test:watch": "mocha --watch",
    "prepublishOnly": "npm run preversion",
    "preversion": "run-s test build"
  },
  "devDependencies": {
    "@jridgewell/resolve-uri-latest": "npm:@jridgewell/resolve-uri@*",
    "@rollup/plugin-typescript": "8.3.0",
    "@typescript-eslint/eslint-plugin": "5.10.0",
    "@typescript-eslint/parser": "5.10.0",
    "c8": "7.11.0",
    "eslint": "8.7.0",
    "eslint-config-prettier": "8.3.0",
    "mocha": "9.2.0",
    "npm-run-all": "4.1.5",
    "prettier": "2.5.1",
    "rollup": "2.66.0",
    "typescript": "4.5.5"
  }
}
```

----

# frontend/node_modules/@jridgewell/sourcemap-codec/package.json
```json
{
  "name": "@jridgewell/sourcemap-codec",
  "version": "1.5.5",
  "description": "Encode/decode sourcemap mappings",
  "keywords": [
    "sourcemap",
    "vlq"
  ],
  "main": "dist/sourcemap-codec.umd.js",
  "module": "dist/sourcemap-codec.mjs",
  "types": "types/sourcemap-codec.d.cts",
  "files": [
    "dist",
    "src",
    "types"
  ],
  "exports": {
    ".": [
      {
        "import": {
          "types": "./types/sourcemap-codec.d.mts",
          "default": "./dist/sourcemap-codec.mjs"
        },
        "default": {
          "types": "./types/sourcemap-codec.d.cts",
          "default": "./dist/sourcemap-codec.umd.js"
        }
      },
      "./dist/sourcemap-codec.umd.js"
    ],
    "./package.json": "./package.json"
  },
  "scripts": {
    "benchmark": "run-s build:code benchmark:*",
    "benchmark:install": "cd benchmark && npm install",
    "benchmark:only": "node --expose-gc benchmark/index.js",
    "build": "run-s -n build:code build:types",
    "build:code": "node ../../esbuild.mjs sourcemap-codec.ts",
    "build:types": "run-s build:types:force build:types:emit build:types:mts",
    "build:types:force": "rimraf tsconfig.build.tsbuildinfo",
    "build:types:emit": "tsc --project tsconfig.build.json",
    "build:types:mts": "node ../../mts-types.mjs",
    "clean": "run-s -n clean:code clean:types",
    "clean:code": "tsc --build --clean tsconfig.build.json",
    "clean:types": "rimraf dist types",
    "test": "run-s -n test:types test:only test:format",
    "test:format": "prettier --check '{src,test}/**/*.ts'",
    "test:only": "mocha",
    "test:types": "eslint '{src,test}/**/*.ts'",
    "lint": "run-s -n lint:types lint:format",
    "lint:format": "npm run test:format -- --write",
    "lint:types": "npm run test:types -- --fix",
    "prepublishOnly": "npm run-s -n build test"
  },
  "homepage": "https://github.com/jridgewell/sourcemaps/tree/main/packages/sourcemap-codec",
  "repository": {
    "type": "git",
    "url": "git+https://github.com/jridgewell/sourcemaps.git",
    "directory": "packages/sourcemap-codec"
  },
  "author": "Justin Ridgewell <justin@ridgewell.name>",
  "license": "MIT"
}
```

----

# frontend/node_modules/@jridgewell/trace-mapping/package.json
```json
{
  "name": "@jridgewell/trace-mapping",
  "version": "0.3.31",
  "description": "Trace the original position through a source map",
  "keywords": [
    "source",
    "map"
  ],
  "main": "dist/trace-mapping.umd.js",
  "module": "dist/trace-mapping.mjs",
  "types": "types/trace-mapping.d.cts",
  "files": [
    "dist",
    "src",
    "types"
  ],
  "exports": {
    ".": [
      {
        "import": {
          "types": "./types/trace-mapping.d.mts",
          "default": "./dist/trace-mapping.mjs"
        },
        "default": {
          "types": "./types/trace-mapping.d.cts",
          "default": "./dist/trace-mapping.umd.js"
        }
      },
      "./dist/trace-mapping.umd.js"
    ],
    "./package.json": "./package.json"
  },
  "scripts": {
    "benchmark": "run-s build:code benchmark:*",
    "benchmark:install": "cd benchmark && npm install",
    "benchmark:only": "node --expose-gc benchmark/index.mjs",
    "build": "run-s -n build:code build:types",
    "build:code": "node ../../esbuild.mjs trace-mapping.ts",
    "build:types": "run-s build:types:force build:types:emit build:types:mts",
    "build:types:force": "rimraf tsconfig.build.tsbuildinfo",
    "build:types:emit": "tsc --project tsconfig.build.json",
    "build:types:mts": "node ../../mts-types.mjs",
    "clean": "run-s -n clean:code clean:types",
    "clean:code": "tsc --build --clean tsconfig.build.json",
    "clean:types": "rimraf dist types",
    "test": "run-s -n test:types test:only test:format",
    "test:format": "prettier --check '{src,test}/**/*.ts'",
    "test:only": "mocha",
    "test:types": "eslint '{src,test}/**/*.ts'",
    "lint": "run-s -n lint:types lint:format",
    "lint:format": "npm run test:format -- --write",
    "lint:types": "npm run test:types -- --fix",
    "prepublishOnly": "npm run-s -n build test"
  },
  "homepage": "https://github.com/jridgewell/sourcemaps/tree/main/packages/trace-mapping",
  "repository": {
    "type": "git",
    "url": "git+https://github.com/jridgewell/sourcemaps.git",
    "directory": "packages/trace-mapping"
  },
  "author": "Justin Ridgewell <justin@ridgewell.name>",
  "license": "MIT",
  "dependencies": {
    "@jridgewell/resolve-uri": "^3.1.0",
    "@jridgewell/sourcemap-codec": "^1.4.14"
  }
}
```

----

# frontend/node_modules/@rolldown/pluginutils/package.json
```json
{
  "name": "@rolldown/pluginutils",
  "version": "1.0.0-beta.27",
  "license": "MIT",
  "type": "module",
  "repository": {
    "type": "git",
    "url": "git+https://github.com/rolldown/rolldown.git",
    "directory": "packages/pluginutils"
  },
  "publishConfig": {
    "access": "public"
  },
  "main": "./dist/index.cjs",
  "module": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "import": "./dist/index.js",
      "require": "./dist/index.cjs"
    }
  },
  "files": [
    "dist"
  ],
  "devDependencies": {
    "@types/picomatch": "^4.0.0",
    "picomatch": "^4.0.2",
    "tsdown": "0.12.9",
    "vitest": "^3.0.1"
  },
  "scripts": {
    "build": "tsdown",
    "test": "vitest --typecheck"
  }
}```

----

# frontend/node_modules/@rollup/rollup-win32-x64-gnu/package.json
```json
{
  "name": "@rollup/rollup-win32-x64-gnu",
  "version": "4.59.0",
  "os": [
    "win32"
  ],
  "cpu": [
    "x64"
  ],
  "files": [
    "rollup.win32-x64-gnu.node"
  ],
  "description": "Native bindings for Rollup",
  "author": "Lukas Taegert-Atkinson",
  "homepage": "https://rollupjs.org/",
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "git+https://github.com/rollup/rollup.git"
  },
  "main": "./rollup.win32-x64-gnu.node"
}```

----

# frontend/node_modules/@rollup/rollup-win32-x64-msvc/package.json
```json
{
  "name": "@rollup/rollup-win32-x64-msvc",
  "version": "4.59.0",
  "os": [
    "win32"
  ],
  "cpu": [
    "x64"
  ],
  "files": [
    "rollup.win32-x64-msvc.node"
  ],
  "description": "Native bindings for Rollup",
  "author": "Lukas Taegert-Atkinson",
  "homepage": "https://rollupjs.org/",
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "git+https://github.com/rollup/rollup.git"
  },
  "main": "./rollup.win32-x64-msvc.node"
}```

----

# frontend/node_modules/@types/babel__core/package.json
```json
{
    "name": "@types/babel__core",
    "version": "7.20.5",
    "description": "TypeScript definitions for @babel/core",
    "homepage": "https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/babel__core",
    "license": "MIT",
    "contributors": [
        {
            "name": "Troy Gerwien",
            "githubUsername": "yortus",
            "url": "https://github.com/yortus"
        },
        {
            "name": "Marvin Hagemeister",
            "githubUsername": "marvinhagemeister",
            "url": "https://github.com/marvinhagemeister"
        },
        {
            "name": "Melvin Groenhoff",
            "githubUsername": "mgroenhoff",
            "url": "https://github.com/mgroenhoff"
        },
        {
            "name": "Jessica Franco",
            "githubUsername": "Jessidhia",
            "url": "https://github.com/Jessidhia"
        },
        {
            "name": "Ifiok Jr.",
            "githubUsername": "ifiokjr",
            "url": "https://github.com/ifiokjr"
        }
    ],
    "main": "",
    "types": "index.d.ts",
    "repository": {
        "type": "git",
        "url": "https://github.com/DefinitelyTyped/DefinitelyTyped.git",
        "directory": "types/babel__core"
    },
    "scripts": {},
    "dependencies": {
        "@babel/parser": "^7.20.7",
        "@babel/types": "^7.20.7",
        "@types/babel__generator": "*",
        "@types/babel__template": "*",
        "@types/babel__traverse": "*"
    },
    "typesPublisherContentHash": "3ece429b02ff9f70503a5644f2b303b04d10e6da7940c91a9eff5e52f2c76b91",
    "typeScriptVersion": "4.5"
}```

----

# frontend/node_modules/@types/babel__generator/package.json
```json
{
    "name": "@types/babel__generator",
    "version": "7.27.0",
    "description": "TypeScript definitions for @babel/generator",
    "homepage": "https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/babel__generator",
    "license": "MIT",
    "contributors": [
        {
            "name": "Troy Gerwien",
            "githubUsername": "yortus",
            "url": "https://github.com/yortus"
        },
        {
            "name": "Melvin Groenhoff",
            "githubUsername": "mgroenhoff",
            "url": "https://github.com/mgroenhoff"
        },
        {
            "name": "Cameron Yan",
            "githubUsername": "khell",
            "url": "https://github.com/khell"
        },
        {
            "name": "Lyanbin",
            "githubUsername": "Lyanbin",
            "url": "https://github.com/Lyanbin"
        }
    ],
    "main": "",
    "types": "index.d.ts",
    "repository": {
        "type": "git",
        "url": "https://github.com/DefinitelyTyped/DefinitelyTyped.git",
        "directory": "types/babel__generator"
    },
    "scripts": {},
    "dependencies": {
        "@babel/types": "^7.0.0"
    },
    "peerDependencies": {},
    "typesPublisherContentHash": "b5c7deac65dbd6ab9b313d1d71c86afe4383b881dcb4e3b3ac51dab07b8f95fb",
    "typeScriptVersion": "5.1"
}```

----

# frontend/node_modules/@types/babel__template/package.json
```json
{
    "name": "@types/babel__template",
    "version": "7.4.4",
    "description": "TypeScript definitions for @babel/template",
    "homepage": "https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/babel__template",
    "license": "MIT",
    "contributors": [
        {
            "name": "Troy Gerwien",
            "githubUsername": "yortus",
            "url": "https://github.com/yortus"
        },
        {
            "name": "Marvin Hagemeister",
            "githubUsername": "marvinhagemeister",
            "url": "https://github.com/marvinhagemeister"
        },
        {
            "name": "Melvin Groenhoff",
            "githubUsername": "mgroenhoff",
            "url": "https://github.com/mgroenhoff"
        },
        {
            "name": "ExE Boss",
            "githubUsername": "ExE-Boss",
            "url": "https://github.com/ExE-Boss"
        }
    ],
    "main": "",
    "types": "index.d.ts",
    "repository": {
        "type": "git",
        "url": "https://github.com/DefinitelyTyped/DefinitelyTyped.git",
        "directory": "types/babel__template"
    },
    "scripts": {},
    "dependencies": {
        "@babel/parser": "^7.1.0",
        "@babel/types": "^7.0.0"
    },
    "typesPublisherContentHash": "5730d754b4d1fcd41676b093f9e32b340c749c4d37b126dfa312e394467e86c6",
    "typeScriptVersion": "4.5"
}```

----

# frontend/node_modules/@types/babel__traverse/package.json
```json
{
    "name": "@types/babel__traverse",
    "version": "7.28.0",
    "description": "TypeScript definitions for @babel/traverse",
    "homepage": "https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/babel__traverse",
    "license": "MIT",
    "contributors": [
        {
            "name": "Troy Gerwien",
            "githubUsername": "yortus",
            "url": "https://github.com/yortus"
        },
        {
            "name": "Marvin Hagemeister",
            "githubUsername": "marvinhagemeister",
            "url": "https://github.com/marvinhagemeister"
        },
        {
            "name": "Ryan Petrich",
            "githubUsername": "rpetrich",
            "url": "https://github.com/rpetrich"
        },
        {
            "name": "Melvin Groenhoff",
            "githubUsername": "mgroenhoff",
            "url": "https://github.com/mgroenhoff"
        },
        {
            "name": "Dean L.",
            "githubUsername": "dlgrit",
            "url": "https://github.com/dlgrit"
        },
        {
            "name": "Ifiok Jr.",
            "githubUsername": "ifiokjr",
            "url": "https://github.com/ifiokjr"
        },
        {
            "name": "ExE Boss",
            "githubUsername": "ExE-Boss",
            "url": "https://github.com/ExE-Boss"
        },
        {
            "name": "Daniel Tschinder",
            "githubUsername": "danez",
            "url": "https://github.com/danez"
        }
    ],
    "main": "",
    "types": "index.d.ts",
    "repository": {
        "type": "git",
        "url": "https://github.com/DefinitelyTyped/DefinitelyTyped.git",
        "directory": "types/babel__traverse"
    },
    "scripts": {},
    "dependencies": {
        "@babel/types": "^7.28.2"
    },
    "peerDependencies": {},
    "typesPublisherContentHash": "f8bf439253873b2b30a22c425df086f130320cf70d832d84412e82a51e410680",
    "typeScriptVersion": "5.1"
}```

----

# frontend/node_modules/@types/estree/package.json
```json
{
    "name": "@types/estree",
    "version": "1.0.8",
    "description": "TypeScript definitions for estree",
    "homepage": "https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/estree",
    "license": "MIT",
    "contributors": [
        {
            "name": "RReverser",
            "githubUsername": "RReverser",
            "url": "https://github.com/RReverser"
        }
    ],
    "main": "",
    "types": "index.d.ts",
    "repository": {
        "type": "git",
        "url": "https://github.com/DefinitelyTyped/DefinitelyTyped.git",
        "directory": "types/estree"
    },
    "scripts": {},
    "dependencies": {},
    "peerDependencies": {},
    "typesPublisherContentHash": "7a167b6e4a4d9f6e9a2cb9fd3fc45c885f89cbdeb44b3e5961bb057a45c082fd",
    "typeScriptVersion": "5.1",
    "nonNpm": true
}```

----

# frontend/node_modules/@types/prop-types/package.json
```json
{
    "name": "@types/prop-types",
    "version": "15.7.15",
    "description": "TypeScript definitions for prop-types",
    "homepage": "https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/prop-types",
    "license": "MIT",
    "contributors": [
        {
            "name": "DovydasNavickas",
            "githubUsername": "DovydasNavickas",
            "url": "https://github.com/DovydasNavickas"
        },
        {
            "name": "Ferdy Budhidharma",
            "githubUsername": "ferdaber",
            "url": "https://github.com/ferdaber"
        },
        {
            "name": "Sebastian Silbermann",
            "githubUsername": "eps1lon",
            "url": "https://github.com/eps1lon"
        }
    ],
    "main": "",
    "types": "index.d.ts",
    "repository": {
        "type": "git",
        "url": "https://github.com/DefinitelyTyped/DefinitelyTyped.git",
        "directory": "types/prop-types"
    },
    "scripts": {},
    "dependencies": {},
    "peerDependencies": {},
    "typesPublisherContentHash": "92a20bc6f48f988ae6f314daa592e457e4b7ccb6ef115535bf69c7061375a248",
    "typeScriptVersion": "5.1"
}```

----

# frontend/node_modules/@types/react-dom/package.json
```json
{
    "name": "@types/react-dom",
    "version": "18.3.7",
    "description": "TypeScript definitions for react-dom",
    "homepage": "https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/react-dom",
    "license": "MIT",
    "contributors": [
        {
            "name": "Asana",
            "url": "https://asana.com"
        },
        {
            "name": "AssureSign",
            "url": "http://www.assuresign.com"
        },
        {
            "name": "Microsoft",
            "url": "https://microsoft.com"
        },
        {
            "name": "MartynasZilinskas",
            "githubUsername": "MartynasZilinskas",
            "url": "https://github.com/MartynasZilinskas"
        },
        {
            "name": "Josh Rutherford",
            "githubUsername": "theruther4d",
            "url": "https://github.com/theruther4d"
        },
        {
            "name": "Jessica Franco",
            "githubUsername": "Jessidhia",
            "url": "https://github.com/Jessidhia"
        },
        {
            "name": "Sebastian Silbermann",
            "githubUsername": "eps1lon",
            "url": "https://github.com/eps1lon"
        }
    ],
    "main": "",
    "types": "index.d.ts",
    "exports": {
        ".": {
            "types": {
                "default": "./index.d.ts"
            }
        },
        "./canary": {
            "types": {
                "default": "./canary.d.ts"
            }
        },
        "./client": {
            "types": {
                "default": "./client.d.ts"
            }
        },
        "./server": {
            "types": {
                "default": "./server.d.ts"
            }
        },
        "./experimental": {
            "types": {
                "default": "./experimental.d.ts"
            }
        },
        "./test-utils": {
            "types": {
                "default": "./test-utils/index.d.ts"
            }
        },
        "./package.json": "./package.json"
    },
    "repository": {
        "type": "git",
        "url": "https://github.com/DefinitelyTyped/DefinitelyTyped.git",
        "directory": "types/react-dom"
    },
    "scripts": {},
    "dependencies": {},
    "peerDependencies": {
        "@types/react": "^18.0.0"
    },
    "typesPublisherContentHash": "091d1528d83863778f5cb9fbf6c81d6e64ed2394f4c3c73a57ed81d9871b4465",
    "typeScriptVersion": "5.1"
}```

----

# frontend/node_modules/@types/react/package.json
```json
{
    "name": "@types/react",
    "version": "18.3.28",
    "description": "TypeScript definitions for react",
    "homepage": "https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/react",
    "license": "MIT",
    "contributors": [
        {
            "name": "Asana",
            "url": "https://asana.com"
        },
        {
            "name": "AssureSign",
            "url": "http://www.assuresign.com"
        },
        {
            "name": "Microsoft",
            "url": "https://microsoft.com"
        },
        {
            "name": "John Reilly",
            "githubUsername": "johnnyreilly",
            "url": "https://github.com/johnnyreilly"
        },
        {
            "name": "Benoit Benezech",
            "githubUsername": "bbenezech",
            "url": "https://github.com/bbenezech"
        },
        {
            "name": "Patricio Zavolinsky",
            "githubUsername": "pzavolinsky",
            "url": "https://github.com/pzavolinsky"
        },
        {
            "name": "Eric Anderson",
            "githubUsername": "ericanderson",
            "url": "https://github.com/ericanderson"
        },
        {
            "name": "Dovydas Navickas",
            "githubUsername": "DovydasNavickas",
            "url": "https://github.com/DovydasNavickas"
        },
        {
            "name": "Josh Rutherford",
            "githubUsername": "theruther4d",
            "url": "https://github.com/theruther4d"
        },
        {
            "name": "Guilherme Hübner",
            "githubUsername": "guilhermehubner",
            "url": "https://github.com/guilhermehubner"
        },
        {
            "name": "Ferdy Budhidharma",
            "githubUsername": "ferdaber",
            "url": "https://github.com/ferdaber"
        },
        {
            "name": "Johann Rakotoharisoa",
            "githubUsername": "jrakotoharisoa",
            "url": "https://github.com/jrakotoharisoa"
        },
        {
            "name": "Olivier Pascal",
            "githubUsername": "pascaloliv",
            "url": "https://github.com/pascaloliv"
        },
        {
            "name": "Martin Hochel",
            "githubUsername": "hotell",
            "url": "https://github.com/hotell"
        },
        {
            "name": "Frank Li",
            "githubUsername": "franklixuefei",
            "url": "https://github.com/franklixuefei"
        },
        {
            "name": "Jessica Franco",
            "githubUsername": "Jessidhia",
            "url": "https://github.com/Jessidhia"
        },
        {
            "name": "Saransh Kataria",
            "githubUsername": "saranshkataria",
            "url": "https://github.com/saranshkataria"
        },
        {
            "name": "Kanitkorn Sujautra",
            "githubUsername": "lukyth",
            "url": "https://github.com/lukyth"
        },
        {
            "name": "Sebastian Silbermann",
            "githubUsername": "eps1lon",
            "url": "https://github.com/eps1lon"
        },
        {
            "name": "Kyle Scully",
            "githubUsername": "zieka",
            "url": "https://github.com/zieka"
        },
        {
            "name": "Cong Zhang",
            "githubUsername": "dancerphil",
            "url": "https://github.com/dancerphil"
        },
        {
            "name": "Dimitri Mitropoulos",
            "githubUsername": "dimitropoulos",
            "url": "https://github.com/dimitropoulos"
        },
        {
            "name": "JongChan Choi",
            "githubUsername": "disjukr",
            "url": "https://github.com/disjukr"
        },
        {
            "name": "Victor Magalhães",
            "githubUsername": "vhfmag",
            "url": "https://github.com/vhfmag"
        },
        {
            "name": "Priyanshu Rav",
            "githubUsername": "priyanshurav",
            "url": "https://github.com/priyanshurav"
        },
        {
            "name": "Dmitry Semigradsky",
            "githubUsername": "Semigradsky",
            "url": "https://github.com/Semigradsky"
        },
        {
            "name": "Matt Pocock",
            "githubUsername": "mattpocock",
            "url": "https://github.com/mattpocock"
        }
    ],
    "main": "",
    "types": "index.d.ts",
    "typesVersions": {
        "<=5.0": {
            "*": [
                "ts5.0/*"
            ]
        }
    },
    "exports": {
        ".": {
            "types@<=5.0": {
                "default": "./ts5.0/index.d.ts"
            },
            "types": {
                "default": "./index.d.ts"
            }
        },
        "./canary": {
            "types@<=5.0": {
                "default": "./ts5.0/canary.d.ts"
            },
            "types": {
                "default": "./canary.d.ts"
            }
        },
        "./experimental": {
            "types@<=5.0": {
                "default": "./ts5.0/experimental.d.ts"
            },
            "types": {
                "default": "./experimental.d.ts"
            }
        },
        "./jsx-runtime": {
            "types@<=5.0": {
                "default": "./ts5.0/jsx-runtime.d.ts"
            },
            "types": {
                "default": "./jsx-runtime.d.ts"
            }
        },
        "./jsx-dev-runtime": {
            "types@<=5.0": {
                "default": "./ts5.0/jsx-dev-runtime.d.ts"
            },
            "types": {
                "default": "./jsx-dev-runtime.d.ts"
            }
        },
        "./package.json": "./package.json"
    },
    "repository": {
        "type": "git",
        "url": "https://github.com/DefinitelyTyped/DefinitelyTyped.git",
        "directory": "types/react"
    },
    "scripts": {},
    "dependencies": {
        "@types/prop-types": "*",
        "csstype": "^3.2.2"
    },
    "peerDependencies": {},
    "typesPublisherContentHash": "0ea06bef541d937c6628af8b44027771d39c4189db995868d91ac6157c442c8f",
    "typeScriptVersion": "5.2"
}```

----

# frontend/node_modules/@vitejs/plugin-react/package.json
```json
{
  "name": "@vitejs/plugin-react",
  "version": "4.7.0",
  "license": "MIT",
  "author": "Evan You",
  "description": "The default Vite plugin for React projects",
  "keywords": [
    "vite",
    "vite-plugin",
    "react",
    "babel",
    "react-refresh",
    "fast refresh"
  ],
  "contributors": [
    "Alec Larson",
    "Arnaud Barré"
  ],
  "files": [
    "dist"
  ],
  "type": "module",
  "main": "./dist/index.cjs",
  "module": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "import": "./dist/index.js",
      "require": "./dist/index.cjs"
    }
  },
  "scripts": {
    "dev": "tsdown --watch",
    "build": "tsdown",
    "prepublishOnly": "npm run build",
    "test-unit": "vitest run"
  },
  "engines": {
    "node": "^14.18.0 || >=16.0.0"
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/vitejs/vite-plugin-react.git",
    "directory": "packages/plugin-react"
  },
  "bugs": {
    "url": "https://github.com/vitejs/vite-plugin-react/issues"
  },
  "homepage": "https://github.com/vitejs/vite-plugin-react/tree/main/packages/plugin-react#readme",
  "dependencies": {
    "@babel/core": "^7.28.0",
    "@babel/plugin-transform-react-jsx-self": "^7.27.1",
    "@babel/plugin-transform-react-jsx-source": "^7.27.1",
    "@rolldown/pluginutils": "1.0.0-beta.27",
    "@types/babel__core": "^7.20.5",
    "react-refresh": "^0.17.0"
  },
  "peerDependencies": {
    "vite": "^4.2.0 || ^5.0.0 || ^6.0.0 || ^7.0.0"
  },
  "devDependencies": {
    "@vitejs/react-common": "workspace:*",
    "babel-plugin-react-compiler": "19.1.0-rc.2",
    "react": "^19.1.0",
    "react-dom": "^19.1.0",
    "rolldown": "1.0.0-beta.27",
    "tsdown": "^0.12.9",
    "vitest": "^3.2.4"
  }
}
```

----

# frontend/node_modules/baseline-browser-mapping/package.json
```json
{
  "name": "baseline-browser-mapping",
  "main": "./dist/index.cjs",
  "version": "2.10.8",
  "description": "A library for obtaining browser versions with their maximum supported Baseline feature set and Widely Available status.",
  "exports": {
    ".": {
      "require": "./dist/index.cjs",
      "types": "./dist/index.d.ts",
      "default": "./dist/index.js"
    },
    "./legacy": {
      "require": "./dist/index.cjs",
      "types": "./dist/index.d.ts"
    }
  },
  "jsdelivr": "./dist/index.js",
  "files": [
    "dist/*",
    "!dist/scripts/*",
    "LICENSE.txt",
    "README.md"
  ],
  "types": "./dist/index.d.ts",
  "type": "module",
  "bin": {
    "baseline-browser-mapping": "dist/cli.cjs"
  },
  "engines": {
    "node": ">=6.0.0"
  },
  "scripts": {
    "fix-cli-permissions": "output=$(npx baseline-browser-mapping 2>&1); path=$(printf '%s\n' \"$output\" | sed -n 's/^.*: \\(.*\\): Permission denied$/\\1/p; t; s/^\\(.*\\): Permission denied$/\\1/p'); if [ -n \"$path\" ]; then echo \"Permission denied for: $path\"; echo \"Removing $path ...\"; rm -rf \"$path\"; else echo \"$output\"; fi",
    "test:format": "npx prettier --check .",
    "test:lint": "npx eslint .",
    "test:legacy-test": "node spec/legacy-tests/legacy-test.cjs; node dist/cli.cjs",
    "test:jasmine": "npx jasmine",
    "test:jasmine-browser": "npx jasmine-browser-runner runSpecs --config ./spec/support/jasmine-browser.js",
    "test": "npm run build && npm run fix-cli-permissions && npm run test:format && npm run test:lint && npm run test:jasmine && npm run test:jasmine-browser",
    "build": "rm -rf dist; npx prettier . --write; rollup -c; rm -rf ./dist/scripts/expose-data.d.ts ./dist/cli.d.ts",
    "refresh-downstream": "npx tsx scripts/refresh-downstream.ts",
    "refresh-static": "npx tsx scripts/refresh-static.ts",
    "update-data-file": "npx tsx scripts/update-data-file.ts; npx prettier ./src/data/data.js --write",
    "update-data-dependencies": "npm i @mdn/browser-compat-data@latest web-features@latest -D",
    "check-data-changes": "git diff --name-only | grep -q '^src/data/data.js$' && echo 'changes-available=TRUE' || echo 'changes-available=FALSE'"
  },
  "license": "Apache-2.0",
  "devDependencies": {
    "@mdn/browser-compat-data": "^7.3.7",
    "@rollup/plugin-terser": "^1.0.0",
    "@rollup/plugin-typescript": "^12.1.3",
    "@types/node": "^22.15.17",
    "eslint-plugin-new-with-error": "^5.0.0",
    "jasmine": "^5.8.0",
    "jasmine-browser-runner": "^3.0.0",
    "jasmine-spec-reporter": "^7.0.0",
    "prettier": "^3.5.3",
    "rollup": "^4.44.0",
    "tslib": "^2.8.1",
    "typescript": "^5.7.2",
    "typescript-eslint": "^8.35.0",
    "web-features": "^3.20.0"
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/web-platform-dx/baseline-browser-mapping.git"
  }
}
```

----

# frontend/node_modules/browserslist/package.json
```json
{
  "name": "browserslist",
  "version": "4.28.1",
  "description": "Share target browsers between different front-end tools, like Autoprefixer, Stylelint and babel-env-preset",
  "keywords": [
    "caniuse",
    "browsers",
    "target"
  ],
  "funding": [
    {
      "type": "opencollective",
      "url": "https://opencollective.com/browserslist"
    },
    {
      "type": "tidelift",
      "url": "https://tidelift.com/funding/github/npm/browserslist"
    },
    {
      "type": "github",
      "url": "https://github.com/sponsors/ai"
    }
  ],
  "author": "Andrey Sitnik <andrey@sitnik.ru>",
  "license": "MIT",
  "repository": "browserslist/browserslist",
  "dependencies": {
    "baseline-browser-mapping": "^2.9.0",
    "caniuse-lite": "^1.0.30001759",
    "electron-to-chromium": "^1.5.263",
    "node-releases": "^2.0.27",
    "update-browserslist-db": "^1.2.0"
  },
  "engines": {
    "node": "^6 || ^7 || ^8 || ^9 || ^10 || ^11 || ^12 || >=13.7"
  },
  "bin": {
    "browserslist": "cli.js"
  },
  "types": "./index.d.ts",
  "browser": {
    "./node.js": "./browser.js",
    "path": false
  }
}
```

----

# frontend/node_modules/caniuse-lite/package.json
```json
{
  "name": "caniuse-lite",
  "version": "1.0.30001779",
  "description": "A smaller version of caniuse-db, with only the essentials!",
  "main": "dist/unpacker/index.js",
  "files": [
    "data",
    "dist"
  ],
  "keywords": [
    "support"
  ],
  "author": {
    "name": "Ben Briggs",
    "email": "beneb.info@gmail.com",
    "url": "http://beneb.info"
  },
  "repository": "browserslist/caniuse-lite",
  "funding": [
    {
      "type": "opencollective",
      "url": "https://opencollective.com/browserslist"
    },
    {
      "type": "tidelift",
      "url": "https://tidelift.com/funding/github/npm/caniuse-lite"
    },
    {
      "type": "github",
      "url": "https://github.com/sponsors/ai"
    }
  ],
  "license": "CC-BY-4.0"
}
```

----

# frontend/node_modules/convert-source-map/package.json
```json
{
  "name": "convert-source-map",
  "version": "2.0.0",
  "description": "Converts a source-map from/to  different formats and allows adding/changing properties.",
  "main": "index.js",
  "scripts": {
    "test": "tap test/*.js --color"
  },
  "repository": {
    "type": "git",
    "url": "git://github.com/thlorenz/convert-source-map.git"
  },
  "homepage": "https://github.com/thlorenz/convert-source-map",
  "devDependencies": {
    "inline-source-map": "~0.6.2",
    "tap": "~9.0.0"
  },
  "keywords": [
    "convert",
    "sourcemap",
    "source",
    "map",
    "browser",
    "debug"
  ],
  "author": {
    "name": "Thorsten Lorenz",
    "email": "thlorenz@gmx.de",
    "url": "http://thlorenz.com"
  },
  "license": "MIT",
  "engine": {
    "node": ">=4"
  },
  "files": [
    "index.js"
  ]
}
```

----

# frontend/node_modules/csstype/package.json
```json
{
  "name": "csstype",
  "version": "3.2.3",
  "main": "",
  "types": "index.d.ts",
  "description": "Strict TypeScript and Flow types for style based on MDN data",
  "repository": "https://github.com/frenic/csstype",
  "author": "Fredrik Nicol <fredrik.nicol@gmail.com>",
  "license": "MIT",
  "devDependencies": {
    "@babel/core": "^7.28.5",
    "@babel/preset-env": "^7.28.5",
    "@babel/preset-typescript": "^7.28.5",
    "@eslint/js": "^9.39.1",
    "@mdn/browser-compat-data": "7.1.21",
    "@tsconfig/node24": "^24.0.2",
    "@types/chokidar": "^2.1.7",
    "@types/css-tree": "^2.3.11",
    "@types/jest": "^30.0.0",
    "@types/jsdom": "^27.0.0",
    "@types/node": "^24.10.1",
    "@types/prettier": "^3.0.0",
    "@types/turndown": "^5.0.6",
    "babel-jest": "^30.2.0",
    "chalk": "^5.6.2",
    "chokidar": "^4.0.3",
    "css-tree": "^3.1.0",
    "eslint-config-prettier": "^10.1.8",
    "eslint-plugin-prettier": "^5.5.4",
    "flow-bin": "^0.291.0",
    "jest": "^30.2.0",
    "jsdom": "^27.2.0",
    "mdn-data": "2.25.0",
    "prettier": "^3.6.2",
    "release-it": "^19.0.6",
    "tsx": "^4.20.6",
    "turndown": "^7.2.2",
    "typescript": "~5.9.3",
    "typescript-eslint": "^8.46.4"
  },
  "overrides": {
    "js-yaml": ">=4.1.1"
  },
  "scripts": {
    "prepublish": "npm install --no-save --prefix __tests__ && npm install --no-save --prefix __tests__/__fixtures__",
    "release": "release-it",
    "update": "tsx update.ts",
    "build": "tsx --inspect build.ts --start",
    "watch": "tsx build.ts --watch",
    "lint": "eslint . --ext .js,.jsx,.ts,.tsx --fix",
    "pretty": "prettier --write build.ts **/*.{ts,js,json,md}",
    "lazy": "tsc && npm run lint",
    "test": "jest --runInBand",
    "test:src": "jest src.*.ts",
    "test:dist": "jest dist.*.ts --runInBand"
  },
  "files": [
    "index.d.ts",
    "index.js.flow"
  ],
  "keywords": [
    "css",
    "style",
    "typescript",
    "flow",
    "typings",
    "types",
    "definitions"
  ]
}
```

----

# frontend/node_modules/debug/package.json
```json
{
  "name": "debug",
  "version": "4.4.3",
  "repository": {
    "type": "git",
    "url": "git://github.com/debug-js/debug.git"
  },
  "description": "Lightweight debugging utility for Node.js and the browser",
  "keywords": [
    "debug",
    "log",
    "debugger"
  ],
  "files": [
    "src",
    "LICENSE",
    "README.md"
  ],
  "author": "Josh Junon (https://github.com/qix-)",
  "contributors": [
    "TJ Holowaychuk <tj@vision-media.ca>",
    "Nathan Rajlich <nathan@tootallnate.net> (http://n8.io)",
    "Andrew Rhyne <rhyneandrew@gmail.com>"
  ],
  "license": "MIT",
  "scripts": {
    "lint": "xo",
    "test": "npm run test:node && npm run test:browser && npm run lint",
    "test:node": "mocha test.js test.node.js",
    "test:browser": "karma start --single-run",
    "test:coverage": "cat ./coverage/lcov.info | coveralls"
  },
  "dependencies": {
    "ms": "^2.1.3"
  },
  "devDependencies": {
    "brfs": "^2.0.1",
    "browserify": "^16.2.3",
    "coveralls": "^3.0.2",
    "karma": "^3.1.4",
    "karma-browserify": "^6.0.0",
    "karma-chrome-launcher": "^2.2.0",
    "karma-mocha": "^1.3.0",
    "mocha": "^5.2.0",
    "mocha-lcov-reporter": "^1.2.0",
    "sinon": "^14.0.0",
    "xo": "^0.23.0"
  },
  "peerDependenciesMeta": {
    "supports-color": {
      "optional": true
    }
  },
  "main": "./src/index.js",
  "browser": "./src/browser.js",
  "engines": {
    "node": ">=6.0"
  },
  "xo": {
    "rules": {
      "import/extensions": "off"
    }
  }
}
```

----

# frontend/node_modules/electron-to-chromium/chromium-versions.json
```json
{"39":"0.20","40":"0.21","41":"0.21","42":"0.25","43":"0.27","44":"0.30","45":"0.31","47":"0.36","49":"0.37","50":"1.1","51":"1.2","52":"1.3","53":"1.4","54":"1.4","56":"1.6","58":"1.7","59":"1.8","61":"2.0","66":"3.0","69":"4.0","72":"5.0","73":"5.0","76":"6.0","78":"7.0","79":"8.0","80":"8.0","82":"9.0","83":"9.0","84":"10.0","85":"10.0","86":"11.0","87":"11.0","89":"12.0","90":"13.0","91":"13.0","92":"14.0","93":"14.0","94":"15.0","95":"16.0","96":"16.0","98":"17.0","99":"18.0","100":"18.0","102":"19.0","103":"20.0","104":"20.0","105":"21.0","106":"21.0","107":"22.0","108":"22.0","110":"23.0","111":"24.0","112":"24.0","114":"25.0","116":"26.0","118":"27.0","119":"28.0","120":"28.0","121":"29.0","122":"29.0","123":"30.0","124":"30.0","125":"31.0","126":"31.0","127":"32.0","128":"32.0","129":"33.0","130":"33.0","131":"34.0","132":"34.0","133":"35.0","134":"35.0","135":"36.0","136":"36.0","137":"37.0","138":"37.0","139":"38.0","140":"38.0","141":"39.0","142":"39.0","143":"40.0","144":"40.0","146":"41.0"}```

----

# frontend/node_modules/electron-to-chromium/full-chromium-versions.json
```json
{"39.0.2171.65":["0.20.0","0.20.1","0.20.2","0.20.3","0.20.4","0.20.5","0.20.6","0.20.7","0.20.8"],"40.0.2214.91":["0.21.0","0.21.1","0.21.2"],"41.0.2272.76":["0.21.3","0.22.1","0.22.2","0.22.3","0.23.0","0.24.0"],"42.0.2311.107":["0.25.0","0.25.1","0.25.2","0.25.3","0.26.0","0.26.1","0.27.0","0.27.1"],"43.0.2357.65":["0.27.2","0.27.3","0.28.0","0.28.1","0.28.2","0.28.3","0.29.1","0.29.2"],"44.0.2403.125":["0.30.4","0.31.0"],"45.0.2454.85":["0.31.2","0.32.2","0.32.3","0.33.0","0.33.1","0.33.2","0.33.3","0.33.4","0.33.6","0.33.7","0.33.8","0.33.9","0.34.0","0.34.1","0.34.2","0.34.3","0.34.4","0.35.1","0.35.2","0.35.3","0.35.4","0.35.5"],"47.0.2526.73":["0.36.0","0.36.2","0.36.3","0.36.4"],"47.0.2526.110":["0.36.5","0.36.6","0.36.7","0.36.8","0.36.9","0.36.10","0.36.11","0.36.12"],"49.0.2623.75":["0.37.0","0.37.1","0.37.3","0.37.4","0.37.5","0.37.6","0.37.7","0.37.8","1.0.0","1.0.1","1.0.2"],"50.0.2661.102":["1.1.0","1.1.1","1.1.2","1.1.3"],"51.0.2704.63":["1.2.0","1.2.1"],"51.0.2704.84":["1.2.2","1.2.3"],"51.0.2704.103":["1.2.4","1.2.5"],"51.0.2704.106":["1.2.6","1.2.7","1.2.8"],"52.0.2743.82":["1.3.0","1.3.1","1.3.2","1.3.3","1.3.4","1.3.5","1.3.6","1.3.7","1.3.9","1.3.10","1.3.13","1.3.14","1.3.15"],"53.0.2785.113":["1.4.0","1.4.1","1.4.2","1.4.3","1.4.4","1.4.5"],"53.0.2785.143":["1.4.6","1.4.7","1.4.8","1.4.10","1.4.11","1.4.13","1.4.14","1.4.15","1.4.16"],"54.0.2840.51":["1.4.12"],"54.0.2840.101":["1.5.0","1.5.1"],"56.0.2924.87":["1.6.0","1.6.1","1.6.2","1.6.3","1.6.4","1.6.5","1.6.6","1.6.7","1.6.8","1.6.9","1.6.10","1.6.11","1.6.12","1.6.13","1.6.14","1.6.15","1.6.16","1.6.17","1.6.18"],"58.0.3029.110":["1.7.0","1.7.1","1.7.2","1.7.3","1.7.4","1.7.5","1.7.6","1.7.7","1.7.8","1.7.9","1.7.10","1.7.11","1.7.12","1.7.13","1.7.14","1.7.15","1.7.16"],"59.0.3071.115":["1.8.0","1.8.1","1.8.2-beta.1","1.8.2-beta.2","1.8.2-beta.3","1.8.2-beta.4","1.8.2-beta.5","1.8.2","1.8.3","1.8.4","1.8.5","1.8.6","1.8.7","1.8.8"],"61.0.3163.100":["2.0.0-beta.1","2.0.0-beta.2","2.0.0-beta.3","2.0.0-beta.4","2.0.0-beta.5","2.0.0-beta.6","2.0.0-beta.7","2.0.0-beta.8","2.0.0","2.0.1","2.0.2","2.0.3","2.0.4","2.0.5","2.0.6","2.0.7","2.0.8","2.0.9","2.0.10","2.0.11","2.0.12","2.0.13","2.0.14","2.0.15","2.0.16","2.0.17","2.0.18","2.1.0-unsupported.20180809"],"66.0.3359.181":["3.0.0-beta.1","3.0.0-beta.2","3.0.0-beta.3","3.0.0-beta.4","3.0.0-beta.5","3.0.0-beta.6","3.0.0-beta.7","3.0.0-beta.8","3.0.0-beta.9","3.0.0-beta.10","3.0.0-beta.11","3.0.0-beta.12","3.0.0-beta.13","3.0.0","3.0.1","3.0.2","3.0.3","3.0.4","3.0.5","3.0.6","3.0.7","3.0.8","3.0.9","3.0.10","3.0.11","3.0.12","3.0.13","3.0.14","3.0.15","3.0.16","3.1.0-beta.1","3.1.0-beta.2","3.1.0-beta.3","3.1.0-beta.4","3.1.0-beta.5","3.1.0","3.1.1","3.1.2","3.1.3","3.1.4","3.1.5","3.1.6","3.1.7","3.1.8","3.1.9","3.1.10","3.1.11","3.1.12","3.1.13"],"69.0.3497.106":["4.0.0-beta.1","4.0.0-beta.2","4.0.0-beta.3","4.0.0-beta.4","4.0.0-beta.5","4.0.0-beta.6","4.0.0-beta.7","4.0.0-beta.8","4.0.0-beta.9","4.0.0-beta.10","4.0.0-beta.11","4.0.0","4.0.1","4.0.2","4.0.3","4.0.4","4.0.5","4.0.6"],"69.0.3497.128":["4.0.7","4.0.8","4.1.0","4.1.1","4.1.2","4.1.3","4.1.4","4.1.5","4.2.0","4.2.1","4.2.2","4.2.3","4.2.4","4.2.5","4.2.6","4.2.7","4.2.8","4.2.9","4.2.10","4.2.11","4.2.12"],"72.0.3626.52":["5.0.0-beta.1","5.0.0-beta.2"],"73.0.3683.27":["5.0.0-beta.3"],"73.0.3683.54":["5.0.0-beta.4"],"73.0.3683.61":["5.0.0-beta.5"],"73.0.3683.84":["5.0.0-beta.6"],"73.0.3683.94":["5.0.0-beta.7"],"73.0.3683.104":["5.0.0-beta.8"],"73.0.3683.117":["5.0.0-beta.9"],"73.0.3683.119":["5.0.0"],"73.0.3683.121":["5.0.1","5.0.2","5.0.3","5.0.4","5.0.5","5.0.6","5.0.7","5.0.8","5.0.9","5.0.10","5.0.11","5.0.12","5.0.13"],"76.0.3774.1":["6.0.0-beta.1"],"76.0.3783.1":["6.0.0-beta.2","6.0.0-beta.3","6.0.0-beta.4"],"76.0.3805.4":["6.0.0-beta.5"],"76.0.3809.3":["6.0.0-beta.6"],"76.0.3809.22":["6.0.0-beta.7"],"76.0.3809.26":["6.0.0-beta.8","6.0.0-beta.9"],"76.0.3809.37":["6.0.0-beta.10"],"76.0.3809.42":["6.0.0-beta.11"],"76.0.3809.54":["6.0.0-beta.12"],"76.0.3809.60":["6.0.0-beta.13"],"76.0.3809.68":["6.0.0-beta.14"],"76.0.3809.74":["6.0.0-beta.15"],"76.0.3809.88":["6.0.0"],"76.0.3809.102":["6.0.1"],"76.0.3809.110":["6.0.2"],"76.0.3809.126":["6.0.3"],"76.0.3809.131":["6.0.4"],"76.0.3809.136":["6.0.5"],"76.0.3809.138":["6.0.6"],"76.0.3809.139":["6.0.7"],"76.0.3809.146":["6.0.8","6.0.9","6.0.10","6.0.11","6.0.12","6.1.0","6.1.1","6.1.2","6.1.3","6.1.4","6.1.5","6.1.6","6.1.7","6.1.8","6.1.9","6.1.10","6.1.11","6.1.12"],"78.0.3866.0":["7.0.0-beta.1","7.0.0-beta.2","7.0.0-beta.3"],"78.0.3896.6":["7.0.0-beta.4"],"78.0.3905.1":["7.0.0-beta.5","7.0.0-beta.6","7.0.0-beta.7","7.0.0"],"78.0.3904.92":["7.0.1"],"78.0.3904.94":["7.1.0"],"78.0.3904.99":["7.1.1"],"78.0.3904.113":["7.1.2"],"78.0.3904.126":["7.1.3"],"78.0.3904.130":["7.1.4","7.1.5","7.1.6","7.1.7","7.1.8","7.1.9","7.1.10","7.1.11","7.1.12","7.1.13","7.1.14","7.2.0","7.2.1","7.2.2","7.2.3","7.2.4","7.3.0","7.3.1","7.3.2","7.3.3"],"79.0.3931.0":["8.0.0-beta.1","8.0.0-beta.2"],"80.0.3955.0":["8.0.0-beta.3","8.0.0-beta.4"],"80.0.3987.14":["8.0.0-beta.5"],"80.0.3987.51":["8.0.0-beta.6"],"80.0.3987.59":["8.0.0-beta.7"],"80.0.3987.75":["8.0.0-beta.8","8.0.0-beta.9"],"80.0.3987.86":["8.0.0","8.0.1","8.0.2"],"80.0.3987.134":["8.0.3"],"80.0.3987.137":["8.1.0"],"80.0.3987.141":["8.1.1"],"80.0.3987.158":["8.2.0"],"80.0.3987.163":["8.2.1","8.2.2","8.2.3","8.5.3","8.5.4","8.5.5"],"80.0.3987.165":["8.2.4","8.2.5","8.3.0","8.3.1","8.3.2","8.3.3","8.3.4","8.4.0","8.4.1","8.5.0","8.5.1","8.5.2"],"82.0.4048.0":["9.0.0-beta.1","9.0.0-beta.2","9.0.0-beta.3","9.0.0-beta.4","9.0.0-beta.5"],"82.0.4058.2":["9.0.0-beta.6","9.0.0-beta.7","9.0.0-beta.9"],"82.0.4085.10":["9.0.0-beta.10"],"82.0.4085.14":["9.0.0-beta.11","9.0.0-beta.12","9.0.0-beta.13"],"82.0.4085.27":["9.0.0-beta.14"],"83.0.4102.3":["9.0.0-beta.15","9.0.0-beta.16"],"83.0.4103.14":["9.0.0-beta.17"],"83.0.4103.16":["9.0.0-beta.18"],"83.0.4103.24":["9.0.0-beta.19"],"83.0.4103.26":["9.0.0-beta.20","9.0.0-beta.21"],"83.0.4103.34":["9.0.0-beta.22"],"83.0.4103.44":["9.0.0-beta.23"],"83.0.4103.45":["9.0.0-beta.24"],"83.0.4103.64":["9.0.0"],"83.0.4103.94":["9.0.1","9.0.2"],"83.0.4103.100":["9.0.3"],"83.0.4103.104":["9.0.4"],"83.0.4103.119":["9.0.5"],"83.0.4103.122":["9.1.0","9.1.1","9.1.2","9.2.0","9.2.1","9.3.0","9.3.1","9.3.2","9.3.3","9.3.4","9.3.5","9.4.0","9.4.1","9.4.2","9.4.3","9.4.4"],"84.0.4129.0":["10.0.0-beta.1","10.0.0-beta.2"],"85.0.4161.2":["10.0.0-beta.3","10.0.0-beta.4"],"85.0.4181.1":["10.0.0-beta.8","10.0.0-beta.9"],"85.0.4183.19":["10.0.0-beta.10"],"85.0.4183.20":["10.0.0-beta.11"],"85.0.4183.26":["10.0.0-beta.12"],"85.0.4183.39":["10.0.0-beta.13","10.0.0-beta.14","10.0.0-beta.15","10.0.0-beta.17","10.0.0-beta.19","10.0.0-beta.20","10.0.0-beta.21"],"85.0.4183.70":["10.0.0-beta.23"],"85.0.4183.78":["10.0.0-beta.24"],"85.0.4183.80":["10.0.0-beta.25"],"85.0.4183.84":["10.0.0"],"85.0.4183.86":["10.0.1"],"85.0.4183.87":["10.1.0"],"85.0.4183.93":["10.1.1"],"85.0.4183.98":["10.1.2"],"85.0.4183.121":["10.1.3","10.1.4","10.1.5","10.1.6","10.1.7","10.2.0","10.3.0","10.3.1","10.3.2","10.4.0","10.4.1","10.4.2","10.4.3","10.4.4","10.4.5","10.4.6","10.4.7"],"86.0.4234.0":["11.0.0-beta.1","11.0.0-beta.3","11.0.0-beta.4","11.0.0-beta.5","11.0.0-beta.6","11.0.0-beta.7"],"87.0.4251.1":["11.0.0-beta.8","11.0.0-beta.9","11.0.0-beta.11"],"87.0.4280.11":["11.0.0-beta.12","11.0.0-beta.13"],"87.0.4280.27":["11.0.0-beta.16","11.0.0-beta.17","11.0.0-beta.18","11.0.0-beta.19"],"87.0.4280.40":["11.0.0-beta.20"],"87.0.4280.47":["11.0.0-beta.22","11.0.0-beta.23"],"87.0.4280.60":["11.0.0","11.0.1"],"87.0.4280.67":["11.0.2","11.0.3","11.0.4"],"87.0.4280.88":["11.0.5","11.1.0","11.1.1"],"87.0.4280.141":["11.2.0","11.2.1","11.2.2","11.2.3","11.3.0","11.4.0","11.4.1","11.4.2","11.4.3","11.4.4","11.4.5","11.4.6","11.4.7","11.4.8","11.4.9","11.4.10","11.4.11","11.4.12","11.5.0"],"89.0.4328.0":["12.0.0-beta.1","12.0.0-beta.3","12.0.0-beta.4","12.0.0-beta.5","12.0.0-beta.6","12.0.0-beta.7","12.0.0-beta.8","12.0.0-beta.9","12.0.0-beta.10","12.0.0-beta.11","12.0.0-beta.12","12.0.0-beta.14"],"89.0.4348.1":["12.0.0-beta.16","12.0.0-beta.18","12.0.0-beta.19","12.0.0-beta.20"],"89.0.4388.2":["12.0.0-beta.21","12.0.0-beta.22","12.0.0-beta.23","12.0.0-beta.24","12.0.0-beta.25","12.0.0-beta.26"],"89.0.4389.23":["12.0.0-beta.27","12.0.0-beta.28","12.0.0-beta.29"],"89.0.4389.58":["12.0.0-beta.30","12.0.0-beta.31"],"89.0.4389.69":["12.0.0"],"89.0.4389.82":["12.0.1"],"89.0.4389.90":["12.0.2"],"89.0.4389.114":["12.0.3","12.0.4"],"89.0.4389.128":["12.0.5","12.0.6","12.0.7","12.0.8","12.0.9","12.0.10","12.0.11","12.0.12","12.0.13","12.0.14","12.0.15","12.0.16","12.0.17","12.0.18","12.1.0","12.1.1","12.1.2","12.2.0","12.2.1","12.2.2","12.2.3"],"90.0.4402.0":["13.0.0-beta.2","13.0.0-beta.3"],"90.0.4415.0":["13.0.0-beta.4","13.0.0-beta.5","13.0.0-beta.6","13.0.0-beta.7","13.0.0-beta.8","13.0.0-beta.9","13.0.0-beta.10","13.0.0-beta.11","13.0.0-beta.12","13.0.0-beta.13"],"91.0.4448.0":["13.0.0-beta.14","13.0.0-beta.16","13.0.0-beta.17","13.0.0-beta.18","13.0.0-beta.20"],"91.0.4472.33":["13.0.0-beta.21","13.0.0-beta.22","13.0.0-beta.23"],"91.0.4472.38":["13.0.0-beta.24","13.0.0-beta.25","13.0.0-beta.26","13.0.0-beta.27","13.0.0-beta.28"],"91.0.4472.69":["13.0.0","13.0.1"],"91.0.4472.77":["13.1.0","13.1.1","13.1.2"],"91.0.4472.106":["13.1.3","13.1.4"],"91.0.4472.124":["13.1.5","13.1.6","13.1.7"],"91.0.4472.164":["13.1.8","13.1.9","13.2.0","13.2.1","13.2.2","13.2.3","13.3.0","13.4.0","13.5.0","13.5.1","13.5.2","13.6.0","13.6.1","13.6.2","13.6.3","13.6.6","13.6.7","13.6.8","13.6.9"],"92.0.4511.0":["14.0.0-beta.1","14.0.0-beta.2","14.0.0-beta.3"],"93.0.4536.0":["14.0.0-beta.5","14.0.0-beta.6","14.0.0-beta.7","14.0.0-beta.8"],"93.0.4539.0":["14.0.0-beta.9","14.0.0-beta.10"],"93.0.4557.4":["14.0.0-beta.11","14.0.0-beta.12"],"93.0.4566.0":["14.0.0-beta.13","14.0.0-beta.14","14.0.0-beta.15","14.0.0-beta.16","14.0.0-beta.17","15.0.0-alpha.1","15.0.0-alpha.2"],"93.0.4577.15":["14.0.0-beta.18","14.0.0-beta.19","14.0.0-beta.20","14.0.0-beta.21"],"93.0.4577.25":["14.0.0-beta.22","14.0.0-beta.23"],"93.0.4577.51":["14.0.0-beta.24","14.0.0-beta.25"],"93.0.4577.58":["14.0.0"],"93.0.4577.63":["14.0.1"],"93.0.4577.82":["14.0.2","14.1.0","14.1.1","14.2.0","14.2.1","14.2.2","14.2.3","14.2.4","14.2.5","14.2.6","14.2.7","14.2.8","14.2.9"],"94.0.4584.0":["15.0.0-alpha.3","15.0.0-alpha.4","15.0.0-alpha.5","15.0.0-alpha.6"],"94.0.4590.2":["15.0.0-alpha.7","15.0.0-alpha.8","15.0.0-alpha.9"],"94.0.4606.12":["15.0.0-alpha.10"],"94.0.4606.20":["15.0.0-beta.1","15.0.0-beta.2"],"94.0.4606.31":["15.0.0-beta.3","15.0.0-beta.4","15.0.0-beta.5","15.0.0-beta.6","15.0.0-beta.7"],"94.0.4606.51":["15.0.0"],"94.0.4606.61":["15.1.0","15.1.1"],"94.0.4606.71":["15.1.2"],"94.0.4606.81":["15.2.0","15.3.0","15.3.1","15.3.2","15.3.3","15.3.4","15.3.5","15.3.6","15.3.7","15.4.0","15.4.1","15.4.2","15.5.0","15.5.1","15.5.2","15.5.3","15.5.4","15.5.5","15.5.6","15.5.7"],"95.0.4629.0":["16.0.0-alpha.1","16.0.0-alpha.2","16.0.0-alpha.3","16.0.0-alpha.4","16.0.0-alpha.5","16.0.0-alpha.6","16.0.0-alpha.7"],"96.0.4647.0":["16.0.0-alpha.8","16.0.0-alpha.9","16.0.0-beta.1","16.0.0-beta.2","16.0.0-beta.3"],"96.0.4664.18":["16.0.0-beta.4","16.0.0-beta.5"],"96.0.4664.27":["16.0.0-beta.6","16.0.0-beta.7"],"96.0.4664.35":["16.0.0-beta.8","16.0.0-beta.9"],"96.0.4664.45":["16.0.0","16.0.1"],"96.0.4664.55":["16.0.2","16.0.3","16.0.4","16.0.5"],"96.0.4664.110":["16.0.6","16.0.7","16.0.8"],"96.0.4664.174":["16.0.9","16.0.10","16.1.0","16.1.1","16.2.0","16.2.1","16.2.2","16.2.3","16.2.4","16.2.5","16.2.6","16.2.7","16.2.8"],"96.0.4664.4":["17.0.0-alpha.1","17.0.0-alpha.2","17.0.0-alpha.3"],"98.0.4706.0":["17.0.0-alpha.4","17.0.0-alpha.5","17.0.0-alpha.6","17.0.0-beta.1","17.0.0-beta.2"],"98.0.4758.9":["17.0.0-beta.3"],"98.0.4758.11":["17.0.0-beta.4","17.0.0-beta.5","17.0.0-beta.6","17.0.0-beta.7","17.0.0-beta.8","17.0.0-beta.9"],"98.0.4758.74":["17.0.0"],"98.0.4758.82":["17.0.1"],"98.0.4758.102":["17.1.0"],"98.0.4758.109":["17.1.1","17.1.2","17.2.0"],"98.0.4758.141":["17.3.0","17.3.1","17.4.0","17.4.1","17.4.2","17.4.3","17.4.4","17.4.5","17.4.6","17.4.7","17.4.8","17.4.9","17.4.10","17.4.11"],"99.0.4767.0":["18.0.0-alpha.1","18.0.0-alpha.2","18.0.0-alpha.3","18.0.0-alpha.4","18.0.0-alpha.5"],"100.0.4894.0":["18.0.0-beta.1","18.0.0-beta.2","18.0.0-beta.3","18.0.0-beta.4","18.0.0-beta.5","18.0.0-beta.6"],"100.0.4896.56":["18.0.0"],"100.0.4896.60":["18.0.1","18.0.2"],"100.0.4896.75":["18.0.3","18.0.4"],"100.0.4896.127":["18.1.0"],"100.0.4896.143":["18.2.0","18.2.1","18.2.2","18.2.3"],"100.0.4896.160":["18.2.4","18.3.0","18.3.1","18.3.2","18.3.3","18.3.4","18.3.5","18.3.6","18.3.7","18.3.8","18.3.9","18.3.11","18.3.12","18.3.13","18.3.14","18.3.15"],"102.0.4962.3":["19.0.0-alpha.1"],"102.0.4971.0":["19.0.0-alpha.2","19.0.0-alpha.3"],"102.0.4989.0":["19.0.0-alpha.4","19.0.0-alpha.5"],"102.0.4999.0":["19.0.0-beta.1","19.0.0-beta.2","19.0.0-beta.3"],"102.0.5005.27":["19.0.0-beta.4"],"102.0.5005.40":["19.0.0-beta.5","19.0.0-beta.6","19.0.0-beta.7"],"102.0.5005.49":["19.0.0-beta.8"],"102.0.5005.61":["19.0.0","19.0.1"],"102.0.5005.63":["19.0.2","19.0.3","19.0.4"],"102.0.5005.115":["19.0.5","19.0.6"],"102.0.5005.134":["19.0.7"],"102.0.5005.148":["19.0.8"],"102.0.5005.167":["19.0.9","19.0.10","19.0.11","19.0.12","19.0.13","19.0.14","19.0.15","19.0.16","19.0.17","19.1.0","19.1.1","19.1.2","19.1.3","19.1.4","19.1.5","19.1.6","19.1.7","19.1.8","19.1.9"],"103.0.5044.0":["20.0.0-alpha.1"],"104.0.5073.0":["20.0.0-alpha.2","20.0.0-alpha.3","20.0.0-alpha.4","20.0.0-alpha.5","20.0.0-alpha.6","20.0.0-alpha.7","20.0.0-beta.1","20.0.0-beta.2","20.0.0-beta.3","20.0.0-beta.4","20.0.0-beta.5","20.0.0-beta.6","20.0.0-beta.7","20.0.0-beta.8"],"104.0.5112.39":["20.0.0-beta.9"],"104.0.5112.48":["20.0.0-beta.10","20.0.0-beta.11","20.0.0-beta.12"],"104.0.5112.57":["20.0.0-beta.13"],"104.0.5112.65":["20.0.0"],"104.0.5112.81":["20.0.1","20.0.2","20.0.3"],"104.0.5112.102":["20.1.0","20.1.1"],"104.0.5112.114":["20.1.2","20.1.3","20.1.4"],"104.0.5112.124":["20.2.0","20.3.0","20.3.1","20.3.2","20.3.3","20.3.4","20.3.5","20.3.6","20.3.7","20.3.8","20.3.9","20.3.10","20.3.11","20.3.12"],"105.0.5187.0":["21.0.0-alpha.1","21.0.0-alpha.2","21.0.0-alpha.3","21.0.0-alpha.4","21.0.0-alpha.5"],"106.0.5216.0":["21.0.0-alpha.6","21.0.0-beta.1","21.0.0-beta.2","21.0.0-beta.3","21.0.0-beta.4","21.0.0-beta.5"],"106.0.5249.40":["21.0.0-beta.6","21.0.0-beta.7","21.0.0-beta.8"],"106.0.5249.51":["21.0.0"],"106.0.5249.61":["21.0.1"],"106.0.5249.91":["21.1.0"],"106.0.5249.103":["21.1.1"],"106.0.5249.119":["21.2.0"],"106.0.5249.165":["21.2.1"],"106.0.5249.168":["21.2.2","21.2.3"],"106.0.5249.181":["21.3.0","21.3.1"],"106.0.5249.199":["21.3.3","21.3.4","21.3.5","21.4.0","21.4.1","21.4.2","21.4.3","21.4.4"],"107.0.5286.0":["22.0.0-alpha.1"],"108.0.5329.0":["22.0.0-alpha.3","22.0.0-alpha.4","22.0.0-alpha.5","22.0.0-alpha.6"],"108.0.5355.0":["22.0.0-alpha.7"],"108.0.5359.10":["22.0.0-alpha.8","22.0.0-beta.1","22.0.0-beta.2","22.0.0-beta.3"],"108.0.5359.29":["22.0.0-beta.4"],"108.0.5359.40":["22.0.0-beta.5","22.0.0-beta.6"],"108.0.5359.48":["22.0.0-beta.7","22.0.0-beta.8"],"108.0.5359.62":["22.0.0"],"108.0.5359.125":["22.0.1"],"108.0.5359.179":["22.0.2","22.0.3","22.1.0"],"108.0.5359.215":["22.2.0","22.2.1","22.3.0","22.3.1","22.3.2","22.3.3","22.3.4","22.3.5","22.3.6","22.3.7","22.3.8","22.3.9","22.3.10","22.3.11","22.3.12","22.3.13","22.3.14","22.3.15","22.3.16","22.3.17","22.3.18","22.3.20","22.3.21","22.3.22","22.3.23","22.3.24","22.3.25","22.3.26","22.3.27"],"110.0.5415.0":["23.0.0-alpha.1"],"110.0.5451.0":["23.0.0-alpha.2","23.0.0-alpha.3"],"110.0.5478.5":["23.0.0-beta.1","23.0.0-beta.2","23.0.0-beta.3"],"110.0.5481.30":["23.0.0-beta.4"],"110.0.5481.38":["23.0.0-beta.5"],"110.0.5481.52":["23.0.0-beta.6","23.0.0-beta.8"],"110.0.5481.77":["23.0.0"],"110.0.5481.100":["23.1.0"],"110.0.5481.104":["23.1.1"],"110.0.5481.177":["23.1.2"],"110.0.5481.179":["23.1.3"],"110.0.5481.192":["23.1.4","23.2.0"],"110.0.5481.208":["23.2.1","23.2.2","23.2.3","23.2.4","23.3.0","23.3.1","23.3.2","23.3.3","23.3.4","23.3.5","23.3.6","23.3.7","23.3.8","23.3.9","23.3.10","23.3.11","23.3.12","23.3.13"],"111.0.5560.0":["24.0.0-alpha.1","24.0.0-alpha.2","24.0.0-alpha.3","24.0.0-alpha.4","24.0.0-alpha.5","24.0.0-alpha.6","24.0.0-alpha.7"],"111.0.5563.50":["24.0.0-beta.1","24.0.0-beta.2"],"112.0.5615.20":["24.0.0-beta.3","24.0.0-beta.4"],"112.0.5615.29":["24.0.0-beta.5"],"112.0.5615.39":["24.0.0-beta.6","24.0.0-beta.7"],"112.0.5615.49":["24.0.0"],"112.0.5615.50":["24.1.0","24.1.1"],"112.0.5615.87":["24.1.2"],"112.0.5615.165":["24.1.3","24.2.0","24.3.0"],"112.0.5615.183":["24.3.1"],"112.0.5615.204":["24.4.0","24.4.1","24.5.0","24.5.1","24.6.0","24.6.1","24.6.2","24.6.3","24.6.4","24.6.5","24.7.0","24.7.1","24.8.0","24.8.1","24.8.2","24.8.3","24.8.4","24.8.5","24.8.6","24.8.7","24.8.8"],"114.0.5694.0":["25.0.0-alpha.1","25.0.0-alpha.2"],"114.0.5710.0":["25.0.0-alpha.3","25.0.0-alpha.4"],"114.0.5719.0":["25.0.0-alpha.5","25.0.0-alpha.6","25.0.0-beta.1","25.0.0-beta.2","25.0.0-beta.3"],"114.0.5735.16":["25.0.0-beta.4","25.0.0-beta.5","25.0.0-beta.6","25.0.0-beta.7"],"114.0.5735.35":["25.0.0-beta.8"],"114.0.5735.45":["25.0.0-beta.9","25.0.0","25.0.1"],"114.0.5735.106":["25.1.0","25.1.1"],"114.0.5735.134":["25.2.0"],"114.0.5735.199":["25.3.0"],"114.0.5735.243":["25.3.1"],"114.0.5735.248":["25.3.2","25.4.0"],"114.0.5735.289":["25.5.0","25.6.0","25.7.0","25.8.0","25.8.1","25.8.2","25.8.3","25.8.4","25.9.0","25.9.1","25.9.2","25.9.3","25.9.4","25.9.5","25.9.6","25.9.7","25.9.8"],"116.0.5791.0":["26.0.0-alpha.1","26.0.0-alpha.2","26.0.0-alpha.3","26.0.0-alpha.4","26.0.0-alpha.5"],"116.0.5815.0":["26.0.0-alpha.6"],"116.0.5831.0":["26.0.0-alpha.7"],"116.0.5845.0":["26.0.0-alpha.8","26.0.0-beta.1"],"116.0.5845.14":["26.0.0-beta.2","26.0.0-beta.3","26.0.0-beta.4","26.0.0-beta.5","26.0.0-beta.6","26.0.0-beta.7"],"116.0.5845.42":["26.0.0-beta.8","26.0.0-beta.9"],"116.0.5845.49":["26.0.0-beta.10","26.0.0-beta.11"],"116.0.5845.62":["26.0.0-beta.12"],"116.0.5845.82":["26.0.0"],"116.0.5845.97":["26.1.0"],"116.0.5845.179":["26.2.0"],"116.0.5845.188":["26.2.1"],"116.0.5845.190":["26.2.2","26.2.3","26.2.4"],"116.0.5845.228":["26.3.0","26.4.0","26.4.1","26.4.2","26.4.3","26.5.0","26.6.0","26.6.1","26.6.2","26.6.3","26.6.4","26.6.5","26.6.6","26.6.7","26.6.8","26.6.9","26.6.10"],"118.0.5949.0":["27.0.0-alpha.1","27.0.0-alpha.2","27.0.0-alpha.3","27.0.0-alpha.4","27.0.0-alpha.5","27.0.0-alpha.6"],"118.0.5993.5":["27.0.0-beta.1","27.0.0-beta.2","27.0.0-beta.3"],"118.0.5993.11":["27.0.0-beta.4"],"118.0.5993.18":["27.0.0-beta.5","27.0.0-beta.6","27.0.0-beta.7","27.0.0-beta.8","27.0.0-beta.9"],"118.0.5993.54":["27.0.0"],"118.0.5993.89":["27.0.1","27.0.2"],"118.0.5993.120":["27.0.3"],"118.0.5993.129":["27.0.4"],"118.0.5993.144":["27.1.0","27.1.2"],"118.0.5993.159":["27.1.3","27.2.0","27.2.1","27.2.2","27.2.3","27.2.4","27.3.0","27.3.1","27.3.2","27.3.3","27.3.4","27.3.5","27.3.6","27.3.7","27.3.8","27.3.9","27.3.10","27.3.11"],"119.0.6045.0":["28.0.0-alpha.1","28.0.0-alpha.2"],"119.0.6045.21":["28.0.0-alpha.3","28.0.0-alpha.4"],"119.0.6045.33":["28.0.0-alpha.5","28.0.0-alpha.6","28.0.0-alpha.7","28.0.0-beta.1"],"120.0.6099.0":["28.0.0-beta.2"],"120.0.6099.5":["28.0.0-beta.3","28.0.0-beta.4"],"120.0.6099.18":["28.0.0-beta.5","28.0.0-beta.6","28.0.0-beta.7","28.0.0-beta.8","28.0.0-beta.9","28.0.0-beta.10"],"120.0.6099.35":["28.0.0-beta.11"],"120.0.6099.56":["28.0.0"],"120.0.6099.109":["28.1.0","28.1.1"],"120.0.6099.199":["28.1.2","28.1.3"],"120.0.6099.216":["28.1.4"],"120.0.6099.227":["28.2.0"],"120.0.6099.268":["28.2.1"],"120.0.6099.276":["28.2.2"],"120.0.6099.283":["28.2.3"],"120.0.6099.291":["28.2.4","28.2.5","28.2.6","28.2.7","28.2.8","28.2.9","28.2.10","28.3.0","28.3.1","28.3.2","28.3.3"],"121.0.6147.0":["29.0.0-alpha.1","29.0.0-alpha.2","29.0.0-alpha.3"],"121.0.6159.0":["29.0.0-alpha.4","29.0.0-alpha.5","29.0.0-alpha.6","29.0.0-alpha.7"],"122.0.6194.0":["29.0.0-alpha.8"],"122.0.6236.2":["29.0.0-alpha.9","29.0.0-alpha.10","29.0.0-alpha.11","29.0.0-beta.1","29.0.0-beta.2"],"122.0.6261.6":["29.0.0-beta.3","29.0.0-beta.4"],"122.0.6261.18":["29.0.0-beta.5","29.0.0-beta.6","29.0.0-beta.7","29.0.0-beta.8","29.0.0-beta.9","29.0.0-beta.10","29.0.0-beta.11"],"122.0.6261.29":["29.0.0-beta.12"],"122.0.6261.39":["29.0.0"],"122.0.6261.57":["29.0.1"],"122.0.6261.70":["29.1.0"],"122.0.6261.111":["29.1.1"],"122.0.6261.112":["29.1.2","29.1.3"],"122.0.6261.129":["29.1.4"],"122.0.6261.130":["29.1.5"],"122.0.6261.139":["29.1.6"],"122.0.6261.156":["29.2.0","29.3.0","29.3.1","29.3.2","29.3.3","29.4.0","29.4.1","29.4.2","29.4.3","29.4.4","29.4.5","29.4.6"],"123.0.6296.0":["30.0.0-alpha.1"],"123.0.6312.5":["30.0.0-alpha.2"],"124.0.6323.0":["30.0.0-alpha.3","30.0.0-alpha.4"],"124.0.6331.0":["30.0.0-alpha.5","30.0.0-alpha.6"],"124.0.6353.0":["30.0.0-alpha.7"],"124.0.6359.0":["30.0.0-beta.1","30.0.0-beta.2"],"124.0.6367.9":["30.0.0-beta.3","30.0.0-beta.4","30.0.0-beta.5"],"124.0.6367.18":["30.0.0-beta.6"],"124.0.6367.29":["30.0.0-beta.7","30.0.0-beta.8"],"124.0.6367.49":["30.0.0"],"124.0.6367.60":["30.0.1"],"124.0.6367.91":["30.0.2"],"124.0.6367.119":["30.0.3"],"124.0.6367.201":["30.0.4"],"124.0.6367.207":["30.0.5","30.0.6"],"124.0.6367.221":["30.0.7"],"124.0.6367.230":["30.0.8"],"124.0.6367.233":["30.0.9"],"124.0.6367.243":["30.1.0","30.1.1","30.1.2","30.2.0","30.3.0","30.3.1","30.4.0","30.5.0","30.5.1"],"125.0.6412.0":["31.0.0-alpha.1","31.0.0-alpha.2","31.0.0-alpha.3","31.0.0-alpha.4","31.0.0-alpha.5"],"126.0.6445.0":["31.0.0-beta.1","31.0.0-beta.2","31.0.0-beta.3","31.0.0-beta.4","31.0.0-beta.5","31.0.0-beta.6","31.0.0-beta.7","31.0.0-beta.8","31.0.0-beta.9"],"126.0.6478.36":["31.0.0-beta.10","31.0.0","31.0.1"],"126.0.6478.61":["31.0.2"],"126.0.6478.114":["31.1.0"],"126.0.6478.127":["31.2.0","31.2.1"],"126.0.6478.183":["31.3.0"],"126.0.6478.185":["31.3.1"],"126.0.6478.234":["31.4.0","31.5.0","31.6.0","31.7.0","31.7.1","31.7.2","31.7.3","31.7.4","31.7.5","31.7.6","31.7.7"],"127.0.6521.0":["32.0.0-alpha.1","32.0.0-alpha.2","32.0.0-alpha.3","32.0.0-alpha.4","32.0.0-alpha.5"],"128.0.6571.0":["32.0.0-alpha.6","32.0.0-alpha.7"],"128.0.6573.0":["32.0.0-alpha.8","32.0.0-alpha.9","32.0.0-alpha.10","32.0.0-beta.1"],"128.0.6611.0":["32.0.0-beta.2"],"128.0.6613.7":["32.0.0-beta.3"],"128.0.6613.18":["32.0.0-beta.4"],"128.0.6613.27":["32.0.0-beta.5","32.0.0-beta.6","32.0.0-beta.7"],"128.0.6613.36":["32.0.0","32.0.1"],"128.0.6613.84":["32.0.2"],"128.0.6613.120":["32.1.0"],"128.0.6613.137":["32.1.1"],"128.0.6613.162":["32.1.2"],"128.0.6613.178":["32.2.0"],"128.0.6613.186":["32.2.1","32.2.2","32.2.3","32.2.4","32.2.5","32.2.6","32.2.7","32.2.8","32.3.0","32.3.1","32.3.2","32.3.3"],"129.0.6668.0":["33.0.0-alpha.1"],"130.0.6672.0":["33.0.0-alpha.2","33.0.0-alpha.3","33.0.0-alpha.4","33.0.0-alpha.5","33.0.0-alpha.6","33.0.0-beta.1","33.0.0-beta.2","33.0.0-beta.3","33.0.0-beta.4"],"130.0.6723.19":["33.0.0-beta.5","33.0.0-beta.6","33.0.0-beta.7"],"130.0.6723.31":["33.0.0-beta.8","33.0.0-beta.9","33.0.0-beta.10"],"130.0.6723.44":["33.0.0-beta.11","33.0.0"],"130.0.6723.59":["33.0.1","33.0.2"],"130.0.6723.91":["33.1.0"],"130.0.6723.118":["33.2.0"],"130.0.6723.137":["33.2.1"],"130.0.6723.152":["33.3.0"],"130.0.6723.170":["33.3.1"],"130.0.6723.191":["33.3.2","33.4.0","33.4.1","33.4.2","33.4.3","33.4.4","33.4.5","33.4.6","33.4.7","33.4.8","33.4.9","33.4.10","33.4.11"],"131.0.6776.0":["34.0.0-alpha.1"],"132.0.6779.0":["34.0.0-alpha.2"],"132.0.6789.1":["34.0.0-alpha.3","34.0.0-alpha.4","34.0.0-alpha.5","34.0.0-alpha.6","34.0.0-alpha.7"],"132.0.6820.0":["34.0.0-alpha.8"],"132.0.6824.0":["34.0.0-alpha.9","34.0.0-beta.1","34.0.0-beta.2","34.0.0-beta.3"],"132.0.6834.6":["34.0.0-beta.4","34.0.0-beta.5"],"132.0.6834.15":["34.0.0-beta.6","34.0.0-beta.7","34.0.0-beta.8"],"132.0.6834.32":["34.0.0-beta.9","34.0.0-beta.10","34.0.0-beta.11"],"132.0.6834.46":["34.0.0-beta.12","34.0.0-beta.13"],"132.0.6834.57":["34.0.0-beta.14","34.0.0-beta.15","34.0.0-beta.16"],"132.0.6834.83":["34.0.0","34.0.1"],"132.0.6834.159":["34.0.2"],"132.0.6834.194":["34.1.0","34.1.1"],"132.0.6834.196":["34.2.0"],"132.0.6834.210":["34.3.0","34.3.1","34.3.2","34.3.3","34.3.4","34.4.0","34.4.1","34.5.0","34.5.1","34.5.2","34.5.3","34.5.4","34.5.5","34.5.6","34.5.7","34.5.8"],"133.0.6920.0":["35.0.0-alpha.1","35.0.0-alpha.2","35.0.0-alpha.3","35.0.0-alpha.4","35.0.0-alpha.5","35.0.0-beta.1"],"134.0.6968.0":["35.0.0-beta.2","35.0.0-beta.3","35.0.0-beta.4"],"134.0.6989.0":["35.0.0-beta.5"],"134.0.6990.0":["35.0.0-beta.6","35.0.0-beta.7"],"134.0.6998.10":["35.0.0-beta.8","35.0.0-beta.9"],"134.0.6998.23":["35.0.0-beta.10","35.0.0-beta.11","35.0.0-beta.12"],"134.0.6998.44":["35.0.0-beta.13","35.0.0","35.0.1"],"134.0.6998.88":["35.0.2","35.0.3"],"134.0.6998.165":["35.1.0","35.1.1"],"134.0.6998.178":["35.1.2"],"134.0.6998.179":["35.1.3","35.1.4","35.1.5"],"134.0.6998.205":["35.2.0","35.2.1","35.2.2","35.3.0","35.4.0","35.5.0","35.5.1","35.6.0","35.7.0","35.7.1","35.7.2","35.7.4","35.7.5"],"135.0.7049.5":["36.0.0-alpha.1"],"136.0.7062.0":["36.0.0-alpha.2","36.0.0-alpha.3","36.0.0-alpha.4"],"136.0.7067.0":["36.0.0-alpha.5","36.0.0-alpha.6","36.0.0-beta.1","36.0.0-beta.2","36.0.0-beta.3","36.0.0-beta.4"],"136.0.7103.17":["36.0.0-beta.5"],"136.0.7103.25":["36.0.0-beta.6","36.0.0-beta.7"],"136.0.7103.33":["36.0.0-beta.8","36.0.0-beta.9"],"136.0.7103.48":["36.0.0","36.0.1"],"136.0.7103.49":["36.1.0","36.2.0"],"136.0.7103.93":["36.2.1"],"136.0.7103.113":["36.3.0","36.3.1"],"136.0.7103.115":["36.3.2"],"136.0.7103.149":["36.4.0"],"136.0.7103.168":["36.5.0"],"136.0.7103.177":["36.6.0","36.7.0","36.7.1","36.7.3","36.7.4","36.8.0","36.8.1","36.9.0","36.9.1","36.9.2","36.9.3","36.9.4","36.9.5"],"137.0.7151.0":["37.0.0-alpha.1","37.0.0-alpha.2"],"138.0.7156.0":["37.0.0-alpha.3"],"138.0.7165.0":["37.0.0-alpha.4"],"138.0.7177.0":["37.0.0-alpha.5"],"138.0.7178.0":["37.0.0-alpha.6","37.0.0-alpha.7","37.0.0-beta.1","37.0.0-beta.2"],"138.0.7190.0":["37.0.0-beta.3"],"138.0.7204.15":["37.0.0-beta.4","37.0.0-beta.5","37.0.0-beta.6","37.0.0-beta.7"],"138.0.7204.23":["37.0.0-beta.8"],"138.0.7204.35":["37.0.0-beta.9","37.0.0","37.1.0"],"138.0.7204.97":["37.2.0","37.2.1"],"138.0.7204.100":["37.2.2","37.2.3"],"138.0.7204.157":["37.2.4"],"138.0.7204.168":["37.2.5"],"138.0.7204.185":["37.2.6"],"138.0.7204.224":["37.3.0"],"138.0.7204.235":["37.3.1"],"138.0.7204.243":["37.4.0"],"138.0.7204.251":["37.5.0","37.5.1","37.6.0","37.6.1","37.7.0","37.7.1","37.8.0","37.9.0","37.10.0","37.10.1","37.10.2","37.10.3"],"139.0.7219.0":["38.0.0-alpha.1","38.0.0-alpha.2","38.0.0-alpha.3"],"140.0.7261.0":["38.0.0-alpha.4","38.0.0-alpha.5","38.0.0-alpha.6"],"140.0.7281.0":["38.0.0-alpha.7","38.0.0-alpha.8"],"140.0.7301.0":["38.0.0-alpha.9"],"140.0.7309.0":["38.0.0-alpha.10"],"140.0.7312.0":["38.0.0-alpha.11"],"140.0.7314.0":["38.0.0-alpha.12","38.0.0-alpha.13","38.0.0-beta.1"],"140.0.7327.0":["38.0.0-beta.2","38.0.0-beta.3"],"140.0.7339.2":["38.0.0-beta.4","38.0.0-beta.5","38.0.0-beta.6"],"140.0.7339.16":["38.0.0-beta.7"],"140.0.7339.24":["38.0.0-beta.8","38.0.0-beta.9"],"140.0.7339.41":["38.0.0-beta.11","38.0.0"],"140.0.7339.80":["38.1.0"],"140.0.7339.133":["38.1.1","38.1.2","38.2.0","38.2.1","38.2.2"],"140.0.7339.240":["38.3.0","38.4.0"],"140.0.7339.249":["38.5.0","38.6.0","38.7.0","38.7.1","38.7.2","38.8.0","38.8.1","38.8.2","38.8.4","38.8.6"],"141.0.7361.0":["39.0.0-alpha.1","39.0.0-alpha.2"],"141.0.7390.7":["39.0.0-alpha.3","39.0.0-alpha.4","39.0.0-alpha.5"],"142.0.7417.0":["39.0.0-alpha.6","39.0.0-alpha.7","39.0.0-alpha.8","39.0.0-alpha.9","39.0.0-beta.1","39.0.0-beta.2","39.0.0-beta.3"],"142.0.7444.34":["39.0.0-beta.4","39.0.0-beta.5"],"142.0.7444.52":["39.0.0"],"142.0.7444.59":["39.1.0","39.1.1"],"142.0.7444.134":["39.1.2"],"142.0.7444.162":["39.2.0","39.2.1","39.2.2"],"142.0.7444.175":["39.2.3"],"142.0.7444.177":["39.2.4","39.2.5"],"142.0.7444.226":["39.2.6"],"142.0.7444.235":["39.2.7"],"142.0.7444.265":["39.3.0","39.4.0","39.5.0","39.5.1","39.5.2","39.6.0","39.6.1","39.7.0","39.8.0"],"143.0.7499.0":["40.0.0-alpha.2"],"144.0.7506.0":["40.0.0-alpha.4"],"144.0.7526.0":["40.0.0-alpha.5","40.0.0-alpha.6","40.0.0-alpha.7","40.0.0-alpha.8"],"144.0.7527.0":["40.0.0-beta.1","40.0.0-beta.2"],"144.0.7547.0":["40.0.0-beta.3","40.0.0-beta.4","40.0.0-beta.5"],"144.0.7559.31":["40.0.0-beta.6","40.0.0-beta.7","40.0.0-beta.8"],"144.0.7559.60":["40.0.0-beta.9","40.0.0"],"144.0.7559.96":["40.1.0"],"144.0.7559.111":["40.2.0","40.2.1"],"144.0.7559.134":["40.3.0","40.4.0"],"144.0.7559.173":["40.4.1"],"144.0.7559.177":["40.5.0","40.6.0"],"144.0.7559.220":["40.6.1"],"144.0.7559.225":["40.7.0"],"144.0.7559.236":["40.8.0"],"146.0.7635.0":["41.0.0-alpha.1","41.0.0-alpha.2"],"146.0.7645.0":["41.0.0-alpha.3"],"146.0.7650.0":["41.0.0-alpha.4","41.0.0-alpha.5","41.0.0-alpha.6","41.0.0-beta.1","41.0.0-beta.2","41.0.0-beta.3"],"146.0.7666.0":["41.0.0-beta.4"],"146.0.7680.16":["41.0.0-beta.5","41.0.0-beta.6"],"146.0.7680.31":["41.0.0-beta.7","41.0.0-beta.8"],"146.0.7680.65":["41.0.0"]}```

----

# frontend/node_modules/electron-to-chromium/full-versions.json
```json
{"0.20.0":"39.0.2171.65","0.20.1":"39.0.2171.65","0.20.2":"39.0.2171.65","0.20.3":"39.0.2171.65","0.20.4":"39.0.2171.65","0.20.5":"39.0.2171.65","0.20.6":"39.0.2171.65","0.20.7":"39.0.2171.65","0.20.8":"39.0.2171.65","0.21.0":"40.0.2214.91","0.21.1":"40.0.2214.91","0.21.2":"40.0.2214.91","0.21.3":"41.0.2272.76","0.22.1":"41.0.2272.76","0.22.2":"41.0.2272.76","0.22.3":"41.0.2272.76","0.23.0":"41.0.2272.76","0.24.0":"41.0.2272.76","0.25.0":"42.0.2311.107","0.25.1":"42.0.2311.107","0.25.2":"42.0.2311.107","0.25.3":"42.0.2311.107","0.26.0":"42.0.2311.107","0.26.1":"42.0.2311.107","0.27.0":"42.0.2311.107","0.27.1":"42.0.2311.107","0.27.2":"43.0.2357.65","0.27.3":"43.0.2357.65","0.28.0":"43.0.2357.65","0.28.1":"43.0.2357.65","0.28.2":"43.0.2357.65","0.28.3":"43.0.2357.65","0.29.1":"43.0.2357.65","0.29.2":"43.0.2357.65","0.30.4":"44.0.2403.125","0.31.0":"44.0.2403.125","0.31.2":"45.0.2454.85","0.32.2":"45.0.2454.85","0.32.3":"45.0.2454.85","0.33.0":"45.0.2454.85","0.33.1":"45.0.2454.85","0.33.2":"45.0.2454.85","0.33.3":"45.0.2454.85","0.33.4":"45.0.2454.85","0.33.6":"45.0.2454.85","0.33.7":"45.0.2454.85","0.33.8":"45.0.2454.85","0.33.9":"45.0.2454.85","0.34.0":"45.0.2454.85","0.34.1":"45.0.2454.85","0.34.2":"45.0.2454.85","0.34.3":"45.0.2454.85","0.34.4":"45.0.2454.85","0.35.1":"45.0.2454.85","0.35.2":"45.0.2454.85","0.35.3":"45.0.2454.85","0.35.4":"45.0.2454.85","0.35.5":"45.0.2454.85","0.36.0":"47.0.2526.73","0.36.2":"47.0.2526.73","0.36.3":"47.0.2526.73","0.36.4":"47.0.2526.73","0.36.5":"47.0.2526.110","0.36.6":"47.0.2526.110","0.36.7":"47.0.2526.110","0.36.8":"47.0.2526.110","0.36.9":"47.0.2526.110","0.36.10":"47.0.2526.110","0.36.11":"47.0.2526.110","0.36.12":"47.0.2526.110","0.37.0":"49.0.2623.75","0.37.1":"49.0.2623.75","0.37.3":"49.0.2623.75","0.37.4":"49.0.2623.75","0.37.5":"49.0.2623.75","0.37.6":"49.0.2623.75","0.37.7":"49.0.2623.75","0.37.8":"49.0.2623.75","1.0.0":"49.0.2623.75","1.0.1":"49.0.2623.75","1.0.2":"49.0.2623.75","1.1.0":"50.0.2661.102","1.1.1":"50.0.2661.102","1.1.2":"50.0.2661.102","1.1.3":"50.0.2661.102","1.2.0":"51.0.2704.63","1.2.1":"51.0.2704.63","1.2.2":"51.0.2704.84","1.2.3":"51.0.2704.84","1.2.4":"51.0.2704.103","1.2.5":"51.0.2704.103","1.2.6":"51.0.2704.106","1.2.7":"51.0.2704.106","1.2.8":"51.0.2704.106","1.3.0":"52.0.2743.82","1.3.1":"52.0.2743.82","1.3.2":"52.0.2743.82","1.3.3":"52.0.2743.82","1.3.4":"52.0.2743.82","1.3.5":"52.0.2743.82","1.3.6":"52.0.2743.82","1.3.7":"52.0.2743.82","1.3.9":"52.0.2743.82","1.3.10":"52.0.2743.82","1.3.13":"52.0.2743.82","1.3.14":"52.0.2743.82","1.3.15":"52.0.2743.82","1.4.0":"53.0.2785.113","1.4.1":"53.0.2785.113","1.4.2":"53.0.2785.113","1.4.3":"53.0.2785.113","1.4.4":"53.0.2785.113","1.4.5":"53.0.2785.113","1.4.6":"53.0.2785.143","1.4.7":"53.0.2785.143","1.4.8":"53.0.2785.143","1.4.10":"53.0.2785.143","1.4.11":"53.0.2785.143","1.4.12":"54.0.2840.51","1.4.13":"53.0.2785.143","1.4.14":"53.0.2785.143","1.4.15":"53.0.2785.143","1.4.16":"53.0.2785.143","1.5.0":"54.0.2840.101","1.5.1":"54.0.2840.101","1.6.0":"56.0.2924.87","1.6.1":"56.0.2924.87","1.6.2":"56.0.2924.87","1.6.3":"56.0.2924.87","1.6.4":"56.0.2924.87","1.6.5":"56.0.2924.87","1.6.6":"56.0.2924.87","1.6.7":"56.0.2924.87","1.6.8":"56.0.2924.87","1.6.9":"56.0.2924.87","1.6.10":"56.0.2924.87","1.6.11":"56.0.2924.87","1.6.12":"56.0.2924.87","1.6.13":"56.0.2924.87","1.6.14":"56.0.2924.87","1.6.15":"56.0.2924.87","1.6.16":"56.0.2924.87","1.6.17":"56.0.2924.87","1.6.18":"56.0.2924.87","1.7.0":"58.0.3029.110","1.7.1":"58.0.3029.110","1.7.2":"58.0.3029.110","1.7.3":"58.0.3029.110","1.7.4":"58.0.3029.110","1.7.5":"58.0.3029.110","1.7.6":"58.0.3029.110","1.7.7":"58.0.3029.110","1.7.8":"58.0.3029.110","1.7.9":"58.0.3029.110","1.7.10":"58.0.3029.110","1.7.11":"58.0.3029.110","1.7.12":"58.0.3029.110","1.7.13":"58.0.3029.110","1.7.14":"58.0.3029.110","1.7.15":"58.0.3029.110","1.7.16":"58.0.3029.110","1.8.0":"59.0.3071.115","1.8.1":"59.0.3071.115","1.8.2-beta.1":"59.0.3071.115","1.8.2-beta.2":"59.0.3071.115","1.8.2-beta.3":"59.0.3071.115","1.8.2-beta.4":"59.0.3071.115","1.8.2-beta.5":"59.0.3071.115","1.8.2":"59.0.3071.115","1.8.3":"59.0.3071.115","1.8.4":"59.0.3071.115","1.8.5":"59.0.3071.115","1.8.6":"59.0.3071.115","1.8.7":"59.0.3071.115","1.8.8":"59.0.3071.115","2.0.0-beta.1":"61.0.3163.100","2.0.0-beta.2":"61.0.3163.100","2.0.0-beta.3":"61.0.3163.100","2.0.0-beta.4":"61.0.3163.100","2.0.0-beta.5":"61.0.3163.100","2.0.0-beta.6":"61.0.3163.100","2.0.0-beta.7":"61.0.3163.100","2.0.0-beta.8":"61.0.3163.100","2.0.0":"61.0.3163.100","2.0.1":"61.0.3163.100","2.0.2":"61.0.3163.100","2.0.3":"61.0.3163.100","2.0.4":"61.0.3163.100","2.0.5":"61.0.3163.100","2.0.6":"61.0.3163.100","2.0.7":"61.0.3163.100","2.0.8":"61.0.3163.100","2.0.9":"61.0.3163.100","2.0.10":"61.0.3163.100","2.0.11":"61.0.3163.100","2.0.12":"61.0.3163.100","2.0.13":"61.0.3163.100","2.0.14":"61.0.3163.100","2.0.15":"61.0.3163.100","2.0.16":"61.0.3163.100","2.0.17":"61.0.3163.100","2.0.18":"61.0.3163.100","2.1.0-unsupported.20180809":"61.0.3163.100","3.0.0-beta.1":"66.0.3359.181","3.0.0-beta.2":"66.0.3359.181","3.0.0-beta.3":"66.0.3359.181","3.0.0-beta.4":"66.0.3359.181","3.0.0-beta.5":"66.0.3359.181","3.0.0-beta.6":"66.0.3359.181","3.0.0-beta.7":"66.0.3359.181","3.0.0-beta.8":"66.0.3359.181","3.0.0-beta.9":"66.0.3359.181","3.0.0-beta.10":"66.0.3359.181","3.0.0-beta.11":"66.0.3359.181","3.0.0-beta.12":"66.0.3359.181","3.0.0-beta.13":"66.0.3359.181","3.0.0":"66.0.3359.181","3.0.1":"66.0.3359.181","3.0.2":"66.0.3359.181","3.0.3":"66.0.3359.181","3.0.4":"66.0.3359.181","3.0.5":"66.0.3359.181","3.0.6":"66.0.3359.181","3.0.7":"66.0.3359.181","3.0.8":"66.0.3359.181","3.0.9":"66.0.3359.181","3.0.10":"66.0.3359.181","3.0.11":"66.0.3359.181","3.0.12":"66.0.3359.181","3.0.13":"66.0.3359.181","3.0.14":"66.0.3359.181","3.0.15":"66.0.3359.181","3.0.16":"66.0.3359.181","3.1.0-beta.1":"66.0.3359.181","3.1.0-beta.2":"66.0.3359.181","3.1.0-beta.3":"66.0.3359.181","3.1.0-beta.4":"66.0.3359.181","3.1.0-beta.5":"66.0.3359.181","3.1.0":"66.0.3359.181","3.1.1":"66.0.3359.181","3.1.2":"66.0.3359.181","3.1.3":"66.0.3359.181","3.1.4":"66.0.3359.181","3.1.5":"66.0.3359.181","3.1.6":"66.0.3359.181","3.1.7":"66.0.3359.181","3.1.8":"66.0.3359.181","3.1.9":"66.0.3359.181","3.1.10":"66.0.3359.181","3.1.11":"66.0.3359.181","3.1.12":"66.0.3359.181","3.1.13":"66.0.3359.181","4.0.0-beta.1":"69.0.3497.106","4.0.0-beta.2":"69.0.3497.106","4.0.0-beta.3":"69.0.3497.106","4.0.0-beta.4":"69.0.3497.106","4.0.0-beta.5":"69.0.3497.106","4.0.0-beta.6":"69.0.3497.106","4.0.0-beta.7":"69.0.3497.106","4.0.0-beta.8":"69.0.3497.106","4.0.0-beta.9":"69.0.3497.106","4.0.0-beta.10":"69.0.3497.106","4.0.0-beta.11":"69.0.3497.106","4.0.0":"69.0.3497.106","4.0.1":"69.0.3497.106","4.0.2":"69.0.3497.106","4.0.3":"69.0.3497.106","4.0.4":"69.0.3497.106","4.0.5":"69.0.3497.106","4.0.6":"69.0.3497.106","4.0.7":"69.0.3497.128","4.0.8":"69.0.3497.128","4.1.0":"69.0.3497.128","4.1.1":"69.0.3497.128","4.1.2":"69.0.3497.128","4.1.3":"69.0.3497.128","4.1.4":"69.0.3497.128","4.1.5":"69.0.3497.128","4.2.0":"69.0.3497.128","4.2.1":"69.0.3497.128","4.2.2":"69.0.3497.128","4.2.3":"69.0.3497.128","4.2.4":"69.0.3497.128","4.2.5":"69.0.3497.128","4.2.6":"69.0.3497.128","4.2.7":"69.0.3497.128","4.2.8":"69.0.3497.128","4.2.9":"69.0.3497.128","4.2.10":"69.0.3497.128","4.2.11":"69.0.3497.128","4.2.12":"69.0.3497.128","5.0.0-beta.1":"72.0.3626.52","5.0.0-beta.2":"72.0.3626.52","5.0.0-beta.3":"73.0.3683.27","5.0.0-beta.4":"73.0.3683.54","5.0.0-beta.5":"73.0.3683.61","5.0.0-beta.6":"73.0.3683.84","5.0.0-beta.7":"73.0.3683.94","5.0.0-beta.8":"73.0.3683.104","5.0.0-beta.9":"73.0.3683.117","5.0.0":"73.0.3683.119","5.0.1":"73.0.3683.121","5.0.2":"73.0.3683.121","5.0.3":"73.0.3683.121","5.0.4":"73.0.3683.121","5.0.5":"73.0.3683.121","5.0.6":"73.0.3683.121","5.0.7":"73.0.3683.121","5.0.8":"73.0.3683.121","5.0.9":"73.0.3683.121","5.0.10":"73.0.3683.121","5.0.11":"73.0.3683.121","5.0.12":"73.0.3683.121","5.0.13":"73.0.3683.121","6.0.0-beta.1":"76.0.3774.1","6.0.0-beta.2":"76.0.3783.1","6.0.0-beta.3":"76.0.3783.1","6.0.0-beta.4":"76.0.3783.1","6.0.0-beta.5":"76.0.3805.4","6.0.0-beta.6":"76.0.3809.3","6.0.0-beta.7":"76.0.3809.22","6.0.0-beta.8":"76.0.3809.26","6.0.0-beta.9":"76.0.3809.26","6.0.0-beta.10":"76.0.3809.37","6.0.0-beta.11":"76.0.3809.42","6.0.0-beta.12":"76.0.3809.54","6.0.0-beta.13":"76.0.3809.60","6.0.0-beta.14":"76.0.3809.68","6.0.0-beta.15":"76.0.3809.74","6.0.0":"76.0.3809.88","6.0.1":"76.0.3809.102","6.0.2":"76.0.3809.110","6.0.3":"76.0.3809.126","6.0.4":"76.0.3809.131","6.0.5":"76.0.3809.136","6.0.6":"76.0.3809.138","6.0.7":"76.0.3809.139","6.0.8":"76.0.3809.146","6.0.9":"76.0.3809.146","6.0.10":"76.0.3809.146","6.0.11":"76.0.3809.146","6.0.12":"76.0.3809.146","6.1.0":"76.0.3809.146","6.1.1":"76.0.3809.146","6.1.2":"76.0.3809.146","6.1.3":"76.0.3809.146","6.1.4":"76.0.3809.146","6.1.5":"76.0.3809.146","6.1.6":"76.0.3809.146","6.1.7":"76.0.3809.146","6.1.8":"76.0.3809.146","6.1.9":"76.0.3809.146","6.1.10":"76.0.3809.146","6.1.11":"76.0.3809.146","6.1.12":"76.0.3809.146","7.0.0-beta.1":"78.0.3866.0","7.0.0-beta.2":"78.0.3866.0","7.0.0-beta.3":"78.0.3866.0","7.0.0-beta.4":"78.0.3896.6","7.0.0-beta.5":"78.0.3905.1","7.0.0-beta.6":"78.0.3905.1","7.0.0-beta.7":"78.0.3905.1","7.0.0":"78.0.3905.1","7.0.1":"78.0.3904.92","7.1.0":"78.0.3904.94","7.1.1":"78.0.3904.99","7.1.2":"78.0.3904.113","7.1.3":"78.0.3904.126","7.1.4":"78.0.3904.130","7.1.5":"78.0.3904.130","7.1.6":"78.0.3904.130","7.1.7":"78.0.3904.130","7.1.8":"78.0.3904.130","7.1.9":"78.0.3904.130","7.1.10":"78.0.3904.130","7.1.11":"78.0.3904.130","7.1.12":"78.0.3904.130","7.1.13":"78.0.3904.130","7.1.14":"78.0.3904.130","7.2.0":"78.0.3904.130","7.2.1":"78.0.3904.130","7.2.2":"78.0.3904.130","7.2.3":"78.0.3904.130","7.2.4":"78.0.3904.130","7.3.0":"78.0.3904.130","7.3.1":"78.0.3904.130","7.3.2":"78.0.3904.130","7.3.3":"78.0.3904.130","8.0.0-beta.1":"79.0.3931.0","8.0.0-beta.2":"79.0.3931.0","8.0.0-beta.3":"80.0.3955.0","8.0.0-beta.4":"80.0.3955.0","8.0.0-beta.5":"80.0.3987.14","8.0.0-beta.6":"80.0.3987.51","8.0.0-beta.7":"80.0.3987.59","8.0.0-beta.8":"80.0.3987.75","8.0.0-beta.9":"80.0.3987.75","8.0.0":"80.0.3987.86","8.0.1":"80.0.3987.86","8.0.2":"80.0.3987.86","8.0.3":"80.0.3987.134","8.1.0":"80.0.3987.137","8.1.1":"80.0.3987.141","8.2.0":"80.0.3987.158","8.2.1":"80.0.3987.163","8.2.2":"80.0.3987.163","8.2.3":"80.0.3987.163","8.2.4":"80.0.3987.165","8.2.5":"80.0.3987.165","8.3.0":"80.0.3987.165","8.3.1":"80.0.3987.165","8.3.2":"80.0.3987.165","8.3.3":"80.0.3987.165","8.3.4":"80.0.3987.165","8.4.0":"80.0.3987.165","8.4.1":"80.0.3987.165","8.5.0":"80.0.3987.165","8.5.1":"80.0.3987.165","8.5.2":"80.0.3987.165","8.5.3":"80.0.3987.163","8.5.4":"80.0.3987.163","8.5.5":"80.0.3987.163","9.0.0-beta.1":"82.0.4048.0","9.0.0-beta.2":"82.0.4048.0","9.0.0-beta.3":"82.0.4048.0","9.0.0-beta.4":"82.0.4048.0","9.0.0-beta.5":"82.0.4048.0","9.0.0-beta.6":"82.0.4058.2","9.0.0-beta.7":"82.0.4058.2","9.0.0-beta.9":"82.0.4058.2","9.0.0-beta.10":"82.0.4085.10","9.0.0-beta.11":"82.0.4085.14","9.0.0-beta.12":"82.0.4085.14","9.0.0-beta.13":"82.0.4085.14","9.0.0-beta.14":"82.0.4085.27","9.0.0-beta.15":"83.0.4102.3","9.0.0-beta.16":"83.0.4102.3","9.0.0-beta.17":"83.0.4103.14","9.0.0-beta.18":"83.0.4103.16","9.0.0-beta.19":"83.0.4103.24","9.0.0-beta.20":"83.0.4103.26","9.0.0-beta.21":"83.0.4103.26","9.0.0-beta.22":"83.0.4103.34","9.0.0-beta.23":"83.0.4103.44","9.0.0-beta.24":"83.0.4103.45","9.0.0":"83.0.4103.64","9.0.1":"83.0.4103.94","9.0.2":"83.0.4103.94","9.0.3":"83.0.4103.100","9.0.4":"83.0.4103.104","9.0.5":"83.0.4103.119","9.1.0":"83.0.4103.122","9.1.1":"83.0.4103.122","9.1.2":"83.0.4103.122","9.2.0":"83.0.4103.122","9.2.1":"83.0.4103.122","9.3.0":"83.0.4103.122","9.3.1":"83.0.4103.122","9.3.2":"83.0.4103.122","9.3.3":"83.0.4103.122","9.3.4":"83.0.4103.122","9.3.5":"83.0.4103.122","9.4.0":"83.0.4103.122","9.4.1":"83.0.4103.122","9.4.2":"83.0.4103.122","9.4.3":"83.0.4103.122","9.4.4":"83.0.4103.122","10.0.0-beta.1":"84.0.4129.0","10.0.0-beta.2":"84.0.4129.0","10.0.0-beta.3":"85.0.4161.2","10.0.0-beta.4":"85.0.4161.2","10.0.0-beta.8":"85.0.4181.1","10.0.0-beta.9":"85.0.4181.1","10.0.0-beta.10":"85.0.4183.19","10.0.0-beta.11":"85.0.4183.20","10.0.0-beta.12":"85.0.4183.26","10.0.0-beta.13":"85.0.4183.39","10.0.0-beta.14":"85.0.4183.39","10.0.0-beta.15":"85.0.4183.39","10.0.0-beta.17":"85.0.4183.39","10.0.0-beta.19":"85.0.4183.39","10.0.0-beta.20":"85.0.4183.39","10.0.0-beta.21":"85.0.4183.39","10.0.0-beta.23":"85.0.4183.70","10.0.0-beta.24":"85.0.4183.78","10.0.0-beta.25":"85.0.4183.80","10.0.0":"85.0.4183.84","10.0.1":"85.0.4183.86","10.1.0":"85.0.4183.87","10.1.1":"85.0.4183.93","10.1.2":"85.0.4183.98","10.1.3":"85.0.4183.121","10.1.4":"85.0.4183.121","10.1.5":"85.0.4183.121","10.1.6":"85.0.4183.121","10.1.7":"85.0.4183.121","10.2.0":"85.0.4183.121","10.3.0":"85.0.4183.121","10.3.1":"85.0.4183.121","10.3.2":"85.0.4183.121","10.4.0":"85.0.4183.121","10.4.1":"85.0.4183.121","10.4.2":"85.0.4183.121","10.4.3":"85.0.4183.121","10.4.4":"85.0.4183.121","10.4.5":"85.0.4183.121","10.4.6":"85.0.4183.121","10.4.7":"85.0.4183.121","11.0.0-beta.1":"86.0.4234.0","11.0.0-beta.3":"86.0.4234.0","11.0.0-beta.4":"86.0.4234.0","11.0.0-beta.5":"86.0.4234.0","11.0.0-beta.6":"86.0.4234.0","11.0.0-beta.7":"86.0.4234.0","11.0.0-beta.8":"87.0.4251.1","11.0.0-beta.9":"87.0.4251.1","11.0.0-beta.11":"87.0.4251.1","11.0.0-beta.12":"87.0.4280.11","11.0.0-beta.13":"87.0.4280.11","11.0.0-beta.16":"87.0.4280.27","11.0.0-beta.17":"87.0.4280.27","11.0.0-beta.18":"87.0.4280.27","11.0.0-beta.19":"87.0.4280.27","11.0.0-beta.20":"87.0.4280.40","11.0.0-beta.22":"87.0.4280.47","11.0.0-beta.23":"87.0.4280.47","11.0.0":"87.0.4280.60","11.0.1":"87.0.4280.60","11.0.2":"87.0.4280.67","11.0.3":"87.0.4280.67","11.0.4":"87.0.4280.67","11.0.5":"87.0.4280.88","11.1.0":"87.0.4280.88","11.1.1":"87.0.4280.88","11.2.0":"87.0.4280.141","11.2.1":"87.0.4280.141","11.2.2":"87.0.4280.141","11.2.3":"87.0.4280.141","11.3.0":"87.0.4280.141","11.4.0":"87.0.4280.141","11.4.1":"87.0.4280.141","11.4.2":"87.0.4280.141","11.4.3":"87.0.4280.141","11.4.4":"87.0.4280.141","11.4.5":"87.0.4280.141","11.4.6":"87.0.4280.141","11.4.7":"87.0.4280.141","11.4.8":"87.0.4280.141","11.4.9":"87.0.4280.141","11.4.10":"87.0.4280.141","11.4.11":"87.0.4280.141","11.4.12":"87.0.4280.141","11.5.0":"87.0.4280.141","12.0.0-beta.1":"89.0.4328.0","12.0.0-beta.3":"89.0.4328.0","12.0.0-beta.4":"89.0.4328.0","12.0.0-beta.5":"89.0.4328.0","12.0.0-beta.6":"89.0.4328.0","12.0.0-beta.7":"89.0.4328.0","12.0.0-beta.8":"89.0.4328.0","12.0.0-beta.9":"89.0.4328.0","12.0.0-beta.10":"89.0.4328.0","12.0.0-beta.11":"89.0.4328.0","12.0.0-beta.12":"89.0.4328.0","12.0.0-beta.14":"89.0.4328.0","12.0.0-beta.16":"89.0.4348.1","12.0.0-beta.18":"89.0.4348.1","12.0.0-beta.19":"89.0.4348.1","12.0.0-beta.20":"89.0.4348.1","12.0.0-beta.21":"89.0.4388.2","12.0.0-beta.22":"89.0.4388.2","12.0.0-beta.23":"89.0.4388.2","12.0.0-beta.24":"89.0.4388.2","12.0.0-beta.25":"89.0.4388.2","12.0.0-beta.26":"89.0.4388.2","12.0.0-beta.27":"89.0.4389.23","12.0.0-beta.28":"89.0.4389.23","12.0.0-beta.29":"89.0.4389.23","12.0.0-beta.30":"89.0.4389.58","12.0.0-beta.31":"89.0.4389.58","12.0.0":"89.0.4389.69","12.0.1":"89.0.4389.82","12.0.2":"89.0.4389.90","12.0.3":"89.0.4389.114","12.0.4":"89.0.4389.114","12.0.5":"89.0.4389.128","12.0.6":"89.0.4389.128","12.0.7":"89.0.4389.128","12.0.8":"89.0.4389.128","12.0.9":"89.0.4389.128","12.0.10":"89.0.4389.128","12.0.11":"89.0.4389.128","12.0.12":"89.0.4389.128","12.0.13":"89.0.4389.128","12.0.14":"89.0.4389.128","12.0.15":"89.0.4389.128","12.0.16":"89.0.4389.128","12.0.17":"89.0.4389.128","12.0.18":"89.0.4389.128","12.1.0":"89.0.4389.128","12.1.1":"89.0.4389.128","12.1.2":"89.0.4389.128","12.2.0":"89.0.4389.128","12.2.1":"89.0.4389.128","12.2.2":"89.0.4389.128","12.2.3":"89.0.4389.128","13.0.0-beta.2":"90.0.4402.0","13.0.0-beta.3":"90.0.4402.0","13.0.0-beta.4":"90.0.4415.0","13.0.0-beta.5":"90.0.4415.0","13.0.0-beta.6":"90.0.4415.0","13.0.0-beta.7":"90.0.4415.0","13.0.0-beta.8":"90.0.4415.0","13.0.0-beta.9":"90.0.4415.0","13.0.0-beta.10":"90.0.4415.0","13.0.0-beta.11":"90.0.4415.0","13.0.0-beta.12":"90.0.4415.0","13.0.0-beta.13":"90.0.4415.0","13.0.0-beta.14":"91.0.4448.0","13.0.0-beta.16":"91.0.4448.0","13.0.0-beta.17":"91.0.4448.0","13.0.0-beta.18":"91.0.4448.0","13.0.0-beta.20":"91.0.4448.0","13.0.0-beta.21":"91.0.4472.33","13.0.0-beta.22":"91.0.4472.33","13.0.0-beta.23":"91.0.4472.33","13.0.0-beta.24":"91.0.4472.38","13.0.0-beta.25":"91.0.4472.38","13.0.0-beta.26":"91.0.4472.38","13.0.0-beta.27":"91.0.4472.38","13.0.0-beta.28":"91.0.4472.38","13.0.0":"91.0.4472.69","13.0.1":"91.0.4472.69","13.1.0":"91.0.4472.77","13.1.1":"91.0.4472.77","13.1.2":"91.0.4472.77","13.1.3":"91.0.4472.106","13.1.4":"91.0.4472.106","13.1.5":"91.0.4472.124","13.1.6":"91.0.4472.124","13.1.7":"91.0.4472.124","13.1.8":"91.0.4472.164","13.1.9":"91.0.4472.164","13.2.0":"91.0.4472.164","13.2.1":"91.0.4472.164","13.2.2":"91.0.4472.164","13.2.3":"91.0.4472.164","13.3.0":"91.0.4472.164","13.4.0":"91.0.4472.164","13.5.0":"91.0.4472.164","13.5.1":"91.0.4472.164","13.5.2":"91.0.4472.164","13.6.0":"91.0.4472.164","13.6.1":"91.0.4472.164","13.6.2":"91.0.4472.164","13.6.3":"91.0.4472.164","13.6.6":"91.0.4472.164","13.6.7":"91.0.4472.164","13.6.8":"91.0.4472.164","13.6.9":"91.0.4472.164","14.0.0-beta.1":"92.0.4511.0","14.0.0-beta.2":"92.0.4511.0","14.0.0-beta.3":"92.0.4511.0","14.0.0-beta.5":"93.0.4536.0","14.0.0-beta.6":"93.0.4536.0","14.0.0-beta.7":"93.0.4536.0","14.0.0-beta.8":"93.0.4536.0","14.0.0-beta.9":"93.0.4539.0","14.0.0-beta.10":"93.0.4539.0","14.0.0-beta.11":"93.0.4557.4","14.0.0-beta.12":"93.0.4557.4","14.0.0-beta.13":"93.0.4566.0","14.0.0-beta.14":"93.0.4566.0","14.0.0-beta.15":"93.0.4566.0","14.0.0-beta.16":"93.0.4566.0","14.0.0-beta.17":"93.0.4566.0","14.0.0-beta.18":"93.0.4577.15","14.0.0-beta.19":"93.0.4577.15","14.0.0-beta.20":"93.0.4577.15","14.0.0-beta.21":"93.0.4577.15","14.0.0-beta.22":"93.0.4577.25","14.0.0-beta.23":"93.0.4577.25","14.0.0-beta.24":"93.0.4577.51","14.0.0-beta.25":"93.0.4577.51","14.0.0":"93.0.4577.58","14.0.1":"93.0.4577.63","14.0.2":"93.0.4577.82","14.1.0":"93.0.4577.82","14.1.1":"93.0.4577.82","14.2.0":"93.0.4577.82","14.2.1":"93.0.4577.82","14.2.2":"93.0.4577.82","14.2.3":"93.0.4577.82","14.2.4":"93.0.4577.82","14.2.5":"93.0.4577.82","14.2.6":"93.0.4577.82","14.2.7":"93.0.4577.82","14.2.8":"93.0.4577.82","14.2.9":"93.0.4577.82","15.0.0-alpha.1":"93.0.4566.0","15.0.0-alpha.2":"93.0.4566.0","15.0.0-alpha.3":"94.0.4584.0","15.0.0-alpha.4":"94.0.4584.0","15.0.0-alpha.5":"94.0.4584.0","15.0.0-alpha.6":"94.0.4584.0","15.0.0-alpha.7":"94.0.4590.2","15.0.0-alpha.8":"94.0.4590.2","15.0.0-alpha.9":"94.0.4590.2","15.0.0-alpha.10":"94.0.4606.12","15.0.0-beta.1":"94.0.4606.20","15.0.0-beta.2":"94.0.4606.20","15.0.0-beta.3":"94.0.4606.31","15.0.0-beta.4":"94.0.4606.31","15.0.0-beta.5":"94.0.4606.31","15.0.0-beta.6":"94.0.4606.31","15.0.0-beta.7":"94.0.4606.31","15.0.0":"94.0.4606.51","15.1.0":"94.0.4606.61","15.1.1":"94.0.4606.61","15.1.2":"94.0.4606.71","15.2.0":"94.0.4606.81","15.3.0":"94.0.4606.81","15.3.1":"94.0.4606.81","15.3.2":"94.0.4606.81","15.3.3":"94.0.4606.81","15.3.4":"94.0.4606.81","15.3.5":"94.0.4606.81","15.3.6":"94.0.4606.81","15.3.7":"94.0.4606.81","15.4.0":"94.0.4606.81","15.4.1":"94.0.4606.81","15.4.2":"94.0.4606.81","15.5.0":"94.0.4606.81","15.5.1":"94.0.4606.81","15.5.2":"94.0.4606.81","15.5.3":"94.0.4606.81","15.5.4":"94.0.4606.81","15.5.5":"94.0.4606.81","15.5.6":"94.0.4606.81","15.5.7":"94.0.4606.81","16.0.0-alpha.1":"95.0.4629.0","16.0.0-alpha.2":"95.0.4629.0","16.0.0-alpha.3":"95.0.4629.0","16.0.0-alpha.4":"95.0.4629.0","16.0.0-alpha.5":"95.0.4629.0","16.0.0-alpha.6":"95.0.4629.0","16.0.0-alpha.7":"95.0.4629.0","16.0.0-alpha.8":"96.0.4647.0","16.0.0-alpha.9":"96.0.4647.0","16.0.0-beta.1":"96.0.4647.0","16.0.0-beta.2":"96.0.4647.0","16.0.0-beta.3":"96.0.4647.0","16.0.0-beta.4":"96.0.4664.18","16.0.0-beta.5":"96.0.4664.18","16.0.0-beta.6":"96.0.4664.27","16.0.0-beta.7":"96.0.4664.27","16.0.0-beta.8":"96.0.4664.35","16.0.0-beta.9":"96.0.4664.35","16.0.0":"96.0.4664.45","16.0.1":"96.0.4664.45","16.0.2":"96.0.4664.55","16.0.3":"96.0.4664.55","16.0.4":"96.0.4664.55","16.0.5":"96.0.4664.55","16.0.6":"96.0.4664.110","16.0.7":"96.0.4664.110","16.0.8":"96.0.4664.110","16.0.9":"96.0.4664.174","16.0.10":"96.0.4664.174","16.1.0":"96.0.4664.174","16.1.1":"96.0.4664.174","16.2.0":"96.0.4664.174","16.2.1":"96.0.4664.174","16.2.2":"96.0.4664.174","16.2.3":"96.0.4664.174","16.2.4":"96.0.4664.174","16.2.5":"96.0.4664.174","16.2.6":"96.0.4664.174","16.2.7":"96.0.4664.174","16.2.8":"96.0.4664.174","17.0.0-alpha.1":"96.0.4664.4","17.0.0-alpha.2":"96.0.4664.4","17.0.0-alpha.3":"96.0.4664.4","17.0.0-alpha.4":"98.0.4706.0","17.0.0-alpha.5":"98.0.4706.0","17.0.0-alpha.6":"98.0.4706.0","17.0.0-beta.1":"98.0.4706.0","17.0.0-beta.2":"98.0.4706.0","17.0.0-beta.3":"98.0.4758.9","17.0.0-beta.4":"98.0.4758.11","17.0.0-beta.5":"98.0.4758.11","17.0.0-beta.6":"98.0.4758.11","17.0.0-beta.7":"98.0.4758.11","17.0.0-beta.8":"98.0.4758.11","17.0.0-beta.9":"98.0.4758.11","17.0.0":"98.0.4758.74","17.0.1":"98.0.4758.82","17.1.0":"98.0.4758.102","17.1.1":"98.0.4758.109","17.1.2":"98.0.4758.109","17.2.0":"98.0.4758.109","17.3.0":"98.0.4758.141","17.3.1":"98.0.4758.141","17.4.0":"98.0.4758.141","17.4.1":"98.0.4758.141","17.4.2":"98.0.4758.141","17.4.3":"98.0.4758.141","17.4.4":"98.0.4758.141","17.4.5":"98.0.4758.141","17.4.6":"98.0.4758.141","17.4.7":"98.0.4758.141","17.4.8":"98.0.4758.141","17.4.9":"98.0.4758.141","17.4.10":"98.0.4758.141","17.4.11":"98.0.4758.141","18.0.0-alpha.1":"99.0.4767.0","18.0.0-alpha.2":"99.0.4767.0","18.0.0-alpha.3":"99.0.4767.0","18.0.0-alpha.4":"99.0.4767.0","18.0.0-alpha.5":"99.0.4767.0","18.0.0-beta.1":"100.0.4894.0","18.0.0-beta.2":"100.0.4894.0","18.0.0-beta.3":"100.0.4894.0","18.0.0-beta.4":"100.0.4894.0","18.0.0-beta.5":"100.0.4894.0","18.0.0-beta.6":"100.0.4894.0","18.0.0":"100.0.4896.56","18.0.1":"100.0.4896.60","18.0.2":"100.0.4896.60","18.0.3":"100.0.4896.75","18.0.4":"100.0.4896.75","18.1.0":"100.0.4896.127","18.2.0":"100.0.4896.143","18.2.1":"100.0.4896.143","18.2.2":"100.0.4896.143","18.2.3":"100.0.4896.143","18.2.4":"100.0.4896.160","18.3.0":"100.0.4896.160","18.3.1":"100.0.4896.160","18.3.2":"100.0.4896.160","18.3.3":"100.0.4896.160","18.3.4":"100.0.4896.160","18.3.5":"100.0.4896.160","18.3.6":"100.0.4896.160","18.3.7":"100.0.4896.160","18.3.8":"100.0.4896.160","18.3.9":"100.0.4896.160","18.3.11":"100.0.4896.160","18.3.12":"100.0.4896.160","18.3.13":"100.0.4896.160","18.3.14":"100.0.4896.160","18.3.15":"100.0.4896.160","19.0.0-alpha.1":"102.0.4962.3","19.0.0-alpha.2":"102.0.4971.0","19.0.0-alpha.3":"102.0.4971.0","19.0.0-alpha.4":"102.0.4989.0","19.0.0-alpha.5":"102.0.4989.0","19.0.0-beta.1":"102.0.4999.0","19.0.0-beta.2":"102.0.4999.0","19.0.0-beta.3":"102.0.4999.0","19.0.0-beta.4":"102.0.5005.27","19.0.0-beta.5":"102.0.5005.40","19.0.0-beta.6":"102.0.5005.40","19.0.0-beta.7":"102.0.5005.40","19.0.0-beta.8":"102.0.5005.49","19.0.0":"102.0.5005.61","19.0.1":"102.0.5005.61","19.0.2":"102.0.5005.63","19.0.3":"102.0.5005.63","19.0.4":"102.0.5005.63","19.0.5":"102.0.5005.115","19.0.6":"102.0.5005.115","19.0.7":"102.0.5005.134","19.0.8":"102.0.5005.148","19.0.9":"102.0.5005.167","19.0.10":"102.0.5005.167","19.0.11":"102.0.5005.167","19.0.12":"102.0.5005.167","19.0.13":"102.0.5005.167","19.0.14":"102.0.5005.167","19.0.15":"102.0.5005.167","19.0.16":"102.0.5005.167","19.0.17":"102.0.5005.167","19.1.0":"102.0.5005.167","19.1.1":"102.0.5005.167","19.1.2":"102.0.5005.167","19.1.3":"102.0.5005.167","19.1.4":"102.0.5005.167","19.1.5":"102.0.5005.167","19.1.6":"102.0.5005.167","19.1.7":"102.0.5005.167","19.1.8":"102.0.5005.167","19.1.9":"102.0.5005.167","20.0.0-alpha.1":"103.0.5044.0","20.0.0-alpha.2":"104.0.5073.0","20.0.0-alpha.3":"104.0.5073.0","20.0.0-alpha.4":"104.0.5073.0","20.0.0-alpha.5":"104.0.5073.0","20.0.0-alpha.6":"104.0.5073.0","20.0.0-alpha.7":"104.0.5073.0","20.0.0-beta.1":"104.0.5073.0","20.0.0-beta.2":"104.0.5073.0","20.0.0-beta.3":"104.0.5073.0","20.0.0-beta.4":"104.0.5073.0","20.0.0-beta.5":"104.0.5073.0","20.0.0-beta.6":"104.0.5073.0","20.0.0-beta.7":"104.0.5073.0","20.0.0-beta.8":"104.0.5073.0","20.0.0-beta.9":"104.0.5112.39","20.0.0-beta.10":"104.0.5112.48","20.0.0-beta.11":"104.0.5112.48","20.0.0-beta.12":"104.0.5112.48","20.0.0-beta.13":"104.0.5112.57","20.0.0":"104.0.5112.65","20.0.1":"104.0.5112.81","20.0.2":"104.0.5112.81","20.0.3":"104.0.5112.81","20.1.0":"104.0.5112.102","20.1.1":"104.0.5112.102","20.1.2":"104.0.5112.114","20.1.3":"104.0.5112.114","20.1.4":"104.0.5112.114","20.2.0":"104.0.5112.124","20.3.0":"104.0.5112.124","20.3.1":"104.0.5112.124","20.3.2":"104.0.5112.124","20.3.3":"104.0.5112.124","20.3.4":"104.0.5112.124","20.3.5":"104.0.5112.124","20.3.6":"104.0.5112.124","20.3.7":"104.0.5112.124","20.3.8":"104.0.5112.124","20.3.9":"104.0.5112.124","20.3.10":"104.0.5112.124","20.3.11":"104.0.5112.124","20.3.12":"104.0.5112.124","21.0.0-alpha.1":"105.0.5187.0","21.0.0-alpha.2":"105.0.5187.0","21.0.0-alpha.3":"105.0.5187.0","21.0.0-alpha.4":"105.0.5187.0","21.0.0-alpha.5":"105.0.5187.0","21.0.0-alpha.6":"106.0.5216.0","21.0.0-beta.1":"106.0.5216.0","21.0.0-beta.2":"106.0.5216.0","21.0.0-beta.3":"106.0.5216.0","21.0.0-beta.4":"106.0.5216.0","21.0.0-beta.5":"106.0.5216.0","21.0.0-beta.6":"106.0.5249.40","21.0.0-beta.7":"106.0.5249.40","21.0.0-beta.8":"106.0.5249.40","21.0.0":"106.0.5249.51","21.0.1":"106.0.5249.61","21.1.0":"106.0.5249.91","21.1.1":"106.0.5249.103","21.2.0":"106.0.5249.119","21.2.1":"106.0.5249.165","21.2.2":"106.0.5249.168","21.2.3":"106.0.5249.168","21.3.0":"106.0.5249.181","21.3.1":"106.0.5249.181","21.3.3":"106.0.5249.199","21.3.4":"106.0.5249.199","21.3.5":"106.0.5249.199","21.4.0":"106.0.5249.199","21.4.1":"106.0.5249.199","21.4.2":"106.0.5249.199","21.4.3":"106.0.5249.199","21.4.4":"106.0.5249.199","22.0.0-alpha.1":"107.0.5286.0","22.0.0-alpha.3":"108.0.5329.0","22.0.0-alpha.4":"108.0.5329.0","22.0.0-alpha.5":"108.0.5329.0","22.0.0-alpha.6":"108.0.5329.0","22.0.0-alpha.7":"108.0.5355.0","22.0.0-alpha.8":"108.0.5359.10","22.0.0-beta.1":"108.0.5359.10","22.0.0-beta.2":"108.0.5359.10","22.0.0-beta.3":"108.0.5359.10","22.0.0-beta.4":"108.0.5359.29","22.0.0-beta.5":"108.0.5359.40","22.0.0-beta.6":"108.0.5359.40","22.0.0-beta.7":"108.0.5359.48","22.0.0-beta.8":"108.0.5359.48","22.0.0":"108.0.5359.62","22.0.1":"108.0.5359.125","22.0.2":"108.0.5359.179","22.0.3":"108.0.5359.179","22.1.0":"108.0.5359.179","22.2.0":"108.0.5359.215","22.2.1":"108.0.5359.215","22.3.0":"108.0.5359.215","22.3.1":"108.0.5359.215","22.3.2":"108.0.5359.215","22.3.3":"108.0.5359.215","22.3.4":"108.0.5359.215","22.3.5":"108.0.5359.215","22.3.6":"108.0.5359.215","22.3.7":"108.0.5359.215","22.3.8":"108.0.5359.215","22.3.9":"108.0.5359.215","22.3.10":"108.0.5359.215","22.3.11":"108.0.5359.215","22.3.12":"108.0.5359.215","22.3.13":"108.0.5359.215","22.3.14":"108.0.5359.215","22.3.15":"108.0.5359.215","22.3.16":"108.0.5359.215","22.3.17":"108.0.5359.215","22.3.18":"108.0.5359.215","22.3.20":"108.0.5359.215","22.3.21":"108.0.5359.215","22.3.22":"108.0.5359.215","22.3.23":"108.0.5359.215","22.3.24":"108.0.5359.215","22.3.25":"108.0.5359.215","22.3.26":"108.0.5359.215","22.3.27":"108.0.5359.215","23.0.0-alpha.1":"110.0.5415.0","23.0.0-alpha.2":"110.0.5451.0","23.0.0-alpha.3":"110.0.5451.0","23.0.0-beta.1":"110.0.5478.5","23.0.0-beta.2":"110.0.5478.5","23.0.0-beta.3":"110.0.5478.5","23.0.0-beta.4":"110.0.5481.30","23.0.0-beta.5":"110.0.5481.38","23.0.0-beta.6":"110.0.5481.52","23.0.0-beta.8":"110.0.5481.52","23.0.0":"110.0.5481.77","23.1.0":"110.0.5481.100","23.1.1":"110.0.5481.104","23.1.2":"110.0.5481.177","23.1.3":"110.0.5481.179","23.1.4":"110.0.5481.192","23.2.0":"110.0.5481.192","23.2.1":"110.0.5481.208","23.2.2":"110.0.5481.208","23.2.3":"110.0.5481.208","23.2.4":"110.0.5481.208","23.3.0":"110.0.5481.208","23.3.1":"110.0.5481.208","23.3.2":"110.0.5481.208","23.3.3":"110.0.5481.208","23.3.4":"110.0.5481.208","23.3.5":"110.0.5481.208","23.3.6":"110.0.5481.208","23.3.7":"110.0.5481.208","23.3.8":"110.0.5481.208","23.3.9":"110.0.5481.208","23.3.10":"110.0.5481.208","23.3.11":"110.0.5481.208","23.3.12":"110.0.5481.208","23.3.13":"110.0.5481.208","24.0.0-alpha.1":"111.0.5560.0","24.0.0-alpha.2":"111.0.5560.0","24.0.0-alpha.3":"111.0.5560.0","24.0.0-alpha.4":"111.0.5560.0","24.0.0-alpha.5":"111.0.5560.0","24.0.0-alpha.6":"111.0.5560.0","24.0.0-alpha.7":"111.0.5560.0","24.0.0-beta.1":"111.0.5563.50","24.0.0-beta.2":"111.0.5563.50","24.0.0-beta.3":"112.0.5615.20","24.0.0-beta.4":"112.0.5615.20","24.0.0-beta.5":"112.0.5615.29","24.0.0-beta.6":"112.0.5615.39","24.0.0-beta.7":"112.0.5615.39","24.0.0":"112.0.5615.49","24.1.0":"112.0.5615.50","24.1.1":"112.0.5615.50","24.1.2":"112.0.5615.87","24.1.3":"112.0.5615.165","24.2.0":"112.0.5615.165","24.3.0":"112.0.5615.165","24.3.1":"112.0.5615.183","24.4.0":"112.0.5615.204","24.4.1":"112.0.5615.204","24.5.0":"112.0.5615.204","24.5.1":"112.0.5615.204","24.6.0":"112.0.5615.204","24.6.1":"112.0.5615.204","24.6.2":"112.0.5615.204","24.6.3":"112.0.5615.204","24.6.4":"112.0.5615.204","24.6.5":"112.0.5615.204","24.7.0":"112.0.5615.204","24.7.1":"112.0.5615.204","24.8.0":"112.0.5615.204","24.8.1":"112.0.5615.204","24.8.2":"112.0.5615.204","24.8.3":"112.0.5615.204","24.8.4":"112.0.5615.204","24.8.5":"112.0.5615.204","24.8.6":"112.0.5615.204","24.8.7":"112.0.5615.204","24.8.8":"112.0.5615.204","25.0.0-alpha.1":"114.0.5694.0","25.0.0-alpha.2":"114.0.5694.0","25.0.0-alpha.3":"114.0.5710.0","25.0.0-alpha.4":"114.0.5710.0","25.0.0-alpha.5":"114.0.5719.0","25.0.0-alpha.6":"114.0.5719.0","25.0.0-beta.1":"114.0.5719.0","25.0.0-beta.2":"114.0.5719.0","25.0.0-beta.3":"114.0.5719.0","25.0.0-beta.4":"114.0.5735.16","25.0.0-beta.5":"114.0.5735.16","25.0.0-beta.6":"114.0.5735.16","25.0.0-beta.7":"114.0.5735.16","25.0.0-beta.8":"114.0.5735.35","25.0.0-beta.9":"114.0.5735.45","25.0.0":"114.0.5735.45","25.0.1":"114.0.5735.45","25.1.0":"114.0.5735.106","25.1.1":"114.0.5735.106","25.2.0":"114.0.5735.134","25.3.0":"114.0.5735.199","25.3.1":"114.0.5735.243","25.3.2":"114.0.5735.248","25.4.0":"114.0.5735.248","25.5.0":"114.0.5735.289","25.6.0":"114.0.5735.289","25.7.0":"114.0.5735.289","25.8.0":"114.0.5735.289","25.8.1":"114.0.5735.289","25.8.2":"114.0.5735.289","25.8.3":"114.0.5735.289","25.8.4":"114.0.5735.289","25.9.0":"114.0.5735.289","25.9.1":"114.0.5735.289","25.9.2":"114.0.5735.289","25.9.3":"114.0.5735.289","25.9.4":"114.0.5735.289","25.9.5":"114.0.5735.289","25.9.6":"114.0.5735.289","25.9.7":"114.0.5735.289","25.9.8":"114.0.5735.289","26.0.0-alpha.1":"116.0.5791.0","26.0.0-alpha.2":"116.0.5791.0","26.0.0-alpha.3":"116.0.5791.0","26.0.0-alpha.4":"116.0.5791.0","26.0.0-alpha.5":"116.0.5791.0","26.0.0-alpha.6":"116.0.5815.0","26.0.0-alpha.7":"116.0.5831.0","26.0.0-alpha.8":"116.0.5845.0","26.0.0-beta.1":"116.0.5845.0","26.0.0-beta.2":"116.0.5845.14","26.0.0-beta.3":"116.0.5845.14","26.0.0-beta.4":"116.0.5845.14","26.0.0-beta.5":"116.0.5845.14","26.0.0-beta.6":"116.0.5845.14","26.0.0-beta.7":"116.0.5845.14","26.0.0-beta.8":"116.0.5845.42","26.0.0-beta.9":"116.0.5845.42","26.0.0-beta.10":"116.0.5845.49","26.0.0-beta.11":"116.0.5845.49","26.0.0-beta.12":"116.0.5845.62","26.0.0":"116.0.5845.82","26.1.0":"116.0.5845.97","26.2.0":"116.0.5845.179","26.2.1":"116.0.5845.188","26.2.2":"116.0.5845.190","26.2.3":"116.0.5845.190","26.2.4":"116.0.5845.190","26.3.0":"116.0.5845.228","26.4.0":"116.0.5845.228","26.4.1":"116.0.5845.228","26.4.2":"116.0.5845.228","26.4.3":"116.0.5845.228","26.5.0":"116.0.5845.228","26.6.0":"116.0.5845.228","26.6.1":"116.0.5845.228","26.6.2":"116.0.5845.228","26.6.3":"116.0.5845.228","26.6.4":"116.0.5845.228","26.6.5":"116.0.5845.228","26.6.6":"116.0.5845.228","26.6.7":"116.0.5845.228","26.6.8":"116.0.5845.228","26.6.9":"116.0.5845.228","26.6.10":"116.0.5845.228","27.0.0-alpha.1":"118.0.5949.0","27.0.0-alpha.2":"118.0.5949.0","27.0.0-alpha.3":"118.0.5949.0","27.0.0-alpha.4":"118.0.5949.0","27.0.0-alpha.5":"118.0.5949.0","27.0.0-alpha.6":"118.0.5949.0","27.0.0-beta.1":"118.0.5993.5","27.0.0-beta.2":"118.0.5993.5","27.0.0-beta.3":"118.0.5993.5","27.0.0-beta.4":"118.0.5993.11","27.0.0-beta.5":"118.0.5993.18","27.0.0-beta.6":"118.0.5993.18","27.0.0-beta.7":"118.0.5993.18","27.0.0-beta.8":"118.0.5993.18","27.0.0-beta.9":"118.0.5993.18","27.0.0":"118.0.5993.54","27.0.1":"118.0.5993.89","27.0.2":"118.0.5993.89","27.0.3":"118.0.5993.120","27.0.4":"118.0.5993.129","27.1.0":"118.0.5993.144","27.1.2":"118.0.5993.144","27.1.3":"118.0.5993.159","27.2.0":"118.0.5993.159","27.2.1":"118.0.5993.159","27.2.2":"118.0.5993.159","27.2.3":"118.0.5993.159","27.2.4":"118.0.5993.159","27.3.0":"118.0.5993.159","27.3.1":"118.0.5993.159","27.3.2":"118.0.5993.159","27.3.3":"118.0.5993.159","27.3.4":"118.0.5993.159","27.3.5":"118.0.5993.159","27.3.6":"118.0.5993.159","27.3.7":"118.0.5993.159","27.3.8":"118.0.5993.159","27.3.9":"118.0.5993.159","27.3.10":"118.0.5993.159","27.3.11":"118.0.5993.159","28.0.0-alpha.1":"119.0.6045.0","28.0.0-alpha.2":"119.0.6045.0","28.0.0-alpha.3":"119.0.6045.21","28.0.0-alpha.4":"119.0.6045.21","28.0.0-alpha.5":"119.0.6045.33","28.0.0-alpha.6":"119.0.6045.33","28.0.0-alpha.7":"119.0.6045.33","28.0.0-beta.1":"119.0.6045.33","28.0.0-beta.2":"120.0.6099.0","28.0.0-beta.3":"120.0.6099.5","28.0.0-beta.4":"120.0.6099.5","28.0.0-beta.5":"120.0.6099.18","28.0.0-beta.6":"120.0.6099.18","28.0.0-beta.7":"120.0.6099.18","28.0.0-beta.8":"120.0.6099.18","28.0.0-beta.9":"120.0.6099.18","28.0.0-beta.10":"120.0.6099.18","28.0.0-beta.11":"120.0.6099.35","28.0.0":"120.0.6099.56","28.1.0":"120.0.6099.109","28.1.1":"120.0.6099.109","28.1.2":"120.0.6099.199","28.1.3":"120.0.6099.199","28.1.4":"120.0.6099.216","28.2.0":"120.0.6099.227","28.2.1":"120.0.6099.268","28.2.2":"120.0.6099.276","28.2.3":"120.0.6099.283","28.2.4":"120.0.6099.291","28.2.5":"120.0.6099.291","28.2.6":"120.0.6099.291","28.2.7":"120.0.6099.291","28.2.8":"120.0.6099.291","28.2.9":"120.0.6099.291","28.2.10":"120.0.6099.291","28.3.0":"120.0.6099.291","28.3.1":"120.0.6099.291","28.3.2":"120.0.6099.291","28.3.3":"120.0.6099.291","29.0.0-alpha.1":"121.0.6147.0","29.0.0-alpha.2":"121.0.6147.0","29.0.0-alpha.3":"121.0.6147.0","29.0.0-alpha.4":"121.0.6159.0","29.0.0-alpha.5":"121.0.6159.0","29.0.0-alpha.6":"121.0.6159.0","29.0.0-alpha.7":"121.0.6159.0","29.0.0-alpha.8":"122.0.6194.0","29.0.0-alpha.9":"122.0.6236.2","29.0.0-alpha.10":"122.0.6236.2","29.0.0-alpha.11":"122.0.6236.2","29.0.0-beta.1":"122.0.6236.2","29.0.0-beta.2":"122.0.6236.2","29.0.0-beta.3":"122.0.6261.6","29.0.0-beta.4":"122.0.6261.6","29.0.0-beta.5":"122.0.6261.18","29.0.0-beta.6":"122.0.6261.18","29.0.0-beta.7":"122.0.6261.18","29.0.0-beta.8":"122.0.6261.18","29.0.0-beta.9":"122.0.6261.18","29.0.0-beta.10":"122.0.6261.18","29.0.0-beta.11":"122.0.6261.18","29.0.0-beta.12":"122.0.6261.29","29.0.0":"122.0.6261.39","29.0.1":"122.0.6261.57","29.1.0":"122.0.6261.70","29.1.1":"122.0.6261.111","29.1.2":"122.0.6261.112","29.1.3":"122.0.6261.112","29.1.4":"122.0.6261.129","29.1.5":"122.0.6261.130","29.1.6":"122.0.6261.139","29.2.0":"122.0.6261.156","29.3.0":"122.0.6261.156","29.3.1":"122.0.6261.156","29.3.2":"122.0.6261.156","29.3.3":"122.0.6261.156","29.4.0":"122.0.6261.156","29.4.1":"122.0.6261.156","29.4.2":"122.0.6261.156","29.4.3":"122.0.6261.156","29.4.4":"122.0.6261.156","29.4.5":"122.0.6261.156","29.4.6":"122.0.6261.156","30.0.0-alpha.1":"123.0.6296.0","30.0.0-alpha.2":"123.0.6312.5","30.0.0-alpha.3":"124.0.6323.0","30.0.0-alpha.4":"124.0.6323.0","30.0.0-alpha.5":"124.0.6331.0","30.0.0-alpha.6":"124.0.6331.0","30.0.0-alpha.7":"124.0.6353.0","30.0.0-beta.1":"124.0.6359.0","30.0.0-beta.2":"124.0.6359.0","30.0.0-beta.3":"124.0.6367.9","30.0.0-beta.4":"124.0.6367.9","30.0.0-beta.5":"124.0.6367.9","30.0.0-beta.6":"124.0.6367.18","30.0.0-beta.7":"124.0.6367.29","30.0.0-beta.8":"124.0.6367.29","30.0.0":"124.0.6367.49","30.0.1":"124.0.6367.60","30.0.2":"124.0.6367.91","30.0.3":"124.0.6367.119","30.0.4":"124.0.6367.201","30.0.5":"124.0.6367.207","30.0.6":"124.0.6367.207","30.0.7":"124.0.6367.221","30.0.8":"124.0.6367.230","30.0.9":"124.0.6367.233","30.1.0":"124.0.6367.243","30.1.1":"124.0.6367.243","30.1.2":"124.0.6367.243","30.2.0":"124.0.6367.243","30.3.0":"124.0.6367.243","30.3.1":"124.0.6367.243","30.4.0":"124.0.6367.243","30.5.0":"124.0.6367.243","30.5.1":"124.0.6367.243","31.0.0-alpha.1":"125.0.6412.0","31.0.0-alpha.2":"125.0.6412.0","31.0.0-alpha.3":"125.0.6412.0","31.0.0-alpha.4":"125.0.6412.0","31.0.0-alpha.5":"125.0.6412.0","31.0.0-beta.1":"126.0.6445.0","31.0.0-beta.2":"126.0.6445.0","31.0.0-beta.3":"126.0.6445.0","31.0.0-beta.4":"126.0.6445.0","31.0.0-beta.5":"126.0.6445.0","31.0.0-beta.6":"126.0.6445.0","31.0.0-beta.7":"126.0.6445.0","31.0.0-beta.8":"126.0.6445.0","31.0.0-beta.9":"126.0.6445.0","31.0.0-beta.10":"126.0.6478.36","31.0.0":"126.0.6478.36","31.0.1":"126.0.6478.36","31.0.2":"126.0.6478.61","31.1.0":"126.0.6478.114","31.2.0":"126.0.6478.127","31.2.1":"126.0.6478.127","31.3.0":"126.0.6478.183","31.3.1":"126.0.6478.185","31.4.0":"126.0.6478.234","31.5.0":"126.0.6478.234","31.6.0":"126.0.6478.234","31.7.0":"126.0.6478.234","31.7.1":"126.0.6478.234","31.7.2":"126.0.6478.234","31.7.3":"126.0.6478.234","31.7.4":"126.0.6478.234","31.7.5":"126.0.6478.234","31.7.6":"126.0.6478.234","31.7.7":"126.0.6478.234","32.0.0-alpha.1":"127.0.6521.0","32.0.0-alpha.2":"127.0.6521.0","32.0.0-alpha.3":"127.0.6521.0","32.0.0-alpha.4":"127.0.6521.0","32.0.0-alpha.5":"127.0.6521.0","32.0.0-alpha.6":"128.0.6571.0","32.0.0-alpha.7":"128.0.6571.0","32.0.0-alpha.8":"128.0.6573.0","32.0.0-alpha.9":"128.0.6573.0","32.0.0-alpha.10":"128.0.6573.0","32.0.0-beta.1":"128.0.6573.0","32.0.0-beta.2":"128.0.6611.0","32.0.0-beta.3":"128.0.6613.7","32.0.0-beta.4":"128.0.6613.18","32.0.0-beta.5":"128.0.6613.27","32.0.0-beta.6":"128.0.6613.27","32.0.0-beta.7":"128.0.6613.27","32.0.0":"128.0.6613.36","32.0.1":"128.0.6613.36","32.0.2":"128.0.6613.84","32.1.0":"128.0.6613.120","32.1.1":"128.0.6613.137","32.1.2":"128.0.6613.162","32.2.0":"128.0.6613.178","32.2.1":"128.0.6613.186","32.2.2":"128.0.6613.186","32.2.3":"128.0.6613.186","32.2.4":"128.0.6613.186","32.2.5":"128.0.6613.186","32.2.6":"128.0.6613.186","32.2.7":"128.0.6613.186","32.2.8":"128.0.6613.186","32.3.0":"128.0.6613.186","32.3.1":"128.0.6613.186","32.3.2":"128.0.6613.186","32.3.3":"128.0.6613.186","33.0.0-alpha.1":"129.0.6668.0","33.0.0-alpha.2":"130.0.6672.0","33.0.0-alpha.3":"130.0.6672.0","33.0.0-alpha.4":"130.0.6672.0","33.0.0-alpha.5":"130.0.6672.0","33.0.0-alpha.6":"130.0.6672.0","33.0.0-beta.1":"130.0.6672.0","33.0.0-beta.2":"130.0.6672.0","33.0.0-beta.3":"130.0.6672.0","33.0.0-beta.4":"130.0.6672.0","33.0.0-beta.5":"130.0.6723.19","33.0.0-beta.6":"130.0.6723.19","33.0.0-beta.7":"130.0.6723.19","33.0.0-beta.8":"130.0.6723.31","33.0.0-beta.9":"130.0.6723.31","33.0.0-beta.10":"130.0.6723.31","33.0.0-beta.11":"130.0.6723.44","33.0.0":"130.0.6723.44","33.0.1":"130.0.6723.59","33.0.2":"130.0.6723.59","33.1.0":"130.0.6723.91","33.2.0":"130.0.6723.118","33.2.1":"130.0.6723.137","33.3.0":"130.0.6723.152","33.3.1":"130.0.6723.170","33.3.2":"130.0.6723.191","33.4.0":"130.0.6723.191","33.4.1":"130.0.6723.191","33.4.2":"130.0.6723.191","33.4.3":"130.0.6723.191","33.4.4":"130.0.6723.191","33.4.5":"130.0.6723.191","33.4.6":"130.0.6723.191","33.4.7":"130.0.6723.191","33.4.8":"130.0.6723.191","33.4.9":"130.0.6723.191","33.4.10":"130.0.6723.191","33.4.11":"130.0.6723.191","34.0.0-alpha.1":"131.0.6776.0","34.0.0-alpha.2":"132.0.6779.0","34.0.0-alpha.3":"132.0.6789.1","34.0.0-alpha.4":"132.0.6789.1","34.0.0-alpha.5":"132.0.6789.1","34.0.0-alpha.6":"132.0.6789.1","34.0.0-alpha.7":"132.0.6789.1","34.0.0-alpha.8":"132.0.6820.0","34.0.0-alpha.9":"132.0.6824.0","34.0.0-beta.1":"132.0.6824.0","34.0.0-beta.2":"132.0.6824.0","34.0.0-beta.3":"132.0.6824.0","34.0.0-beta.4":"132.0.6834.6","34.0.0-beta.5":"132.0.6834.6","34.0.0-beta.6":"132.0.6834.15","34.0.0-beta.7":"132.0.6834.15","34.0.0-beta.8":"132.0.6834.15","34.0.0-beta.9":"132.0.6834.32","34.0.0-beta.10":"132.0.6834.32","34.0.0-beta.11":"132.0.6834.32","34.0.0-beta.12":"132.0.6834.46","34.0.0-beta.13":"132.0.6834.46","34.0.0-beta.14":"132.0.6834.57","34.0.0-beta.15":"132.0.6834.57","34.0.0-beta.16":"132.0.6834.57","34.0.0":"132.0.6834.83","34.0.1":"132.0.6834.83","34.0.2":"132.0.6834.159","34.1.0":"132.0.6834.194","34.1.1":"132.0.6834.194","34.2.0":"132.0.6834.196","34.3.0":"132.0.6834.210","34.3.1":"132.0.6834.210","34.3.2":"132.0.6834.210","34.3.3":"132.0.6834.210","34.3.4":"132.0.6834.210","34.4.0":"132.0.6834.210","34.4.1":"132.0.6834.210","34.5.0":"132.0.6834.210","34.5.1":"132.0.6834.210","34.5.2":"132.0.6834.210","34.5.3":"132.0.6834.210","34.5.4":"132.0.6834.210","34.5.5":"132.0.6834.210","34.5.6":"132.0.6834.210","34.5.7":"132.0.6834.210","34.5.8":"132.0.6834.210","35.0.0-alpha.1":"133.0.6920.0","35.0.0-alpha.2":"133.0.6920.0","35.0.0-alpha.3":"133.0.6920.0","35.0.0-alpha.4":"133.0.6920.0","35.0.0-alpha.5":"133.0.6920.0","35.0.0-beta.1":"133.0.6920.0","35.0.0-beta.2":"134.0.6968.0","35.0.0-beta.3":"134.0.6968.0","35.0.0-beta.4":"134.0.6968.0","35.0.0-beta.5":"134.0.6989.0","35.0.0-beta.6":"134.0.6990.0","35.0.0-beta.7":"134.0.6990.0","35.0.0-beta.8":"134.0.6998.10","35.0.0-beta.9":"134.0.6998.10","35.0.0-beta.10":"134.0.6998.23","35.0.0-beta.11":"134.0.6998.23","35.0.0-beta.12":"134.0.6998.23","35.0.0-beta.13":"134.0.6998.44","35.0.0":"134.0.6998.44","35.0.1":"134.0.6998.44","35.0.2":"134.0.6998.88","35.0.3":"134.0.6998.88","35.1.0":"134.0.6998.165","35.1.1":"134.0.6998.165","35.1.2":"134.0.6998.178","35.1.3":"134.0.6998.179","35.1.4":"134.0.6998.179","35.1.5":"134.0.6998.179","35.2.0":"134.0.6998.205","35.2.1":"134.0.6998.205","35.2.2":"134.0.6998.205","35.3.0":"134.0.6998.205","35.4.0":"134.0.6998.205","35.5.0":"134.0.6998.205","35.5.1":"134.0.6998.205","35.6.0":"134.0.6998.205","35.7.0":"134.0.6998.205","35.7.1":"134.0.6998.205","35.7.2":"134.0.6998.205","35.7.4":"134.0.6998.205","35.7.5":"134.0.6998.205","36.0.0-alpha.1":"135.0.7049.5","36.0.0-alpha.2":"136.0.7062.0","36.0.0-alpha.3":"136.0.7062.0","36.0.0-alpha.4":"136.0.7062.0","36.0.0-alpha.5":"136.0.7067.0","36.0.0-alpha.6":"136.0.7067.0","36.0.0-beta.1":"136.0.7067.0","36.0.0-beta.2":"136.0.7067.0","36.0.0-beta.3":"136.0.7067.0","36.0.0-beta.4":"136.0.7067.0","36.0.0-beta.5":"136.0.7103.17","36.0.0-beta.6":"136.0.7103.25","36.0.0-beta.7":"136.0.7103.25","36.0.0-beta.8":"136.0.7103.33","36.0.0-beta.9":"136.0.7103.33","36.0.0":"136.0.7103.48","36.0.1":"136.0.7103.48","36.1.0":"136.0.7103.49","36.2.0":"136.0.7103.49","36.2.1":"136.0.7103.93","36.3.0":"136.0.7103.113","36.3.1":"136.0.7103.113","36.3.2":"136.0.7103.115","36.4.0":"136.0.7103.149","36.5.0":"136.0.7103.168","36.6.0":"136.0.7103.177","36.7.0":"136.0.7103.177","36.7.1":"136.0.7103.177","36.7.3":"136.0.7103.177","36.7.4":"136.0.7103.177","36.8.0":"136.0.7103.177","36.8.1":"136.0.7103.177","36.9.0":"136.0.7103.177","36.9.1":"136.0.7103.177","36.9.2":"136.0.7103.177","36.9.3":"136.0.7103.177","36.9.4":"136.0.7103.177","36.9.5":"136.0.7103.177","37.0.0-alpha.1":"137.0.7151.0","37.0.0-alpha.2":"137.0.7151.0","37.0.0-alpha.3":"138.0.7156.0","37.0.0-alpha.4":"138.0.7165.0","37.0.0-alpha.5":"138.0.7177.0","37.0.0-alpha.6":"138.0.7178.0","37.0.0-alpha.7":"138.0.7178.0","37.0.0-beta.1":"138.0.7178.0","37.0.0-beta.2":"138.0.7178.0","37.0.0-beta.3":"138.0.7190.0","37.0.0-beta.4":"138.0.7204.15","37.0.0-beta.5":"138.0.7204.15","37.0.0-beta.6":"138.0.7204.15","37.0.0-beta.7":"138.0.7204.15","37.0.0-beta.8":"138.0.7204.23","37.0.0-beta.9":"138.0.7204.35","37.0.0":"138.0.7204.35","37.1.0":"138.0.7204.35","37.2.0":"138.0.7204.97","37.2.1":"138.0.7204.97","37.2.2":"138.0.7204.100","37.2.3":"138.0.7204.100","37.2.4":"138.0.7204.157","37.2.5":"138.0.7204.168","37.2.6":"138.0.7204.185","37.3.0":"138.0.7204.224","37.3.1":"138.0.7204.235","37.4.0":"138.0.7204.243","37.5.0":"138.0.7204.251","37.5.1":"138.0.7204.251","37.6.0":"138.0.7204.251","37.6.1":"138.0.7204.251","37.7.0":"138.0.7204.251","37.7.1":"138.0.7204.251","37.8.0":"138.0.7204.251","37.9.0":"138.0.7204.251","37.10.0":"138.0.7204.251","37.10.1":"138.0.7204.251","37.10.2":"138.0.7204.251","37.10.3":"138.0.7204.251","38.0.0-alpha.1":"139.0.7219.0","38.0.0-alpha.2":"139.0.7219.0","38.0.0-alpha.3":"139.0.7219.0","38.0.0-alpha.4":"140.0.7261.0","38.0.0-alpha.5":"140.0.7261.0","38.0.0-alpha.6":"140.0.7261.0","38.0.0-alpha.7":"140.0.7281.0","38.0.0-alpha.8":"140.0.7281.0","38.0.0-alpha.9":"140.0.7301.0","38.0.0-alpha.10":"140.0.7309.0","38.0.0-alpha.11":"140.0.7312.0","38.0.0-alpha.12":"140.0.7314.0","38.0.0-alpha.13":"140.0.7314.0","38.0.0-beta.1":"140.0.7314.0","38.0.0-beta.2":"140.0.7327.0","38.0.0-beta.3":"140.0.7327.0","38.0.0-beta.4":"140.0.7339.2","38.0.0-beta.5":"140.0.7339.2","38.0.0-beta.6":"140.0.7339.2","38.0.0-beta.7":"140.0.7339.16","38.0.0-beta.8":"140.0.7339.24","38.0.0-beta.9":"140.0.7339.24","38.0.0-beta.11":"140.0.7339.41","38.0.0":"140.0.7339.41","38.1.0":"140.0.7339.80","38.1.1":"140.0.7339.133","38.1.2":"140.0.7339.133","38.2.0":"140.0.7339.133","38.2.1":"140.0.7339.133","38.2.2":"140.0.7339.133","38.3.0":"140.0.7339.240","38.4.0":"140.0.7339.240","38.5.0":"140.0.7339.249","38.6.0":"140.0.7339.249","38.7.0":"140.0.7339.249","38.7.1":"140.0.7339.249","38.7.2":"140.0.7339.249","38.8.0":"140.0.7339.249","38.8.1":"140.0.7339.249","38.8.2":"140.0.7339.249","38.8.4":"140.0.7339.249","38.8.6":"140.0.7339.249","39.0.0-alpha.1":"141.0.7361.0","39.0.0-alpha.2":"141.0.7361.0","39.0.0-alpha.3":"141.0.7390.7","39.0.0-alpha.4":"141.0.7390.7","39.0.0-alpha.5":"141.0.7390.7","39.0.0-alpha.6":"142.0.7417.0","39.0.0-alpha.7":"142.0.7417.0","39.0.0-alpha.8":"142.0.7417.0","39.0.0-alpha.9":"142.0.7417.0","39.0.0-beta.1":"142.0.7417.0","39.0.0-beta.2":"142.0.7417.0","39.0.0-beta.3":"142.0.7417.0","39.0.0-beta.4":"142.0.7444.34","39.0.0-beta.5":"142.0.7444.34","39.0.0":"142.0.7444.52","39.1.0":"142.0.7444.59","39.1.1":"142.0.7444.59","39.1.2":"142.0.7444.134","39.2.0":"142.0.7444.162","39.2.1":"142.0.7444.162","39.2.2":"142.0.7444.162","39.2.3":"142.0.7444.175","39.2.4":"142.0.7444.177","39.2.5":"142.0.7444.177","39.2.6":"142.0.7444.226","39.2.7":"142.0.7444.235","39.3.0":"142.0.7444.265","39.4.0":"142.0.7444.265","39.5.0":"142.0.7444.265","39.5.1":"142.0.7444.265","39.5.2":"142.0.7444.265","39.6.0":"142.0.7444.265","39.6.1":"142.0.7444.265","39.7.0":"142.0.7444.265","39.8.0":"142.0.7444.265","40.0.0-alpha.2":"143.0.7499.0","40.0.0-alpha.4":"144.0.7506.0","40.0.0-alpha.5":"144.0.7526.0","40.0.0-alpha.6":"144.0.7526.0","40.0.0-alpha.7":"144.0.7526.0","40.0.0-alpha.8":"144.0.7526.0","40.0.0-beta.1":"144.0.7527.0","40.0.0-beta.2":"144.0.7527.0","40.0.0-beta.3":"144.0.7547.0","40.0.0-beta.4":"144.0.7547.0","40.0.0-beta.5":"144.0.7547.0","40.0.0-beta.6":"144.0.7559.31","40.0.0-beta.7":"144.0.7559.31","40.0.0-beta.8":"144.0.7559.31","40.0.0-beta.9":"144.0.7559.60","40.0.0":"144.0.7559.60","40.1.0":"144.0.7559.96","40.2.0":"144.0.7559.111","40.2.1":"144.0.7559.111","40.3.0":"144.0.7559.134","40.4.0":"144.0.7559.134","40.4.1":"144.0.7559.173","40.5.0":"144.0.7559.177","40.6.0":"144.0.7559.177","40.6.1":"144.0.7559.220","40.7.0":"144.0.7559.225","40.8.0":"144.0.7559.236","41.0.0-alpha.1":"146.0.7635.0","41.0.0-alpha.2":"146.0.7635.0","41.0.0-alpha.3":"146.0.7645.0","41.0.0-alpha.4":"146.0.7650.0","41.0.0-alpha.5":"146.0.7650.0","41.0.0-alpha.6":"146.0.7650.0","41.0.0-beta.1":"146.0.7650.0","41.0.0-beta.2":"146.0.7650.0","41.0.0-beta.3":"146.0.7650.0","41.0.0-beta.4":"146.0.7666.0","41.0.0-beta.5":"146.0.7680.16","41.0.0-beta.6":"146.0.7680.16","41.0.0-beta.7":"146.0.7680.31","41.0.0-beta.8":"146.0.7680.31","41.0.0":"146.0.7680.65"}```

----

# frontend/node_modules/electron-to-chromium/package.json
```json
{
  "name": "electron-to-chromium",
  "version": "1.5.313",
  "description": "Provides a list of electron-to-chromium version mappings",
  "main": "index.js",
  "files": [
    "versions.js",
    "full-versions.js",
    "chromium-versions.js",
    "full-chromium-versions.js",
    "versions.json",
    "full-versions.json",
    "chromium-versions.json",
    "full-chromium-versions.json",
    "LICENSE"
  ],
  "scripts": {
    "build": "node build.mjs",
    "update": "node automated-update.js",
    "test": "nyc ava --verbose",
    "report": "nyc report --reporter=text-lcov > coverage.lcov && codecov"
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/kilian/electron-to-chromium.git"
  },
  "keywords": [
    "electron",
    "chrome",
    "chromium",
    "browserslist",
    "browserlist"
  ],
  "author": "Kilian Valkhof",
  "license": "ISC",
  "devDependencies": {
    "ava": "^5.1.1",
    "codecov": "^3.8.2",
    "compare-versions": "^6.0.0-rc.1",
    "node-fetch": "^3.3.0",
    "nyc": "^15.1.0",
    "shelljs": "^0.8.5"
  }
}
```

----

# frontend/node_modules/electron-to-chromium/versions.json
```json
{"0.20":"39","0.21":"41","0.22":"41","0.23":"41","0.24":"41","0.25":"42","0.26":"42","0.27":"43","0.28":"43","0.29":"43","0.30":"44","0.31":"45","0.32":"45","0.33":"45","0.34":"45","0.35":"45","0.36":"47","0.37":"49","1.0":"49","1.1":"50","1.2":"51","1.3":"52","1.4":"53","1.5":"54","1.6":"56","1.7":"58","1.8":"59","2.0":"61","2.1":"61","3.0":"66","3.1":"66","4.0":"69","4.1":"69","4.2":"69","5.0":"73","6.0":"76","6.1":"76","7.0":"78","7.1":"78","7.2":"78","7.3":"78","8.0":"80","8.1":"80","8.2":"80","8.3":"80","8.4":"80","8.5":"80","9.0":"83","9.1":"83","9.2":"83","9.3":"83","9.4":"83","10.0":"85","10.1":"85","10.2":"85","10.3":"85","10.4":"85","11.0":"87","11.1":"87","11.2":"87","11.3":"87","11.4":"87","11.5":"87","12.0":"89","12.1":"89","12.2":"89","13.0":"91","13.1":"91","13.2":"91","13.3":"91","13.4":"91","13.5":"91","13.6":"91","14.0":"93","14.1":"93","14.2":"93","15.0":"94","15.1":"94","15.2":"94","15.3":"94","15.4":"94","15.5":"94","16.0":"96","16.1":"96","16.2":"96","17.0":"98","17.1":"98","17.2":"98","17.3":"98","17.4":"98","18.0":"100","18.1":"100","18.2":"100","18.3":"100","19.0":"102","19.1":"102","20.0":"104","20.1":"104","20.2":"104","20.3":"104","21.0":"106","21.1":"106","21.2":"106","21.3":"106","21.4":"106","22.0":"108","22.1":"108","22.2":"108","22.3":"108","23.0":"110","23.1":"110","23.2":"110","23.3":"110","24.0":"112","24.1":"112","24.2":"112","24.3":"112","24.4":"112","24.5":"112","24.6":"112","24.7":"112","24.8":"112","25.0":"114","25.1":"114","25.2":"114","25.3":"114","25.4":"114","25.5":"114","25.6":"114","25.7":"114","25.8":"114","25.9":"114","26.0":"116","26.1":"116","26.2":"116","26.3":"116","26.4":"116","26.5":"116","26.6":"116","27.0":"118","27.1":"118","27.2":"118","27.3":"118","28.0":"120","28.1":"120","28.2":"120","28.3":"120","29.0":"122","29.1":"122","29.2":"122","29.3":"122","29.4":"122","30.0":"124","30.1":"124","30.2":"124","30.3":"124","30.4":"124","30.5":"124","31.0":"126","31.1":"126","31.2":"126","31.3":"126","31.4":"126","31.5":"126","31.6":"126","31.7":"126","32.0":"128","32.1":"128","32.2":"128","32.3":"128","33.0":"130","33.1":"130","33.2":"130","33.3":"130","33.4":"130","34.0":"132","34.1":"132","34.2":"132","34.3":"132","34.4":"132","34.5":"132","35.0":"134","35.1":"134","35.2":"134","35.3":"134","35.4":"134","35.5":"134","35.6":"134","35.7":"134","36.0":"136","36.1":"136","36.2":"136","36.3":"136","36.4":"136","36.5":"136","36.6":"136","36.7":"136","36.8":"136","36.9":"136","37.0":"138","37.1":"138","37.2":"138","37.3":"138","37.4":"138","37.5":"138","37.6":"138","37.7":"138","37.8":"138","37.9":"138","37.10":"138","38.0":"140","38.1":"140","38.2":"140","38.3":"140","38.4":"140","38.5":"140","38.6":"140","38.7":"140","38.8":"140","39.0":"142","39.1":"142","39.2":"142","39.3":"142","39.4":"142","39.5":"142","39.6":"142","39.7":"142","39.8":"142","40.0":"144","40.1":"144","40.2":"144","40.3":"144","40.4":"144","40.5":"144","40.6":"144","40.7":"144","40.8":"144","41.0":"146"}```

----

# frontend/node_modules/escalade/package.json
```json
{
  "name": "escalade",
  "version": "3.2.0",
  "repository": "lukeed/escalade",
  "description": "A tiny (183B to 210B) and fast utility to ascend parent directories",
  "module": "dist/index.mjs",
  "main": "dist/index.js",
  "types": "index.d.ts",
  "license": "MIT",
  "author": {
    "name": "Luke Edwards",
    "email": "luke.edwards05@gmail.com",
    "url": "https://lukeed.com"
  },
  "exports": {
    ".": [
      {
        "import": {
          "types": "./index.d.mts",
          "default": "./dist/index.mjs"
        },
        "require": {
          "types": "./index.d.ts",
          "default": "./dist/index.js"
        }
      },
      "./dist/index.js"
    ],
    "./sync": [
      {
        "import": {
          "types": "./sync/index.d.mts",
          "default": "./sync/index.mjs"
        },
        "require": {
          "types": "./sync/index.d.ts",
          "default": "./sync/index.js"
        }
      },
      "./sync/index.js"
    ]
  },
  "files": [
    "*.d.mts",
    "*.d.ts",
    "dist",
    "sync"
  ],
  "modes": {
    "sync": "src/sync.js",
    "default": "src/async.js"
  },
  "engines": {
    "node": ">=6"
  },
  "scripts": {
    "build": "bundt",
    "pretest": "npm run build",
    "test": "uvu -r esm test -i fixtures"
  },
  "keywords": [
    "find",
    "parent",
    "parents",
    "directory",
    "search",
    "walk"
  ],
  "devDependencies": {
    "bundt": "1.1.1",
    "esm": "3.2.25",
    "uvu": "0.3.3"
  }
}
```

----

# frontend/node_modules/gensync/package.json
```json
{
  "name": "gensync",
  "version": "1.0.0-beta.2",
  "license": "MIT",
  "description": "Allows users to use generators in order to write common functions that can be both sync or async.",
  "main": "index.js",
  "author": "Logan Smyth <loganfsmyth@gmail.com>",
  "homepage": "https://github.com/loganfsmyth/gensync",
  "repository": {
    "type": "git",
    "url": "https://github.com/loganfsmyth/gensync.git"
  },
  "scripts": {
    "test": "jest"
  },
  "engines": {
    "node": ">=6.9.0"
  },
  "keywords": [
    "async",
    "sync",
    "generators",
    "async-await",
    "callbacks"
  ],
  "devDependencies": {
    "babel-core": "^6.26.3",
    "babel-preset-env": "^1.6.1",
    "eslint": "^4.19.1",
    "eslint-config-prettier": "^2.9.0",
    "eslint-plugin-node": "^6.0.1",
    "eslint-plugin-prettier": "^2.6.0",
    "flow-bin": "^0.71.0",
    "jest": "^22.4.3",
    "prettier": "^1.12.1"
  }
}
```

----

# frontend/node_modules/js-tokens/package.json
```json
{
  "name": "js-tokens",
  "version": "4.0.0",
  "author": "Simon Lydell",
  "license": "MIT",
  "description": "A regex that tokenizes JavaScript.",
  "keywords": [
    "JavaScript",
    "js",
    "token",
    "tokenize",
    "regex"
  ],
  "files": [
    "index.js"
  ],
  "repository": "lydell/js-tokens",
  "scripts": {
    "test": "mocha --ui tdd",
    "esprima-compare": "node esprima-compare ./index.js everything.js/es5.js",
    "build": "node generate-index.js",
    "dev": "npm run build && npm test"
  },
  "devDependencies": {
    "coffeescript": "2.1.1",
    "esprima": "4.0.0",
    "everything.js": "1.0.3",
    "mocha": "5.0.0"
  }
}
```

----

# frontend/node_modules/jsesc/package.json
```json
{
  "name": "jsesc",
  "version": "3.1.0",
  "description": "Given some data, jsesc returns the shortest possible stringified & ASCII-safe representation of that data.",
  "homepage": "https://mths.be/jsesc",
  "engines": {
    "node": ">=6"
  },
  "main": "jsesc.js",
  "bin": "bin/jsesc",
  "man": "man/jsesc.1",
  "keywords": [
    "buffer",
    "escape",
    "javascript",
    "json",
    "map",
    "set",
    "string",
    "stringify",
    "tool"
  ],
  "license": "MIT",
  "author": {
    "name": "Mathias Bynens",
    "url": "https://mathiasbynens.be/"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/mathiasbynens/jsesc.git"
  },
  "bugs": "https://github.com/mathiasbynens/jsesc/issues",
  "files": [
    "LICENSE-MIT.txt",
    "jsesc.js",
    "bin/",
    "man/"
  ],
  "scripts": {
    "build": "grunt template",
    "coveralls": "istanbul cover --verbose --dir 'coverage' 'tests/tests.js' && coveralls < coverage/lcov.info'",
    "cover": "istanbul cover --report 'html' --verbose --dir 'coverage' 'tests/tests.js'",
    "test": "mocha tests"
  },
  "devDependencies": {
    "coveralls": "^2.11.6",
    "grunt": "^0.4.5",
    "grunt-cli": "^1.3.2",
    "grunt-template": "^0.2.3",
    "istanbul": "^0.4.2",
    "mocha": "^5.2.0",
    "regenerate": "^1.3.0",
    "requirejs": "^2.1.22",
    "unicode-13.0.0": "0.8.0"
  }
}
```

----

# frontend/node_modules/json5/package.json
```json
{
  "name": "json5",
  "version": "2.2.3",
  "description": "JSON for Humans",
  "main": "lib/index.js",
  "module": "dist/index.mjs",
  "bin": "lib/cli.js",
  "browser": "dist/index.js",
  "types": "lib/index.d.ts",
  "files": [
    "lib/",
    "dist/"
  ],
  "engines": {
    "node": ">=6"
  },
  "scripts": {
    "build": "rollup -c",
    "build-package": "node build/package.js",
    "build-unicode": "node build/unicode.js",
    "coverage": "tap --coverage-report html test",
    "lint": "eslint --fix .",
    "lint-report": "eslint .",
    "prepublishOnly": "npm run production",
    "preversion": "npm run production",
    "production": "run-s test build",
    "tap": "tap -Rspec --100 test",
    "test": "run-s lint-report tap",
    "version": "npm run build-package && git add package.json5"
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/json5/json5.git"
  },
  "keywords": [
    "json",
    "json5",
    "es5",
    "es2015",
    "ecmascript"
  ],
  "author": "Aseem Kishore <aseem.kishore@gmail.com>",
  "contributors": [
    "Max Nanasy <max.nanasy@gmail.com>",
    "Andrew Eisenberg <andrew@eisenberg.as>",
    "Jordan Tucker <jordanbtucker@gmail.com>"
  ],
  "license": "MIT",
  "bugs": {
    "url": "https://github.com/json5/json5/issues"
  },
  "homepage": "http://json5.org/",
  "devDependencies": {
    "core-js": "^2.6.5",
    "eslint": "^5.15.3",
    "eslint-config-standard": "^12.0.0",
    "eslint-plugin-import": "^2.16.0",
    "eslint-plugin-node": "^8.0.1",
    "eslint-plugin-promise": "^4.0.1",
    "eslint-plugin-standard": "^4.0.0",
    "npm-run-all": "^4.1.5",
    "regenerate": "^1.4.0",
    "rollup": "^0.64.1",
    "rollup-plugin-buble": "^0.19.6",
    "rollup-plugin-commonjs": "^9.2.1",
    "rollup-plugin-node-resolve": "^3.4.0",
    "rollup-plugin-terser": "^1.0.1",
    "sinon": "^6.3.5",
    "tap": "^12.6.0",
    "unicode-10.0.0": "^0.7.5"
  }
}
```

----

# frontend/node_modules/loose-envify/package.json
```json
{
  "name": "loose-envify",
  "version": "1.4.0",
  "description": "Fast (and loose) selective `process.env` replacer using js-tokens instead of an AST",
  "keywords": [
    "environment",
    "variables",
    "browserify",
    "browserify-transform",
    "transform",
    "source",
    "configuration"
  ],
  "homepage": "https://github.com/zertosh/loose-envify",
  "license": "MIT",
  "author": "Andres Suarez <zertosh@gmail.com>",
  "main": "index.js",
  "bin": {
    "loose-envify": "cli.js"
  },
  "repository": {
    "type": "git",
    "url": "git://github.com/zertosh/loose-envify.git"
  },
  "scripts": {
    "test": "tap test/*.js"
  },
  "dependencies": {
    "js-tokens": "^3.0.0 || ^4.0.0"
  },
  "devDependencies": {
    "browserify": "^13.1.1",
    "envify": "^3.4.0",
    "tap": "^8.0.0"
  }
}
```

----

# frontend/node_modules/lru-cache/package.json
```json
{
  "name": "lru-cache",
  "description": "A cache object that deletes the least-recently-used items.",
  "version": "5.1.1",
  "author": "Isaac Z. Schlueter <i@izs.me>",
  "keywords": [
    "mru",
    "lru",
    "cache"
  ],
  "scripts": {
    "test": "tap test/*.js --100 -J",
    "snap": "TAP_SNAPSHOT=1 tap test/*.js -J",
    "coveragerport": "tap --coverage-report=html",
    "preversion": "npm test",
    "postversion": "npm publish",
    "postpublish": "git push origin --all; git push origin --tags"
  },
  "main": "index.js",
  "repository": "git://github.com/isaacs/node-lru-cache.git",
  "devDependencies": {
    "benchmark": "^2.1.4",
    "tap": "^12.1.0"
  },
  "license": "ISC",
  "dependencies": {
    "yallist": "^3.0.2"
  },
  "files": [
    "index.js"
  ]
}
```

----

# frontend/node_modules/lucide-react/package.json
```json
{
  "name": "lucide-react",
  "description": "A Lucide icon library package for React applications.",
  "version": "0.577.0",
  "license": "ISC",
  "homepage": "https://lucide.dev",
  "bugs": "https://github.com/lucide-icons/lucide/issues",
  "repository": {
    "type": "git",
    "url": "https://github.com/lucide-icons/lucide.git",
    "directory": "packages/lucide-react"
  },
  "keywords": [
    "Lucide",
    "React",
    "Feather",
    "Icons",
    "Icon",
    "SVG",
    "Feather Icons",
    "Fontawesome",
    "Font Awesome"
  ],
  "author": "Eric Fennis",
  "amdName": "lucide-react",
  "main": "dist/cjs/lucide-react.js",
  "main:umd": "dist/umd/lucide-react.js",
  "module": "dist/esm/lucide-react.js",
  "unpkg": "dist/umd/lucide-react.min.js",
  "typings": "dist/lucide-react.d.ts",
  "sideEffects": false,
  "files": [
    "dist",
    "dynamic.mjs",
    "dynamic.js.map",
    "dynamic.d.ts",
    "dynamicIconImports.mjs",
    "dynamicIconImports.js.map",
    "dynamicIconImports.d.ts"
  ],
  "devDependencies": {
    "@testing-library/jest-dom": "^6.8.0",
    "@testing-library/react": "^14.1.2",
    "@types/react": "^18.2.37",
    "@vitejs/plugin-react": "^4.4.1",
    "jest-serializer-html": "^7.1.0",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "rollup": "^4.59.0",
    "rollup-plugin-dts": "^6.2.3",
    "rollup-plugin-preserve-directives": "^0.4.0",
    "typescript": "^5.8.3",
    "vite": "^7.2.4",
    "vitest": "^4.0.12",
    "@lucide/build-icons": "1.1.0",
    "@lucide/rollup-plugins": "1.0.0",
    "@lucide/shared": "1.0.0"
  },
  "peerDependencies": {
    "react": "^16.5.1 || ^17.0.0 || ^18.0.0 || ^19.0.0"
  },
  "scripts": {
    "build": "pnpm clean && pnpm copy:license && pnpm build:icons && pnpm typecheck && pnpm build:bundles",
    "copy:license": "cp ../../LICENSE ./LICENSE",
    "clean": "rm -rf dist && rm -rf stats && rm -rf ./src/icons/*.ts && rm -f dynamic.* && rm -f dynamicIconImports.d.ts",
    "build:icons": "build-icons --output=./src --templateSrc=./scripts/exportTemplate.mts --renderUniqueKey --withAliases --withDynamicImports --separateAliasesFile --separateAliasesFileIgnore=fingerprint --aliasesFileExtension=.ts --iconFileExtension=.ts --exportFileName=index.ts",
    "build:bundles": "rollup -c ./rollup.config.mjs",
    "typecheck": "tsc",
    "typecheck:watch": "tsc -w",
    "test": "pnpm build:icons && vitest run",
    "test:watch": "vitest watch",
    "version": "pnpm version --git-tag-version=false"
  }
}```

----

# frontend/node_modules/ms/package.json
```json
{
  "name": "ms",
  "version": "2.1.3",
  "description": "Tiny millisecond conversion utility",
  "repository": "vercel/ms",
  "main": "./index",
  "files": [
    "index.js"
  ],
  "scripts": {
    "precommit": "lint-staged",
    "lint": "eslint lib/* bin/*",
    "test": "mocha tests.js"
  },
  "eslintConfig": {
    "extends": "eslint:recommended",
    "env": {
      "node": true,
      "es6": true
    }
  },
  "lint-staged": {
    "*.js": [
      "npm run lint",
      "prettier --single-quote --write",
      "git add"
    ]
  },
  "license": "MIT",
  "devDependencies": {
    "eslint": "4.18.2",
    "expect.js": "0.3.1",
    "husky": "0.14.3",
    "lint-staged": "5.0.0",
    "mocha": "4.0.1",
    "prettier": "2.0.5"
  }
}
```

----

# frontend/node_modules/nanoid/async/package.json
```json
{
  "type": "module",
  "main": "index.cjs",
  "module": "index.js",
  "react-native": {
    "./index.js": "./index.native.js"
  },
  "browser": {
    "./index.js": "./index.browser.js",
    "./index.cjs": "./index.browser.cjs"
  }
}```

----

# frontend/node_modules/nanoid/non-secure/package.json
```json
{
  "type": "module",
  "main": "index.cjs",
  "module": "index.js",
  "react-native": "index.js"
}```

----

# frontend/node_modules/nanoid/package.json
```json
{
  "name": "nanoid",
  "version": "3.3.11",
  "description": "A tiny (116 bytes), secure URL-friendly unique string ID generator",
  "keywords": [
    "uuid",
    "random",
    "id",
    "url"
  ],
  "engines": {
    "node": "^10 || ^12 || ^13.7 || ^14 || >=15.0.1"
  },
  "funding": [
    {
      "type": "github",
      "url": "https://github.com/sponsors/ai"
    }
  ],
  "author": "Andrey Sitnik <andrey@sitnik.ru>",
  "license": "MIT",
  "repository": "ai/nanoid",
  "browser": {
    "./index.js": "./index.browser.js",
    "./async/index.js": "./async/index.browser.js",
    "./async/index.cjs": "./async/index.browser.cjs",
    "./index.cjs": "./index.browser.cjs"
  },
  "react-native": "index.js",
  "bin": "./bin/nanoid.cjs",
  "sideEffects": false,
  "types": "./index.d.ts",
  "type": "module",
  "main": "index.cjs",
  "module": "index.js",
  "exports": {
    ".": {
      "react-native": "./index.browser.js",
      "browser": "./index.browser.js",
      "require": {
        "types": "./index.d.cts",
        "default": "./index.cjs"
      },
      "import": {
        "types": "./index.d.ts",
        "default": "./index.js"
      },
      "default": "./index.js"
    },
    "./package.json": "./package.json",
    "./async/package.json": "./async/package.json",
    "./async": {
      "browser": "./async/index.browser.js",
      "require": {
        "types": "./index.d.cts",
        "default": "./async/index.cjs"
      },
      "import": {
        "types": "./index.d.ts",
        "default": "./async/index.js"
      },
      "default": "./async/index.js"
    },
    "./non-secure/package.json": "./non-secure/package.json",
    "./non-secure": {
      "require": {
        "types": "./index.d.cts",
        "default": "./non-secure/index.cjs"
      },
      "import": {
        "types": "./index.d.ts",
        "default": "./non-secure/index.js"
      },
      "default": "./non-secure/index.js"
    },
    "./url-alphabet/package.json": "./url-alphabet/package.json",
    "./url-alphabet": {
      "require": {
        "types": "./index.d.cts",
        "default": "./url-alphabet/index.cjs"
      },
      "import": {
        "types": "./index.d.ts",
        "default": "./url-alphabet/index.js"
      },
      "default": "./url-alphabet/index.js"
    }
  }
}
```

----

# frontend/node_modules/nanoid/url-alphabet/package.json
```json
{
  "type": "module",
  "main": "index.cjs",
  "module": "index.js",
  "react-native": "index.js"
}```

----

# frontend/node_modules/node-releases/data/processed/envs.json
```json
[{"name":"nodejs","version":"0.2.0","date":"2011-08-26","lts":false,"security":false,"v8":"2.3.8.0"},{"name":"nodejs","version":"0.3.0","date":"2011-08-26","lts":false,"security":false,"v8":"2.5.1.0"},{"name":"nodejs","version":"0.4.0","date":"2011-08-26","lts":false,"security":false,"v8":"3.1.2.0"},{"name":"nodejs","version":"0.5.0","date":"2011-08-26","lts":false,"security":false,"v8":"3.1.8.25"},{"name":"nodejs","version":"0.6.0","date":"2011-11-04","lts":false,"security":false,"v8":"3.6.6.6"},{"name":"nodejs","version":"0.7.0","date":"2012-01-17","lts":false,"security":false,"v8":"3.8.6.0"},{"name":"nodejs","version":"0.8.0","date":"2012-06-22","lts":false,"security":false,"v8":"3.11.10.10"},{"name":"nodejs","version":"0.9.0","date":"2012-07-20","lts":false,"security":false,"v8":"3.11.10.15"},{"name":"nodejs","version":"0.10.0","date":"2013-03-11","lts":false,"security":false,"v8":"3.14.5.8"},{"name":"nodejs","version":"0.11.0","date":"2013-03-28","lts":false,"security":false,"v8":"3.17.13.0"},{"name":"nodejs","version":"0.12.0","date":"2015-02-06","lts":false,"security":false,"v8":"3.28.73.0"},{"name":"nodejs","version":"4.0.0","date":"2015-09-08","lts":false,"security":false,"v8":"4.5.103.30"},{"name":"nodejs","version":"4.1.0","date":"2015-09-17","lts":false,"security":false,"v8":"4.5.103.33"},{"name":"nodejs","version":"4.2.0","date":"2015-10-12","lts":"Argon","security":false,"v8":"4.5.103.35"},{"name":"nodejs","version":"4.3.0","date":"2016-02-09","lts":"Argon","security":false,"v8":"4.5.103.35"},{"name":"nodejs","version":"4.4.0","date":"2016-03-08","lts":"Argon","security":false,"v8":"4.5.103.35"},{"name":"nodejs","version":"4.5.0","date":"2016-08-16","lts":"Argon","security":false,"v8":"4.5.103.37"},{"name":"nodejs","version":"4.6.0","date":"2016-09-27","lts":"Argon","security":true,"v8":"4.5.103.37"},{"name":"nodejs","version":"4.7.0","date":"2016-12-06","lts":"Argon","security":false,"v8":"4.5.103.43"},{"name":"nodejs","version":"4.8.0","date":"2017-02-21","lts":"Argon","security":false,"v8":"4.5.103.45"},{"name":"nodejs","version":"4.9.0","date":"2018-03-28","lts":"Argon","security":true,"v8":"4.5.103.53"},{"name":"nodejs","version":"5.0.0","date":"2015-10-29","lts":false,"security":false,"v8":"4.6.85.28"},{"name":"nodejs","version":"5.1.0","date":"2015-11-17","lts":false,"security":false,"v8":"4.6.85.31"},{"name":"nodejs","version":"5.2.0","date":"2015-12-09","lts":false,"security":false,"v8":"4.6.85.31"},{"name":"nodejs","version":"5.3.0","date":"2015-12-15","lts":false,"security":false,"v8":"4.6.85.31"},{"name":"nodejs","version":"5.4.0","date":"2016-01-06","lts":false,"security":false,"v8":"4.6.85.31"},{"name":"nodejs","version":"5.5.0","date":"2016-01-21","lts":false,"security":false,"v8":"4.6.85.31"},{"name":"nodejs","version":"5.6.0","date":"2016-02-09","lts":false,"security":false,"v8":"4.6.85.31"},{"name":"nodejs","version":"5.7.0","date":"2016-02-23","lts":false,"security":false,"v8":"4.6.85.31"},{"name":"nodejs","version":"5.8.0","date":"2016-03-09","lts":false,"security":false,"v8":"4.6.85.31"},{"name":"nodejs","version":"5.9.0","date":"2016-03-16","lts":false,"security":false,"v8":"4.6.85.31"},{"name":"nodejs","version":"5.10.0","date":"2016-04-01","lts":false,"security":false,"v8":"4.6.85.31"},{"name":"nodejs","version":"5.11.0","date":"2016-04-21","lts":false,"security":false,"v8":"4.6.85.31"},{"name":"nodejs","version":"5.12.0","date":"2016-06-23","lts":false,"security":false,"v8":"4.6.85.32"},{"name":"nodejs","version":"6.0.0","date":"2016-04-26","lts":false,"security":false,"v8":"5.0.71.35"},{"name":"nodejs","version":"6.1.0","date":"2016-05-05","lts":false,"security":false,"v8":"5.0.71.35"},{"name":"nodejs","version":"6.2.0","date":"2016-05-17","lts":false,"security":false,"v8":"5.0.71.47"},{"name":"nodejs","version":"6.3.0","date":"2016-07-06","lts":false,"security":false,"v8":"5.0.71.52"},{"name":"nodejs","version":"6.4.0","date":"2016-08-12","lts":false,"security":false,"v8":"5.0.71.60"},{"name":"nodejs","version":"6.5.0","date":"2016-08-26","lts":false,"security":false,"v8":"5.1.281.81"},{"name":"nodejs","version":"6.6.0","date":"2016-09-14","lts":false,"security":false,"v8":"5.1.281.83"},{"name":"nodejs","version":"6.7.0","date":"2016-09-27","lts":false,"security":true,"v8":"5.1.281.83"},{"name":"nodejs","version":"6.8.0","date":"2016-10-12","lts":false,"security":false,"v8":"5.1.281.84"},{"name":"nodejs","version":"6.9.0","date":"2016-10-18","lts":"Boron","security":false,"v8":"5.1.281.84"},{"name":"nodejs","version":"6.10.0","date":"2017-02-21","lts":"Boron","security":false,"v8":"5.1.281.93"},{"name":"nodejs","version":"6.11.0","date":"2017-06-06","lts":"Boron","security":false,"v8":"5.1.281.102"},{"name":"nodejs","version":"6.12.0","date":"2017-11-06","lts":"Boron","security":false,"v8":"5.1.281.108"},{"name":"nodejs","version":"6.13.0","date":"2018-02-10","lts":"Boron","security":false,"v8":"5.1.281.111"},{"name":"nodejs","version":"6.14.0","date":"2018-03-28","lts":"Boron","security":true,"v8":"5.1.281.111"},{"name":"nodejs","version":"6.15.0","date":"2018-11-27","lts":"Boron","security":true,"v8":"5.1.281.111"},{"name":"nodejs","version":"6.16.0","date":"2018-12-26","lts":"Boron","security":false,"v8":"5.1.281.111"},{"name":"nodejs","version":"6.17.0","date":"2019-02-28","lts":"Boron","security":true,"v8":"5.1.281.111"},{"name":"nodejs","version":"7.0.0","date":"2016-10-25","lts":false,"security":false,"v8":"5.4.500.36"},{"name":"nodejs","version":"7.1.0","date":"2016-11-08","lts":false,"security":false,"v8":"5.4.500.36"},{"name":"nodejs","version":"7.2.0","date":"2016-11-22","lts":false,"security":false,"v8":"5.4.500.43"},{"name":"nodejs","version":"7.3.0","date":"2016-12-20","lts":false,"security":false,"v8":"5.4.500.45"},{"name":"nodejs","version":"7.4.0","date":"2017-01-04","lts":false,"security":false,"v8":"5.4.500.45"},{"name":"nodejs","version":"7.5.0","date":"2017-01-31","lts":false,"security":false,"v8":"5.4.500.48"},{"name":"nodejs","version":"7.6.0","date":"2017-02-21","lts":false,"security":false,"v8":"5.5.372.40"},{"name":"nodejs","version":"7.7.0","date":"2017-02-28","lts":false,"security":false,"v8":"5.5.372.41"},{"name":"nodejs","version":"7.8.0","date":"2017-03-29","lts":false,"security":false,"v8":"5.5.372.43"},{"name":"nodejs","version":"7.9.0","date":"2017-04-11","lts":false,"security":false,"v8":"5.5.372.43"},{"name":"nodejs","version":"7.10.0","date":"2017-05-02","lts":false,"security":false,"v8":"5.5.372.43"},{"name":"nodejs","version":"8.0.0","date":"2017-05-30","lts":false,"security":false,"v8":"5.8.283.41"},{"name":"nodejs","version":"8.1.0","date":"2017-06-08","lts":false,"security":false,"v8":"5.8.283.41"},{"name":"nodejs","version":"8.2.0","date":"2017-07-19","lts":false,"security":false,"v8":"5.8.283.41"},{"name":"nodejs","version":"8.3.0","date":"2017-08-08","lts":false,"security":false,"v8":"6.0.286.52"},{"name":"nodejs","version":"8.4.0","date":"2017-08-15","lts":false,"security":false,"v8":"6.0.286.52"},{"name":"nodejs","version":"8.5.0","date":"2017-09-12","lts":false,"security":false,"v8":"6.0.287.53"},{"name":"nodejs","version":"8.6.0","date":"2017-09-26","lts":false,"security":false,"v8":"6.0.287.53"},{"name":"nodejs","version":"8.7.0","date":"2017-10-11","lts":false,"security":false,"v8":"6.1.534.42"},{"name":"nodejs","version":"8.8.0","date":"2017-10-24","lts":false,"security":false,"v8":"6.1.534.42"},{"name":"nodejs","version":"8.9.0","date":"2017-10-31","lts":"Carbon","security":false,"v8":"6.1.534.46"},{"name":"nodejs","version":"8.10.0","date":"2018-03-06","lts":"Carbon","security":false,"v8":"6.2.414.50"},{"name":"nodejs","version":"8.11.0","date":"2018-03-28","lts":"Carbon","security":true,"v8":"6.2.414.50"},{"name":"nodejs","version":"8.12.0","date":"2018-09-10","lts":"Carbon","security":false,"v8":"6.2.414.66"},{"name":"nodejs","version":"8.13.0","date":"2018-11-20","lts":"Carbon","security":false,"v8":"6.2.414.72"},{"name":"nodejs","version":"8.14.0","date":"2018-11-27","lts":"Carbon","security":true,"v8":"6.2.414.72"},{"name":"nodejs","version":"8.15.0","date":"2018-12-26","lts":"Carbon","security":false,"v8":"6.2.414.75"},{"name":"nodejs","version":"8.16.0","date":"2019-04-16","lts":"Carbon","security":false,"v8":"6.2.414.77"},{"name":"nodejs","version":"8.17.0","date":"2019-12-17","lts":"Carbon","security":true,"v8":"6.2.414.78"},{"name":"nodejs","version":"9.0.0","date":"2017-10-31","lts":false,"security":false,"v8":"6.2.414.32"},{"name":"nodejs","version":"9.1.0","date":"2017-11-07","lts":false,"security":false,"v8":"6.2.414.32"},{"name":"nodejs","version":"9.2.0","date":"2017-11-14","lts":false,"security":false,"v8":"6.2.414.44"},{"name":"nodejs","version":"9.3.0","date":"2017-12-12","lts":false,"security":false,"v8":"6.2.414.46"},{"name":"nodejs","version":"9.4.0","date":"2018-01-10","lts":false,"security":false,"v8":"6.2.414.46"},{"name":"nodejs","version":"9.5.0","date":"2018-01-31","lts":false,"security":false,"v8":"6.2.414.46"},{"name":"nodejs","version":"9.6.0","date":"2018-02-21","lts":false,"security":false,"v8":"6.2.414.46"},{"name":"nodejs","version":"9.7.0","date":"2018-03-01","lts":false,"security":false,"v8":"6.2.414.46"},{"name":"nodejs","version":"9.8.0","date":"2018-03-07","lts":false,"security":false,"v8":"6.2.414.46"},{"name":"nodejs","version":"9.9.0","date":"2018-03-21","lts":false,"security":false,"v8":"6.2.414.46"},{"name":"nodejs","version":"9.10.0","date":"2018-03-28","lts":false,"security":true,"v8":"6.2.414.46"},{"name":"nodejs","version":"9.11.0","date":"2018-04-04","lts":false,"security":false,"v8":"6.2.414.46"},{"name":"nodejs","version":"10.0.0","date":"2018-04-24","lts":false,"security":false,"v8":"6.6.346.24"},{"name":"nodejs","version":"10.1.0","date":"2018-05-08","lts":false,"security":false,"v8":"6.6.346.27"},{"name":"nodejs","version":"10.2.0","date":"2018-05-23","lts":false,"security":false,"v8":"6.6.346.32"},{"name":"nodejs","version":"10.3.0","date":"2018-05-29","lts":false,"security":false,"v8":"6.6.346.32"},{"name":"nodejs","version":"10.4.0","date":"2018-06-06","lts":false,"security":false,"v8":"6.7.288.43"},{"name":"nodejs","version":"10.5.0","date":"2018-06-20","lts":false,"security":false,"v8":"6.7.288.46"},{"name":"nodejs","version":"10.6.0","date":"2018-07-04","lts":false,"security":false,"v8":"6.7.288.46"},{"name":"nodejs","version":"10.7.0","date":"2018-07-18","lts":false,"security":false,"v8":"6.7.288.49"},{"name":"nodejs","version":"10.8.0","date":"2018-08-01","lts":false,"security":false,"v8":"6.7.288.49"},{"name":"nodejs","version":"10.9.0","date":"2018-08-15","lts":false,"security":false,"v8":"6.8.275.24"},{"name":"nodejs","version":"10.10.0","date":"2018-09-06","lts":false,"security":false,"v8":"6.8.275.30"},{"name":"nodejs","version":"10.11.0","date":"2018-09-19","lts":false,"security":false,"v8":"6.8.275.32"},{"name":"nodejs","version":"10.12.0","date":"2018-10-10","lts":false,"security":false,"v8":"6.8.275.32"},{"name":"nodejs","version":"10.13.0","date":"2018-10-30","lts":"Dubnium","security":false,"v8":"6.8.275.32"},{"name":"nodejs","version":"10.14.0","date":"2018-11-27","lts":"Dubnium","security":true,"v8":"6.8.275.32"},{"name":"nodejs","version":"10.15.0","date":"2018-12-26","lts":"Dubnium","security":false,"v8":"6.8.275.32"},{"name":"nodejs","version":"10.16.0","date":"2019-05-28","lts":"Dubnium","security":false,"v8":"6.8.275.32"},{"name":"nodejs","version":"10.17.0","date":"2019-10-22","lts":"Dubnium","security":false,"v8":"6.8.275.32"},{"name":"nodejs","version":"10.18.0","date":"2019-12-17","lts":"Dubnium","security":true,"v8":"6.8.275.32"},{"name":"nodejs","version":"10.19.0","date":"2020-02-05","lts":"Dubnium","security":true,"v8":"6.8.275.32"},{"name":"nodejs","version":"10.20.0","date":"2020-03-26","lts":"Dubnium","security":false,"v8":"6.8.275.32"},{"name":"nodejs","version":"10.21.0","date":"2020-06-02","lts":"Dubnium","security":true,"v8":"6.8.275.32"},{"name":"nodejs","version":"10.22.0","date":"2020-07-21","lts":"Dubnium","security":false,"v8":"6.8.275.32"},{"name":"nodejs","version":"10.23.0","date":"2020-10-27","lts":"Dubnium","security":false,"v8":"6.8.275.32"},{"name":"nodejs","version":"10.24.0","date":"2021-02-23","lts":"Dubnium","security":true,"v8":"6.8.275.32"},{"name":"nodejs","version":"11.0.0","date":"2018-10-23","lts":false,"security":false,"v8":"7.0.276.28"},{"name":"nodejs","version":"11.1.0","date":"2018-10-30","lts":false,"security":false,"v8":"7.0.276.32"},{"name":"nodejs","version":"11.2.0","date":"2018-11-15","lts":false,"security":false,"v8":"7.0.276.38"},{"name":"nodejs","version":"11.3.0","date":"2018-11-27","lts":false,"security":true,"v8":"7.0.276.38"},{"name":"nodejs","version":"11.4.0","date":"2018-12-07","lts":false,"security":false,"v8":"7.0.276.38"},{"name":"nodejs","version":"11.5.0","date":"2018-12-18","lts":false,"security":false,"v8":"7.0.276.38"},{"name":"nodejs","version":"11.6.0","date":"2018-12-26","lts":false,"security":false,"v8":"7.0.276.38"},{"name":"nodejs","version":"11.7.0","date":"2019-01-17","lts":false,"security":false,"v8":"7.0.276.38"},{"name":"nodejs","version":"11.8.0","date":"2019-01-24","lts":false,"security":false,"v8":"7.0.276.38"},{"name":"nodejs","version":"11.9.0","date":"2019-01-30","lts":false,"security":false,"v8":"7.0.276.38"},{"name":"nodejs","version":"11.10.0","date":"2019-02-14","lts":false,"security":false,"v8":"7.0.276.38"},{"name":"nodejs","version":"11.11.0","date":"2019-03-05","lts":false,"security":false,"v8":"7.0.276.38"},{"name":"nodejs","version":"11.12.0","date":"2019-03-14","lts":false,"security":false,"v8":"7.0.276.38"},{"name":"nodejs","version":"11.13.0","date":"2019-03-28","lts":false,"security":false,"v8":"7.0.276.38"},{"name":"nodejs","version":"11.14.0","date":"2019-04-10","lts":false,"security":false,"v8":"7.0.276.38"},{"name":"nodejs","version":"11.15.0","date":"2019-04-30","lts":false,"security":false,"v8":"7.0.276.38"},{"name":"nodejs","version":"12.0.0","date":"2019-04-23","lts":false,"security":false,"v8":"7.4.288.21"},{"name":"nodejs","version":"12.1.0","date":"2019-04-29","lts":false,"security":false,"v8":"7.4.288.21"},{"name":"nodejs","version":"12.2.0","date":"2019-05-07","lts":false,"security":false,"v8":"7.4.288.21"},{"name":"nodejs","version":"12.3.0","date":"2019-05-21","lts":false,"security":false,"v8":"7.4.288.27"},{"name":"nodejs","version":"12.4.0","date":"2019-06-04","lts":false,"security":false,"v8":"7.4.288.27"},{"name":"nodejs","version":"12.5.0","date":"2019-06-26","lts":false,"security":false,"v8":"7.5.288.22"},{"name":"nodejs","version":"12.6.0","date":"2019-07-03","lts":false,"security":false,"v8":"7.5.288.22"},{"name":"nodejs","version":"12.7.0","date":"2019-07-23","lts":false,"security":false,"v8":"7.5.288.22"},{"name":"nodejs","version":"12.8.0","date":"2019-08-06","lts":false,"security":false,"v8":"7.5.288.22"},{"name":"nodejs","version":"12.9.0","date":"2019-08-20","lts":false,"security":false,"v8":"7.6.303.29"},{"name":"nodejs","version":"12.10.0","date":"2019-09-04","lts":false,"security":false,"v8":"7.6.303.29"},{"name":"nodejs","version":"12.11.0","date":"2019-09-25","lts":false,"security":false,"v8":"7.7.299.11"},{"name":"nodejs","version":"12.12.0","date":"2019-10-11","lts":false,"security":false,"v8":"7.7.299.13"},{"name":"nodejs","version":"12.13.0","date":"2019-10-21","lts":"Erbium","security":false,"v8":"7.7.299.13"},{"name":"nodejs","version":"12.14.0","date":"2019-12-17","lts":"Erbium","security":true,"v8":"7.7.299.13"},{"name":"nodejs","version":"12.15.0","date":"2020-02-05","lts":"Erbium","security":true,"v8":"7.7.299.13"},{"name":"nodejs","version":"12.16.0","date":"2020-02-11","lts":"Erbium","security":false,"v8":"7.8.279.23"},{"name":"nodejs","version":"12.17.0","date":"2020-05-26","lts":"Erbium","security":false,"v8":"7.8.279.23"},{"name":"nodejs","version":"12.18.0","date":"2020-06-02","lts":"Erbium","security":true,"v8":"7.8.279.23"},{"name":"nodejs","version":"12.19.0","date":"2020-10-06","lts":"Erbium","security":false,"v8":"7.8.279.23"},{"name":"nodejs","version":"12.20.0","date":"2020-11-24","lts":"Erbium","security":false,"v8":"7.8.279.23"},{"name":"nodejs","version":"12.21.0","date":"2021-02-23","lts":"Erbium","security":true,"v8":"7.8.279.23"},{"name":"nodejs","version":"12.22.0","date":"2021-03-30","lts":"Erbium","security":false,"v8":"7.8.279.23"},{"name":"nodejs","version":"13.0.0","date":"2019-10-22","lts":false,"security":false,"v8":"7.8.279.17"},{"name":"nodejs","version":"13.1.0","date":"2019-11-05","lts":false,"security":false,"v8":"7.8.279.17"},{"name":"nodejs","version":"13.2.0","date":"2019-11-21","lts":false,"security":false,"v8":"7.9.317.23"},{"name":"nodejs","version":"13.3.0","date":"2019-12-03","lts":false,"security":false,"v8":"7.9.317.25"},{"name":"nodejs","version":"13.4.0","date":"2019-12-17","lts":false,"security":true,"v8":"7.9.317.25"},{"name":"nodejs","version":"13.5.0","date":"2019-12-18","lts":false,"security":false,"v8":"7.9.317.25"},{"name":"nodejs","version":"13.6.0","date":"2020-01-07","lts":false,"security":false,"v8":"7.9.317.25"},{"name":"nodejs","version":"13.7.0","date":"2020-01-21","lts":false,"security":false,"v8":"7.9.317.25"},{"name":"nodejs","version":"13.8.0","date":"2020-02-05","lts":false,"security":true,"v8":"7.9.317.25"},{"name":"nodejs","version":"13.9.0","date":"2020-02-18","lts":false,"security":false,"v8":"7.9.317.25"},{"name":"nodejs","version":"13.10.0","date":"2020-03-04","lts":false,"security":false,"v8":"7.9.317.25"},{"name":"nodejs","version":"13.11.0","date":"2020-03-12","lts":false,"security":false,"v8":"7.9.317.25"},{"name":"nodejs","version":"13.12.0","date":"2020-03-26","lts":false,"security":false,"v8":"7.9.317.25"},{"name":"nodejs","version":"13.13.0","date":"2020-04-14","lts":false,"security":false,"v8":"7.9.317.25"},{"name":"nodejs","version":"13.14.0","date":"2020-04-29","lts":false,"security":false,"v8":"7.9.317.25"},{"name":"nodejs","version":"14.0.0","date":"2020-04-21","lts":false,"security":false,"v8":"8.1.307.30"},{"name":"nodejs","version":"14.1.0","date":"2020-04-29","lts":false,"security":false,"v8":"8.1.307.31"},{"name":"nodejs","version":"14.2.0","date":"2020-05-05","lts":false,"security":false,"v8":"8.1.307.31"},{"name":"nodejs","version":"14.3.0","date":"2020-05-19","lts":false,"security":false,"v8":"8.1.307.31"},{"name":"nodejs","version":"14.4.0","date":"2020-06-02","lts":false,"security":true,"v8":"8.1.307.31"},{"name":"nodejs","version":"14.5.0","date":"2020-06-30","lts":false,"security":false,"v8":"8.3.110.9"},{"name":"nodejs","version":"14.6.0","date":"2020-07-20","lts":false,"security":false,"v8":"8.4.371.19"},{"name":"nodejs","version":"14.7.0","date":"2020-07-29","lts":false,"security":false,"v8":"8.4.371.19"},{"name":"nodejs","version":"14.8.0","date":"2020-08-11","lts":false,"security":false,"v8":"8.4.371.19"},{"name":"nodejs","version":"14.9.0","date":"2020-08-27","lts":false,"security":false,"v8":"8.4.371.19"},{"name":"nodejs","version":"14.10.0","date":"2020-09-08","lts":false,"security":false,"v8":"8.4.371.19"},{"name":"nodejs","version":"14.11.0","date":"2020-09-15","lts":false,"security":true,"v8":"8.4.371.19"},{"name":"nodejs","version":"14.12.0","date":"2020-09-22","lts":false,"security":false,"v8":"8.4.371.19"},{"name":"nodejs","version":"14.13.0","date":"2020-09-29","lts":false,"security":false,"v8":"8.4.371.19"},{"name":"nodejs","version":"14.14.0","date":"2020-10-15","lts":false,"security":false,"v8":"8.4.371.19"},{"name":"nodejs","version":"14.15.0","date":"2020-10-27","lts":"Fermium","security":false,"v8":"8.4.371.19"},{"name":"nodejs","version":"14.16.0","date":"2021-02-23","lts":"Fermium","security":true,"v8":"8.4.371.19"},{"name":"nodejs","version":"14.17.0","date":"2021-05-11","lts":"Fermium","security":false,"v8":"8.4.371.23"},{"name":"nodejs","version":"14.18.0","date":"2021-09-28","lts":"Fermium","security":false,"v8":"8.4.371.23"},{"name":"nodejs","version":"14.19.0","date":"2022-02-01","lts":"Fermium","security":false,"v8":"8.4.371.23"},{"name":"nodejs","version":"14.20.0","date":"2022-07-07","lts":"Fermium","security":true,"v8":"8.4.371.23"},{"name":"nodejs","version":"14.21.0","date":"2022-11-01","lts":"Fermium","security":false,"v8":"8.4.371.23"},{"name":"nodejs","version":"15.0.0","date":"2020-10-20","lts":false,"security":false,"v8":"8.6.395.16"},{"name":"nodejs","version":"15.1.0","date":"2020-11-04","lts":false,"security":false,"v8":"8.6.395.17"},{"name":"nodejs","version":"15.2.0","date":"2020-11-10","lts":false,"security":false,"v8":"8.6.395.17"},{"name":"nodejs","version":"15.3.0","date":"2020-11-24","lts":false,"security":false,"v8":"8.6.395.17"},{"name":"nodejs","version":"15.4.0","date":"2020-12-09","lts":false,"security":false,"v8":"8.6.395.17"},{"name":"nodejs","version":"15.5.0","date":"2020-12-22","lts":false,"security":false,"v8":"8.6.395.17"},{"name":"nodejs","version":"15.6.0","date":"2021-01-14","lts":false,"security":false,"v8":"8.6.395.17"},{"name":"nodejs","version":"15.7.0","date":"2021-01-25","lts":false,"security":false,"v8":"8.6.395.17"},{"name":"nodejs","version":"15.8.0","date":"2021-02-02","lts":false,"security":false,"v8":"8.6.395.17"},{"name":"nodejs","version":"15.9.0","date":"2021-02-18","lts":false,"security":false,"v8":"8.6.395.17"},{"name":"nodejs","version":"15.10.0","date":"2021-02-23","lts":false,"security":true,"v8":"8.6.395.17"},{"name":"nodejs","version":"15.11.0","date":"2021-03-03","lts":false,"security":false,"v8":"8.6.395.17"},{"name":"nodejs","version":"15.12.0","date":"2021-03-17","lts":false,"security":false,"v8":"8.6.395.17"},{"name":"nodejs","version":"15.13.0","date":"2021-03-31","lts":false,"security":false,"v8":"8.6.395.17"},{"name":"nodejs","version":"15.14.0","date":"2021-04-06","lts":false,"security":false,"v8":"8.6.395.17"},{"name":"nodejs","version":"16.0.0","date":"2021-04-20","lts":false,"security":false,"v8":"9.0.257.17"},{"name":"nodejs","version":"16.1.0","date":"2021-05-04","lts":false,"security":false,"v8":"9.0.257.24"},{"name":"nodejs","version":"16.2.0","date":"2021-05-19","lts":false,"security":false,"v8":"9.0.257.25"},{"name":"nodejs","version":"16.3.0","date":"2021-06-03","lts":false,"security":false,"v8":"9.0.257.25"},{"name":"nodejs","version":"16.4.0","date":"2021-06-23","lts":false,"security":false,"v8":"9.1.269.36"},{"name":"nodejs","version":"16.5.0","date":"2021-07-14","lts":false,"security":false,"v8":"9.1.269.38"},{"name":"nodejs","version":"16.6.0","date":"2021-07-29","lts":false,"security":true,"v8":"9.2.230.21"},{"name":"nodejs","version":"16.7.0","date":"2021-08-18","lts":false,"security":false,"v8":"9.2.230.21"},{"name":"nodejs","version":"16.8.0","date":"2021-08-25","lts":false,"security":false,"v8":"9.2.230.21"},{"name":"nodejs","version":"16.9.0","date":"2021-09-07","lts":false,"security":false,"v8":"9.3.345.16"},{"name":"nodejs","version":"16.10.0","date":"2021-09-22","lts":false,"security":false,"v8":"9.3.345.19"},{"name":"nodejs","version":"16.11.0","date":"2021-10-08","lts":false,"security":false,"v8":"9.4.146.19"},{"name":"nodejs","version":"16.12.0","date":"2021-10-20","lts":false,"security":false,"v8":"9.4.146.19"},{"name":"nodejs","version":"16.13.0","date":"2021-10-26","lts":"Gallium","security":false,"v8":"9.4.146.19"},{"name":"nodejs","version":"16.14.0","date":"2022-02-08","lts":"Gallium","security":false,"v8":"9.4.146.24"},{"name":"nodejs","version":"16.15.0","date":"2022-04-26","lts":"Gallium","security":false,"v8":"9.4.146.24"},{"name":"nodejs","version":"16.16.0","date":"2022-07-07","lts":"Gallium","security":true,"v8":"9.4.146.24"},{"name":"nodejs","version":"16.17.0","date":"2022-08-16","lts":"Gallium","security":false,"v8":"9.4.146.26"},{"name":"nodejs","version":"16.18.0","date":"2022-10-12","lts":"Gallium","security":false,"v8":"9.4.146.26"},{"name":"nodejs","version":"16.19.0","date":"2022-12-13","lts":"Gallium","security":false,"v8":"9.4.146.26"},{"name":"nodejs","version":"16.20.0","date":"2023-03-28","lts":"Gallium","security":false,"v8":"9.4.146.26"},{"name":"nodejs","version":"17.0.0","date":"2021-10-19","lts":false,"security":false,"v8":"9.5.172.21"},{"name":"nodejs","version":"17.1.0","date":"2021-11-09","lts":false,"security":false,"v8":"9.5.172.25"},{"name":"nodejs","version":"17.2.0","date":"2021-11-30","lts":false,"security":false,"v8":"9.6.180.14"},{"name":"nodejs","version":"17.3.0","date":"2021-12-17","lts":false,"security":false,"v8":"9.6.180.15"},{"name":"nodejs","version":"17.4.0","date":"2022-01-18","lts":false,"security":false,"v8":"9.6.180.15"},{"name":"nodejs","version":"17.5.0","date":"2022-02-10","lts":false,"security":false,"v8":"9.6.180.15"},{"name":"nodejs","version":"17.6.0","date":"2022-02-22","lts":false,"security":false,"v8":"9.6.180.15"},{"name":"nodejs","version":"17.7.0","date":"2022-03-09","lts":false,"security":false,"v8":"9.6.180.15"},{"name":"nodejs","version":"17.8.0","date":"2022-03-22","lts":false,"security":false,"v8":"9.6.180.15"},{"name":"nodejs","version":"17.9.0","date":"2022-04-07","lts":false,"security":false,"v8":"9.6.180.15"},{"name":"nodejs","version":"18.0.0","date":"2022-04-18","lts":false,"security":false,"v8":"10.1.124.8"},{"name":"nodejs","version":"18.1.0","date":"2022-05-03","lts":false,"security":false,"v8":"10.1.124.8"},{"name":"nodejs","version":"18.2.0","date":"2022-05-17","lts":false,"security":false,"v8":"10.1.124.8"},{"name":"nodejs","version":"18.3.0","date":"2022-06-02","lts":false,"security":false,"v8":"10.2.154.4"},{"name":"nodejs","version":"18.4.0","date":"2022-06-16","lts":false,"security":false,"v8":"10.2.154.4"},{"name":"nodejs","version":"18.5.0","date":"2022-07-06","lts":false,"security":true,"v8":"10.2.154.4"},{"name":"nodejs","version":"18.6.0","date":"2022-07-13","lts":false,"security":false,"v8":"10.2.154.13"},{"name":"nodejs","version":"18.7.0","date":"2022-07-26","lts":false,"security":false,"v8":"10.2.154.13"},{"name":"nodejs","version":"18.8.0","date":"2022-08-24","lts":false,"security":false,"v8":"10.2.154.13"},{"name":"nodejs","version":"18.9.0","date":"2022-09-07","lts":false,"security":false,"v8":"10.2.154.15"},{"name":"nodejs","version":"18.10.0","date":"2022-09-28","lts":false,"security":false,"v8":"10.2.154.15"},{"name":"nodejs","version":"18.11.0","date":"2022-10-13","lts":false,"security":false,"v8":"10.2.154.15"},{"name":"nodejs","version":"18.12.0","date":"2022-10-25","lts":"Hydrogen","security":false,"v8":"10.2.154.15"},{"name":"nodejs","version":"18.13.0","date":"2023-01-05","lts":"Hydrogen","security":false,"v8":"10.2.154.23"},{"name":"nodejs","version":"18.14.0","date":"2023-02-01","lts":"Hydrogen","security":false,"v8":"10.2.154.23"},{"name":"nodejs","version":"18.15.0","date":"2023-03-05","lts":"Hydrogen","security":false,"v8":"10.2.154.26"},{"name":"nodejs","version":"18.16.0","date":"2023-04-12","lts":"Hydrogen","security":false,"v8":"10.2.154.26"},{"name":"nodejs","version":"18.17.0","date":"2023-07-18","lts":"Hydrogen","security":false,"v8":"10.2.154.26"},{"name":"nodejs","version":"18.18.0","date":"2023-09-18","lts":"Hydrogen","security":false,"v8":"10.2.154.26"},{"name":"nodejs","version":"18.19.0","date":"2023-11-29","lts":"Hydrogen","security":false,"v8":"10.2.154.26"},{"name":"nodejs","version":"18.20.0","date":"2024-03-26","lts":"Hydrogen","security":false,"v8":"10.2.154.26"},{"name":"nodejs","version":"19.0.0","date":"2022-10-17","lts":false,"security":false,"v8":"10.7.193.13"},{"name":"nodejs","version":"19.1.0","date":"2022-11-14","lts":false,"security":false,"v8":"10.7.193.20"},{"name":"nodejs","version":"19.2.0","date":"2022-11-29","lts":false,"security":false,"v8":"10.8.168.20"},{"name":"nodejs","version":"19.3.0","date":"2022-12-14","lts":false,"security":false,"v8":"10.8.168.21"},{"name":"nodejs","version":"19.4.0","date":"2023-01-05","lts":false,"security":false,"v8":"10.8.168.25"},{"name":"nodejs","version":"19.5.0","date":"2023-01-24","lts":false,"security":false,"v8":"10.8.168.25"},{"name":"nodejs","version":"19.6.0","date":"2023-02-01","lts":false,"security":false,"v8":"10.8.168.25"},{"name":"nodejs","version":"19.7.0","date":"2023-02-21","lts":false,"security":false,"v8":"10.8.168.25"},{"name":"nodejs","version":"19.8.0","date":"2023-03-14","lts":false,"security":false,"v8":"10.8.168.25"},{"name":"nodejs","version":"19.9.0","date":"2023-04-10","lts":false,"security":false,"v8":"10.8.168.25"},{"name":"nodejs","version":"20.0.0","date":"2023-04-17","lts":false,"security":false,"v8":"11.3.244.4"},{"name":"nodejs","version":"20.1.0","date":"2023-05-03","lts":false,"security":false,"v8":"11.3.244.8"},{"name":"nodejs","version":"20.2.0","date":"2023-05-16","lts":false,"security":false,"v8":"11.3.244.8"},{"name":"nodejs","version":"20.3.0","date":"2023-06-08","lts":false,"security":false,"v8":"11.3.244.8"},{"name":"nodejs","version":"20.4.0","date":"2023-07-04","lts":false,"security":false,"v8":"11.3.244.8"},{"name":"nodejs","version":"20.5.0","date":"2023-07-19","lts":false,"security":false,"v8":"11.3.244.8"},{"name":"nodejs","version":"20.6.0","date":"2023-08-23","lts":false,"security":false,"v8":"11.3.244.8"},{"name":"nodejs","version":"20.7.0","date":"2023-09-18","lts":false,"security":false,"v8":"11.3.244.8"},{"name":"nodejs","version":"20.8.0","date":"2023-09-28","lts":false,"security":false,"v8":"11.3.244.8"},{"name":"nodejs","version":"20.9.0","date":"2023-10-24","lts":"Iron","security":false,"v8":"11.3.244.8"},{"name":"nodejs","version":"20.10.0","date":"2023-11-22","lts":"Iron","security":false,"v8":"11.3.244.8"},{"name":"nodejs","version":"20.11.0","date":"2024-01-09","lts":"Iron","security":false,"v8":"11.3.244.8"},{"name":"nodejs","version":"20.12.0","date":"2024-03-26","lts":"Iron","security":false,"v8":"11.3.244.8"},{"name":"nodejs","version":"20.13.0","date":"2024-05-07","lts":"Iron","security":false,"v8":"11.3.244.8"},{"name":"nodejs","version":"20.14.0","date":"2024-05-28","lts":"Iron","security":false,"v8":"11.3.244.8"},{"name":"nodejs","version":"20.15.0","date":"2024-06-20","lts":"Iron","security":false,"v8":"11.3.244.8"},{"name":"nodejs","version":"20.16.0","date":"2024-07-24","lts":"Iron","security":false,"v8":"11.3.244.8"},{"name":"nodejs","version":"20.17.0","date":"2024-08-21","lts":"Iron","security":false,"v8":"11.3.244.8"},{"name":"nodejs","version":"20.18.0","date":"2024-10-03","lts":"Iron","security":false,"v8":"11.3.244.8"},{"name":"nodejs","version":"20.19.0","date":"2025-03-13","lts":"Iron","security":false,"v8":"11.3.244.8"},{"name":"nodejs","version":"20.20.0","date":"2026-01-12","lts":"Iron","security":true,"v8":"11.3.244.8"},{"name":"nodejs","version":"21.0.0","date":"2023-10-17","lts":false,"security":false,"v8":"11.8.172.13"},{"name":"nodejs","version":"21.1.0","date":"2023-10-24","lts":false,"security":false,"v8":"11.8.172.15"},{"name":"nodejs","version":"21.2.0","date":"2023-11-14","lts":false,"security":false,"v8":"11.8.172.17"},{"name":"nodejs","version":"21.3.0","date":"2023-11-30","lts":false,"security":false,"v8":"11.8.172.17"},{"name":"nodejs","version":"21.4.0","date":"2023-12-05","lts":false,"security":false,"v8":"11.8.172.17"},{"name":"nodejs","version":"21.5.0","date":"2023-12-19","lts":false,"security":false,"v8":"11.8.172.17"},{"name":"nodejs","version":"21.6.0","date":"2024-01-14","lts":false,"security":false,"v8":"11.8.172.17"},{"name":"nodejs","version":"21.7.0","date":"2024-03-06","lts":false,"security":false,"v8":"11.8.172.17"},{"name":"nodejs","version":"22.0.0","date":"2024-04-24","lts":false,"security":false,"v8":"12.4.254.14"},{"name":"nodejs","version":"22.1.0","date":"2024-05-02","lts":false,"security":false,"v8":"12.4.254.14"},{"name":"nodejs","version":"22.2.0","date":"2024-05-15","lts":false,"security":false,"v8":"12.4.254.14"},{"name":"nodejs","version":"22.3.0","date":"2024-06-11","lts":false,"security":false,"v8":"12.4.254.20"},{"name":"nodejs","version":"22.4.0","date":"2024-07-02","lts":false,"security":false,"v8":"12.4.254.21"},{"name":"nodejs","version":"22.5.0","date":"2024-07-17","lts":false,"security":false,"v8":"12.4.254.21"},{"name":"nodejs","version":"22.6.0","date":"2024-08-06","lts":false,"security":false,"v8":"12.4.254.21"},{"name":"nodejs","version":"22.7.0","date":"2024-08-21","lts":false,"security":false,"v8":"12.4.254.21"},{"name":"nodejs","version":"22.8.0","date":"2024-09-03","lts":false,"security":false,"v8":"12.4.254.21"},{"name":"nodejs","version":"22.9.0","date":"2024-09-17","lts":false,"security":false,"v8":"12.4.254.21"},{"name":"nodejs","version":"22.10.0","date":"2024-10-16","lts":false,"security":false,"v8":"12.4.254.21"},{"name":"nodejs","version":"22.11.0","date":"2024-10-29","lts":"Jod","security":false,"v8":"12.4.254.21"},{"name":"nodejs","version":"22.12.0","date":"2024-12-02","lts":"Jod","security":false,"v8":"12.4.254.21"},{"name":"nodejs","version":"22.13.0","date":"2025-01-06","lts":"Jod","security":false,"v8":"12.4.254.21"},{"name":"nodejs","version":"22.14.0","date":"2025-02-11","lts":"Jod","security":false,"v8":"12.4.254.21"},{"name":"nodejs","version":"22.15.0","date":"2025-04-22","lts":"Jod","security":false,"v8":"12.4.254.21"},{"name":"nodejs","version":"22.16.0","date":"2025-05-20","lts":"Jod","security":false,"v8":"12.4.254.21"},{"name":"nodejs","version":"22.17.0","date":"2025-06-24","lts":"Jod","security":false,"v8":"12.4.254.21"},{"name":"nodejs","version":"22.18.0","date":"2025-07-31","lts":"Jod","security":false,"v8":"12.4.254.21"},{"name":"nodejs","version":"22.19.0","date":"2025-08-28","lts":"Jod","security":false,"v8":"12.4.254.21"},{"name":"nodejs","version":"22.20.0","date":"2025-09-24","lts":"Jod","security":false,"v8":"12.4.254.21"},{"name":"nodejs","version":"22.21.0","date":"2025-10-20","lts":"Jod","security":false,"v8":"12.4.254.21"},{"name":"nodejs","version":"22.22.0","date":"2026-01-12","lts":"Jod","security":true,"v8":"12.4.254.21"},{"name":"nodejs","version":"23.0.0","date":"2024-10-16","lts":false,"security":false,"v8":"12.9.202.26"},{"name":"nodejs","version":"23.1.0","date":"2024-10-24","lts":false,"security":false,"v8":"12.9.202.28"},{"name":"nodejs","version":"23.2.0","date":"2024-11-11","lts":false,"security":false,"v8":"12.9.202.28"},{"name":"nodejs","version":"23.3.0","date":"2024-11-20","lts":false,"security":false,"v8":"12.9.202.28"},{"name":"nodejs","version":"23.4.0","date":"2024-12-10","lts":false,"security":false,"v8":"12.9.202.28"},{"name":"nodejs","version":"23.5.0","date":"2024-12-19","lts":false,"security":false,"v8":"12.9.202.28"},{"name":"nodejs","version":"23.6.0","date":"2025-01-07","lts":false,"security":false,"v8":"12.9.202.28"},{"name":"nodejs","version":"23.7.0","date":"2025-01-30","lts":false,"security":false,"v8":"12.9.202.28"},{"name":"nodejs","version":"23.8.0","date":"2025-02-13","lts":false,"security":false,"v8":"12.9.202.28"},{"name":"nodejs","version":"23.9.0","date":"2025-02-26","lts":false,"security":false,"v8":"12.9.202.28"},{"name":"nodejs","version":"23.10.0","date":"2025-03-13","lts":false,"security":false,"v8":"12.9.202.28"},{"name":"nodejs","version":"23.11.0","date":"2025-04-01","lts":false,"security":false,"v8":"12.9.202.28"},{"name":"nodejs","version":"24.0.0","date":"2025-05-06","lts":false,"security":false,"v8":"13.6.233.8"},{"name":"nodejs","version":"24.1.0","date":"2025-05-20","lts":false,"security":false,"v8":"13.6.233.10"},{"name":"nodejs","version":"24.2.0","date":"2025-06-09","lts":false,"security":false,"v8":"13.6.233.10"},{"name":"nodejs","version":"24.3.0","date":"2025-06-24","lts":false,"security":false,"v8":"13.6.233.10"},{"name":"nodejs","version":"24.4.0","date":"2025-07-09","lts":false,"security":false,"v8":"13.6.233.10"},{"name":"nodejs","version":"24.5.0","date":"2025-07-31","lts":false,"security":false,"v8":"13.6.233.10"},{"name":"nodejs","version":"24.6.0","date":"2025-08-14","lts":false,"security":false,"v8":"13.6.233.10"},{"name":"nodejs","version":"24.7.0","date":"2025-08-27","lts":false,"security":false,"v8":"13.6.233.10"},{"name":"nodejs","version":"24.8.0","date":"2025-09-10","lts":false,"security":false,"v8":"13.6.233.10"},{"name":"nodejs","version":"24.9.0","date":"2025-09-25","lts":false,"security":false,"v8":"13.6.233.10"},{"name":"nodejs","version":"24.10.0","date":"2025-10-08","lts":false,"security":false,"v8":"13.6.233.10"},{"name":"nodejs","version":"24.11.0","date":"2025-10-28","lts":"Krypton","security":false,"v8":"13.6.233.10"},{"name":"nodejs","version":"24.12.0","date":"2025-12-10","lts":"Krypton","security":false,"v8":"13.6.233.17"},{"name":"nodejs","version":"24.13.0","date":"2026-01-12","lts":"Krypton","security":true,"v8":"13.6.233.17"},{"name":"nodejs","version":"24.14.0","date":"2026-02-24","lts":"Krypton","security":false,"v8":"13.6.233.17"},{"name":"nodejs","version":"25.0.0","date":"2025-10-15","lts":false,"security":false,"v8":"14.1.146.11"},{"name":"nodejs","version":"25.1.0","date":"2025-10-28","lts":false,"security":false,"v8":"14.1.146.11"},{"name":"nodejs","version":"25.2.0","date":"2025-11-11","lts":false,"security":false,"v8":"14.1.146.11"},{"name":"nodejs","version":"25.3.0","date":"2026-01-12","lts":false,"security":true,"v8":"14.1.146.11"},{"name":"nodejs","version":"25.4.0","date":"2026-01-19","lts":false,"security":false,"v8":"14.1.146.11"},{"name":"nodejs","version":"25.5.0","date":"2026-01-26","lts":false,"security":false,"v8":"14.1.146.11"},{"name":"nodejs","version":"25.6.0","date":"2026-02-02","lts":false,"security":false,"v8":"14.1.146.11"},{"name":"nodejs","version":"25.7.0","date":"2026-02-24","lts":false,"security":false,"v8":"14.1.146.11"},{"name":"nodejs","version":"25.8.0","date":"2026-03-03","lts":false,"security":false,"v8":"14.1.146.11"}]```

----

# frontend/node_modules/node-releases/data/release-schedule/release-schedule.json
```json
{"v0.8":{"start":"2012-06-25","end":"2014-07-31"},"v0.10":{"start":"2013-03-11","end":"2016-10-31"},"v0.12":{"start":"2015-02-06","end":"2016-12-31"},"v4":{"start":"2015-09-08","lts":"2015-10-12","maintenance":"2017-04-01","end":"2018-04-30","codename":"Argon"},"v5":{"start":"2015-10-29","maintenance":"2016-04-30","end":"2016-06-30"},"v6":{"start":"2016-04-26","lts":"2016-10-18","maintenance":"2018-04-30","end":"2019-04-30","codename":"Boron"},"v7":{"start":"2016-10-25","maintenance":"2017-04-30","end":"2017-06-30"},"v8":{"start":"2017-05-30","lts":"2017-10-31","maintenance":"2019-01-01","end":"2019-12-31","codename":"Carbon"},"v9":{"start":"2017-10-01","maintenance":"2018-04-01","end":"2018-06-30"},"v10":{"start":"2018-04-24","lts":"2018-10-30","maintenance":"2020-05-19","end":"2021-04-30","codename":"Dubnium"},"v11":{"start":"2018-10-23","maintenance":"2019-04-22","end":"2019-06-01"},"v12":{"start":"2019-04-23","lts":"2019-10-21","maintenance":"2020-11-30","end":"2022-04-30","codename":"Erbium"},"v13":{"start":"2019-10-22","maintenance":"2020-04-01","end":"2020-06-01"},"v14":{"start":"2020-04-21","lts":"2020-10-27","maintenance":"2021-10-19","end":"2023-04-30","codename":"Fermium"},"v15":{"start":"2020-10-20","maintenance":"2021-04-01","end":"2021-06-01"},"v16":{"start":"2021-04-20","lts":"2021-10-26","maintenance":"2022-10-18","end":"2023-09-11","codename":"Gallium"},"v17":{"start":"2021-10-19","maintenance":"2022-04-01","end":"2022-06-01"},"v18":{"start":"2022-04-19","lts":"2022-10-25","maintenance":"2023-10-18","end":"2025-04-30","codename":"Hydrogen"},"v19":{"start":"2022-10-18","maintenance":"2023-04-01","end":"2023-06-01"},"v20":{"start":"2023-04-18","lts":"2023-10-24","maintenance":"2024-10-22","end":"2026-04-30","codename":"Iron"},"v21":{"start":"2023-10-17","maintenance":"2024-04-01","end":"2024-06-01"},"v22":{"start":"2024-04-24","lts":"2024-10-29","maintenance":"2025-10-21","end":"2027-04-30","codename":"Jod"},"v23":{"start":"2024-10-16","maintenance":"2025-04-01","end":"2025-06-01"},"v24":{"start":"2025-05-06","lts":"2025-10-28","maintenance":"2026-10-20","end":"2028-04-30","codename":"Krypton"},"v25":{"start":"2025-10-15","maintenance":"2026-04-01","end":"2026-06-01"},"v26":{"start":"2026-04-22","lts":"2026-10-28","maintenance":"2027-10-20","end":"2029-04-30","codename":""}}```

----

# frontend/node_modules/node-releases/package.json
```json
{
  "name": "node-releases",
  "version": "2.0.36",
  "description": "Node.js releases data",
  "type": "module",
  "scripts": {
    "build": "node scripts/build.js"
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/chicoxyzzy/node-releases.git"
  },
  "keywords": [
    "nodejs",
    "releases"
  ],
  "author": "Sergey Rubanov <chi187@gmail.com>",
  "license": "MIT",
  "devDependencies": {
    "semver": "^7.3.5"
  }
}
```

----

# frontend/node_modules/picocolors/package.json
```json
{
  "name": "picocolors",
  "version": "1.1.1",
  "main": "./picocolors.js",
  "types": "./picocolors.d.ts",
  "browser": {
    "./picocolors.js": "./picocolors.browser.js"
  },
  "sideEffects": false,
  "description": "The tiniest and the fastest library for terminal output formatting with ANSI colors",
  "files": [
    "picocolors.*",
    "types.d.ts"
  ],
  "keywords": [
    "terminal",
    "colors",
    "formatting",
    "cli",
    "console"
  ],
  "author": "Alexey Raspopov",
  "repository": "alexeyraspopov/picocolors",
  "license": "ISC"
}
```

----

# frontend/node_modules/postcss/package.json
```json
{
  "name": "postcss",
  "version": "8.5.8",
  "description": "Tool for transforming styles with JS plugins",
  "engines": {
    "node": "^10 || ^12 || >=14"
  },
  "exports": {
    ".": {
      "import": "./lib/postcss.mjs",
      "require": "./lib/postcss.js"
    },
    "./lib/at-rule": "./lib/at-rule.js",
    "./lib/comment": "./lib/comment.js",
    "./lib/container": "./lib/container.js",
    "./lib/css-syntax-error": "./lib/css-syntax-error.js",
    "./lib/declaration": "./lib/declaration.js",
    "./lib/fromJSON": "./lib/fromJSON.js",
    "./lib/input": "./lib/input.js",
    "./lib/lazy-result": "./lib/lazy-result.js",
    "./lib/no-work-result": "./lib/no-work-result.js",
    "./lib/list": "./lib/list.js",
    "./lib/map-generator": "./lib/map-generator.js",
    "./lib/node": "./lib/node.js",
    "./lib/parse": "./lib/parse.js",
    "./lib/parser": "./lib/parser.js",
    "./lib/postcss": "./lib/postcss.js",
    "./lib/previous-map": "./lib/previous-map.js",
    "./lib/processor": "./lib/processor.js",
    "./lib/result": "./lib/result.js",
    "./lib/root": "./lib/root.js",
    "./lib/rule": "./lib/rule.js",
    "./lib/stringifier": "./lib/stringifier.js",
    "./lib/stringify": "./lib/stringify.js",
    "./lib/symbols": "./lib/symbols.js",
    "./lib/terminal-highlight": "./lib/terminal-highlight.js",
    "./lib/tokenize": "./lib/tokenize.js",
    "./lib/warn-once": "./lib/warn-once.js",
    "./lib/warning": "./lib/warning.js",
    "./package.json": "./package.json"
  },
  "main": "./lib/postcss.js",
  "types": "./lib/postcss.d.ts",
  "keywords": [
    "css",
    "postcss",
    "rework",
    "preprocessor",
    "parser",
    "source map",
    "transform",
    "manipulation",
    "transpiler"
  ],
  "funding": [
    {
      "type": "opencollective",
      "url": "https://opencollective.com/postcss/"
    },
    {
      "type": "tidelift",
      "url": "https://tidelift.com/funding/github/npm/postcss"
    },
    {
      "type": "github",
      "url": "https://github.com/sponsors/ai"
    }
  ],
  "author": "Andrey Sitnik <andrey@sitnik.ru>",
  "license": "MIT",
  "homepage": "https://postcss.org/",
  "repository": "postcss/postcss",
  "bugs": {
    "url": "https://github.com/postcss/postcss/issues"
  },
  "dependencies": {
    "nanoid": "^3.3.11",
    "picocolors": "^1.1.1",
    "source-map-js": "^1.2.1"
  },
  "browser": {
    "./lib/terminal-highlight": false,
    "source-map-js": false,
    "path": false,
    "url": false,
    "fs": false
  }
}
```

----

# frontend/node_modules/react-dom/package.json
```json
{
  "name": "react-dom",
  "version": "18.3.1",
  "description": "React package for working with the DOM.",
  "main": "index.js",
  "repository": {
    "type": "git",
    "url": "https://github.com/facebook/react.git",
    "directory": "packages/react-dom"
  },
  "keywords": [
    "react"
  ],
  "license": "MIT",
  "bugs": {
    "url": "https://github.com/facebook/react/issues"
  },
  "homepage": "https://reactjs.org/",
  "dependencies": {
    "loose-envify": "^1.1.0",
    "scheduler": "^0.23.2"
  },
  "peerDependencies": {
    "react": "^18.3.1"
  },
  "files": [
    "LICENSE",
    "README.md",
    "index.js",
    "client.js",
    "profiling.js",
    "server.js",
    "server.browser.js",
    "server.node.js",
    "test-utils.js",
    "cjs/",
    "umd/"
  ],
  "exports": {
    ".": "./index.js",
    "./client": "./client.js",
    "./server": {
      "deno": "./server.browser.js",
      "worker": "./server.browser.js",
      "browser": "./server.browser.js",
      "default": "./server.node.js"
    },
    "./server.browser": "./server.browser.js",
    "./server.node": "./server.node.js",
    "./profiling": "./profiling.js",
    "./test-utils": "./test-utils.js",
    "./package.json": "./package.json"
  },
  "browser": {
    "./server.js": "./server.browser.js"
  },
  "browserify": {
    "transform": [
      "loose-envify"
    ]
  }
}```

----

# frontend/node_modules/react-refresh/package.json
```json
{
  "name": "react-refresh",
  "description": "React is a JavaScript library for building user interfaces.",
  "keywords": [
    "react"
  ],
  "version": "0.17.0",
  "homepage": "https://react.dev/",
  "bugs": "https://github.com/facebook/react/issues",
  "license": "MIT",
  "files": [
    "LICENSE",
    "README.md",
    "babel.js",
    "runtime.js",
    "cjs/"
  ],
  "main": "runtime.js",
  "exports": {
    ".": "./runtime.js",
    "./runtime": "./runtime.js",
    "./babel": "./babel.js",
    "./package.json": "./package.json"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/facebook/react.git",
    "directory": "packages/react"
  },
  "engines": {
    "node": ">=0.10.0"
  },
  "devDependencies": {
    "react-16-8": "npm:react@16.8.0",
    "react-dom-16-8": "npm:react-dom@16.8.0",
    "scheduler-0-13": "npm:scheduler@0.13.0"
  }
}```

----

# frontend/node_modules/react/package.json
```json
{
  "name": "react",
  "description": "React is a JavaScript library for building user interfaces.",
  "keywords": [
    "react"
  ],
  "version": "18.3.1",
  "homepage": "https://reactjs.org/",
  "bugs": "https://github.com/facebook/react/issues",
  "license": "MIT",
  "files": [
    "LICENSE",
    "README.md",
    "index.js",
    "cjs/",
    "umd/",
    "jsx-runtime.js",
    "jsx-dev-runtime.js",
    "react.shared-subset.js"
  ],
  "main": "index.js",
  "exports": {
    ".": {
      "react-server": "./react.shared-subset.js",
      "default": "./index.js"
    },
    "./package.json": "./package.json",
    "./jsx-runtime": "./jsx-runtime.js",
    "./jsx-dev-runtime": "./jsx-dev-runtime.js"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/facebook/react.git",
    "directory": "packages/react"
  },
  "engines": {
    "node": ">=0.10.0"
  },
  "dependencies": {
    "loose-envify": "^1.1.0"
  },
  "browserify": {
    "transform": [
      "loose-envify"
    ]
  }
}```

----

# frontend/node_modules/rollup/package.json
```json
{
  "name": "rollup",
  "version": "4.59.0",
  "description": "Next-generation ES module bundler",
  "main": "dist/rollup.js",
  "module": "dist/es/rollup.js",
  "types": "dist/rollup.d.ts",
  "bin": {
    "rollup": "dist/bin/rollup"
  },
  "napi": {
    "binaryName": "rollup",
    "packageName": "@rollup/rollup",
    "targets": [
      "aarch64-apple-darwin",
      "aarch64-linux-android",
      "aarch64-pc-windows-msvc",
      "aarch64-unknown-freebsd",
      "aarch64-unknown-linux-gnu",
      "aarch64-unknown-linux-musl",
      "armv7-linux-androideabi",
      "armv7-unknown-linux-gnueabihf",
      "armv7-unknown-linux-musleabihf",
      "i686-pc-windows-msvc",
      "loongarch64-unknown-linux-gnu",
      "loongarch64-unknown-linux-musl",
      "riscv64gc-unknown-linux-gnu",
      "riscv64gc-unknown-linux-musl",
      "powerpc64le-unknown-linux-gnu",
      "powerpc64le-unknown-linux-musl",
      "s390x-unknown-linux-gnu",
      "x86_64-apple-darwin",
      "x86_64-pc-windows-gnu",
      "x86_64-pc-windows-msvc",
      "x86_64-unknown-freebsd",
      "x86_64-unknown-linux-gnu",
      "x86_64-unknown-linux-musl",
      "x86_64-unknown-openbsd",
      "aarch64-unknown-linux-ohos"
    ]
  },
  "scripts": {
    "build": "concurrently -c green,blue \"npm run build:wasm\" \"npm:build:ast-converters\" && concurrently -c green,blue \"npm run build:napi -- --release\" \"npm:build:js\" && npm run build:copy-native",
    "build:quick": "concurrently -c green,blue 'npm:build:napi' 'npm:build:cjs' && npm run build:copy-native",
    "build:napi": "napi build --cwd rust/bindings_napi --platform --dts ../../native.d.ts --no-js --output-dir ../.. --package-json-path ../../package.json",
    "build:wasm": "wasm-pack build rust/bindings_wasm --out-dir ../../wasm --target web --no-pack && shx rm wasm/.gitignore",
    "build:wasm:node": "wasm-pack build rust/bindings_wasm --out-dir ../../wasm-node --target nodejs --no-pack && shx rm wasm-node/.gitignore",
    "update:napi": "npm run build:napi && npm run build:copy-native",
    "build:js": "rollup --config rollup.config.ts --configPlugin typescript --forceExit",
    "build:js:node": "rollup --config rollup.config.ts --configPlugin typescript --configIsBuildNode --forceExit",
    "build:prepare": "concurrently -c green,blue \"npm run build:napi -- --release\" \"npm:build:js:node\" && npm run build:copy-native",
    "update:js": "npm run build:js && npm run build:copy-native",
    "build:copy-native": "shx mkdir -p dist && shx cp rollup.*.node dist/",
    "dev": "concurrently -kc green,blue 'nodemon --watch rust -e rs --exec \"npm run build:wasm\"' 'vitepress dev docs'",
    "build:cjs": "rollup --config rollup.config.ts --configPlugin typescript --configTest --forceExit",
    "build:bootstrap": "shx mv dist dist-build && node dist-build/bin/rollup --config rollup.config.ts --configPlugin typescript --forceExit && shx rm -rf dist-build",
    "build:bootstrap:cjs": "shx mv dist dist-build && node dist-build/bin/rollup --config rollup.config.ts --configPlugin typescript --configTest --forceExit && shx rm -rf dist-build",
    "build:docs": "vitepress build docs",
    "build:ast-converters": "node scripts/generate-ast-converters.js",
    "preview:docs": "vitepress preview docs",
    "ci:artifacts": "napi artifacts",
    "ci:lint": "concurrently -c red,yellow,green,blue 'npm:lint:js:nofix' 'npm:lint:native-js' 'npm:lint:markdown:nofix' 'npm:lint:rust:nofix'",
    "ci:test:all": "concurrently --kill-others-on-fail -c green,blue,magenta,cyan 'npm:test:only' 'npm:test:typescript' 'npm:test:leak' 'npm:test:browser'",
    "ci:coverage": "NODE_OPTIONS=--no-experimental-require-module nyc --reporter lcovonly mocha",
    "lint": "concurrently -c red,yellow,green,blue 'npm:lint:js' 'npm:lint:native-js' 'npm:lint:markdown' 'npm:lint:rust'",
    "lint:js": "eslint . --fix --cache --concurrency auto",
    "lint:js:nofix": "eslint . --cache --concurrency auto",
    "lint:native-js": "node scripts/lint-native-js.js",
    "lint:markdown": "prettier --write \"**/*.md\"",
    "lint:markdown:nofix": "prettier --check \"**/*.md\"",
    "lint:rust": "cd rust && cargo fmt && cargo clippy --fix --allow-dirty",
    "lint:rust:nofix": "cd rust && cargo fmt --check && cargo clippy",
    "perf": "npm run build:bootstrap:cjs && node --expose-gc scripts/perf-report/index.js",
    "prepare": "husky && npm run prepare:patch && node scripts/check-release.js || npm run build:prepare",
    "prepare:patch": "patch-package",
    "prepublishOnly": "node scripts/check-release.js && node scripts/prepublish.js",
    "postpublish": "node scripts/postpublish.js",
    "prepublish:napi": "napi prepublish --no-gh-release",
    "release": "node scripts/prepare-release.js",
    "release:docs": "git fetch --update-head-ok origin master:master && git branch --force documentation-published master && git push origin documentation-published",
    "check-audit": "check-audit",
    "resolve-audit": "resolve-audit",
    "test": "npm run build && npm run test:all",
    "test:update-snapshots": "node scripts/update-snapshots.js",
    "test:cjs": "npm run build:cjs && npm run test:only",
    "test:quick": "mocha -b test/test.js",
    "test:all": "concurrently --kill-others-on-fail -c green,blue,magenta,cyan,red 'npm:test:only' 'npm:test:browser' 'npm:test:typescript' 'npm:test:package' 'npm:test:options'",
    "test:coverage": "npm run build:cjs && shx rm -rf coverage/* && nyc --reporter html mocha test/test.js",
    "test:coverage:browser": "npm run build && shx rm -rf coverage/* && nyc mocha test/browser/index.js",
    "test:leak": "npm install --no-save weak-napi && node --expose-gc test/leak/index.js",
    "test:package": "node scripts/test-package.js",
    "test:options": "node scripts/test-options.js",
    "test:only": "mocha test/test.js",
    "test:typescript": "shx rm -rf test/typescript/dist && shx cp -r dist test/typescript/ && tsc --noEmit -p test/typescript && tsc --noEmit -p . && tsc --noEmit -p scripts && vue-tsc --noEmit -p docs",
    "test:browser": "mocha test/browser/index.js",
    "watch": "rollup --config rollup.config.ts --configPlugin typescript --watch"
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/rollup/rollup.git"
  },
  "keywords": [
    "modules",
    "bundler",
    "bundling",
    "es6",
    "optimizer"
  ],
  "author": "Rich Harris",
  "license": "MIT",
  "bugs": {
    "url": "https://github.com/rollup/rollup/issues"
  },
  "homepage": "https://rollupjs.org/",
  "optionalDependencies": {
    "fsevents": "~2.3.2",
    "@rollup/rollup-darwin-arm64": "4.59.0",
    "@rollup/rollup-android-arm64": "4.59.0",
    "@rollup/rollup-win32-arm64-msvc": "4.59.0",
    "@rollup/rollup-freebsd-arm64": "4.59.0",
    "@rollup/rollup-linux-arm64-gnu": "4.59.0",
    "@rollup/rollup-linux-arm64-musl": "4.59.0",
    "@rollup/rollup-android-arm-eabi": "4.59.0",
    "@rollup/rollup-linux-arm-gnueabihf": "4.59.0",
    "@rollup/rollup-linux-arm-musleabihf": "4.59.0",
    "@rollup/rollup-win32-ia32-msvc": "4.59.0",
    "@rollup/rollup-linux-loong64-gnu": "4.59.0",
    "@rollup/rollup-linux-loong64-musl": "4.59.0",
    "@rollup/rollup-linux-riscv64-gnu": "4.59.0",
    "@rollup/rollup-linux-riscv64-musl": "4.59.0",
    "@rollup/rollup-linux-ppc64-gnu": "4.59.0",
    "@rollup/rollup-linux-ppc64-musl": "4.59.0",
    "@rollup/rollup-linux-s390x-gnu": "4.59.0",
    "@rollup/rollup-darwin-x64": "4.59.0",
    "@rollup/rollup-win32-x64-gnu": "4.59.0",
    "@rollup/rollup-win32-x64-msvc": "4.59.0",
    "@rollup/rollup-freebsd-x64": "4.59.0",
    "@rollup/rollup-linux-x64-gnu": "4.59.0",
    "@rollup/rollup-linux-x64-musl": "4.59.0",
    "@rollup/rollup-openbsd-x64": "4.59.0",
    "@rollup/rollup-openharmony-arm64": "4.59.0"
  },
  "dependencies": {
    "@types/estree": "1.0.8"
  },
  "devDependenciesComments": {
    "core-js": "We only update manually as every update requires a snapshot update"
  },
  "devDependencies": {
    "@codemirror/commands": "^6.10.2",
    "@codemirror/lang-javascript": "^6.2.4",
    "@codemirror/language": "^6.12.1",
    "@codemirror/search": "^6.6.0",
    "@codemirror/state": "^6.5.4",
    "@codemirror/view": "^6.39.14",
    "@eslint/js": "^10.0.1",
    "@inquirer/prompts": "^7.10.1",
    "@jridgewell/sourcemap-codec": "^1.5.5",
    "@mermaid-js/mermaid-cli": "^11.12.0",
    "@napi-rs/cli": "3.4.1",
    "@rollup/plugin-alias": "^6.0.0",
    "@rollup/plugin-buble": "^1.0.3",
    "@rollup/plugin-commonjs": "^29.0.0",
    "@rollup/plugin-json": "^6.1.0",
    "@rollup/plugin-node-resolve": "^16.0.3",
    "@rollup/plugin-replace": "^6.0.3",
    "@rollup/plugin-terser": "^0.4.4",
    "@rollup/plugin-typescript": "^12.3.0",
    "@rollup/pluginutils": "^5.3.0",
    "@shikijs/vitepress-twoslash": "^3.22.0",
    "@types/mocha": "^10.0.10",
    "@types/node": "^20.19.33",
    "@types/picomatch": "^4.0.2",
    "@types/semver": "^7.7.1",
    "@types/yargs-parser": "^21.0.3",
    "@vue/language-server": "^3.2.4",
    "acorn": "^8.15.0",
    "acorn-import-assertions": "^1.9.0",
    "acorn-jsx": "^5.3.2",
    "buble": "^0.20.0",
    "builtin-modules": "^5.0.0",
    "chokidar": "^3.6.0",
    "concurrently": "^9.2.1",
    "core-js": "3.38.1",
    "cross-env": "^10.1.0",
    "date-time": "^4.0.0",
    "es5-shim": "^4.6.7",
    "es6-shim": "^0.35.8",
    "eslint": "^10.0.0",
    "eslint-config-prettier": "^10.1.8",
    "eslint-plugin-prettier": "^5.5.5",
    "eslint-plugin-unicorn": "^63.0.0",
    "eslint-plugin-vue": "^10.8.0",
    "fixturify": "^3.0.0",
    "flru": "^1.0.2",
    "fs-extra": "^11.3.3",
    "github-api": "^3.4.0",
    "globals": "^17.3.0",
    "husky": "^9.1.7",
    "is-reference": "^3.0.3",
    "lint-staged": "^16.2.7",
    "locate-character": "^3.0.0",
    "magic-string": "^0.30.21",
    "memfs": "^4.56.10",
    "mocha": "11.3.0",
    "nodemon": "^3.1.11",
    "npm-audit-resolver": "^3.0.0-RC.0",
    "nyc": "^17.1.0",
    "patch-package": "^8.0.1",
    "picocolors": "^1.1.1",
    "picomatch": "^4.0.3",
    "pinia": "^3.0.4",
    "prettier": "^3.8.1",
    "prettier-plugin-organize-imports": "^4.3.0",
    "pretty-bytes": "^7.1.0",
    "pretty-ms": "^9.3.0",
    "requirejs": "^2.3.8",
    "rollup": "^4.57.1",
    "rollup-plugin-license": "^3.7.0",
    "semver": "^7.7.4",
    "shx": "^0.4.0",
    "signal-exit": "^4.1.0",
    "source-map": "^0.7.6",
    "source-map-support": "^0.5.21",
    "systemjs": "^6.15.1",
    "terser": "^5.46.0",
    "tslib": "^2.8.1",
    "typescript": "^5.9.3",
    "typescript-eslint": "^8.56.0",
    "vite": "^7.3.1",
    "vitepress": "^1.6.4",
    "vue": "^3.5.28",
    "vue-eslint-parser": "^10.4.0",
    "vue-tsc": "^3.2.4",
    "wasm-pack": "^0.14.0",
    "yargs-parser": "^21.1.1"
  },
  "overrides": {
    "axios": "^1.13.5",
    "esbuild": ">0.24.2",
    "lodash-es": ">4.17.22",
    "path-scurry": {
      "lru-cache": "^11.2.6"
    },
    "readable-stream": "npm:@built-in/readable-stream@1",
    "semver": "^7.7.4",
    "tar": ">7.5.6",
    "vite": "$vite"
  },
  "comments": {
    "vue-tsc": "This is necessary so that prettier-plugin-organize-imports works correctly in Vue templatges"
  },
  "files": [
    "dist/*.node",
    "dist/**/*.js",
    "dist/*.d.ts",
    "dist/bin/rollup",
    "dist/es/package.json"
  ],
  "engines": {
    "node": ">=18.0.0",
    "npm": ">=8.0.0"
  },
  "exports": {
    ".": {
      "types": "./dist/rollup.d.ts",
      "import": "./dist/es/rollup.js",
      "require": "./dist/rollup.js"
    },
    "./loadConfigFile": {
      "types": "./dist/loadConfigFile.d.ts",
      "require": "./dist/loadConfigFile.js",
      "default": "./dist/loadConfigFile.js"
    },
    "./getLogFilter": {
      "types": "./dist/getLogFilter.d.ts",
      "import": "./dist/es/getLogFilter.js",
      "require": "./dist/getLogFilter.js"
    },
    "./parseAst": {
      "types": "./dist/parseAst.d.ts",
      "import": "./dist/es/parseAst.js",
      "require": "./dist/parseAst.js"
    },
    "./dist/*": "./dist/*",
    "./package.json": "./package.json"
  }
}```

----

# frontend/node_modules/scheduler/package.json
```json
{
  "name": "scheduler",
  "version": "0.23.2",
  "description": "Cooperative scheduler for the browser environment.",
  "main": "index.js",
  "repository": {
    "type": "git",
    "url": "https://github.com/facebook/react.git",
    "directory": "packages/scheduler"
  },
  "license": "MIT",
  "keywords": [
    "react"
  ],
  "bugs": {
    "url": "https://github.com/facebook/react/issues"
  },
  "homepage": "https://reactjs.org/",
  "dependencies": {
    "loose-envify": "^1.1.0"
  },
  "files": [
    "LICENSE",
    "README.md",
    "index.js",
    "unstable_mock.js",
    "unstable_post_task.js",
    "cjs/",
    "umd/"
  ],
  "browserify": {
    "transform": [
      "loose-envify"
    ]
  }
}```

----

# frontend/node_modules/semver/package.json
```json
{
  "name": "semver",
  "version": "6.3.1",
  "description": "The semantic version parser used by npm.",
  "main": "semver.js",
  "scripts": {
    "test": "tap test/ --100 --timeout=30",
    "lint": "echo linting disabled",
    "postlint": "template-oss-check",
    "template-oss-apply": "template-oss-apply --force",
    "lintfix": "npm run lint -- --fix",
    "snap": "tap test/ --100 --timeout=30",
    "posttest": "npm run lint"
  },
  "devDependencies": {
    "@npmcli/template-oss": "4.17.0",
    "tap": "^12.7.0"
  },
  "license": "ISC",
  "repository": {
    "type": "git",
    "url": "https://github.com/npm/node-semver.git"
  },
  "bin": {
    "semver": "./bin/semver.js"
  },
  "files": [
    "bin",
    "range.bnf",
    "semver.js"
  ],
  "author": "GitHub Inc.",
  "templateOSS": {
    "//@npmcli/template-oss": "This file is partially managed by @npmcli/template-oss. Edits may be overwritten.",
    "content": "./scripts/template-oss",
    "version": "4.17.0"
  }
}
```

----

# frontend/node_modules/source-map-js/package.json
```json
{
  "name": "source-map-js",
  "description": "Generates and consumes source maps",
  "version": "1.2.1",
  "homepage": "https://github.com/7rulnik/source-map-js",
  "author": "Valentin 7rulnik Semirulnik <v7rulnik@gmail.com>",
  "contributors": [
    "Nick Fitzgerald <nfitzgerald@mozilla.com>",
    "Tobias Koppers <tobias.koppers@googlemail.com>",
    "Duncan Beevers <duncan@dweebd.com>",
    "Stephen Crane <scrane@mozilla.com>",
    "Ryan Seddon <seddon.ryan@gmail.com>",
    "Miles Elam <miles.elam@deem.com>",
    "Mihai Bazon <mihai.bazon@gmail.com>",
    "Michael Ficarra <github.public.email@michael.ficarra.me>",
    "Todd Wolfson <todd@twolfson.com>",
    "Alexander Solovyov <alexander@solovyov.net>",
    "Felix Gnass <fgnass@gmail.com>",
    "Conrad Irwin <conrad.irwin@gmail.com>",
    "usrbincc <usrbincc@yahoo.com>",
    "David Glasser <glasser@davidglasser.net>",
    "Chase Douglas <chase@newrelic.com>",
    "Evan Wallace <evan.exe@gmail.com>",
    "Heather Arthur <fayearthur@gmail.com>",
    "Hugh Kennedy <hughskennedy@gmail.com>",
    "David Glasser <glasser@davidglasser.net>",
    "Simon Lydell <simon.lydell@gmail.com>",
    "Jmeas Smith <jellyes2@gmail.com>",
    "Michael Z Goddard <mzgoddard@gmail.com>",
    "azu <azu@users.noreply.github.com>",
    "John Gozde <john@gozde.ca>",
    "Adam Kirkton <akirkton@truefitinnovation.com>",
    "Chris Montgomery <christopher.montgomery@dowjones.com>",
    "J. Ryan Stinnett <jryans@gmail.com>",
    "Jack Herrington <jherrington@walmartlabs.com>",
    "Chris Truter <jeffpalentine@gmail.com>",
    "Daniel Espeset <daniel@danielespeset.com>",
    "Jamie Wong <jamie.lf.wong@gmail.com>",
    "Eddy Bruël <ejpbruel@mozilla.com>",
    "Hawken Rives <hawkrives@gmail.com>",
    "Gilad Peleg <giladp007@gmail.com>",
    "djchie <djchie.dev@gmail.com>",
    "Gary Ye <garysye@gmail.com>",
    "Nicolas Lalevée <nicolas.lalevee@hibnet.org>"
  ],
  "repository": "7rulnik/source-map-js",
  "main": "./source-map.js",
  "files": [
    "source-map.js",
    "source-map.d.ts",
    "lib/"
  ],
  "engines": {
    "node": ">=0.10.0"
  },
  "license": "BSD-3-Clause",
  "scripts": {
    "test": "npm run build && node test/run-tests.js",
    "build": "webpack --color",
    "toc": "doctoc --title '## Table of Contents' README.md && doctoc --title '## Table of Contents' CONTRIBUTING.md"
  },
  "devDependencies": {
    "clean-publish": "^3.1.0",
    "doctoc": "^0.15.0",
    "webpack": "^1.12.0"
  },
  "clean-publish": {
    "cleanDocs": true
  },
  "typings": "source-map.d.ts"
}
```

----

# frontend/node_modules/update-browserslist-db/package.json
```json
{
  "name": "update-browserslist-db",
  "version": "1.2.3",
  "description": "CLI tool to update caniuse-lite to refresh target browsers from Browserslist config",
  "keywords": [
    "caniuse",
    "browsers",
    "target"
  ],
  "funding": [
    {
      "type": "opencollective",
      "url": "https://opencollective.com/browserslist"
    },
    {
      "type": "tidelift",
      "url": "https://tidelift.com/funding/github/npm/browserslist"
    },
    {
      "type": "github",
      "url": "https://github.com/sponsors/ai"
    }
  ],
  "author": "Andrey Sitnik <andrey@sitnik.ru>",
  "license": "MIT",
  "repository": "browserslist/update-db",
  "types": "./index.d.ts",
  "exports": {
    ".": "./index.js",
    "./package.json": "./package.json"
  },
  "dependencies": {
    "escalade": "^3.2.0",
    "picocolors": "^1.1.1"
  },
  "peerDependencies": {
    "browserslist": ">= 4.21.0"
  },
  "bin": "cli.js"
}
```

----

# frontend/node_modules/vite/package.json
```json
{
  "name": "vite",
  "version": "5.4.21",
  "type": "module",
  "license": "MIT",
  "author": "Evan You",
  "description": "Native-ESM powered web dev build tool",
  "bin": {
    "vite": "bin/vite.js"
  },
  "keywords": [
    "frontend",
    "framework",
    "hmr",
    "dev-server",
    "build-tool",
    "vite"
  ],
  "main": "./dist/node/index.js",
  "types": "./dist/node/index.d.ts",
  "exports": {
    ".": {
      "import": {
        "types": "./dist/node/index.d.ts",
        "default": "./dist/node/index.js"
      },
      "require": {
        "types": "./index.d.cts",
        "default": "./index.cjs"
      }
    },
    "./client": {
      "types": "./client.d.ts"
    },
    "./runtime": {
      "types": "./dist/node/runtime.d.ts",
      "import": "./dist/node/runtime.js"
    },
    "./dist/client/*": "./dist/client/*",
    "./types/*": {
      "types": "./types/*"
    },
    "./package.json": "./package.json"
  },
  "typesVersions": {
    "*": {
      "runtime": [
        "dist/node/runtime.d.ts"
      ]
    }
  },
  "files": [
    "bin",
    "dist",
    "client.d.ts",
    "index.cjs",
    "index.d.cts",
    "types"
  ],
  "engines": {
    "node": "^18.0.0 || >=20.0.0"
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/vitejs/vite.git",
    "directory": "packages/vite"
  },
  "bugs": {
    "url": "https://github.com/vitejs/vite/issues"
  },
  "homepage": "https://vite.dev",
  "funding": "https://github.com/vitejs/vite?sponsor=1",
  "//": "READ CONTRIBUTING.md to understand what to put under deps vs. devDeps!",
  "dependencies": {
    "esbuild": "^0.21.3",
    "postcss": "^8.4.43",
    "rollup": "^4.20.0"
  },
  "optionalDependencies": {
    "fsevents": "~2.3.3"
  },
  "devDependencies": {
    "@ampproject/remapping": "^2.3.0",
    "@babel/parser": "^7.25.6",
    "@jridgewell/trace-mapping": "^0.3.25",
    "@polka/compression": "^1.0.0-next.25",
    "@rollup/plugin-alias": "^5.1.0",
    "@rollup/plugin-commonjs": "^26.0.1",
    "@rollup/plugin-dynamic-import-vars": "^2.1.2",
    "@rollup/plugin-json": "^6.1.0",
    "@rollup/plugin-node-resolve": "15.2.3",
    "@rollup/pluginutils": "^5.1.0",
    "@types/escape-html": "^1.0.4",
    "@types/pnpapi": "^0.0.5",
    "artichokie": "^0.2.1",
    "cac": "^6.7.14",
    "chokidar": "^3.6.0",
    "connect": "^3.7.0",
    "convert-source-map": "^2.0.0",
    "cors": "^2.8.5",
    "cross-spawn": "^7.0.3",
    "debug": "^4.3.6",
    "dep-types": "link:./src/types",
    "dotenv": "^16.4.5",
    "dotenv-expand": "^11.0.6",
    "es-module-lexer": "^1.5.4",
    "escape-html": "^1.0.3",
    "estree-walker": "^3.0.3",
    "etag": "^1.8.1",
    "fast-glob": "^3.3.2",
    "http-proxy": "^1.18.1",
    "launch-editor-middleware": "^2.9.1",
    "lightningcss": "^1.26.0",
    "magic-string": "^0.30.11",
    "micromatch": "^4.0.8",
    "mlly": "^1.7.1",
    "mrmime": "^2.0.0",
    "open": "^8.4.2",
    "parse5": "^7.1.2",
    "pathe": "^1.1.2",
    "periscopic": "^4.0.2",
    "picocolors": "^1.0.1",
    "picomatch": "^2.3.1",
    "postcss-import": "^16.1.0",
    "postcss-load-config": "^4.0.2",
    "postcss-modules": "^6.0.0",
    "resolve.exports": "^2.0.2",
    "rollup-plugin-dts": "^6.1.1",
    "rollup-plugin-esbuild": "^6.1.1",
    "rollup-plugin-license": "^3.5.2",
    "sass": "^1.77.8",
    "sass-embedded": "^1.77.8",
    "sirv": "^2.0.4",
    "source-map-support": "^0.5.21",
    "strip-ansi": "^7.1.0",
    "strip-literal": "^2.1.0",
    "tsconfck": "^3.1.4",
    "tslib": "^2.7.0",
    "types": "link:./types",
    "ufo": "^1.5.4",
    "ws": "^8.18.0"
  },
  "peerDependencies": {
    "@types/node": "^18.0.0 || >=20.0.0",
    "less": "*",
    "lightningcss": "^1.21.0",
    "sass": "*",
    "sass-embedded": "*",
    "stylus": "*",
    "sugarss": "*",
    "terser": "^5.4.0"
  },
  "peerDependenciesMeta": {
    "@types/node": {
      "optional": true
    },
    "sass": {
      "optional": true
    },
    "sass-embedded": {
      "optional": true
    },
    "stylus": {
      "optional": true
    },
    "less": {
      "optional": true
    },
    "sugarss": {
      "optional": true
    },
    "lightningcss": {
      "optional": true
    },
    "terser": {
      "optional": true
    }
  },
  "scripts": {
    "dev": "tsx scripts/dev.ts",
    "build": "rimraf dist && run-s build-bundle build-types",
    "build-bundle": "rollup --config rollup.config.ts --configPlugin esbuild",
    "build-types": "run-s build-types-temp build-types-roll build-types-check",
    "build-types-temp": "tsc --emitDeclarationOnly --outDir temp -p src/node",
    "build-types-roll": "rollup --config rollup.dts.config.ts --configPlugin esbuild && rimraf temp",
    "build-types-check": "tsc --project tsconfig.check.json",
    "typecheck": "tsc --noEmit",
    "lint": "eslint --cache --ext .ts src/**",
    "format": "prettier --write --cache --parser typescript \"src/**/*.ts\""
  }
}```

----

# frontend/node_modules/vite/types/package.json
```json
{
  "//": "this file is here to make typescript happy when moduleResolution=node16+",
  "version": "0.0.0"
}
```

----

# frontend/node_modules/yallist/package.json
```json
{
  "name": "yallist",
  "version": "3.1.1",
  "description": "Yet Another Linked List",
  "main": "yallist.js",
  "directories": {
    "test": "test"
  },
  "files": [
    "yallist.js",
    "iterator.js"
  ],
  "dependencies": {},
  "devDependencies": {
    "tap": "^12.1.0"
  },
  "scripts": {
    "test": "tap test/*.js --100",
    "preversion": "npm test",
    "postversion": "npm publish",
    "postpublish": "git push origin --all; git push origin --tags"
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/isaacs/yallist.git"
  },
  "author": "Isaac Z. Schlueter <i@izs.me> (http://blog.izs.me/)",
  "license": "ISC"
}
```

----

# frontend/package-lock.json
```json
{
  "name": "porypal-frontend",
  "version": "3.0.0",
  "lockfileVersion": 3,
  "requires": true,
  "packages": {
    "": {
      "name": "porypal-frontend",
      "version": "3.0.0",
      "dependencies": {
        "lucide-react": "^0.577.0",
        "react": "^18.3.1",
        "react-dom": "^18.3.1"
      },
      "devDependencies": {
        "@types/react": "^18.3.1",
        "@types/react-dom": "^18.3.1",
        "@vitejs/plugin-react": "^4.3.1",
        "vite": "^5.4.1"
      }
    },
    "node_modules/@babel/code-frame": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/code-frame/-/code-frame-7.29.0.tgz",
      "integrity": "sha512-9NhCeYjq9+3uxgdtp20LSiJXJvN0FeCtNGpJxuMFZ1Kv3cWUNb6DOhJwUvcVCzKGR66cw4njwM6hrJLqgOwbcw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/helper-validator-identifier": "^7.28.5",
        "js-tokens": "^4.0.0",
        "picocolors": "^1.1.1"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/compat-data": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/compat-data/-/compat-data-7.29.0.tgz",
      "integrity": "sha512-T1NCJqT/j9+cn8fvkt7jtwbLBfLC/1y1c7NtCeXFRgzGTsafi68MRv8yzkYSapBnFA6L3U2VSc02ciDzoAJhJg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/core": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/core/-/core-7.29.0.tgz",
      "integrity": "sha512-CGOfOJqWjg2qW/Mb6zNsDm+u5vFQ8DxXfbM09z69p5Z6+mE1ikP2jUXw+j42Pf1XTYED2Rni5f95npYeuwMDQA==",
      "dev": true,
      "license": "MIT",
      "peer": true,
      "dependencies": {
        "@babel/code-frame": "^7.29.0",
        "@babel/generator": "^7.29.0",
        "@babel/helper-compilation-targets": "^7.28.6",
        "@babel/helper-module-transforms": "^7.28.6",
        "@babel/helpers": "^7.28.6",
        "@babel/parser": "^7.29.0",
        "@babel/template": "^7.28.6",
        "@babel/traverse": "^7.29.0",
        "@babel/types": "^7.29.0",
        "@jridgewell/remapping": "^2.3.5",
        "convert-source-map": "^2.0.0",
        "debug": "^4.1.0",
        "gensync": "^1.0.0-beta.2",
        "json5": "^2.2.3",
        "semver": "^6.3.1"
      },
      "engines": {
        "node": ">=6.9.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/babel"
      }
    },
    "node_modules/@babel/generator": {
      "version": "7.29.1",
      "resolved": "https://registry.npmjs.org/@babel/generator/-/generator-7.29.1.tgz",
      "integrity": "sha512-qsaF+9Qcm2Qv8SRIMMscAvG4O3lJ0F1GuMo5HR/Bp02LopNgnZBC/EkbevHFeGs4ls/oPz9v+Bsmzbkbe+0dUw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/parser": "^7.29.0",
        "@babel/types": "^7.29.0",
        "@jridgewell/gen-mapping": "^0.3.12",
        "@jridgewell/trace-mapping": "^0.3.28",
        "jsesc": "^3.0.2"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-compilation-targets": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/helper-compilation-targets/-/helper-compilation-targets-7.28.6.tgz",
      "integrity": "sha512-JYtls3hqi15fcx5GaSNL7SCTJ2MNmjrkHXg4FSpOA/grxK8KwyZ5bubHsCq8FXCkua6xhuaaBit+3b7+VZRfcA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/compat-data": "^7.28.6",
        "@babel/helper-validator-option": "^7.27.1",
        "browserslist": "^4.24.0",
        "lru-cache": "^5.1.1",
        "semver": "^6.3.1"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-globals": {
      "version": "7.28.0",
      "resolved": "https://registry.npmjs.org/@babel/helper-globals/-/helper-globals-7.28.0.tgz",
      "integrity": "sha512-+W6cISkXFa1jXsDEdYA8HeevQT/FULhxzR99pxphltZcVaugps53THCeiWA8SguxxpSp3gKPiuYfSWopkLQ4hw==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-module-imports": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/helper-module-imports/-/helper-module-imports-7.28.6.tgz",
      "integrity": "sha512-l5XkZK7r7wa9LucGw9LwZyyCUscb4x37JWTPz7swwFE/0FMQAGpiWUZn8u9DzkSBWEcK25jmvubfpw2dnAMdbw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/traverse": "^7.28.6",
        "@babel/types": "^7.28.6"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-module-transforms": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/helper-module-transforms/-/helper-module-transforms-7.28.6.tgz",
      "integrity": "sha512-67oXFAYr2cDLDVGLXTEABjdBJZ6drElUSI7WKp70NrpyISso3plG9SAGEF6y7zbha/wOzUByWWTJvEDVNIUGcA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/helper-module-imports": "^7.28.6",
        "@babel/helper-validator-identifier": "^7.28.5",
        "@babel/traverse": "^7.28.6"
      },
      "engines": {
        "node": ">=6.9.0"
      },
      "peerDependencies": {
        "@babel/core": "^7.0.0"
      }
    },
    "node_modules/@babel/helper-plugin-utils": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/helper-plugin-utils/-/helper-plugin-utils-7.28.6.tgz",
      "integrity": "sha512-S9gzZ/bz83GRysI7gAD4wPT/AI3uCnY+9xn+Mx/KPs2JwHJIz1W8PZkg2cqyt3RNOBM8ejcXhV6y8Og7ly/Dug==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-string-parser": {
      "version": "7.27.1",
      "resolved": "https://registry.npmjs.org/@babel/helper-string-parser/-/helper-string-parser-7.27.1.tgz",
      "integrity": "sha512-qMlSxKbpRlAridDExk92nSobyDdpPijUq2DW6oDnUqd0iOGxmQjyqhMIihI9+zv4LPyZdRje2cavWPbCbWm3eA==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-validator-identifier": {
      "version": "7.28.5",
      "resolved": "https://registry.npmjs.org/@babel/helper-validator-identifier/-/helper-validator-identifier-7.28.5.tgz",
      "integrity": "sha512-qSs4ifwzKJSV39ucNjsvc6WVHs6b7S03sOh2OcHF9UHfVPqWWALUsNUVzhSBiItjRZoLHx7nIarVjqKVusUZ1Q==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-validator-option": {
      "version": "7.27.1",
      "resolved": "https://registry.npmjs.org/@babel/helper-validator-option/-/helper-validator-option-7.27.1.tgz",
      "integrity": "sha512-YvjJow9FxbhFFKDSuFnVCe2WxXk1zWc22fFePVNEaWJEu8IrZVlda6N0uHwzZrUM1il7NC9Mlp4MaJYbYd9JSg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helpers": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/helpers/-/helpers-7.28.6.tgz",
      "integrity": "sha512-xOBvwq86HHdB7WUDTfKfT/Vuxh7gElQ+Sfti2Cy6yIWNW05P8iUslOVcZ4/sKbE+/jQaukQAdz/gf3724kYdqw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/template": "^7.28.6",
        "@babel/types": "^7.28.6"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/parser": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/parser/-/parser-7.29.0.tgz",
      "integrity": "sha512-IyDgFV5GeDUVX4YdF/3CPULtVGSXXMLh1xVIgdCgxApktqnQV0r7/8Nqthg+8YLGaAtdyIlo2qIdZrbCv4+7ww==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/types": "^7.29.0"
      },
      "bin": {
        "parser": "bin/babel-parser.js"
      },
      "engines": {
        "node": ">=6.0.0"
      }
    },
    "node_modules/@babel/plugin-transform-react-jsx-self": {
      "version": "7.27.1",
      "resolved": "https://registry.npmjs.org/@babel/plugin-transform-react-jsx-self/-/plugin-transform-react-jsx-self-7.27.1.tgz",
      "integrity": "sha512-6UzkCs+ejGdZ5mFFC/OCUrv028ab2fp1znZmCZjAOBKiBK2jXD1O+BPSfX8X2qjJ75fZBMSnQn3Rq2mrBJK2mw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/helper-plugin-utils": "^7.27.1"
      },
      "engines": {
        "node": ">=6.9.0"
      },
      "peerDependencies": {
        "@babel/core": "^7.0.0-0"
      }
    },
    "node_modules/@babel/plugin-transform-react-jsx-source": {
      "version": "7.27.1",
      "resolved": "https://registry.npmjs.org/@babel/plugin-transform-react-jsx-source/-/plugin-transform-react-jsx-source-7.27.1.tgz",
      "integrity": "sha512-zbwoTsBruTeKB9hSq73ha66iFeJHuaFkUbwvqElnygoNbj/jHRsSeokowZFN3CZ64IvEqcmmkVe89OPXc7ldAw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/helper-plugin-utils": "^7.27.1"
      },
      "engines": {
        "node": ">=6.9.0"
      },
      "peerDependencies": {
        "@babel/core": "^7.0.0-0"
      }
    },
    "node_modules/@babel/template": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/template/-/template-7.28.6.tgz",
      "integrity": "sha512-YA6Ma2KsCdGb+WC6UpBVFJGXL58MDA6oyONbjyF/+5sBgxY/dwkhLogbMT2GXXyU84/IhRw/2D1Os1B/giz+BQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/code-frame": "^7.28.6",
        "@babel/parser": "^7.28.6",
        "@babel/types": "^7.28.6"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/traverse": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/traverse/-/traverse-7.29.0.tgz",
      "integrity": "sha512-4HPiQr0X7+waHfyXPZpWPfWL/J7dcN1mx9gL6WdQVMbPnF3+ZhSMs8tCxN7oHddJE9fhNE7+lxdnlyemKfJRuA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/code-frame": "^7.29.0",
        "@babel/generator": "^7.29.0",
        "@babel/helper-globals": "^7.28.0",
        "@babel/parser": "^7.29.0",
        "@babel/template": "^7.28.6",
        "@babel/types": "^7.29.0",
        "debug": "^4.3.1"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/types": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/types/-/types-7.29.0.tgz",
      "integrity": "sha512-LwdZHpScM4Qz8Xw2iKSzS+cfglZzJGvofQICy7W7v4caru4EaAmyUuO6BGrbyQ2mYV11W0U8j5mBhd14dd3B0A==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/helper-string-parser": "^7.27.1",
        "@babel/helper-validator-identifier": "^7.28.5"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@esbuild/aix-ppc64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/aix-ppc64/-/aix-ppc64-0.21.5.tgz",
      "integrity": "sha512-1SDgH6ZSPTlggy1yI6+Dbkiz8xzpHJEVAlF/AM1tHPLsf5STom9rwtjE4hKAF20FfXXNTFqEYXyJNWh1GiZedQ==",
      "cpu": [
        "ppc64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "aix"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/android-arm": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/android-arm/-/android-arm-0.21.5.tgz",
      "integrity": "sha512-vCPvzSjpPHEi1siZdlvAlsPxXl7WbOVUBBAowWug4rJHb68Ox8KualB+1ocNvT5fjv6wpkX6o/iEpbDrf68zcg==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "android"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/android-arm64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/android-arm64/-/android-arm64-0.21.5.tgz",
      "integrity": "sha512-c0uX9VAUBQ7dTDCjq+wdyGLowMdtR/GoC2U5IYk/7D1H1JYC0qseD7+11iMP2mRLN9RcCMRcjC4YMclCzGwS/A==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "android"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/android-x64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/android-x64/-/android-x64-0.21.5.tgz",
      "integrity": "sha512-D7aPRUUNHRBwHxzxRvp856rjUHRFW1SdQATKXH2hqA0kAZb1hKmi02OpYRacl0TxIGz/ZmXWlbZgjwWYaCakTA==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "android"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/darwin-arm64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/darwin-arm64/-/darwin-arm64-0.21.5.tgz",
      "integrity": "sha512-DwqXqZyuk5AiWWf3UfLiRDJ5EDd49zg6O9wclZ7kUMv2WRFr4HKjXp/5t8JZ11QbQfUS6/cRCKGwYhtNAY88kQ==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "darwin"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/darwin-x64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/darwin-x64/-/darwin-x64-0.21.5.tgz",
      "integrity": "sha512-se/JjF8NlmKVG4kNIuyWMV/22ZaerB+qaSi5MdrXtd6R08kvs2qCN4C09miupktDitvh8jRFflwGFBQcxZRjbw==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "darwin"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/freebsd-arm64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/freebsd-arm64/-/freebsd-arm64-0.21.5.tgz",
      "integrity": "sha512-5JcRxxRDUJLX8JXp/wcBCy3pENnCgBR9bN6JsY4OmhfUtIHe3ZW0mawA7+RDAcMLrMIZaf03NlQiX9DGyB8h4g==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "freebsd"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/freebsd-x64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/freebsd-x64/-/freebsd-x64-0.21.5.tgz",
      "integrity": "sha512-J95kNBj1zkbMXtHVH29bBriQygMXqoVQOQYA+ISs0/2l3T9/kj42ow2mpqerRBxDJnmkUDCaQT/dfNXWX/ZZCQ==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "freebsd"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/linux-arm": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-arm/-/linux-arm-0.21.5.tgz",
      "integrity": "sha512-bPb5AHZtbeNGjCKVZ9UGqGwo8EUu4cLq68E95A53KlxAPRmUyYv2D6F0uUI65XisGOL1hBP5mTronbgo+0bFcA==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/linux-arm64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-arm64/-/linux-arm64-0.21.5.tgz",
      "integrity": "sha512-ibKvmyYzKsBeX8d8I7MH/TMfWDXBF3db4qM6sy+7re0YXya+K1cem3on9XgdT2EQGMu4hQyZhan7TeQ8XkGp4Q==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/linux-ia32": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-ia32/-/linux-ia32-0.21.5.tgz",
      "integrity": "sha512-YvjXDqLRqPDl2dvRODYmmhz4rPeVKYvppfGYKSNGdyZkA01046pLWyRKKI3ax8fbJoK5QbxblURkwK/MWY18Tg==",
      "cpu": [
        "ia32"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/linux-loong64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-loong64/-/linux-loong64-0.21.5.tgz",
      "integrity": "sha512-uHf1BmMG8qEvzdrzAqg2SIG/02+4/DHB6a9Kbya0XDvwDEKCoC8ZRWI5JJvNdUjtciBGFQ5PuBlpEOXQj+JQSg==",
      "cpu": [
        "loong64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/linux-mips64el": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-mips64el/-/linux-mips64el-0.21.5.tgz",
      "integrity": "sha512-IajOmO+KJK23bj52dFSNCMsz1QP1DqM6cwLUv3W1QwyxkyIWecfafnI555fvSGqEKwjMXVLokcV5ygHW5b3Jbg==",
      "cpu": [
        "mips64el"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/linux-ppc64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-ppc64/-/linux-ppc64-0.21.5.tgz",
      "integrity": "sha512-1hHV/Z4OEfMwpLO8rp7CvlhBDnjsC3CttJXIhBi+5Aj5r+MBvy4egg7wCbe//hSsT+RvDAG7s81tAvpL2XAE4w==",
      "cpu": [
        "ppc64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/linux-riscv64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-riscv64/-/linux-riscv64-0.21.5.tgz",
      "integrity": "sha512-2HdXDMd9GMgTGrPWnJzP2ALSokE/0O5HhTUvWIbD3YdjME8JwvSCnNGBnTThKGEB91OZhzrJ4qIIxk/SBmyDDA==",
      "cpu": [
        "riscv64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/linux-s390x": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-s390x/-/linux-s390x-0.21.5.tgz",
      "integrity": "sha512-zus5sxzqBJD3eXxwvjN1yQkRepANgxE9lgOW2qLnmr8ikMTphkjgXu1HR01K4FJg8h1kEEDAqDcZQtbrRnB41A==",
      "cpu": [
        "s390x"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/linux-x64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/linux-x64/-/linux-x64-0.21.5.tgz",
      "integrity": "sha512-1rYdTpyv03iycF1+BhzrzQJCdOuAOtaqHTWJZCWvijKD2N5Xu0TtVC8/+1faWqcP9iBCWOmjmhoH94dH82BxPQ==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/netbsd-x64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/netbsd-x64/-/netbsd-x64-0.21.5.tgz",
      "integrity": "sha512-Woi2MXzXjMULccIwMnLciyZH4nCIMpWQAs049KEeMvOcNADVxo0UBIQPfSmxB3CWKedngg7sWZdLvLczpe0tLg==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "netbsd"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/openbsd-x64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/openbsd-x64/-/openbsd-x64-0.21.5.tgz",
      "integrity": "sha512-HLNNw99xsvx12lFBUwoT8EVCsSvRNDVxNpjZ7bPn947b8gJPzeHWyNVhFsaerc0n3TsbOINvRP2byTZ5LKezow==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "openbsd"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/sunos-x64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/sunos-x64/-/sunos-x64-0.21.5.tgz",
      "integrity": "sha512-6+gjmFpfy0BHU5Tpptkuh8+uw3mnrvgs+dSPQXQOv3ekbordwnzTVEb4qnIvQcYXq6gzkyTnoZ9dZG+D4garKg==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "sunos"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/win32-arm64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/win32-arm64/-/win32-arm64-0.21.5.tgz",
      "integrity": "sha512-Z0gOTd75VvXqyq7nsl93zwahcTROgqvuAcYDUr+vOv8uHhNSKROyU961kgtCD1e95IqPKSQKH7tBTslnS3tA8A==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/win32-ia32": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/win32-ia32/-/win32-ia32-0.21.5.tgz",
      "integrity": "sha512-SWXFF1CL2RVNMaVs+BBClwtfZSvDgtL//G/smwAc5oVK/UPu2Gu9tIaRgFmYFFKrmg3SyAjSrElf0TiJ1v8fYA==",
      "cpu": [
        "ia32"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@esbuild/win32-x64": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/@esbuild/win32-x64/-/win32-x64-0.21.5.tgz",
      "integrity": "sha512-tQd/1efJuzPC6rCFwEvLtci/xNFcTZknmXs98FYDfGE4wP9ClFV98nyKrzJKVPMhdDnjzLhdUyMX4PsQAPjwIw==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ],
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/@jridgewell/gen-mapping": {
      "version": "0.3.13",
      "resolved": "https://registry.npmjs.org/@jridgewell/gen-mapping/-/gen-mapping-0.3.13.tgz",
      "integrity": "sha512-2kkt/7niJ6MgEPxF0bYdQ6etZaA+fQvDcLKckhy1yIQOzaoKjBBjSj63/aLVjYE3qhRt5dvM+uUyfCg6UKCBbA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@jridgewell/sourcemap-codec": "^1.5.0",
        "@jridgewell/trace-mapping": "^0.3.24"
      }
    },
    "node_modules/@jridgewell/remapping": {
      "version": "2.3.5",
      "resolved": "https://registry.npmjs.org/@jridgewell/remapping/-/remapping-2.3.5.tgz",
      "integrity": "sha512-LI9u/+laYG4Ds1TDKSJW2YPrIlcVYOwi2fUC6xB43lueCjgxV4lffOCZCtYFiH6TNOX+tQKXx97T4IKHbhyHEQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@jridgewell/gen-mapping": "^0.3.5",
        "@jridgewell/trace-mapping": "^0.3.24"
      }
    },
    "node_modules/@jridgewell/resolve-uri": {
      "version": "3.1.2",
      "resolved": "https://registry.npmjs.org/@jridgewell/resolve-uri/-/resolve-uri-3.1.2.tgz",
      "integrity": "sha512-bRISgCIjP20/tbWSPWMEi54QVPRZExkuD9lJL+UIxUKtwVJA8wW1Trb1jMs1RFXo1CBTNZ/5hpC9QvmKWdopKw==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.0.0"
      }
    },
    "node_modules/@jridgewell/sourcemap-codec": {
      "version": "1.5.5",
      "resolved": "https://registry.npmjs.org/@jridgewell/sourcemap-codec/-/sourcemap-codec-1.5.5.tgz",
      "integrity": "sha512-cYQ9310grqxueWbl+WuIUIaiUaDcj7WOq5fVhEljNVgRfOUhY9fy2zTvfoqWsnebh8Sl70VScFbICvJnLKB0Og==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@jridgewell/trace-mapping": {
      "version": "0.3.31",
      "resolved": "https://registry.npmjs.org/@jridgewell/trace-mapping/-/trace-mapping-0.3.31.tgz",
      "integrity": "sha512-zzNR+SdQSDJzc8joaeP8QQoCQr8NuYx2dIIytl1QeBEZHJ9uW6hebsrYgbz8hJwUQao3TWCMtmfV8Nu1twOLAw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@jridgewell/resolve-uri": "^3.1.0",
        "@jridgewell/sourcemap-codec": "^1.4.14"
      }
    },
    "node_modules/@rolldown/pluginutils": {
      "version": "1.0.0-beta.27",
      "resolved": "https://registry.npmjs.org/@rolldown/pluginutils/-/pluginutils-1.0.0-beta.27.tgz",
      "integrity": "sha512-+d0F4MKMCbeVUJwG96uQ4SgAznZNSq93I3V+9NHA4OpvqG8mRCpGdKmK8l/dl02h2CCDHwW2FqilnTyDcAnqjA==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@rollup/rollup-android-arm-eabi": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-android-arm-eabi/-/rollup-android-arm-eabi-4.59.0.tgz",
      "integrity": "sha512-upnNBkA6ZH2VKGcBj9Fyl9IGNPULcjXRlg0LLeaioQWueH30p6IXtJEbKAgvyv+mJaMxSm1l6xwDXYjpEMiLMg==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "android"
      ]
    },
    "node_modules/@rollup/rollup-android-arm64": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-android-arm64/-/rollup-android-arm64-4.59.0.tgz",
      "integrity": "sha512-hZ+Zxj3SySm4A/DylsDKZAeVg0mvi++0PYVceVyX7hemkw7OreKdCvW2oQ3T1FMZvCaQXqOTHb8qmBShoqk69Q==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "android"
      ]
    },
    "node_modules/@rollup/rollup-darwin-arm64": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-darwin-arm64/-/rollup-darwin-arm64-4.59.0.tgz",
      "integrity": "sha512-W2Psnbh1J8ZJw0xKAd8zdNgF9HRLkdWwwdWqubSVk0pUuQkoHnv7rx4GiF9rT4t5DIZGAsConRE3AxCdJ4m8rg==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "darwin"
      ]
    },
    "node_modules/@rollup/rollup-darwin-x64": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-darwin-x64/-/rollup-darwin-x64-4.59.0.tgz",
      "integrity": "sha512-ZW2KkwlS4lwTv7ZVsYDiARfFCnSGhzYPdiOU4IM2fDbL+QGlyAbjgSFuqNRbSthybLbIJ915UtZBtmuLrQAT/w==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "darwin"
      ]
    },
    "node_modules/@rollup/rollup-freebsd-arm64": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-freebsd-arm64/-/rollup-freebsd-arm64-4.59.0.tgz",
      "integrity": "sha512-EsKaJ5ytAu9jI3lonzn3BgG8iRBjV4LxZexygcQbpiU0wU0ATxhNVEpXKfUa0pS05gTcSDMKpn3Sx+QB9RlTTA==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "freebsd"
      ]
    },
    "node_modules/@rollup/rollup-freebsd-x64": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-freebsd-x64/-/rollup-freebsd-x64-4.59.0.tgz",
      "integrity": "sha512-d3DuZi2KzTMjImrxoHIAODUZYoUUMsuUiY4SRRcJy6NJoZ6iIqWnJu9IScV9jXysyGMVuW+KNzZvBLOcpdl3Vg==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "freebsd"
      ]
    },
    "node_modules/@rollup/rollup-linux-arm-gnueabihf": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-arm-gnueabihf/-/rollup-linux-arm-gnueabihf-4.59.0.tgz",
      "integrity": "sha512-t4ONHboXi/3E0rT6OZl1pKbl2Vgxf9vJfWgmUoCEVQVxhW6Cw/c8I6hbbu7DAvgp82RKiH7TpLwxnJeKv2pbsw==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-arm-musleabihf": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-arm-musleabihf/-/rollup-linux-arm-musleabihf-4.59.0.tgz",
      "integrity": "sha512-CikFT7aYPA2ufMD086cVORBYGHffBo4K8MQ4uPS/ZnY54GKj36i196u8U+aDVT2LX4eSMbyHtyOh7D7Zvk2VvA==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-arm64-gnu": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-arm64-gnu/-/rollup-linux-arm64-gnu-4.59.0.tgz",
      "integrity": "sha512-jYgUGk5aLd1nUb1CtQ8E+t5JhLc9x5WdBKew9ZgAXg7DBk0ZHErLHdXM24rfX+bKrFe+Xp5YuJo54I5HFjGDAA==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-arm64-musl": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-arm64-musl/-/rollup-linux-arm64-musl-4.59.0.tgz",
      "integrity": "sha512-peZRVEdnFWZ5Bh2KeumKG9ty7aCXzzEsHShOZEFiCQlDEepP1dpUl/SrUNXNg13UmZl+gzVDPsiCwnV1uI0RUA==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-loong64-gnu": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-loong64-gnu/-/rollup-linux-loong64-gnu-4.59.0.tgz",
      "integrity": "sha512-gbUSW/97f7+r4gHy3Jlup8zDG190AuodsWnNiXErp9mT90iCy9NKKU0Xwx5k8VlRAIV2uU9CsMnEFg/xXaOfXg==",
      "cpu": [
        "loong64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-loong64-musl": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-loong64-musl/-/rollup-linux-loong64-musl-4.59.0.tgz",
      "integrity": "sha512-yTRONe79E+o0FWFijasoTjtzG9EBedFXJMl888NBEDCDV9I2wGbFFfJQQe63OijbFCUZqxpHz1GzpbtSFikJ4Q==",
      "cpu": [
        "loong64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-ppc64-gnu": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-ppc64-gnu/-/rollup-linux-ppc64-gnu-4.59.0.tgz",
      "integrity": "sha512-sw1o3tfyk12k3OEpRddF68a1unZ5VCN7zoTNtSn2KndUE+ea3m3ROOKRCZxEpmT9nsGnogpFP9x6mnLTCaoLkA==",
      "cpu": [
        "ppc64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-ppc64-musl": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-ppc64-musl/-/rollup-linux-ppc64-musl-4.59.0.tgz",
      "integrity": "sha512-+2kLtQ4xT3AiIxkzFVFXfsmlZiG5FXYW7ZyIIvGA7Bdeuh9Z0aN4hVyXS/G1E9bTP/vqszNIN/pUKCk/BTHsKA==",
      "cpu": [
        "ppc64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-riscv64-gnu": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-riscv64-gnu/-/rollup-linux-riscv64-gnu-4.59.0.tgz",
      "integrity": "sha512-NDYMpsXYJJaj+I7UdwIuHHNxXZ/b/N2hR15NyH3m2qAtb/hHPA4g4SuuvrdxetTdndfj9b1WOmy73kcPRoERUg==",
      "cpu": [
        "riscv64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-riscv64-musl": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-riscv64-musl/-/rollup-linux-riscv64-musl-4.59.0.tgz",
      "integrity": "sha512-nLckB8WOqHIf1bhymk+oHxvM9D3tyPndZH8i8+35p/1YiVoVswPid2yLzgX7ZJP0KQvnkhM4H6QZ5m0LzbyIAg==",
      "cpu": [
        "riscv64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-s390x-gnu": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-s390x-gnu/-/rollup-linux-s390x-gnu-4.59.0.tgz",
      "integrity": "sha512-oF87Ie3uAIvORFBpwnCvUzdeYUqi2wY6jRFWJAy1qus/udHFYIkplYRW+wo+GRUP4sKzYdmE1Y3+rY5Gc4ZO+w==",
      "cpu": [
        "s390x"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-x64-gnu": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-x64-gnu/-/rollup-linux-x64-gnu-4.59.0.tgz",
      "integrity": "sha512-3AHmtQq/ppNuUspKAlvA8HtLybkDflkMuLK4DPo77DfthRb71V84/c4MlWJXixZz4uruIH4uaa07IqoAkG64fg==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-linux-x64-musl": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-linux-x64-musl/-/rollup-linux-x64-musl-4.59.0.tgz",
      "integrity": "sha512-2UdiwS/9cTAx7qIUZB/fWtToJwvt0Vbo0zmnYt7ED35KPg13Q0ym1g442THLC7VyI6JfYTP4PiSOWyoMdV2/xg==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ]
    },
    "node_modules/@rollup/rollup-openbsd-x64": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-openbsd-x64/-/rollup-openbsd-x64-4.59.0.tgz",
      "integrity": "sha512-M3bLRAVk6GOwFlPTIxVBSYKUaqfLrn8l0psKinkCFxl4lQvOSz8ZrKDz2gxcBwHFpci0B6rttydI4IpS4IS/jQ==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "openbsd"
      ]
    },
    "node_modules/@rollup/rollup-openharmony-arm64": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-openharmony-arm64/-/rollup-openharmony-arm64-4.59.0.tgz",
      "integrity": "sha512-tt9KBJqaqp5i5HUZzoafHZX8b5Q2Fe7UjYERADll83O4fGqJ49O1FsL6LpdzVFQcpwvnyd0i+K/VSwu/o/nWlA==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "openharmony"
      ]
    },
    "node_modules/@rollup/rollup-win32-arm64-msvc": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-win32-arm64-msvc/-/rollup-win32-arm64-msvc-4.59.0.tgz",
      "integrity": "sha512-V5B6mG7OrGTwnxaNUzZTDTjDS7F75PO1ae6MJYdiMu60sq0CqN5CVeVsbhPxalupvTX8gXVSU9gq+Rx1/hvu6A==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ]
    },
    "node_modules/@rollup/rollup-win32-ia32-msvc": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-win32-ia32-msvc/-/rollup-win32-ia32-msvc-4.59.0.tgz",
      "integrity": "sha512-UKFMHPuM9R0iBegwzKF4y0C4J9u8C6MEJgFuXTBerMk7EJ92GFVFYBfOZaSGLu6COf7FxpQNqhNS4c4icUPqxA==",
      "cpu": [
        "ia32"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ]
    },
    "node_modules/@rollup/rollup-win32-x64-gnu": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-win32-x64-gnu/-/rollup-win32-x64-gnu-4.59.0.tgz",
      "integrity": "sha512-laBkYlSS1n2L8fSo1thDNGrCTQMmxjYY5G0WFWjFFYZkKPjsMBsgJfGf4TLxXrF6RyhI60L8TMOjBMvXiTcxeA==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ]
    },
    "node_modules/@rollup/rollup-win32-x64-msvc": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/@rollup/rollup-win32-x64-msvc/-/rollup-win32-x64-msvc-4.59.0.tgz",
      "integrity": "sha512-2HRCml6OztYXyJXAvdDXPKcawukWY2GpR5/nxKp4iBgiO3wcoEGkAaqctIbZcNB6KlUQBIqt8VYkNSj2397EfA==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ]
    },
    "node_modules/@types/babel__core": {
      "version": "7.20.5",
      "resolved": "https://registry.npmjs.org/@types/babel__core/-/babel__core-7.20.5.tgz",
      "integrity": "sha512-qoQprZvz5wQFJwMDqeseRXWv3rqMvhgpbXFfVyWhbx9X47POIA6i/+dXefEmZKoAgOaTdaIgNSMqMIU61yRyzA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/parser": "^7.20.7",
        "@babel/types": "^7.20.7",
        "@types/babel__generator": "*",
        "@types/babel__template": "*",
        "@types/babel__traverse": "*"
      }
    },
    "node_modules/@types/babel__generator": {
      "version": "7.27.0",
      "resolved": "https://registry.npmjs.org/@types/babel__generator/-/babel__generator-7.27.0.tgz",
      "integrity": "sha512-ufFd2Xi92OAVPYsy+P4n7/U7e68fex0+Ee8gSG9KX7eo084CWiQ4sdxktvdl0bOPupXtVJPY19zk6EwWqUQ8lg==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/types": "^7.0.0"
      }
    },
    "node_modules/@types/babel__template": {
      "version": "7.4.4",
      "resolved": "https://registry.npmjs.org/@types/babel__template/-/babel__template-7.4.4.tgz",
      "integrity": "sha512-h/NUaSyG5EyxBIp8YRxo4RMe2/qQgvyowRwVMzhYhBCONbW8PUsg4lkFMrhgZhUe5z3L3MiLDuvyJ/CaPa2A8A==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/parser": "^7.1.0",
        "@babel/types": "^7.0.0"
      }
    },
    "node_modules/@types/babel__traverse": {
      "version": "7.28.0",
      "resolved": "https://registry.npmjs.org/@types/babel__traverse/-/babel__traverse-7.28.0.tgz",
      "integrity": "sha512-8PvcXf70gTDZBgt9ptxJ8elBeBjcLOAcOtoO/mPJjtji1+CdGbHgm77om1GrsPxsiE+uXIpNSK64UYaIwQXd4Q==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/types": "^7.28.2"
      }
    },
    "node_modules/@types/estree": {
      "version": "1.0.8",
      "resolved": "https://registry.npmjs.org/@types/estree/-/estree-1.0.8.tgz",
      "integrity": "sha512-dWHzHa2WqEXI/O1E9OjrocMTKJl2mSrEolh1Iomrv6U+JuNwaHXsXx9bLu5gG7BUWFIN0skIQJQ/L1rIex4X6w==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@types/prop-types": {
      "version": "15.7.15",
      "resolved": "https://registry.npmjs.org/@types/prop-types/-/prop-types-15.7.15.tgz",
      "integrity": "sha512-F6bEyamV9jKGAFBEmlQnesRPGOQqS2+Uwi0Em15xenOxHaf2hv6L8YCVn3rPdPJOiJfPiCnLIRyvwVaqMY3MIw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@types/react": {
      "version": "18.3.28",
      "resolved": "https://registry.npmjs.org/@types/react/-/react-18.3.28.tgz",
      "integrity": "sha512-z9VXpC7MWrhfWipitjNdgCauoMLRdIILQsAEV+ZesIzBq/oUlxk0m3ApZuMFCXdnS4U7KrI+l3WRUEGQ8K1QKw==",
      "dev": true,
      "license": "MIT",
      "peer": true,
      "dependencies": {
        "@types/prop-types": "*",
        "csstype": "^3.2.2"
      }
    },
    "node_modules/@types/react-dom": {
      "version": "18.3.7",
      "resolved": "https://registry.npmjs.org/@types/react-dom/-/react-dom-18.3.7.tgz",
      "integrity": "sha512-MEe3UeoENYVFXzoXEWsvcpg6ZvlrFNlOQ7EOsvhI3CfAXwzPfO8Qwuxd40nepsYKqyyVQnTdEfv68q91yLcKrQ==",
      "dev": true,
      "license": "MIT",
      "peerDependencies": {
        "@types/react": "^18.0.0"
      }
    },
    "node_modules/@vitejs/plugin-react": {
      "version": "4.7.0",
      "resolved": "https://registry.npmjs.org/@vitejs/plugin-react/-/plugin-react-4.7.0.tgz",
      "integrity": "sha512-gUu9hwfWvvEDBBmgtAowQCojwZmJ5mcLn3aufeCsitijs3+f2NsrPtlAWIR6OPiqljl96GVCUbLe0HyqIpVaoA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/core": "^7.28.0",
        "@babel/plugin-transform-react-jsx-self": "^7.27.1",
        "@babel/plugin-transform-react-jsx-source": "^7.27.1",
        "@rolldown/pluginutils": "1.0.0-beta.27",
        "@types/babel__core": "^7.20.5",
        "react-refresh": "^0.17.0"
      },
      "engines": {
        "node": "^14.18.0 || >=16.0.0"
      },
      "peerDependencies": {
        "vite": "^4.2.0 || ^5.0.0 || ^6.0.0 || ^7.0.0"
      }
    },
    "node_modules/baseline-browser-mapping": {
      "version": "2.10.8",
      "resolved": "https://registry.npmjs.org/baseline-browser-mapping/-/baseline-browser-mapping-2.10.8.tgz",
      "integrity": "sha512-PCLz/LXGBsNTErbtB6i5u4eLpHeMfi93aUv5duMmj6caNu6IphS4q6UevDnL36sZQv9lrP11dbPKGMaXPwMKfQ==",
      "dev": true,
      "license": "Apache-2.0",
      "bin": {
        "baseline-browser-mapping": "dist/cli.cjs"
      },
      "engines": {
        "node": ">=6.0.0"
      }
    },
    "node_modules/browserslist": {
      "version": "4.28.1",
      "resolved": "https://registry.npmjs.org/browserslist/-/browserslist-4.28.1.tgz",
      "integrity": "sha512-ZC5Bd0LgJXgwGqUknZY/vkUQ04r8NXnJZ3yYi4vDmSiZmC/pdSN0NbNRPxZpbtO4uAfDUAFffO8IZoM3Gj8IkA==",
      "dev": true,
      "funding": [
        {
          "type": "opencollective",
          "url": "https://opencollective.com/browserslist"
        },
        {
          "type": "tidelift",
          "url": "https://tidelift.com/funding/github/npm/browserslist"
        },
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "MIT",
      "peer": true,
      "dependencies": {
        "baseline-browser-mapping": "^2.9.0",
        "caniuse-lite": "^1.0.30001759",
        "electron-to-chromium": "^1.5.263",
        "node-releases": "^2.0.27",
        "update-browserslist-db": "^1.2.0"
      },
      "bin": {
        "browserslist": "cli.js"
      },
      "engines": {
        "node": "^6 || ^7 || ^8 || ^9 || ^10 || ^11 || ^12 || >=13.7"
      }
    },
    "node_modules/caniuse-lite": {
      "version": "1.0.30001779",
      "resolved": "https://registry.npmjs.org/caniuse-lite/-/caniuse-lite-1.0.30001779.tgz",
      "integrity": "sha512-U5og2PN7V4DMgF50YPNtnZJGWVLFjjsN3zb6uMT5VGYIewieDj1upwfuVNXf4Kor+89c3iCRJnSzMD5LmTvsfA==",
      "dev": true,
      "funding": [
        {
          "type": "opencollective",
          "url": "https://opencollective.com/browserslist"
        },
        {
          "type": "tidelift",
          "url": "https://tidelift.com/funding/github/npm/caniuse-lite"
        },
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "CC-BY-4.0"
    },
    "node_modules/convert-source-map": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/convert-source-map/-/convert-source-map-2.0.0.tgz",
      "integrity": "sha512-Kvp459HrV2FEJ1CAsi1Ku+MY3kasH19TFykTz2xWmMeq6bk2NU3XXvfJ+Q61m0xktWwt+1HSYf3JZsTms3aRJg==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/csstype": {
      "version": "3.2.3",
      "resolved": "https://registry.npmjs.org/csstype/-/csstype-3.2.3.tgz",
      "integrity": "sha512-z1HGKcYy2xA8AGQfwrn0PAy+PB7X/GSj3UVJW9qKyn43xWa+gl5nXmU4qqLMRzWVLFC8KusUX8T/0kCiOYpAIQ==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/debug": {
      "version": "4.4.3",
      "resolved": "https://registry.npmjs.org/debug/-/debug-4.4.3.tgz",
      "integrity": "sha512-RGwwWnwQvkVfavKVt22FGLw+xYSdzARwm0ru6DhTVA3umU5hZc28V3kO4stgYryrTlLpuvgI9GiijltAjNbcqA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "ms": "^2.1.3"
      },
      "engines": {
        "node": ">=6.0"
      },
      "peerDependenciesMeta": {
        "supports-color": {
          "optional": true
        }
      }
    },
    "node_modules/electron-to-chromium": {
      "version": "1.5.313",
      "resolved": "https://registry.npmjs.org/electron-to-chromium/-/electron-to-chromium-1.5.313.tgz",
      "integrity": "sha512-QBMrTWEf00GXZmJyx2lbYD45jpI3TUFnNIzJ5BBc8piGUDwMPa1GV6HJWTZVvY/eiN3fSopl7NRbgGp9sZ9LTA==",
      "dev": true,
      "license": "ISC"
    },
    "node_modules/esbuild": {
      "version": "0.21.5",
      "resolved": "https://registry.npmjs.org/esbuild/-/esbuild-0.21.5.tgz",
      "integrity": "sha512-mg3OPMV4hXywwpoDxu3Qda5xCKQi+vCTZq8S9J/EpkhB2HzKXq4SNFZE3+NK93JYxc8VMSep+lOUSC/RVKaBqw==",
      "dev": true,
      "hasInstallScript": true,
      "license": "MIT",
      "bin": {
        "esbuild": "bin/esbuild"
      },
      "engines": {
        "node": ">=12"
      },
      "optionalDependencies": {
        "@esbuild/aix-ppc64": "0.21.5",
        "@esbuild/android-arm": "0.21.5",
        "@esbuild/android-arm64": "0.21.5",
        "@esbuild/android-x64": "0.21.5",
        "@esbuild/darwin-arm64": "0.21.5",
        "@esbuild/darwin-x64": "0.21.5",
        "@esbuild/freebsd-arm64": "0.21.5",
        "@esbuild/freebsd-x64": "0.21.5",
        "@esbuild/linux-arm": "0.21.5",
        "@esbuild/linux-arm64": "0.21.5",
        "@esbuild/linux-ia32": "0.21.5",
        "@esbuild/linux-loong64": "0.21.5",
        "@esbuild/linux-mips64el": "0.21.5",
        "@esbuild/linux-ppc64": "0.21.5",
        "@esbuild/linux-riscv64": "0.21.5",
        "@esbuild/linux-s390x": "0.21.5",
        "@esbuild/linux-x64": "0.21.5",
        "@esbuild/netbsd-x64": "0.21.5",
        "@esbuild/openbsd-x64": "0.21.5",
        "@esbuild/sunos-x64": "0.21.5",
        "@esbuild/win32-arm64": "0.21.5",
        "@esbuild/win32-ia32": "0.21.5",
        "@esbuild/win32-x64": "0.21.5"
      }
    },
    "node_modules/escalade": {
      "version": "3.2.0",
      "resolved": "https://registry.npmjs.org/escalade/-/escalade-3.2.0.tgz",
      "integrity": "sha512-WUj2qlxaQtO4g6Pq5c29GTcWGDyd8itL8zTlipgECz3JesAiiOKotd8JU6otB3PACgG6xkJUyVhboMS+bje/jA==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6"
      }
    },
    "node_modules/fsevents": {
      "version": "2.3.3",
      "resolved": "https://registry.npmjs.org/fsevents/-/fsevents-2.3.3.tgz",
      "integrity": "sha512-5xoDfX+fL7faATnagmWPpbFtwh/R77WmMMqqHGS65C3vvB0YHrgF+B1YmZ3441tMj5n63k0212XNoJwzlhffQw==",
      "dev": true,
      "hasInstallScript": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "darwin"
      ],
      "engines": {
        "node": "^8.16.0 || ^10.6.0 || >=11.0.0"
      }
    },
    "node_modules/gensync": {
      "version": "1.0.0-beta.2",
      "resolved": "https://registry.npmjs.org/gensync/-/gensync-1.0.0-beta.2.tgz",
      "integrity": "sha512-3hN7NaskYvMDLQY55gnW3NQ+mesEAepTqlg+VEbj7zzqEMBVNhzcGYYeqFo/TlYz6eQiFcp1HcsCZO+nGgS8zg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/js-tokens": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/js-tokens/-/js-tokens-4.0.0.tgz",
      "integrity": "sha512-RdJUflcE3cUzKiMqQgsCu06FPu9UdIJO0beYbPhHN4k6apgJtifcoCtT9bcxOpYBtpD2kCM6Sbzg4CausW/PKQ==",
      "license": "MIT"
    },
    "node_modules/jsesc": {
      "version": "3.1.0",
      "resolved": "https://registry.npmjs.org/jsesc/-/jsesc-3.1.0.tgz",
      "integrity": "sha512-/sM3dO2FOzXjKQhJuo0Q173wf2KOo8t4I8vHy6lF9poUp7bKT0/NHE8fPX23PwfhnykfqnC2xRxOnVw5XuGIaA==",
      "dev": true,
      "license": "MIT",
      "bin": {
        "jsesc": "bin/jsesc"
      },
      "engines": {
        "node": ">=6"
      }
    },
    "node_modules/json5": {
      "version": "2.2.3",
      "resolved": "https://registry.npmjs.org/json5/-/json5-2.2.3.tgz",
      "integrity": "sha512-XmOWe7eyHYH14cLdVPoyg+GOH3rYX++KpzrylJwSW98t3Nk+U8XOl8FWKOgwtzdb8lXGf6zYwDUzeHMWfxasyg==",
      "dev": true,
      "license": "MIT",
      "bin": {
        "json5": "lib/cli.js"
      },
      "engines": {
        "node": ">=6"
      }
    },
    "node_modules/loose-envify": {
      "version": "1.4.0",
      "resolved": "https://registry.npmjs.org/loose-envify/-/loose-envify-1.4.0.tgz",
      "integrity": "sha512-lyuxPGr/Wfhrlem2CL/UcnUc1zcqKAImBDzukY7Y5F/yQiNdko6+fRLevlw1HgMySw7f611UIY408EtxRSoK3Q==",
      "license": "MIT",
      "dependencies": {
        "js-tokens": "^3.0.0 || ^4.0.0"
      },
      "bin": {
        "loose-envify": "cli.js"
      }
    },
    "node_modules/lru-cache": {
      "version": "5.1.1",
      "resolved": "https://registry.npmjs.org/lru-cache/-/lru-cache-5.1.1.tgz",
      "integrity": "sha512-KpNARQA3Iwv+jTA0utUVVbrh+Jlrr1Fv0e56GGzAFOXN7dk/FviaDW8LHmK52DlcH4WP2n6gI8vN1aesBFgo9w==",
      "dev": true,
      "license": "ISC",
      "dependencies": {
        "yallist": "^3.0.2"
      }
    },
    "node_modules/lucide-react": {
      "version": "0.577.0",
      "resolved": "https://registry.npmjs.org/lucide-react/-/lucide-react-0.577.0.tgz",
      "integrity": "sha512-4LjoFv2eEPwYDPg/CUdBJQSDfPyzXCRrVW1X7jrx/trgxnxkHFjnVZINbzvzxjN70dxychOfg+FTYwBiS3pQ5A==",
      "license": "ISC",
      "peerDependencies": {
        "react": "^16.5.1 || ^17.0.0 || ^18.0.0 || ^19.0.0"
      }
    },
    "node_modules/ms": {
      "version": "2.1.3",
      "resolved": "https://registry.npmjs.org/ms/-/ms-2.1.3.tgz",
      "integrity": "sha512-6FlzubTLZG3J2a/NVCAleEhjzq5oxgHyaCU9yYXvcLsvoVaHJq/s5xXI6/XXP6tz7R9xAOtHnSO/tXtF3WRTlA==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/nanoid": {
      "version": "3.3.11",
      "resolved": "https://registry.npmjs.org/nanoid/-/nanoid-3.3.11.tgz",
      "integrity": "sha512-N8SpfPUnUp1bK+PMYW8qSWdl9U+wwNWI4QKxOYDy9JAro3WMX7p2OeVRF9v+347pnakNevPmiHhNmZ2HbFA76w==",
      "dev": true,
      "funding": [
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "MIT",
      "bin": {
        "nanoid": "bin/nanoid.cjs"
      },
      "engines": {
        "node": "^10 || ^12 || ^13.7 || ^14 || >=15.0.1"
      }
    },
    "node_modules/node-releases": {
      "version": "2.0.36",
      "resolved": "https://registry.npmjs.org/node-releases/-/node-releases-2.0.36.tgz",
      "integrity": "sha512-TdC8FSgHz8Mwtw9g5L4gR/Sh9XhSP/0DEkQxfEFXOpiul5IiHgHan2VhYYb6agDSfp4KuvltmGApc8HMgUrIkA==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/picocolors": {
      "version": "1.1.1",
      "resolved": "https://registry.npmjs.org/picocolors/-/picocolors-1.1.1.tgz",
      "integrity": "sha512-xceH2snhtb5M9liqDsmEw56le376mTZkEX/jEb/RxNFyegNul7eNslCXP9FDj/Lcu0X8KEyMceP2ntpaHrDEVA==",
      "dev": true,
      "license": "ISC"
    },
    "node_modules/postcss": {
      "version": "8.5.8",
      "resolved": "https://registry.npmjs.org/postcss/-/postcss-8.5.8.tgz",
      "integrity": "sha512-OW/rX8O/jXnm82Ey1k44pObPtdblfiuWnrd8X7GJ7emImCOstunGbXUpp7HdBrFQX6rJzn3sPT397Wp5aCwCHg==",
      "dev": true,
      "funding": [
        {
          "type": "opencollective",
          "url": "https://opencollective.com/postcss/"
        },
        {
          "type": "tidelift",
          "url": "https://tidelift.com/funding/github/npm/postcss"
        },
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "MIT",
      "dependencies": {
        "nanoid": "^3.3.11",
        "picocolors": "^1.1.1",
        "source-map-js": "^1.2.1"
      },
      "engines": {
        "node": "^10 || ^12 || >=14"
      }
    },
    "node_modules/react": {
      "version": "18.3.1",
      "resolved": "https://registry.npmjs.org/react/-/react-18.3.1.tgz",
      "integrity": "sha512-wS+hAgJShR0KhEvPJArfuPVN1+Hz1t0Y6n5jLrGQbkb4urgPE/0Rve+1kMB1v/oWgHgm4WIcV+i7F2pTVj+2iQ==",
      "license": "MIT",
      "peer": true,
      "dependencies": {
        "loose-envify": "^1.1.0"
      },
      "engines": {
        "node": ">=0.10.0"
      }
    },
    "node_modules/react-dom": {
      "version": "18.3.1",
      "resolved": "https://registry.npmjs.org/react-dom/-/react-dom-18.3.1.tgz",
      "integrity": "sha512-5m4nQKp+rZRb09LNH59GM4BxTh9251/ylbKIbpe7TpGxfJ+9kv6BLkLBXIjjspbgbnIBNqlI23tRnTWT0snUIw==",
      "license": "MIT",
      "dependencies": {
        "loose-envify": "^1.1.0",
        "scheduler": "^0.23.2"
      },
      "peerDependencies": {
        "react": "^18.3.1"
      }
    },
    "node_modules/react-refresh": {
      "version": "0.17.0",
      "resolved": "https://registry.npmjs.org/react-refresh/-/react-refresh-0.17.0.tgz",
      "integrity": "sha512-z6F7K9bV85EfseRCp2bzrpyQ0Gkw1uLoCel9XBVWPg/TjRj94SkJzUTGfOa4bs7iJvBWtQG0Wq7wnI0syw3EBQ==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=0.10.0"
      }
    },
    "node_modules/rollup": {
      "version": "4.59.0",
      "resolved": "https://registry.npmjs.org/rollup/-/rollup-4.59.0.tgz",
      "integrity": "sha512-2oMpl67a3zCH9H79LeMcbDhXW/UmWG/y2zuqnF2jQq5uq9TbM9TVyXvA4+t+ne2IIkBdrLpAaRQAvo7YI/Yyeg==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@types/estree": "1.0.8"
      },
      "bin": {
        "rollup": "dist/bin/rollup"
      },
      "engines": {
        "node": ">=18.0.0",
        "npm": ">=8.0.0"
      },
      "optionalDependencies": {
        "@rollup/rollup-android-arm-eabi": "4.59.0",
        "@rollup/rollup-android-arm64": "4.59.0",
        "@rollup/rollup-darwin-arm64": "4.59.0",
        "@rollup/rollup-darwin-x64": "4.59.0",
        "@rollup/rollup-freebsd-arm64": "4.59.0",
        "@rollup/rollup-freebsd-x64": "4.59.0",
        "@rollup/rollup-linux-arm-gnueabihf": "4.59.0",
        "@rollup/rollup-linux-arm-musleabihf": "4.59.0",
        "@rollup/rollup-linux-arm64-gnu": "4.59.0",
        "@rollup/rollup-linux-arm64-musl": "4.59.0",
        "@rollup/rollup-linux-loong64-gnu": "4.59.0",
        "@rollup/rollup-linux-loong64-musl": "4.59.0",
        "@rollup/rollup-linux-ppc64-gnu": "4.59.0",
        "@rollup/rollup-linux-ppc64-musl": "4.59.0",
        "@rollup/rollup-linux-riscv64-gnu": "4.59.0",
        "@rollup/rollup-linux-riscv64-musl": "4.59.0",
        "@rollup/rollup-linux-s390x-gnu": "4.59.0",
        "@rollup/rollup-linux-x64-gnu": "4.59.0",
        "@rollup/rollup-linux-x64-musl": "4.59.0",
        "@rollup/rollup-openbsd-x64": "4.59.0",
        "@rollup/rollup-openharmony-arm64": "4.59.0",
        "@rollup/rollup-win32-arm64-msvc": "4.59.0",
        "@rollup/rollup-win32-ia32-msvc": "4.59.0",
        "@rollup/rollup-win32-x64-gnu": "4.59.0",
        "@rollup/rollup-win32-x64-msvc": "4.59.0",
        "fsevents": "~2.3.2"
      }
    },
    "node_modules/scheduler": {
      "version": "0.23.2",
      "resolved": "https://registry.npmjs.org/scheduler/-/scheduler-0.23.2.tgz",
      "integrity": "sha512-UOShsPwz7NrMUqhR6t0hWjFduvOzbtv7toDH1/hIrfRNIDBnnBWd0CwJTGvTpngVlmwGCdP9/Zl/tVrDqcuYzQ==",
      "license": "MIT",
      "dependencies": {
        "loose-envify": "^1.1.0"
      }
    },
    "node_modules/semver": {
      "version": "6.3.1",
      "resolved": "https://registry.npmjs.org/semver/-/semver-6.3.1.tgz",
      "integrity": "sha512-BR7VvDCVHO+q2xBEWskxS6DJE1qRnb7DxzUrogb71CWoSficBxYsiAGd+Kl0mmq/MprG9yArRkyrQxTO6XjMzA==",
      "dev": true,
      "license": "ISC",
      "bin": {
        "semver": "bin/semver.js"
      }
    },
    "node_modules/source-map-js": {
      "version": "1.2.1",
      "resolved": "https://registry.npmjs.org/source-map-js/-/source-map-js-1.2.1.tgz",
      "integrity": "sha512-UXWMKhLOwVKb728IUtQPXxfYU+usdybtUrK/8uGE8CQMvrhOpwvzDBwj0QhSL7MQc7vIsISBG8VQ8+IDQxpfQA==",
      "dev": true,
      "license": "BSD-3-Clause",
      "engines": {
        "node": ">=0.10.0"
      }
    },
    "node_modules/update-browserslist-db": {
      "version": "1.2.3",
      "resolved": "https://registry.npmjs.org/update-browserslist-db/-/update-browserslist-db-1.2.3.tgz",
      "integrity": "sha512-Js0m9cx+qOgDxo0eMiFGEueWztz+d4+M3rGlmKPT+T4IS/jP4ylw3Nwpu6cpTTP8R1MAC1kF4VbdLt3ARf209w==",
      "dev": true,
      "funding": [
        {
          "type": "opencollective",
          "url": "https://opencollective.com/browserslist"
        },
        {
          "type": "tidelift",
          "url": "https://tidelift.com/funding/github/npm/browserslist"
        },
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "MIT",
      "dependencies": {
        "escalade": "^3.2.0",
        "picocolors": "^1.1.1"
      },
      "bin": {
        "update-browserslist-db": "cli.js"
      },
      "peerDependencies": {
        "browserslist": ">= 4.21.0"
      }
    },
    "node_modules/vite": {
      "version": "5.4.21",
      "resolved": "https://registry.npmjs.org/vite/-/vite-5.4.21.tgz",
      "integrity": "sha512-o5a9xKjbtuhY6Bi5S3+HvbRERmouabWbyUcpXXUA1u+GNUKoROi9byOJ8M0nHbHYHkYICiMlqxkg1KkYmm25Sw==",
      "dev": true,
      "license": "MIT",
      "peer": true,
      "dependencies": {
        "esbuild": "^0.21.3",
        "postcss": "^8.4.43",
        "rollup": "^4.20.0"
      },
      "bin": {
        "vite": "bin/vite.js"
      },
      "engines": {
        "node": "^18.0.0 || >=20.0.0"
      },
      "funding": {
        "url": "https://github.com/vitejs/vite?sponsor=1"
      },
      "optionalDependencies": {
        "fsevents": "~2.3.3"
      },
      "peerDependencies": {
        "@types/node": "^18.0.0 || >=20.0.0",
        "less": "*",
        "lightningcss": "^1.21.0",
        "sass": "*",
        "sass-embedded": "*",
        "stylus": "*",
        "sugarss": "*",
        "terser": "^5.4.0"
      },
      "peerDependenciesMeta": {
        "@types/node": {
          "optional": true
        },
        "less": {
          "optional": true
        },
        "lightningcss": {
          "optional": true
        },
        "sass": {
          "optional": true
        },
        "sass-embedded": {
          "optional": true
        },
        "stylus": {
          "optional": true
        },
        "sugarss": {
          "optional": true
        },
        "terser": {
          "optional": true
        }
      }
    },
    "node_modules/yallist": {
      "version": "3.1.1",
      "resolved": "https://registry.npmjs.org/yallist/-/yallist-3.1.1.tgz",
      "integrity": "sha512-a4UGQaWPH59mOXUYnAG2ewncQS4i4F43Tv3JoAM+s2VDAmS9NsK8GpDMLrCHPksFT7h3K6TOoUNn2pb7RoXx4g==",
      "dev": true,
      "license": "ISC"
    }
  }
}
```

----

# frontend/package.json
```json
{
  "name": "porypal-frontend",
  "private": true,
  "version": "3.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "lucide-react": "^0.577.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.1",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.1",
    "vite": "^5.4.1"
  }
}
```

----

# main.py
```python
#!/usr/bin/env python3
"""
main.py — Porypal v3 launcher

Starts the FastAPI server and opens the browser automatically.
Usage:
    python main.py          # default port 7860
    python main.py --port 8080
    python main.py --no-browser
"""

import argparse
import threading
import time
import webbrowser
import sys

import uvicorn

DEFAULT_PORT = 7860
DEFAULT_HOST = "127.0.0.1"


def open_browser(host: str, port: int, delay: float = 1.2):
    """Open the browser after a short delay to let the server start."""
    time.sleep(delay)
    webbrowser.open(f"http://{host}:{port}")


def main():
    parser = argparse.ArgumentParser(description="Porypal — palette toolchain for Gen 3 ROM hacking")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host to bind (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to listen on (default: {DEFAULT_PORT})")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (dev mode)")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    print(f"\n  Porypal running at {url}\n")

    if not args.no_browser:
        t = threading.Thread(target=open_browser, args=(args.host, args.port), daemon=True)
        t.start()

    uvicorn.run(
        "server.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
```

----

# model/QNotificationWidget.py
```python
from PySide6.QtWidgets import QDockWidget, QLabel, QApplication, QWidget, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, QRect, QPropertyAnimation
from PySide6.QtGui import QPalette
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
__version__ = '3.0.0'
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

    def __init__(self, image: Image.Image, palette: Palette, colors_used: int, used_indices: set = None):
        self.image = image          # PIL Image (mode "P", indexed)
        self.palette = palette
        self.colors_used = colors_used
        self.used_indices = used_indices or set()  # palette indices actually present in the image

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

        return ConversionResult(image=out, palette=palette, colors_used=colors_used, used_indices=used)

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
        return self._current_image_path```

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
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsScene

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
        from PySide6.QtGui import QImage, QPainter
        
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

# model/tileset_manager.py
```python
"""
model/tileset_manager.py

Tileset loading, slicing, reordering — pure Pillow, no Qt.
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional

from PIL import Image


class TilesetManager:
    """
    Loads a spritesheet, slices it into tiles, reorders them
    according to config, and produces a processed output image.
    """

    def __init__(self, config: dict):
        self.config = config
        self._source: Optional[Image.Image] = None
        self._tiles: list[Image.Image] = []
        self._processed: Optional[Image.Image] = None

    # ---------- public ----------

    def load(self, file_path: str | Path) -> bool:
        """Load, resize, slice and arrange. Returns True on success."""
        try:
            img = Image.open(file_path).convert("RGBA")
            self._source = self._resize(img)
            self._tiles = self._extract_tiles(self._source)
            self._processed = self._arrange(self._tiles)
            logging.debug(f"Tileset loaded: {file_path} → {len(self._tiles)} tiles")
            return True
        except Exception as e:
            logging.error(f"Failed to load tileset: {e}")
            return False

    def get_tiles(self) -> list[Image.Image]:
        """Return individual tile images."""
        return self._tiles

    def get_processed(self) -> Optional[Image.Image]:
        """Return the arranged output image."""
        return self._processed

    def get_source(self) -> Optional[Image.Image]:
        """Return the (possibly resized) source image."""
        return self._source

    # ---------- pipeline steps ----------

    def _resize(self, img: Image.Image) -> Image.Image:
        cfg = self.config.get("tileset", {})
        supported = cfg.get("supported_sizes", [])

        matched = next(
            (s for s in supported if img.width == s["width"] and img.height == s["height"]),
            None,
        )
        if matched:
            target = matched["resize_to"]
        elif cfg.get("resize_tileset", False):
            target = cfg.get("resize_to", img.width)
        else:
            return img

        return img.resize((target, target), Image.NEAREST)

    def _extract_tiles(self, img: Image.Image) -> list[Image.Image]:
        cfg = self.config.get("tileset", {})
        sprite_size = cfg.get("output_sprite_size", {"width": 32, "height": 32})
        tw = sprite_size["width"]
        th = sprite_size["height"]

        tiles = []
        for y in range(0, img.height, th):
            for x in range(0, img.width, tw):
                tile = img.crop((x, y, x + tw, y + th))
                tiles.append(tile)
        return tiles

    def _arrange(self, tiles: list[Image.Image]) -> Image.Image:
        cfg = self.config.get("tileset", {})
        order = cfg.get("sprite_order", list(range(len(tiles))))
        sprite_size = cfg.get("output_sprite_size", {"width": 32, "height": 32})
        out_cfg = self.config.get("output", {})

        out_w = out_cfg.get("output_width", sprite_size["width"] * len(order))
        out_h = out_cfg.get("output_height", sprite_size["height"])

        output = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 0))
        for i, idx in enumerate(order):
            if idx < len(tiles):
                x_pos = i * sprite_size["width"]
                output.paste(tiles[idx], (x_pos, 0))
        return output```

----

# presets/gen_4_ow_sprites.json
```json
{
  "name": "Gen 4 OW Sprites",
  "tile_w": 64,
  "tile_h": 64,
  "cols": 9,
  "rows": 1,
  "slots": [
    0,
    12,
    4,
    1,
    3,
    13,
    15,
    5,
    7
  ],
  "slot_labels": null,
  "is_default": false
}```

----

# presets/ow_sprite.json
```json
{
  "name": "Overworld sprite (9x1)",
  "tile_w": 32,
  "tile_h": 32,
  "cols": 9,
  "rows": 1,
  "slots": [
    null,
    null,
    null,
    null,
    null,
    null,
    null,
    null,
    null
  ],
  "slot_labels": [
    "down idle",
    "up idle",
    "left idle",
    "down walk 1",
    "down walk 2",
    "up walk 1",
    "up walk 2",
    "left walk 1",
    "left walk 2"
  ],
  "is_default": true
}```

----

# server/__init__.py
```python
```

----

# server/app.py
```python
"""
server/app.py

FastAPI server for Porypal v3.
Wraps the pure-Python model layer and exposes it as a REST API.
All image data is transferred as base64 PNG to avoid file system coupling with the browser.
"""

from __future__ import annotations
import base64
import io
import logging
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image

from model.palette import Palette
from model.palette_manager import PaletteManager
from model.image_manager import ImageManager, ConversionResult
from model.palette_extractor import PaletteExtractor

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="Porypal API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- helpers ----------

def pil_to_b64(img: Image.Image) -> str:
    """Convert a PIL image to a base64-encoded PNG string."""
    buf = io.BytesIO()
    img.convert("RGBA").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def load_config() -> dict:
    cfg_path = Path("config.yaml")
    if cfg_path.exists():
        import yaml
        return yaml.safe_load(cfg_path.read_text()) or {}
    return {}

# ---------- shared state ----------
# Simple in-process state — fine for a single-user local tool.

class AppState:
    def __init__(self):
        self.config = load_config()
        self.palette_manager = PaletteManager(self.config)
        self.image_manager = ImageManager(self.config)
        self.extractor = PaletteExtractor()

state = AppState()

# ---------- routes ----------

@app.get("/api/palettes")
def list_palettes():
    """Return all loaded palettes with their colors as hex strings."""
    return [
        {
            "name": p.name,
            "colors": [c.to_hex() for c in p.colors],
            "count": len(p.colors),
        }
        for p in state.palette_manager.get_palettes()
    ]


@app.post("/api/palettes/reload")
def reload_palettes():
    """Reload palettes from the palettes/ directory."""
    state.palette_manager.reload()
    return {"loaded": len(state.palette_manager.get_palettes())}


@app.post("/api/convert")
async def convert(
    file: UploadFile = File(...),
    palette_name: str | None = Form(default=None),
):
    """
    Convert an uploaded sprite against all (or one specific) palette(s).
    Returns base64 PNG previews + color counts for each result.
    """
    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data))
    except Exception as e:
        raise HTTPException(400, f"Cannot open image: {e}")

    # Write to a temp file so ImageManager can use its path-based loader
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        state.image_manager.load_image(tmp_path)

        palettes = state.palette_manager.get_palettes()
        if palette_name:
            palettes = [p for p in palettes if p.name == palette_name]
            if not palettes:
                raise HTTPException(404, f"Palette '{palette_name}' not found")

        results = state.image_manager.process_all_palettes(palettes)
        best = state.image_manager.get_best_indices()

        return {
            "original": pil_to_b64(state.image_manager._original_rgba),
            "results": [
                {
                    "palette_name": r.palette.name,
                    "colors_used": r.colors_used,
                    "used_indices": sorted(r.used_indices),
                    "colors": [c.to_hex() for c in r.palette.colors],
                    "image": pil_to_b64(r.image.convert("RGBA")),
                    "best": i in best,
                }
                for i, r in enumerate(results)
            ],
        }
    finally:
        os.unlink(tmp_path)


@app.post("/api/convert/download")
async def download_converted(
    file: UploadFile = File(...),
    palette_name: str = Form(...),
):
    """
    Convert and return a single GBA-compatible indexed PNG for download.
    """
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        state.image_manager.load_image(tmp_path)
        palette = state.palette_manager.get_palette_by_name(palette_name)
        if not palette:
            raise HTTPException(404, f"Palette '{palette_name}' not found")

        results = state.image_manager.process_all_palettes([palette])
        result = results[0]

        out_buf = io.BytesIO()
        result.image.save(out_buf, format="PNG", bits=4, optimize=True)
        out_buf.seek(0)

        stem = Path(file.filename).stem
        pal_stem = Path(palette_name).stem
        filename = f"{stem}_{pal_stem}.png"

        return StreamingResponse(
            out_buf,
            media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        os.unlink(tmp_path)


@app.post("/api/convert/download-all")
async def download_all_converted(file: UploadFile = File(...)):
    """
    Convert against all palettes and return a zip of all results.
    """
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        state.image_manager.load_image(tmp_path)
        results = state.image_manager.process_all_palettes(
            state.palette_manager.get_palettes()
        )

        zip_buf = io.BytesIO()
        stem = Path(file.filename).stem
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for r in results:
                pal_stem = Path(r.palette.name).stem
                img_buf = io.BytesIO()
                r.image.save(img_buf, format="PNG", bits=4, optimize=True)
                zf.writestr(f"{stem}_{pal_stem}.png", img_buf.getvalue())
        zip_buf.seek(0)

        return StreamingResponse(
            zip_buf,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{stem}_all_palettes.zip"'},
        )
    finally:
        os.unlink(tmp_path)


@app.post("/api/extract")
async def extract_palette(
    file: UploadFile = File(...),
    n_colors: int = Form(default=16),
):
    """
    Extract a GBA palette from the uploaded sprite using k-means.
    Returns the palette as hex colors + a downloadable .pal file as base64.
    """
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        palette = state.extractor.extract(tmp_path, n_colors=n_colors)

        pal_buf = io.StringIO()
        pal_buf.write("JASC-PAL\n0100\n")
        pal_buf.write(f"{len(palette.colors)}\n")
        for c in palette.colors:
            pal_buf.write(f"{c.r} {c.g} {c.b}\n")

        return {
            "name": palette.name,
            "colors": [c.to_hex() for c in palette.colors],
            "pal_content": pal_buf.getvalue(),
        }
    finally:
        os.unlink(tmp_path)


@app.post("/api/batch")
async def batch_convert(
    files: list[UploadFile] = File(...),
    palette_name: str = Form(...),
):
    """
    Convert multiple sprites against one palette.
    Returns a zip of all converted images.
    """
    palette = state.palette_manager.get_palette_by_name(palette_name)
    if not palette:
        raise HTTPException(404, f"Palette '{palette_name}' not found")

    zip_buf = io.BytesIO()
    results_meta = []

    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for upload in files:
            data = await upload.read()
            with tempfile.NamedTemporaryFile(suffix=Path(upload.filename).suffix, delete=False) as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            try:
                state.image_manager.load_image(tmp_path)
                results = state.image_manager.process_all_palettes([palette])
                r = results[0]
                stem = Path(upload.filename).stem
                pal_stem = Path(palette_name).stem
                out_name = f"{stem}_{pal_stem}.png"
                img_buf = io.BytesIO()
                r.image.save(img_buf, format="PNG", bits=4, optimize=True)
                zf.writestr(out_name, img_buf.getvalue())
                results_meta.append({"file": upload.filename, "colors_used": r.colors_used, "output": out_name})
            except Exception as e:
                results_meta.append({"file": upload.filename, "error": str(e)})
            finally:
                os.unlink(tmp_path)

    zip_buf.seek(0)
    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="batch_output.zip"'},
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "palettes_loaded": len(state.palette_manager.get_palettes())}


# ---------- serve frontend in production ----------
example_dir = Path(__file__).parent.parent / "example"
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if example_dir.exists():
    app.mount("/example", StaticFiles(directory=str(example_dir)), name="example")

if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")



# ---------- tileset routes ----------

from model.tileset_manager import TilesetManager
from server.presets import list_presets, load_preset, save_preset, delete_preset
from pydantic import BaseModel
from typing import Optional

# -- presets --

@app.get("/api/presets")
def get_presets():
    return list_presets()

@app.get("/api/presets/{preset_id}")
def get_preset(preset_id: str):
    p = load_preset(preset_id)
    if not p:
        raise HTTPException(404, f"Preset '{preset_id}' not found")
    return p

class PresetBody(BaseModel):
    name: str
    tile_w: int = 32
    tile_h: int = 32
    cols: int = 9
    rows: int = 1
    slots: list
    slot_labels: Optional[list] = None

@app.post("/api/presets/{preset_id}")
def upsert_preset(preset_id: str, body: PresetBody):
    return save_preset(preset_id, body.model_dump())

@app.delete("/api/presets/{preset_id}")
def remove_preset(preset_id: str):
    p = load_preset(preset_id)
    if not p:
        raise HTTPException(404, f"Preset '{preset_id}' not found")
    if p.get("is_default", False):
        raise HTTPException(403, f"Preset '{preset_id}' is a default preset and cannot be deleted")
    if not delete_preset(preset_id):
        raise HTTPException(500, "Failed to delete preset")
    return {"deleted": preset_id}


# -- tileset --

@app.post("/api/tileset/slice")
async def tileset_slice(
    file: UploadFile = File(...),
    tile_width: int = Form(default=32),
    tile_height: int = Form(default=32),
):
    """Slice a tileset into individual tiles. Returns source image + all tile images as base64."""
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        tmp.write(data); tmp_path = tmp.name
    try:
        config = {
            "tileset": {
                "output_sprite_size": {"width": tile_width, "height": tile_height},
                "sprite_order": [0],
                "resize_tileset": False,
                "resize_to": 128,
                "supported_sizes": [],
            },
            "output": {"output_width": tile_width, "output_height": tile_height},
        }
        from PIL import Image as PILImage
        source_img = PILImage.open(tmp_path).convert("RGBA")
        source_w, source_h = source_img.size

        mgr = TilesetManager(config)
        if not mgr.load(tmp_path):
            raise HTTPException(400, "Failed to slice tileset")

        return {
            "source": pil_to_b64(mgr.get_source()),
            "source_w": source_w,
            "source_h": source_h,
            "tiles": [pil_to_b64(t) for t in mgr.get_tiles()],
            "tile_count": len(mgr.get_tiles()),
            "tile_width": tile_width,
            "tile_height": tile_height,
        }
    finally:
        os.unlink(tmp_path)


@app.post("/api/tileset/arrange")
async def tileset_arrange(
    file: UploadFile = File(...),
    tile_width: int = Form(default=32),
    tile_height: int = Form(default=32),
    cols: int = Form(default=9),
    rows: int = Form(default=1),
    sprite_order: str = Form(...),
):
    """Arrange tiles by order string and return a downloadable PNG."""
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        tmp.write(data); tmp_path = tmp.name
    try:
        order = [int(x.strip()) for x in sprite_order.split(",") if x.strip()]
        config = {
            "tileset": {
                "output_sprite_size": {"width": tile_width, "height": tile_height},
                "sprite_order": order,
                "resize_tileset": False,
                "resize_to": 128,
                "supported_sizes": [],
            },
            "output": {
                "output_width": cols * tile_width,
                "output_height": rows * tile_height,
            },
        }
        mgr = TilesetManager(config)
        if not mgr.load(tmp_path):
            raise HTTPException(400, "Failed to process tileset")

        buf = io.BytesIO()
        mgr.get_processed().save(buf, format="PNG")
        buf.seek(0)
        stem = Path(file.filename).stem
        return StreamingResponse(
            buf, media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="{stem}_arranged.png"'},
        )
    finally:
        os.unlink(tmp_path)


# ---------- serve static ----------

example_dir = Path(__file__).parent.parent / "example"
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"

if example_dir.exists():
    app.mount("/example", StaticFiles(directory=str(example_dir)), name="example")

if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")```

----

# server/presets.py
```python
"""
server/presets.py

Preset management — load/save JSON presets from the presets/ folder.
Each preset stores: name, tile_w, tile_h, cols, rows, slots (list of tile indices or null).
"""

from __future__ import annotations
import json
import logging
from pathlib import Path

PRESETS_DIR = Path("presets")


def _ensure_dir():
    PRESETS_DIR.mkdir(exist_ok=True)


def list_presets() -> list[dict]:
    _ensure_dir()
    result = []
    for f in sorted(PRESETS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            result.append({
                "id": f.stem,
                "name": data.get("name", f.stem),
                "tile_w": data.get("tile_w", 32),
                "tile_h": data.get("tile_h", 32),
                "cols": data.get("cols", 9),
                "rows": data.get("rows", 1),
                "slots": data.get("slots", []),
                "is_default": data.get("is_default", False),
            })
        except Exception as e:
            logging.warning(f"Could not read preset {f.name}: {e}")
    return result


def load_preset(preset_id: str) -> dict | None:
    _ensure_dir()
    f = PRESETS_DIR / f"{preset_id}.json"
    if not f.exists():
        return None
    return json.loads(f.read_text())


def save_preset(preset_id: str, data: dict) -> dict:
    _ensure_dir()
    f = PRESETS_DIR / f"{preset_id}.json"
    f.write_text(json.dumps(data, indent=2))
    return data


def delete_preset(preset_id: str) -> bool:
    _ensure_dir()
    f = PRESETS_DIR / f"{preset_id}.json"
    if f.exists():
        f.unlink()
        return True
    return False```

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
__version__ = '3.0.0'
```

----

# view/automation_view.py
```python
# view/automation_view.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog
from PySide6.QtCore import Qt
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
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog
from PySide6.QtCore import Qt
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
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtGui import QColor, QPainter
from PySide6.QtCore import Qt, QSize

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
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication
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
from PySide6.QtCore import Qt, QRectF, QEvent
from PySide6.QtGui import QPixmap, QScreen, QCursor
from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsView, QLabel, QWidget, 
    QMessageBox, QHBoxLayout, QSizePolicy, 
    QApplication, QPushButton
)
from PySide6.QtUiTools import QUiLoader
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
        self._load_ui(ui_file)

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
from PySide6.QtCore import Qt, QRectF
from PySide6.QtWidgets import QWidget, QGraphicsScene, QApplication, QMessageBox
from PySide6.QtGui import QPixmap, QCursor
from PySide6.QtUiTools import QUiLoader
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
        self._load_ui(ui_file)
        
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
from PySide6.QtWidgets import QGraphicsView, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QMouseEvent
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

