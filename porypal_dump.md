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

# frontend/src/App.css
```css
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:       #0e1117;
  --surface:  #161b22;
  --surface2: #1c2330;
  --border:   #2d3748;
  --border2:  #3d4f66;
  --text:     #e2e8f0;
  --muted:    #718096;
  --accent:   #58a6ff;
  --best:     #3fb950;
  --danger:   #f85149;
  --mono:     'IBM Plex Mono', monospace;
  --sans:     'IBM Plex Sans', sans-serif;
  --radius:   6px;
}

html, body, #root { height: 100%; }
body { font-family: var(--sans); background: var(--bg); color: var(--text); font-size: 14px; line-height: 1.5; -webkit-font-smoothing: antialiased; }

.header { border-bottom: 1px solid var(--border); background: var(--surface); position: sticky; top: 0; z-index: 10; }
.header-inner { max-width: 1400px; margin: 0 auto; padding: 0 24px; height: 52px; display: flex; align-items: center; gap: 32px; }
.logo { display: flex; align-items: center; gap: 6px; font-family: var(--mono); }
.logo-mark { width: 28px; height: 28px; background: var(--accent); color: var(--bg); border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 15px; font-weight: 500; }
.logo-text { font-size: 16px; font-weight: 500; }
.nav { display: flex; gap: 2px; }
.nav-tab { padding: 6px 14px; border: none; background: transparent; color: var(--muted); font-family: var(--mono); font-size: 13px; cursor: pointer; border-radius: var(--radius); transition: color 0.15s, background 0.15s; }
.nav-tab:hover { color: var(--text); background: var(--surface2); }
.nav-tab.active { color: var(--accent); background: rgba(88,166,255,0.1); }
.header-right { margin-left: auto; }
.palette-count { font-family: var(--mono); font-size: 12px; color: var(--muted); }

.main { max-width: 1400px; margin: 0 auto; padding: 28px 24px; }
.tab-content { animation: fadeIn 0.15s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(3px); } to { opacity: 1; transform: none; } }

/* shared primitives used across multiple components */
.section-label { font-family: var(--mono); font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
.pixel-img { display: block; image-rendering: pixelated; image-rendering: crisp-edges; }
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 300px; gap: 12px; color: var(--muted); font-size: 13px; text-align: center; }
.error-msg { font-family: var(--mono); font-size: 12px; color: var(--danger); }
.spinner { width: 22px; height: 22px; border: 2px solid var(--border2); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* shared buttons used in multiple tabs */
.btn-primary { padding: 10px 18px; background: var(--accent); color: var(--bg); border: none; border-radius: var(--radius); font-family: var(--mono); font-size: 13px; font-weight: 500; cursor: pointer; transition: opacity 0.15s, transform 0.1s; width: 100%; }
.btn-primary:hover:not(:disabled) { opacity: 0.88; }
.btn-primary:active:not(:disabled) { transform: scale(0.98); }
.btn-primary:disabled { opacity: 0.35; cursor: not-allowed; }
.btn-secondary { padding: 8px 14px; background: transparent; color: var(--text); border: 1px solid var(--border2); border-radius: var(--radius); font-family: var(--mono); font-size: 12px; cursor: pointer; transition: border-color 0.15s; width: 100%; }
.btn-secondary:hover { border-color: var(--accent); }
.btn-ghost { padding: 4px 8px; background: transparent; border: none; color: var(--muted); font-family: var(--mono); font-size: 11px; cursor: pointer; }
.btn-ghost:hover { color: var(--text); }
.btn-ghost-subtle { padding: 6px; background: transparent; border: none; color: var(--muted); font-family: var(--mono); font-size: 11px; cursor: pointer; text-align: center; width: 100%; }
.btn-ghost-subtle:hover:not(:disabled) { color: var(--text); }
.btn-ghost-subtle:disabled { opacity: 0.3; cursor: not-allowed; }

/* shared field */
.field { display: flex; flex-direction: column; gap: 6px; }
.field-label { font-family: var(--mono); font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
.field-input { background: var(--surface2); border: 1px solid var(--border); border-radius: var(--radius); color: var(--text); font-family: var(--mono); font-size: 13px; padding: 8px 10px; width: 100%; transition: border-color 0.15s; }
.field-input:focus { outline: none; border-color: var(--accent); }


.logo {
  display: flex;
  align-items: center;
  height: 100%;
}

.logo-icon {
  height: 100%;
  max-height: 100%;
  width: auto;
  object-fit: contain;
}

.star-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  background: transparent;
  border: 1px solid var(--border2);
  border-radius: var(--radius);
  color: var(--muted);
  font-family: var(--mono);
  font-size: 11px;
  text-decoration: none;
  transition: color 0.15s, border-color 0.15s;
  white-space: nowrap;
}
.star-btn:hover {
  color: #e3b341;
  border-color: #e3b341;
}```

----

# frontend/src/App.jsx
```jsx
import { useState, useEffect } from 'react'
import { ConvertTab } from './tabs/ConvertTab'
import { ExtractTab } from './tabs/ExtractTab'
import { BatchTab } from './tabs/BatchTab'
import { TilesetTab } from './tabs/TilesetTab'
import './App.css'

const API = '/api'
const TABS = ['convert', 'extract', 'batch', 'tileset']

export default function App() {
  const [tab, setTab] = useState('convert')
  const [palettes, setPalettes] = useState([])

  useEffect(() => {
    fetch(`${API}/palettes`)
      .then(r => r.json())
      .then(setPalettes)
      .catch(() => {})
  }, [])

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <a className="logo" href='#' onClick={() => setTab('convert')}>
            <img src="/porypal.ico" alt="Porypal" className="logo-icon" />
          </a>
          <nav className="nav">
            {TABS.map(t => (
              <button
                key={t}
                className={`nav-tab ${tab === t ? 'active' : ''}`}
                onClick={() => setTab(t)}
              >
                {t}
              </button>
            ))}
          </nav>
          <div className="header-right">
            <a
              className="star-btn"
              href="https://github.com/loxed/porypal"
              target="_blank"
              rel="noopener noreferrer"
            >
              <svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"/>
              </svg>
              Support the project
            </a>
          </div>
        </div>
      </header>
      <main className="main">
        {tab === 'convert' && <ConvertTab />}
        {tab === 'extract' && <ExtractTab />}
        {tab === 'batch'   && <BatchTab palettes={palettes} />}
        {tab === 'tileset' && <TilesetTab />}
      </main>
    </div>
  )
}```

----

# frontend/src/components/ColorSwatch.css
```css
.inline-swatch {
  display: inline-block;
  width: 1em;
  height: 1em;
  border-radius: 2px;
  border: 1px solid rgba(255,255,255,0.15);
  vertical-align: middle;
  margin-right: 3px;
  position: relative;
  top: -1px;
}```

----

# frontend/src/components/ColorSwatch.jsx
```jsx
import './ColorSwatch.css'

export function ColorSwatch({ hex }) {
  return (
    <span
      className="inline-swatch"
      style={{ background: hex }}
      title={hex}
    />
  )
}```

----

# frontend/src/components/DropZone.css
```css
.dropzone { border: 1px dashed var(--border2); border-radius: var(--radius); padding: 28px 16px; text-align: center; cursor: pointer; transition: border-color 0.15s, background 0.15s; display: flex; flex-direction: column; align-items: center; gap: 8px; }
.dropzone:hover, .dropzone.dragging { border-color: var(--accent); background: rgba(88,166,255,0.04); }
.dropzone-label { font-size: 13px; font-weight: 500; }
.dropzone-hint { font-size: 11px; font-family: var(--mono); color: var(--muted); }
```

----

# frontend/src/components/DropZone.jsx
```jsx
import { useState, useRef } from 'react'
import './DropZone.css'

export function DropZone({ onFile, label = 'Drop sprite here' }) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef()

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) onFile(f)
  }

  return (
    <div
      className={`dropzone ${dragging ? 'dragging' : ''}`}
      onDragOver={e => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        style={{ display: 'none' }}
        onChange={e => e.target.files[0] && onFile(e.target.files[0])}
      />
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ color: 'var(--muted)' }}>
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="17 8 12 3 7 8"/>
        <line x1="12" y1="3" x2="12" y2="15"/>
      </svg>
      <p className="dropzone-label">{label}</p>
      <p className="dropzone-hint">PNG, JPG, BMP · click or drag</p>
    </div>
  )
}
```

----

# frontend/src/components/PaletteStrip.css
```css
.palette-strip {
  display: grid;
  grid-template-columns: repeat(16, 1fr);
  gap: 2px;
  width: 100%;
  overflow: visible;
}

.palette-swatch {
  aspect-ratio: 1;
  border-radius: 4px;
  border: 1px solid rgba(255,255,255,0.08);
  cursor: pointer;
  min-width: 0;
  position: relative;
}

.palette-swatch.used {
  opacity: 0.8;
}

.palette-swatch.used:hover {
  opacity: 1;
}

.palette-swatch.unused {
  opacity: 0.2;
}

.palette-swatch.unused::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: repeating-conic-gradient(rgba(0,0,0,0.35) 0% 25%, transparent 0% 50%);
  background-size: var(--check-size, 25%) var(--check-size, 25%);
  pointer-events: none;
  border-radius: inherit;
  transition: opacity 0.15s;
}

.palette-swatch.unused:hover {
  opacity: 1;
}

.palette-swatch.unused:hover::before {
  opacity: 0.2;
}

.swatch-tooltip {
  position: absolute;
  top: calc(100% + 4px);
  left: 50%;
  transform: translateX(-50%);
  background: var(--surface);
  border: 1px solid var(--border2);
  border-radius: 4px;
  padding: 3px 6px;
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
  z-index: 100;
  pointer-events: none;
}

.swatch-hex {
  font-family: var(--mono);
  font-size: 10px;
  color: var(--text);
}

.swatch-icon {
  color: var(--muted);
}

.swatch-icon.copied {
  color: var(--best);
}```

----

# frontend/src/components/PaletteStrip.jsx
```jsx
import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import './PaletteStrip.css'

export function PaletteStrip({ colors, usedIndices = [], checkSize = '25%' }) {
  const [hover, setHover] = useState(null)
  const [copied, setCopied] = useState(null)
  const usedSet = new Set(usedIndices)

  const handleClick = (e, hex, i) => {
    e.stopPropagation()
    navigator.clipboard.writeText(hex).then(() => {
      setCopied(i)
      setTimeout(() => setCopied(null), 1500)
    })
  }

  return (
    <div className="palette-strip">
      {colors.map((hex, i) => (
        <div
          key={i}
          className={`palette-swatch ${usedSet.has(i) ? 'used' : 'unused'}`}
          style={{ background: hex, '--check-size': checkSize }}
          onMouseEnter={() => setHover(i)}
          onMouseLeave={() => setHover(null)}
          onClick={e => handleClick(e, hex, i)}
        >
          {(hover === i || copied === i) && (
            <div className="swatch-tooltip">
              {hover === i && <span className="swatch-hex">{hex}</span>}
              {copied === i
                ? <Check size={11} className="swatch-icon copied" />
                : <Copy size={11} className="swatch-icon" />
              }
            </div>
          )}
        </div>
      ))}
    </div>
  )
}```

----

# frontend/src/components/PresetList.css
```css
.preset-list { display: flex; flex-direction: column; gap: 2px; }

.preset-row {
  display: flex; align-items: center; justify-content: space-between;
  gap: 8px; padding: 7px 8px; border-radius: 4px;
  border: 1px solid var(--border);
  background: var(--surface2);
  transition: border-color 0.1s, background 0.1s;
  min-height: 36px;
}
.preset-row:hover { border-color: var(--border2); background: var(--surface); }
.preset-row.active { border-color: var(--accent); background: rgba(88,166,255,0.07); }

.preset-info { display: flex; flex-direction: column; gap: 1px; flex: 1; min-width: 0; }
.preset-name { font-family: var(--mono); font-size: 12px; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.preset-meta { font-family: var(--mono); font-size: 10px; color: var(--muted); }

.preset-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }

.preset-hover-actions { display: flex; align-items: center; gap: 4px; }

.preset-apply {
  display: flex; align-items: center; gap: 4px;
  padding: 3px 8px;
  background: var(--accent); color: var(--bg);
  border: none; border-radius: 4px;
  font-family: var(--mono); font-size: 11px; font-weight: 500;
  cursor: pointer; white-space: nowrap;
  transition: opacity 0.1s;
}
.preset-apply:hover { opacity: 0.85; }

.preset-delete {
  background: transparent; border: none; color: var(--muted);
  cursor: pointer; padding: 3px; display: flex; align-items: center;
  border-radius: 3px; transition: color 0.1s;
}
.preset-delete:hover { color: var(--danger); }

.preset-warn {
  color: #EF9F27; display: flex; align-items: center;
  cursor: default;
}

.preset-active-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent); display: block;
}

.preset-loading { display: flex; align-items: center; color: var(--muted); }

@keyframes spin { to { transform: rotate(360deg); } }
.spin { animation: spin 0.7s linear infinite; }```

----

# frontend/src/components/PresetList.jsx
```jsx
import { useState } from 'react'
import { Trash2, AlertTriangle, Check, Loader } from 'lucide-react'
import './PresetList.css'

export function PresetList({ presets, defaultIds, activePresetId, onLoad, onDelete, currentState }) {
  const [hoveredId, setHoveredId] = useState(null)
  const [loadingId, setLoadingId] = useState(null)

  const isDirty = (preset) => {
    if (!currentState) return false
    return (
      currentState.tileW !== preset.tile_w ||
      currentState.tileH !== preset.tile_h ||
      currentState.cols !== preset.cols ||
      currentState.rows !== preset.rows ||
      currentState.slots.some(s => s !== null)
    )
  }

  const handleApply = async (id) => {
    setLoadingId(id)
    await onLoad(id)
    setLoadingId(null)
    setHoveredId(null)
  }

  return (
    <div className="preset-list">
      {presets.map(p => {
        const isActive = activePresetId === p.id
        const isHovered = hoveredId === p.id
        const isLoading = loadingId === p.id
        const dirty = isDirty(p)

        return (
          <div
            key={p.id}
            className={`preset-row ${isActive ? 'active' : ''}`}
            onMouseEnter={() => setHoveredId(p.id)}
            onMouseLeave={() => setHoveredId(null)}
          >
            <div className="preset-info">
              <span className="preset-name">{p.name}</span>
              <span className="preset-meta">{p.cols}×{p.rows} · {p.tile_w}px</span>
            </div>

            <div className="preset-actions">
              {isLoading ? (
                <span className="preset-loading"><Loader size={13} className="spin"/></span>
              ) : isHovered ? (
                <div className="preset-hover-actions">
                  {dirty && (
                    <span className="preset-warn" title="Will reset current layout">
                      <AlertTriangle size={12}/>
                    </span>
                  )}
                  <button className="preset-apply" onClick={() => handleApply(p.id)}>
                    <Check size={12}/> apply
                  </button>
                  {!defaultIds.has(p.id) && (
                    <button className="preset-delete"
                      onClick={e => { e.stopPropagation(); onDelete(p.id) }}>
                      <Trash2 size={11}/>
                    </button>
                  )}
                </div>
              ) : isActive ? (
                <span className="preset-active-dot" title="active"/>
              ) : null}
            </div>
          </div>
        )
      })}
    </div>
  )
}```

----

# frontend/src/components/ResultCard.css
```css
/* ---- shared ---- */
.result-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px;
  cursor: pointer;
  transition: border-color 0.15s;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.result-card:hover { border-color: var(--border2); }
.result-card.selected { border-color: #4A8DFC; box-shadow: 0 0 0 1px #4A8DFC; }
.result-card.selected.best { border-color: #FFE5F5; box-shadow: 0 0 0 1px #FFE5F5; }
.result-card.best:not(.selected) { border-color: #FFFF72; box-shadow: 0 0 0 1px #FFFF72; }

.result-name { font-family: var(--mono); font-size: 12px; font-weight: 500; }
.result-colors { font-family: var(--mono); font-size: 11px; color: var(--muted); }

/* inline best badge — sits in the flow, no absolute positioning */

/* ---- grid mode ---- */
.result-header { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
/* push colors to right but keep best tag after it */
.result-header .result-colors { margin-right: auto; }

.grid-footer { display: flex; flex-direction: column; gap: 6px; }

/* ---- list mode ---- */
.result-card.list-mode { gap: 10px; }

.list-row-1 {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: nowrap;
}
.list-palette { flex: 1; min-width: 0; }

.list-row-2 {
  display: flex;
  align-items: stretch;
  gap: 10px;
  height: 160px;
}
.list-zoom { flex: 1; min-width: 0; overflow: hidden; }
.list-zoom .zoomable-wrap { height: 100%; }
.list-zoom .zoomable-scroll { max-height: calc(160px - 32px); }
.list-mode .walk-animation { height: 100%; justify-content: center; }
.list-mode .walk-canvas { height: 100% !important; width: auto !important; }

/* ---- buttons ---- */
.btn-download { padding: 5px 10px; background: transparent; border: 1px solid var(--border); border-radius: 4px; font-family: var(--mono); font-size: 11px; color: var(--muted); cursor: pointer; transition: color 0.1s, border-color 0.1s; white-space: nowrap; flex-shrink: 0; }
.btn-download:hover { color: var(--accent); border-color: var(--accent); }
.btn-download.full-width { width: 100%; text-align: center; }

/* ---- frames ---- */
.frames-row { display: flex; align-items: center; gap: 6px; }
.split-row { display: flex; gap: 4px; align-items: center; }
.frame-count-input { width: 44px; background: var(--surface2); border: 1px solid var(--border); border-radius: 4px; color: var(--text); font-family: var(--mono); font-size: 12px; padding: 4px 6px; text-align: center; }
.frame-count-input:focus { outline: none; border-color: var(--accent); }
.btn-split { padding: 4px 8px; background: transparent; border: 1px solid var(--border2); border-radius: 4px; color: var(--muted); font-family: var(--mono); font-size: 11px; cursor: pointer; transition: color 0.1s, border-color 0.1s; white-space: nowrap; }
.btn-split:hover { color: var(--accent); border-color: var(--accent); }
.btn-ghost { padding: 4px 8px; background: transparent; border: none; color: var(--muted); font-family: var(--mono); font-size: 11px; cursor: pointer; }
.btn-ghost:hover { color: var(--text); }

.frames-section { border-top: 1px solid var(--border); padding-top: 8px; display: flex; flex-direction: column; gap: 6px; }
.frame-strip { display: flex; flex-wrap: wrap; gap: 4px; }
.frame-cell { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.frame-img { width: 32px; image-rendering: pixelated; image-rendering: crisp-edges; background: repeating-conic-gradient(#1c2330 0% 25%, #161b22 0% 50%) 0 0/8px 8px; }
.frame-index { font-family: var(--mono); font-size: 9px; color: var(--muted); }```

----

# frontend/src/components/ResultCard.jsx
```jsx
import { useState, useEffect } from 'react'
import './ResultCard.css'
import { ZoomableImage } from './ZoomableImage'
import { PaletteStrip } from './PaletteStrip'
import { WalkAnimation } from './WalkAnimation'
import { splitFrames } from '../utils'

function detectOWSprite(b64) {
  return new Promise(resolve => {
    const img = new window.Image()
    img.onload = () => resolve(img.width / img.height >= 7.5 && img.width / img.height <= 10.5)
    img.src = `data:image/png;base64,${b64}`
  })
}

function FramesSection({ b64, frameCount, setFrameCount }) {
  const [frames, setFrames] = useState(null)
  const [show, setShow] = useState(false)

  const handleSplit = async (e) => {
    e.stopPropagation()
    const f = await splitFrames(b64, frameCount)
    setFrames(f); setShow(true)
  }

  return (
    <>
      <div className="frames-row" onClick={e => e.stopPropagation()}>
        <div className="split-row">
          <input type="number" min={1} max={32} value={frameCount}
            className="frame-count-input" title="frame count"
            onChange={e => setFrameCount(Number(e.target.value))} />
          <button className="btn-split" onClick={handleSplit}>
            {show ? 'refresh' : 'show frames'}
          </button>
          {show && <button className="btn-ghost" onClick={e => { e.stopPropagation(); setShow(false) }}>hide</button>}
        </div>
      </div>
      {show && frames && (
        <div className="frames-section" onClick={e => e.stopPropagation()}>
          <p className="section-label">frames ({frames.length})</p>
          <div className="frame-strip">
            {frames.map((f, i) => (
              <div key={i} className="frame-cell">
                <img src={`data:image/png;base64,${f}`} alt={`frame ${i}`}
                  className="pixel-img frame-img" draggable={false} />
                <span className="frame-index">{i}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  )
}

export function ResultCard({ result, selected, onSelect, onDownload, listMode = false }) {
  const [frameCount, setFrameCount] = useState(9)
  const [isOWSprite, setIsOWSprite] = useState(false)

  useEffect(() => {
    detectOWSprite(result.image).then(setIsOWSprite)
  }, [result.image])

  const colorsLabel = `${result.colors_used}/16`

  if (listMode) {
    return (
      <div
        className={`result-card list-mode ${selected ? 'selected' : ''} ${result.best ? 'best' : ''}`}
        onClick={onSelect}
      >
        {/* row 1: name -- colors -- best tag -- palette strip -- download */}
        <div className="list-row-1" onClick={e => e.stopPropagation()}>
          <span className="result-name">{result.palette_name.replace('.pal', '')}</span>
          <span className="result-colors">{colorsLabel} colors</span>
          <div className="list-palette">
            <PaletteStrip colors={result.colors} usedIndices={result.used_indices} checkSize="50%" />
          </div>
          <button className="btn-download"
            onClick={e => { e.stopPropagation(); onDownload(result.palette_name) }}>
            download
          </button>
        </div>

        {/* row 2: animation + zoom */}
        <div className="list-row-2">
          {isOWSprite && <WalkAnimation spriteB64={result.image} />}
          <div className="list-zoom">
            <ZoomableImage src={result.image} alt={result.palette_name} />
          </div>
        </div>

        {/* row 3: frames */}
        {isOWSprite && (
          <FramesSection b64={result.image} frameCount={frameCount} setFrameCount={setFrameCount} />
        )}
      </div>
    )
  }

  // grid mode
  return (
    <div
      className={`result-card ${selected ? 'selected' : ''} ${result.best ? 'best' : ''}`}
      onClick={onSelect}
    >
      {/* row 1: name -- colors -- best tag inline */}
      <div className="result-header">
        <span className="result-name">{result.palette_name.replace('.pal', '')}</span>
        <span className="result-colors">{colorsLabel} colors</span>
      </div>

      {/* row 2: palette strip */}
      <PaletteStrip colors={result.colors} usedIndices={result.used_indices} checkSize="100%" />

      {/* row 3: full-width zoomable image */}
      <ZoomableImage src={result.image} alt={result.palette_name} />

      {/* row 4: animation */}
      {isOWSprite && <WalkAnimation spriteB64={result.image} />}

      {/* row 5: frames + download */}
      <div className="grid-footer" onClick={e => e.stopPropagation()}>
        {isOWSprite && (
          <FramesSection b64={result.image} frameCount={frameCount} setFrameCount={setFrameCount} />
        )}
        <button className="btn-download full-width"
          onClick={e => { e.stopPropagation(); onDownload(result.palette_name) }}>
          download
        </button>
      </div>
    </div>
  )
}```

----

# frontend/src/components/WalkAnimation.css
```css
.walk-animation { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.walk-canvas {
  image-rendering: pixelated;
  image-rendering: crisp-edges;
  /* JS sets width/height style to DISPLAY_SIZE px — keeps it square */
  background: repeating-conic-gradient(#1c2330 0% 25%, #161b22 0% 50%) 0 0/14px 14px;
  border-radius: 4px;
  display: block;
  flex-shrink: 0;
}
.walk-loading { width: 120px; height: 120px; display: flex; align-items: center; justify-content: center; }```

----

# frontend/src/components/WalkAnimation.jsx
```jsx
import { useEffect, useRef, useState } from 'react'
import './WalkAnimation.css'
import { splitFrames } from '../utils'

// 0: down
// 1: up
// 2: left (right is just flipped left)
// 3: down step 1
// 4: down step 2
// 5: up step 1
// 6: up step 2
// 7: left step 1
// 8: left step 2

// 3,0,4,0,3,0,4,0 - walk down
// 7,2,8,2,7,2,8,2 - walk left
// 5,1,6,1,5,1,6,1 - walk up
// 7f,2f,8f,2f,7f,2f,8f,2f - walk right (flip left frames)

const SEQUENCE = [
    { f: 3 }, { f: 0 }, { f: 4 }, { f: 0 }, // walk down
    { f: 3 }, { f: 0 }, { f: 4 }, { f: 0 }, // walk down
    // { f: 0 }, { f: 0 }, { f: 0 }, { f: 0 }, // idle down
    { f: 7}, { f: 2 }, { f: 8 }, { f: 2 }, // walk left
    { f: 7}, { f: 2 }, { f: 8 }, { f: 2 }, // walk left
    // { f: 2}, { f: 2 }, { f: 2 }, { f: 2 }, // idle left
    { f: 5 }, { f: 1 }, { f: 6 }, { f: 1 }, // walk up
    { f: 5 }, { f: 1 }, { f: 6 }, { f: 1 }, // walk up
    // { f: 1 }, { f: 1 }, { f: 1 }, { f: 1 }, // idle up
    { f: 7, flip: true}, { f: 2, flip: true}, { f: 8, flip: true}, { f: 2, flip: true}, // walk right
    { f: 7, flip: true}, { f: 2, flip: true}, { f: 8, flip: true}, { f: 2, flip: true}, // walk right
    // { f: 2, flip: true}, { f: 2, flip: true}, { f: 2, flip: true}, { f: 2, flip: true}, // idle right
]
const FRAME_MS = 150
const DISPLAY_SIZE = 120 // fixed square display in CSS px

export function WalkAnimation({ spriteB64 }) {
  const canvasRef = useRef()
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    let cancelled = false
    let timer = null
    setStatus('loading')

    const run = async () => {
      try {
        const b64Frames = await splitFrames(spriteB64, 9)
        if (cancelled) return
        if (b64Frames.length < 9) { setStatus('error'); return }

        // Draw each frame into an offscreen canvas — avoids XrayWrapper issues
        const offscreens = await Promise.all(b64Frames.map(b64 => new Promise((resolve, reject) => {
          const img = new Image()
          img.onload = () => {
            const c = document.createElement('canvas')
            c.width = img.width
            c.height = img.height
            c.getContext('2d').drawImage(img, 0, 0)
            resolve(c)
          }
          img.onerror = reject
          img.src = `data:image/png;base64,${b64}`
        })))

        if (cancelled) return

        const canvas = canvasRef.current
        if (!canvas) return

        const fw = offscreens[0].width
        const fh = offscreens[0].height

        // Canvas internal resolution = one frame (square)
        canvas.width = fw
        canvas.height = fh
        // CSS display size = fixed square
        canvas.style.width = `${DISPLAY_SIZE}px`
        canvas.style.height = `${DISPLAY_SIZE}px`

        const ctx = canvas.getContext('2d')
        ctx.imageSmoothingEnabled = false

        let seq = 0
        const draw = () => {
          const step = SEQUENCE[seq % SEQUENCE.length]
          const src = offscreens[step.f]
          ctx.clearRect(0, 0, fw, fh)
          if (step.flip) {
            ctx.save(); ctx.translate(fw, 0); ctx.scale(-1, 1)
          }
          ctx.drawImage(src, 0, 0)
          if (step.flip) ctx.restore()
          seq++
        }

        draw()
        setStatus('ready')
        timer = setInterval(draw, FRAME_MS)
      } catch {
        if (!cancelled) setStatus('error')
      }
    }

    run()
    return () => { cancelled = true; clearInterval(timer) }
  }, [spriteB64])

  if (status === 'error') return null

  return (
    <div className="walk-animation">
      {status === 'loading' && <div className="walk-loading"><div className="spinner" style={{ width: 16, height: 16 }} /></div>}
      <canvas ref={canvasRef} className="walk-canvas" style={{ display: status === 'ready' ? 'block' : 'none' }} />
    </div>
  )
}```

----

# frontend/src/components/ZoomableImage.css
```css
.zoomable-wrap { background: repeating-conic-gradient(#1c2330 0% 25%, #161b22 0% 50%) 0 0/14px 14px; border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
.zoom-controls { display: flex; align-items: center; gap: 4px; padding: 4px 6px; background: rgba(14,17,23,0.85); border-bottom: 1px solid var(--border); }
.zoom-btn { width: 22px; height: 22px; background: var(--surface2); border: 1px solid var(--border); border-radius: 4px; color: var(--text); font-family: var(--mono); font-size: 13px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: border-color 0.1s; padding: 0; }
.zoom-btn:hover { border-color: var(--accent); color: var(--accent); }
.zoom-label { font-family: var(--mono); font-size: 11px; color: var(--muted); min-width: 24px; text-align: center; }
.zoomable-scroll { overflow: auto; max-height: 220px; }

/* picking mode */
.zoomable-picking .zoomable-scroll { cursor: crosshair; }

/* hidden canvas used only for getImageData sampling — never visible */
.zoomable-sample-canvas { display: none; }```

----

# frontend/src/components/ZoomableImage.jsx
```jsx
import { useState, useRef, useCallback } from 'react'
import './ZoomableImage.css'

const ZOOM_LEVELS = [0.25, 0.5, 1, 2, 4, 8, 16, 32, 64]
const MIN_ZOOM = ZOOM_LEVELS[0]
const MAX_ZOOM = ZOOM_LEVELS[ZOOM_LEVELS.length - 1]

export function ZoomableImage({ src, alt = '', picking = false, onPick }) {
  const [zoom, setZoom] = useState(1)
  const [hoverColor, setHoverColor] = useState(null)
  const [hoverPos, setHoverPos] = useState(null)

  const canvasRef = useRef()
  const imgRef = useRef()

  const canvasRefCallback = useCallback((canvas) => {
    canvasRef.current = canvas
    if (!canvas || !src) return

    const img = new window.Image()
    img.onload = () => {
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      canvas.getContext('2d').drawImage(img, 0, 0)
    }

    img.src = `data:image/png;base64,${src}`
  }, [src])

  const changeZoom = (delta) => {
    setZoom((z) => {
      const index = ZOOM_LEVELS.indexOf(z)
      const nextIndex = index + (delta > 0 ? 1 : -1)

      if (nextIndex < 0 || nextIndex >= ZOOM_LEVELS.length) return z
      return ZOOM_LEVELS[nextIndex]
    })
  }

  const getColorAtEvent = (e) => {
    const canvas = canvasRef.current
    if (!canvas) return null

    const rect = imgRef.current.getBoundingClientRect()

    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height

    const x = Math.floor((e.clientX - rect.left) * scaleX)
    const y = Math.floor((e.clientY - rect.top) * scaleY)

    if (x < 0 || y < 0 || x >= canvas.width || y >= canvas.height) return null

    const [r, g, b] = canvas.getContext('2d').getImageData(x, y, 1, 1).data

    return `#${r.toString(16).padStart(2, '0')}${g
      .toString(16)
      .padStart(2, '0')}${b.toString(16).padStart(2, '0')}`.toUpperCase()
  }

  const handleMouseMove = (e) => {
    if (!picking) return

    setHoverPos({ x: e.clientX, y: e.clientY })
    setHoverColor(getColorAtEvent(e))
  }

  const handleMouseLeave = () => {
    setHoverPos(null)
    setHoverColor(null)
  }

  const handleClick = (e) => {
    if (!picking || !onPick) return

    e.stopPropagation()

    const hex = getColorAtEvent(e)
    if (hex) onPick(hex)
  }

  return (
    <>
      <div className={`zoomable-wrap ${picking ? 'zoomable-picking' : ''}`}>
        <div className="zoom-controls">
          <button className="zoom-btn" onClick={() => changeZoom(1)}>+</button>
          <span className="zoom-label">{zoom}×</span>
          <button className="zoom-btn" onClick={() => changeZoom(-1)}>−</button>
          <button
            className="zoom-btn"
            onClick={() => setZoom(1)}
            title="reset"
          >
            ⟳
          </button>
        </div>

        <div className="zoomable-scroll">
          <img
            ref={imgRef}
            src={`data:image/png;base64,${src}`}
            alt={alt}
            className="pixel-img"
            style={{ width: `${zoom * 100}%`, maxWidth: 'none' }}
            draggable={false}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            onClick={handleClick}
          />
        </div>

        <canvas
          ref={canvasRefCallback}
          className="zoomable-sample-canvas"
        />
      </div>

      {picking && hoverPos && hoverColor && (
        <div
          className="pipette-preview"
          style={{
            left: hoverPos.x + 16,
            top: hoverPos.y + 16
          }}
        >
          <div
            className="pipette-swatch"
            style={{ background: hoverColor }}
          />
          <span className="pipette-hex">{hoverColor}</span>
        </div>
      )}
    </>
  )
}```

----

# frontend/src/main.jsx
```jsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './App.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

----

# frontend/src/tabs/BatchTab.css
```css
.batch-layout { display: flex; flex-direction: column; gap: 18px; max-width: 480px; }
.file-list { display: flex; flex-wrap: wrap; gap: 6px; }
.file-chip { font-family: var(--mono); font-size: 11px; background: var(--surface2); border: 1px solid var(--border); color: var(--muted); padding: 3px 8px; border-radius: 4px; }
```

----

# frontend/src/tabs/BatchTab.jsx
```jsx
import { useState, useRef } from 'react'
import { useFetch } from '../hooks/useFetch'
import './BatchTab.css'
import { downloadBlob } from '../utils'

const API = '/api'

export function BatchTab({ palettes }) {
  const [files, setFiles] = useState([])
  const [paletteName, setPaletteName] = useState('')
  const { loading, error, run } = useFetch()
  const inputRef = useRef()

  const handleBatch = async () => {
    const fd = new FormData()
    files.forEach(f => fd.append('files', f))
    fd.append('palette_name', paletteName)
    await run(async () => {
      const res = await fetch(`${API}/batch`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      downloadBlob(await res.blob(), 'batch_output.zip')
    })
  }

  return (
    <div className="tab-content">
      <div className="batch-layout">

        <div className="field">
          <label className="field-label">sprites</label>
          <button className="btn-secondary" onClick={() => inputRef.current.click()}>
            select files ({files.length} selected)
          </button>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept="image/*"
            style={{ display: 'none' }}
            onChange={e => setFiles(Array.from(e.target.files))}
          />
        </div>

        {files.length > 0 && (
          <div className="file-list">
            {files.map(f => (
              <span key={f.name} className="file-chip">{f.name}</span>
            ))}
          </div>
        )}

        <div className="field">
          <label className="field-label">target palette</label>
          <select
            className="field-input"
            value={paletteName}
            onChange={e => setPaletteName(e.target.value)}
          >
            <option value="">select palette…</option>
            {palettes.map(p => (
              <option key={p.name} value={p.name}>{p.name.replace('.pal', '')}</option>
            ))}
          </select>
        </div>

        <button
          className="btn-primary"
          disabled={files.length === 0 || !paletteName || loading}
          onClick={handleBatch}
        >
          {loading ? 'processing…' : `convert ${files.length} sprites → zip`}
        </button>

        {error && <p className="error-msg">{error}</p>}

      </div>
    </div>
  )
}
```

----

# frontend/src/tabs/ConvertTab.css
```css
.convert-layout { display: grid; grid-template-columns: 280px 1fr; gap: 28px; align-items: start; }
.convert-left { display: flex; flex-direction: column; gap: 14px; }
.convert-right { min-height: 400px; display: flex; flex-direction: column; gap: 12px; }

/* original preview */
.original-preview { display: flex; flex-direction: column; gap: 8px; }

/* toolbar */
.results-toolbar { display: flex; align-items: center; justify-content: space-between; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
.results-count { font-family: var(--mono); font-size: 11px; color: var(--muted); }
.toolbar-right { display: flex; align-items: center; gap: 8px; }
.view-toggle { display: flex; gap: 2px; }
.view-btn { width: 28px; height: 28px; background: transparent; border: 1px solid var(--border); border-radius: var(--radius); color: var(--muted); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: color 0.1s, border-color 0.1s, background 0.1s; }
.view-btn:hover { color: var(--text); border-color: var(--border2); }
.view-btn.active { color: var(--accent); border-color: var(--accent); background: rgba(88,166,255,0.08); }

/* results */
.results-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.results-list { display: flex; flex-direction: column; gap: 8px; }

/* palette manager button */
.palette-mgr-btn { display: flex; align-items: center; gap: 5px; padding: 4px 8px; background: var(--surface2); border: 1px solid var(--border); border-radius: var(--radius); font-family: var(--mono); font-size: 11px; color: var(--muted); cursor: pointer; transition: color 0.1s, border-color 0.1s; }
.palette-mgr-btn:hover { color: var(--text); border-color: var(--border2); }
.palette-mgr-btn.filtered { color: var(--accent); border-color: var(--accent); background: rgba(88,166,255,0.08); }
.palette-mgr-badge { font-size: 10px; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 0 5px; color: var(--muted); }
.palette-mgr-btn.filtered .palette-mgr-badge { color: var(--accent); border-color: var(--accent); }

/* icon buttons */
.icon-btn { width: 24px; height: 24px; background: var(--surface2); border: 1px solid var(--border); border-radius: var(--radius); color: var(--muted); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: color 0.1s, border-color 0.1s; flex-shrink: 0; }
.icon-btn:hover:not(:disabled) { color: var(--accent); border-color: var(--accent); }
.icon-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.icon-btn--danger:hover:not(:disabled) { color: var(--danger); border-color: var(--danger); }
.hidden-input { display: none; }

@keyframes spin { to { transform: rotate(360deg); } }
.spinning { animation: spin 0.7s linear infinite; }

/* palette modal */
.modal-palettes { width: 520px; max-height: 75vh; }
.modal-header-actions { display: flex; align-items: center; gap: 6px; }
.palette-empty { font-family: var(--mono); font-size: 11px; color: var(--muted); line-height: 1.6; }
.palette-empty code { background: var(--surface2); padding: 1px 4px; border-radius: 3px; }
.palette-select-all { padding-bottom: 8px; border-bottom: 1px solid var(--border); margin-bottom: 4px; }
.palette-checkbox-row { display: flex; align-items: center; gap: 7px; cursor: pointer; font-family: var(--mono); font-size: 11px; color: var(--muted); }
.palette-checkbox-row:hover { color: var(--text); }
.palette-checkbox-row input[type="checkbox"] { accent-color: var(--accent); cursor: pointer; }
.palette-count-badge { margin-left: auto; font-size: 10px; background: var(--surface2); border: 1px solid var(--border); border-radius: 10px; padding: 1px 7px; color: var(--muted); }
.palette-list { display: flex; flex-direction: column; gap: 2px; }
.palette-row { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: var(--radius); border: 1px solid transparent; transition: background 0.1s, border-color 0.1s; }
.palette-row:hover { background: var(--surface2); }
.palette-row.active { border-color: var(--border); background: var(--surface2); }
.palette-row-label { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; cursor: pointer; }
.palette-row-label input[type="checkbox"] { accent-color: var(--accent); cursor: pointer; flex-shrink: 0; }
.palette-row-info { display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 0; }
.palette-name { font-family: var(--mono); font-size: 11px; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }```

----

# frontend/src/tabs/ExtractTab.css
```css
/* ── Layout ── */
.extract-layout { display: grid; grid-template-columns: 260px 1fr; gap: 28px; align-items: start; }
.extract-left { display: flex; flex-direction: column; gap: 14px; }
.extract-right { display: flex; flex-direction: column; gap: 20px; min-height: 400px; }

.extract-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.extract-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ── Previews ── */
.extract-previews { display: flex; flex-direction: column; gap: 20px; }
.extract-preview-section { display: flex; flex-direction: column; gap: 8px; }

.extract-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

/* ── Transparent bg color picker ── */
.bg-mode-row { display: flex; gap: 4px; flex-wrap: wrap; }
.bg-mode-btn {
  display: flex; align-items: center; gap: 4px;
  padding: 4px 10px;
  background: transparent;
  border: 1px solid var(--border2);
  border-radius: var(--radius);
  font-family: var(--mono); font-size: 11px; color: var(--muted);
  cursor: pointer;
  transition: color 0.1s, border-color 0.1s, background 0.1s;
}
.bg-mode-btn:hover { color: var(--text); border-color: var(--border2); }
.bg-mode-btn.active { color: var(--accent); border-color: var(--accent); background: rgba(88,166,255,0.08); }
.bg-mode-btn.picking { color: #EF9F27; border-color: #EF9F27; background: rgba(239,159,39,0.1); }

.bg-color-row { display: flex; align-items: center; gap: 8px; margin-top: 6px; }
.bg-swatch { width: 20px; height: 20px; border-radius: 3px; border: 1px solid rgba(255,255,255,0.15); flex-shrink: 0; }
.field-hint { font-family: var(--mono); font-size: 11px; color: var(--muted); }
.bg-mode-tag { font-family: var(--mono); font-size: 10px; color: var(--muted); opacity: 0.7; }
.field-error { border-color: var(--danger) !important; }
.field-hint-error { font-family: var(--mono); font-size: 11px; color: var(--danger); margin-top: 4px; }

/* ── Pipette ── */
.pick-hint { color: #EF9F27; font-size: 10px; margin-left: 8px; }

.pipette-preview {
  position: fixed;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  background: var(--surface2);
  border: 1px solid var(--border2);
  border-radius: var(--radius);
  pointer-events: none;
  z-index: 1000;
  box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}
.pipette-swatch {
  width: 16px; height: 16px;
  border-radius: 3px;
  border: 1px solid rgba(255,255,255,0.15);
  flex-shrink: 0;
}
.pipette-hex { font-family: var(--mono); font-size: 11px; color: var(--text); }

/* ── Palette strip ── */
.palette-strip-wrap { position: relative; }

/* ── Buttons ── */
.btn-primary-sm {
  padding: 5px 12px;
  background: var(--accent); color: var(--bg);
  border: none; border-radius: var(--radius);
  font-family: var(--mono); font-size: 12px; font-weight: 500;
  cursor: pointer; transition: opacity 0.15s; white-space: nowrap;
}
.btn-primary-sm:hover:not(:disabled) { opacity: 0.85; }
.btn-primary-sm:disabled { opacity: 0.35; cursor: not-allowed; }

.btn-dl {
  padding: 3px 8px;
  background: transparent;
  border: 1px solid var(--border2); border-radius: var(--radius);
  color: var(--muted);
  font-family: var(--mono); font-size: 11px;
  cursor: pointer; white-space: nowrap; flex-shrink: 0;
  transition: border-color 0.15s, color 0.15s;
}
.btn-dl:hover { border-color: var(--accent); color: var(--accent); }

.help-btn {
  width: 28px; height: 28px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--muted);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: color 0.1s, border-color 0.1s;
  flex-shrink: 0;
}
.help-btn:hover { color: var(--accent); border-color: var(--accent); }

/* ── Modal ── */
.modal-backdrop {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center;
  z-index: 500;
}
.modal-box {
  background: var(--surface);
  border: 1px solid var(--border2);
  border-radius: 8px;
  width: 480px; max-width: 95vw; max-height: 85vh;
  display: flex; flex-direction: column;
  overflow: hidden;
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}
.modal-title { font-family: var(--mono); font-size: 13px; font-weight: 600; color: var(--text); }
.modal-close {
  background: none; border: none; color: var(--muted);
  cursor: pointer; padding: 2px;
  display: flex; align-items: center; border-radius: 3px;
}
.modal-close:hover { color: var(--text); }
.modal-body {
  padding: 16px; overflow-y: auto;
  display: flex; flex-direction: column; gap: 16px;
}
.modal-desc { font-size: 13px; color: var(--muted); line-height: 1.5; }

/* ── Help modal content ── */
.help-steps { display: flex; flex-direction: column; gap: 14px; }
.help-step { display: flex; gap: 12px; align-items: flex-start; }
.help-step-num {
  width: 22px; height: 22px; flex-shrink: 0;
  background: var(--accent); color: var(--bg);
  border-radius: 50%;
  font-family: var(--mono); font-size: 11px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  margin-top: 1px;
}
.help-step strong { font-size: 13px; color: var(--text); display: block; margin-bottom: 3px; }
.help-step p { font-size: 12px; color: var(--muted); line-height: 1.5; margin: 0; }
.help-list {
  margin: 6px 0 0 0; padding-left: 0;
  list-style: none;
  display: flex; flex-direction: column; gap: 4px;
}
.help-list li { font-size: 12px; color: var(--muted); line-height: 1.5; }
.help-tag {
  font-family: var(--mono); font-size: 10px;
  background: var(--surface2); color: var(--text);
  border: 1px solid var(--border2);
  padding: 1px 5px; border-radius: 3px; margin-right: 4px;
}
.help-step code {
  font-family: var(--mono); font-size: 11px;
  background: var(--surface2); padding: 1px 4px; border-radius: 3px; color: var(--text);
}
.help-note {
  font-size: 12px; color: var(--muted);
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 10px 12px; line-height: 1.5;
}
.help-note strong { color: var(--text); }```

----

# frontend/src/tabs/ExtractTab.jsx
```jsx
import { useState, useEffect } from 'react'
import './ExtractTab.css'
import { DropZone } from '../components/DropZone'
import { ZoomableImage } from '../components/ZoomableImage'
import { PaletteStrip } from '../components/PaletteStrip'
import { useFetch } from '../hooks/useFetch'
import { Info, Pipette, PaintBucket, X, Eclipse, Palette, Scan } from 'lucide-react'
import { ColorSwatch } from '../components/ColorSwatch'

const API = '/api'
const GBA_TRANSPARENT = '#73C5A4'
const MAX_COLORS = 16
const MAX_EXTRA_COLORS = MAX_COLORS - 1

// ---------------------------------------------------------------------------
// Corner-based background color detection
// Samples the 4 corners, returns the majority color.
// Falls back to top-left if all 4 differ.
// ---------------------------------------------------------------------------
function detectBgColor(imageB64) {
  return new Promise(resolve => {
    const img = new window.Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0)
      const w = canvas.width - 1
      const h = canvas.height - 1
      const corners = [
        ctx.getImageData(0, 0, 1, 1).data,
        ctx.getImageData(w, 0, 1, 1).data,
        ctx.getImageData(0, h, 1, 1).data,
        ctx.getImageData(w, h, 1, 1).data,
      ].map(d => {
        if (d[3] < 128) return null  // skip transparent corners
        return `#${d[0].toString(16).padStart(2,'0')}${d[1].toString(16).padStart(2,'0')}${d[2].toString(16).padStart(2,'0')}`
      })
      const counts = {}
      for (const c of corners) {
        if (c) counts[c] = (counts[c] || 0) + 1
      }
      const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1])
      resolve(sorted.length > 0 ? sorted[0][0] : GBA_TRANSPARENT)
    }
    img.src = `data:image/png;base64,${imageB64}`
  })
}

// ---------------------------------------------------------------------------
// Help modal
// ---------------------------------------------------------------------------
function HelpModal({ onClose }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">palette extraction</span>
          <button className="modal-close" onClick={onClose}><X size={16}/></button>
        </div>
        <div className="modal-body">
          <p className="modal-desc">
            Extracts a GBA-compatible 16-color palette from any sprite using k-means clustering.
            Both color spaces are shown so you can pick the best result.
          </p>
          <div className="help-steps">
            <div className="help-step">
              <span className="help-step-num">1</span>
              <div>
                <strong>Drop a sprite</strong>
                <p>Any PNG or image with the colors you want to extract.</p>
              </div>
            </div>
            <div className="help-step">
              <span className="help-step-num">2</span>
              <div>
                <strong>Set the transparent color (slot 0)</strong>
                <p>This color will always be first in the palette. The GBA uses slot 0 as the background/transparent color.</p>
                <ul className="help-list">
                  <li><span className="help-tag">auto <Scan size={8} /></span> samples the 4 corners and picks the majority color — works for most sprites</li>
                  <li><span className="help-tag">default <Eclipse size={8} /></span> uses <code><ColorSwatch hex="#73C5A4" />#73C5A4</code>, the standard GBA transparent green</li>
                  <li><span className="help-tag">custom <PaintBucket size={8} /></span> lets you type any hex value</li>
                  <li><span className="help-tag">pipette <Pipette size={8} /></span> click any pixel on your sprite to sample it directly</li>
                </ul>
              </div>
            </div>
            <div className="help-step">
              <span className="help-step-num">3</span>
              <div>
                <strong>Choose color count</strong>
                <p>Max 15 sprite colors + 1 transparent = 16 total. GBA palettes are hard-limited to 16 colors per palette bank.</p>
              </div>
            </div>
            <div className="help-step">
              <span className="help-step-num">4</span>
              <div>
                <strong>Compare & Download</strong>
                <p>
                  <strong>Oklab:</strong> Clusters by perceptual similarity. <b>RECOMMENDED.</b>{' '}
                  <strong>RGB:</strong> Clusters by raw channel distance. (Less faithful to original colors.)
                </p>
              </div>
            </div>
          </div>
          <div className="help-note">
            <strong>JASC-PAL format</strong> — compatible with Porypal, Usenti, and most GBA sprite editors.
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Remap preview
// ---------------------------------------------------------------------------
function hexToRgb(hex) {
  const h = hex.replace('#', '')
  return [parseInt(h.slice(0,2),16), parseInt(h.slice(2,4),16), parseInt(h.slice(4,6),16)]
}

function remapToPalette(imageB64, paletteHexColors) {
  return new Promise(resolve => {
    const img = new window.Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0)
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
      const data = imageData.data
      const palette = paletteHexColors.map(hexToRgb)
      const [tr, tg, tb] = palette[0]
      for (let i = 0; i < data.length; i += 4) {
        if (data[i+3] < 128) {
          data[i] = tr; data[i+1] = tg; data[i+2] = tb; data[i+3] = 255
          continue
        }
        const r = data[i], g = data[i+1], b = data[i+2]
        let bestIdx = 0, bestDist = Infinity
        for (let j = 0; j < palette.length; j++) {
          const [pr,pg,pb] = palette[j]
          const dist = (r-pr)**2 + (g-pg)**2 + (b-pb)**2
          if (dist < bestDist) { bestDist = dist; bestIdx = j }
        }
        ;[data[i], data[i+1], data[i+2]] = palette[bestIdx]
      }
      ctx.putImageData(imageData, 0, 0)
      resolve(canvas.toDataURL('image/png').split(',')[1])
    }
    img.src = `data:image/png;base64,${imageB64}`
  })
}

// ---------------------------------------------------------------------------
// Tab
// ---------------------------------------------------------------------------
export function ExtractTab() {
  const [file, setFile]               = useState(null)
  const [originalB64, setOriginalB64] = useState(null)
  const [nColors, setNColors]         = useState(15)
  const [bgColor, setBgColor]         = useState(GBA_TRANSPARENT)
  const [bgMode, setBgMode]           = useState('default')
  const [imageSize, setImageSize]     = useState(null)

  const [resultOklab, setResultOklab]   = useState(null)
  const [resultRgb, setResultRgb]       = useState(null)
  const [previewOklab, setPreviewOklab] = useState(null)
  const [previewRgb, setPreviewRgb]     = useState(null)

  const [picking, setPicking]   = useState(false)
  const [showHelp, setShowHelp] = useState(false)

  const { loading, error, run } = useFetch()

  useEffect(() => {
    if (!originalB64) return
    const img = new window.Image()
    img.onload = () => setImageSize({ w: img.naturalWidth, h: img.naturalHeight })
    img.src = `data:image/png;base64,${originalB64}`
  }, [originalB64])

  useEffect(() => {
    if (!originalB64) return
    if (resultOklab?.colors?.length > 1)
      remapToPalette(originalB64, resultOklab.colors).then(setPreviewOklab)
    else
      setPreviewOklab(null)
    if (resultRgb?.colors?.length > 1)
      remapToPalette(originalB64, resultRgb.colors).then(setPreviewRgb)
    else
      setPreviewRgb(null)
  }, [resultOklab, resultRgb, originalB64])

  const handleFile = (f) => {
    setFile(f)
    setResultOklab(null); setResultRgb(null)
    setPreviewOklab(null); setPreviewRgb(null)
    const reader = new FileReader()
    reader.onload = e => {
      const b64 = e.target.result.split(',')[1]
      setOriginalB64(b64)
      // Auto-detect bg color from corners on every new file
      detectBgColor(b64).then(detected => {
        setBgColor(detected)
        setBgMode('auto')
      })
    }
    reader.readAsDataURL(f)
  }

  const runExtract = async (space) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('n_colors', nColors)
    fd.append('bg_color', bgColor)
    fd.append('color_space', space)
    const res = await fetch(`${API}/extract`, { method: 'POST', body: fd })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  }

  const handleExtract = () => {
    if (!file) return
    run(async () => {
      const [oklab, rgb] = await Promise.all([runExtract('oklab'), runExtract('rgb')])
      setResultOklab(oklab)
      setResultRgb(rgb)
    })
  }

  const downloadPal = (result) => {
    const blob = new Blob([result.pal_content], { type: 'text/plain' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${result.name}_${result.color_space}.pal`
    a.click()
  }

  const handlePick = (hex) => {
    setBgColor(hex)
    setBgMode('pick')
    setPicking(false)
  }

  const tooMany = nColors > MAX_EXTRA_COLORS

  return (
    <div className="tab-content">
      {showHelp && <HelpModal onClose={() => setShowHelp(false)} />}

      <div className="extract-layout">

        {/* ── Left: controls ── */}
        <div className="extract-left">
          <DropZone onFile={handleFile} label="Drop sprite to extract palette" />

          <div className="field">
            <label className="field-label">colors (max 15 + transparent = 16 for GBA)</label>
            <input
              type="number"
              className={`field-input ${tooMany ? 'field-error' : ''}`}
              min={1} max={MAX_EXTRA_COLORS}
              value={nColors}
              onChange={e => setNColors(Number(e.target.value))}
            />
            {tooMany && (
              <p className="field-hint-error">
                GBA supports max 16 colors — slot 0 is reserved for transparent, leaving 15 for sprite colors
              </p>
            )}
          </div>

          <div className="field">
            <label className="field-label">transparent color (slot 0)</label>
            <div className="bg-mode-row">
              {originalB64 && (
                <button
                  className={`bg-mode-btn ${bgMode === 'auto' ? 'active' : ''}`}
                  onClick={() =>
                    detectBgColor(originalB64).then(detected => {
                      setBgColor(detected); setBgMode('auto')
                    })
                  }
                  title="detect from image corners"
                >auto <Scan size={8} /></button>
              )}
              <button
                className={`bg-mode-btn ${bgMode === 'default' ? 'active' : ''}`}
                onClick={() => { setBgMode('default'); setBgColor(GBA_TRANSPARENT) }}
              >default <Eclipse size={8} /></button>
              <button
                className={`bg-mode-btn ${bgMode === 'custom' ? 'active' : ''}`}
                onClick={() => setBgMode('custom')}
              >custom <PaintBucket size={8} /></button>
              {originalB64 && (
                <button
                  className={`bg-mode-btn ${picking ? 'picking' : ''}`}
                  onClick={() => setPicking(p => !p)}
                  title="click a pixel on the image to pick its color"
                >pipette <Pipette size={8} /></button>
              )}
            </div>

            <div className="bg-color-row">
              <div className="bg-swatch" style={{ background: bgColor }} />
              {bgMode === 'custom' || bgMode === 'pick' ? (
                <input
                  className="field-input field-mono"
                  value={bgColor}
                  onChange={e => setBgColor(e.target.value)}
                  placeholder="#73C5A4"
                  maxLength={7}
                />
              ) : (
                <span className="field-hint">
                  {bgColor}
                  {bgMode === 'auto'    && <span className="bg-mode-tag"> auto-detected</span>}
                  {bgMode === 'default' && <span className="bg-mode-tag"> GBA default</span>}
                </span>
              )}
            </div>
          </div>

          <div className="extract-actions">
            <button
              className="btn-primary"
              disabled={!file || loading || tooMany}
              onClick={handleExtract}
            >
              {loading ? 'extracting… ' : 'extract palette '}
              <Palette size={10} />
            </button>
          </div>

          {error && <p className="error-msg">{error}</p>}
        </div>

        {/* ── Right: stacked previews ── */}
        <div className="extract-right">

          <div className="extract-toolbar">
            <span className="section-label">
              {resultOklab
                ? `${resultOklab.name} — ${resultOklab.colors.length} colors`
                : 'preview'}
            </span>
            <button className="help-btn" onClick={() => setShowHelp(true)} title="Help">
              <Info size={15}/>
            </button>
          </div>

          {!originalB64 && (
            <div className="empty-state">
              drop a sprite to extract a GBA-compatible palette
            </div>
          )}

          {originalB64 && (
            <div className="extract-previews">

              <div className="extract-preview-section">
                <p className="section-label">
                  original{imageSize ? ` — ${imageSize.w}×${imageSize.h}px` : ''}
                  {picking && <span className="pick-hint"> · click to pick bg color</span>}
                </p>
                <ZoomableImage
                  src={originalB64}
                  alt="source sprite"
                  picking={picking}
                  onPick={handlePick}
                />
              </div>

              {previewOklab && resultOklab && (
                <div className="extract-preview-section">
                  <div className="extract-section-header">
                    <p className="section-label">oklab — recommended</p>
                    <button className="btn-dl" onClick={() => downloadPal(resultOklab)}>↓ .pal</button>
                  </div>
                  <ZoomableImage src={previewOklab} alt="oklab preview" />
                  <div className="palette-strip-wrap">
                    <PaletteStrip
                      colors={resultOklab.colors}
                      usedIndices={resultOklab.colors.map((_, i) => i)}
                    />
                  </div>
                </div>
              )}

              {previewRgb && resultRgb && (
                <div className="extract-preview-section">
                  <div className="extract-section-header">
                    <p className="section-label">rgb</p>
                    <button className="btn-dl" onClick={() => downloadPal(resultRgb)}>↓ .pal</button>
                  </div>
                  <ZoomableImage src={previewRgb} alt="rgb preview" />
                  <div className="palette-strip-wrap">
                    <PaletteStrip
                      colors={resultRgb.colors}
                      usedIndices={resultRgb.colors.map((_, i) => i)}
                    />
                  </div>
                </div>
              )}

            </div>
          )}

        </div>

      </div>
    </div>
  )
}```

----

# frontend/src/tabs/TilesetTab.css
```css
.tileset-layout { display: grid; grid-template-columns: 260px 1fr; gap: 28px; align-items: start; }
.tileset-left { display: flex; flex-direction: column; gap: 14px; }
.tileset-right { display: flex; flex-direction: column; gap: 16px; min-height: 400px; }
.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.field-mono { font-family: var(--mono) !important; }

/* toolbar */
.tileset-toolbar { display: flex; align-items: center; justify-content: space-between; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
.help-btn { background: transparent; border: 1px solid var(--border); border-radius: var(--radius); color: var(--muted); cursor: pointer; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; transition: color 0.1s, border-color 0.1s; }
.help-btn:hover { color: var(--accent); border-color: var(--accent); }

/* place hint */
.place-hint { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 6px 10px; background: rgba(74,141,252,0.1); border: 1px solid rgba(74,141,252,0.3); border-radius: var(--radius); font-family: var(--mono); font-size: 12px; color: #4A8DFC; }

/* source sheet */
.source-section { display: flex; flex-direction: column; gap: 6px; }
.source-sheet-wrap { border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; background: repeating-conic-gradient(#1c2330 0% 25%, #161b22 0% 50%) 0 0/14px 14px; }
.source-img { width: 100%; height: auto; display: block; image-rendering: pixelated; image-rendering: crisp-edges; }
.source-grid-container { position: relative; display: block; width: 100%; }
.source-tile-grid {
  position: absolute; inset: 0;
  display: grid;
  grid-template-columns: repeat(var(--src-cols), 1fr);
  grid-template-rows: repeat(var(--src-rows), 1fr);
}
.source-tile {
  border: 0.5px solid rgba(255,255,255,0.15);
  cursor: pointer;
  transition: background 0.08s;
}
.source-tile:hover { background: rgba(255,255,255,0.12); }
.source-tile.selected { background: rgba(74,141,252,0.4); outline: 2px solid #4A8DFC; outline-offset: -1px; }
.selected-hint { color: var(--accent); font-size: 10px; margin-left: 6px; }

/* output grid = preview */
.output-grid {
  display: grid;
  grid-template-columns: repeat(var(--cols, 9), 1fr);
  gap: 3px;
}

.output-slot {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 3px; padding: 3px;
  border-radius: 4px;
  border: 1px dashed var(--border2);
  cursor: pointer; position: relative;
  transition: border-color 0.1s, background 0.1s;
  aspect-ratio: 1;
}
.output-slot.empty { background: var(--surface2); }
.output-slot.droppable { border-color: var(--accent); background: rgba(88,166,255,0.08); }
.output-slot.droppable:hover { background: rgba(88,166,255,0.15); }
.output-slot.filled { border-style: solid; border-color: var(--border); background: var(--surface); }
.output-slot.filled:hover { border-color: var(--border2); }

.slot-img { width: 100%; height: auto; image-rendering: pixelated; image-rendering: crisp-edges; display: block; background: repeating-conic-gradient(#1c2330 0% 25%, #161b22 0% 50%) 0 0/6px 6px; border-radius: 2px; }
.slot-plus { font-size: 16px; color: var(--border2); line-height: 1; }
.slot-label { font-family: var(--mono); font-size: 8px; color: var(--muted); text-align: center; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; width: 100%; }
.slot-clear { position: absolute; top: 2px; right: 2px; background: rgba(0,0,0,0.6); border: none; border-radius: 3px; color: var(--muted); cursor: pointer; padding: 1px; display: flex; align-items: center; opacity: 0; transition: opacity 0.1s; }
.output-slot:hover .slot-clear { opacity: 1; }
.slot-clear:hover { color: var(--danger); }

/* presets */
.preset-section { display: flex; flex-direction: column; gap: 8px; }
.preset-list { display: flex; flex-direction: column; gap: 2px; }
.preset-row {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 8px; border-radius: 4px;
  border: 1px solid var(--border);
  cursor: pointer; background: var(--surface2);
  transition: border-color 0.1s, background 0.1s;
}
.preset-row:hover { border-color: var(--border2); background: var(--surface); }
.preset-row.active { border-color: var(--accent); background: rgba(88,166,255,0.08); }
.preset-name { font-family: var(--mono); font-size: 12px; color: var(--text); flex: 1; }
.preset-meta { font-family: var(--mono); font-size: 10px; color: var(--muted); flex-shrink: 0; }
.preset-delete { background: transparent; border: none; color: var(--muted); cursor: pointer; padding: 2px; display: flex; align-items: center; flex-shrink: 0; opacity: 0; transition: opacity 0.1s, color 0.1s; }
.preset-row:hover .preset-delete { opacity: 1; }
.preset-delete:hover { color: var(--danger); }
.preset-save-btn { display: flex; align-items: center; justify-content: center; gap: 6px; }

/* small primary */
.btn-primary-sm { padding: 5px 12px; background: var(--accent); color: var(--bg); border: none; border-radius: var(--radius); font-family: var(--mono); font-size: 12px; font-weight: 500; cursor: pointer; transition: opacity 0.15s; white-space: nowrap; }
.btn-primary-sm:hover:not(:disabled) { opacity: 0.85; }
.btn-primary-sm:disabled { opacity: 0.35; cursor: not-allowed; }

/* modal */
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 1000; display: flex; align-items: center; justify-content: center; }
.modal-box { background: var(--surface); border: 1px solid var(--border2); border-radius: 12px; width: 520px; max-width: 90vw; max-height: 80vh; display: flex; flex-direction: column; overflow: hidden; }
.modal-sm { width: 360px; }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; border-bottom: 1px solid var(--border); }
.modal-title { font-family: var(--mono); font-size: 13px; font-weight: 500; }
.modal-close { background: transparent; border: none; color: var(--muted); cursor: pointer; padding: 2px; display: flex; align-items: center; }
.modal-close:hover { color: var(--text); }
.modal-body { padding: 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; }
.modal-desc { font-size: 13px; color: var(--muted); line-height: 1.6; }
.modal-note { font-size: 12px; color: var(--muted); font-style: italic; border-left: 2px solid var(--border2); padding-left: 10px; }
.frame-reference { display: flex; flex-direction: column; gap: 2px; }
.frame-ref-row { display: flex; align-items: center; gap: 12px; padding: 5px 8px; border-radius: 4px; border: 1px solid var(--border); background: var(--surface2); }
.frame-ref-idx { font-family: var(--mono); font-size: 12px; font-weight: 500; color: var(--accent); width: 20px; flex-shrink: 0; }
.frame-ref-label { font-family: var(--mono); font-size: 12px; }
.modal-examples { display: flex; flex-direction: column; gap: 10px; }
.example-imgs { display: flex; flex-direction: column; gap: 12px; width: 100%; }
.example-img-wrap { display: flex; flex-direction: column; gap: 4px; width: 100%; }
.example-img { image-rendering: pixelated; image-rendering: crisp-edges; background: repeating-conic-gradient(#1c2330 0% 25%, #161b22 0% 50%) 0 0/8px 8px; border: 1px solid var(--border); border-radius: 4px; width: 100%; height: auto; display: block; }
.example-caption { font-family: var(--mono); font-size: 10px; color: var(--muted); }```

----

# frontend/src/tabs/TilesetTab.jsx
```jsx
import { useState, useEffect } from 'react'
import './TilesetTab.css'
import { DropZone } from '../components/DropZone'
import { useFetch } from '../hooks/useFetch'
import { downloadBlob } from '../utils'
import { Info, X, Save } from 'lucide-react'
import { PresetList } from '../components/PresetList'

const API = '/api'

const OW_LABELS = [
  'down idle','up idle','left idle',
  'down walk 1','down walk 2',
  'up walk 1','up walk 2',
  'left walk 1','left walk 2',
]

function useDebounce(value, delay) {
  const [d, setD] = useState(value)
  useEffect(() => { const t = setTimeout(() => setD(value), delay); return () => clearTimeout(t) }, [value, delay])
  return d
}

// ---- Help Modal ----
function HelpModal({ onClose }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Overworld sprite format</span>
          <button className="modal-close" onClick={onClose}><X size={16}/></button>
        </div>
        <div className="modal-body">
          <p className="modal-desc">Gen 3 overworld sprites are 9-frame spritesheets arranged horizontally:</p>
          <div className="frame-reference">
            {OW_LABELS.map((label, i) => (
              <div key={i} className="frame-ref-row">
                <span className="frame-ref-idx">{i}</span>
                <span className="frame-ref-label">{label}</span>
              </div>
            ))}
          </div>
          <p className="modal-note">Right-facing frames are generated by flipping left-facing frames at runtime.</p>
          <div className="modal-examples">
            <p className="section-label" style={{ marginBottom: 8 }}>examples</p>
            <div className="example-imgs">
              <div className="example-img-wrap">
                <img src="/example/e4.png" alt="e4" className="example-img" draggable={false}/>
                <span className="example-caption">NDS styled sprite</span>
              </div>
              <div className="example-img-wrap">
                <img src="/example/waiter_f.png" alt="waiter" className="example-img" draggable={false}/>
                <span className="example-caption">waiter_f.png</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ---- Save preset modal ----
function SaveModal({ onSave, onClose }) {
  const [name, setName] = useState('')
  const [id, setId] = useState('')
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box modal-sm" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">save preset</span>
          <button className="modal-close" onClick={onClose}><X size={16}/></button>
        </div>
        <div className="modal-body" style={{ gap: 12 }}>
          <div className="field">
            <label className="field-label">name</label>
            <input className="field-input" value={name}
              onChange={e => { setName(e.target.value); setId(e.target.value.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_+|_+$/g,'')) }}
              placeholder="My custom preset" />
          </div>
          <div className="field">
            <label className="field-label">id</label>
            <input className="field-input field-mono" value={id}
              onChange={e => setId(e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g,''))}
              placeholder="my_custom_preset" />
          </div>
          <button className="btn-primary" disabled={!name || !id} onClick={() => onSave(id, name)}>save</button>
        </div>
      </div>
    </div>
  )
}

// ---- Source sheet — plain div grid over the image ----
function SourceSheet({ b64, sourceW, sourceH, tileW, tileH, selectedTile, onTileClick }) {
  if (!b64) return null
  const cols = Math.max(1, Math.floor(sourceW / tileW))
  const rows = Math.max(1, Math.floor(sourceH / tileH))
  const total = cols * rows

  return (
    <div className="source-sheet-wrap">
      <div className="source-grid-container">
        <img src={`data:image/png;base64,${b64}`} alt="source" className="source-img" draggable={false}/>
        <div className="source-tile-grid" style={{ '--src-cols': cols, '--src-rows': rows }}>
          {Array.from({ length: total }).map((_, idx) => (
            <div
              key={idx}
              className={`source-tile ${selectedTile === idx ? 'selected' : ''}`}
              onClick={() => onTileClick(idx)}
              title={`tile ${idx}`}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

// ---- Output grid ----
function OutputGrid({ slots, setSlots, cols, rows, tiles, selectedTile, setSelectedTile, slotLabels }) {
  const handleSlotClick = (idx) => {
    if (selectedTile !== null) {
      // place selected tile into this slot
      setSlots(prev => { const s = [...prev]; s[idx] = selectedTile; return s })
      setSelectedTile(null)
    } else if (slots[idx] !== null && slots[idx] !== undefined) {
      // pick tile back out of slot
      setSelectedTile(slots[idx])
      setSlots(prev => { const s = [...prev]; s[idx] = null; return s })
    }
  }

  const clearSlot = (e, idx) => {
    e.stopPropagation()
    setSlots(prev => { const s = [...prev]; s[idx] = null; return s })
  }

  const canPlace = selectedTile !== null

  return (
    <div className="output-grid" style={{ '--cols': cols }}>
      {Array.from({ length: cols * rows }).map((_, idx) => {
        const tileIdx = slots[idx]
        const hasTile = tileIdx !== null && tileIdx !== undefined
        const label = slotLabels?.[idx] ?? String(idx)

        return (
          <div
            key={idx}
            className={`output-slot ${hasTile ? 'filled' : 'empty'} ${canPlace && !hasTile ? 'droppable' : ''}`}
            onClick={() => handleSlotClick(idx)}
          >
            {hasTile && tiles?.[tileIdx]
              ? <img src={`data:image/png;base64,${tiles[tileIdx]}`} alt={label} className="slot-img" draggable={false}/>
              : <span className="slot-plus">+</span>
            }
            <span className="slot-label">{label}</span>
            {hasTile && (
              <button className="slot-clear" onClick={e => clearSlot(e, idx)}><X size={9}/></button>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ---- Download: assemble canvas client-side ----
function buildAndDownload(tiles, slots, cols, rows, tileW, tileH, filename) {
  const canvas = document.createElement('canvas')
  canvas.width = cols * tileW
  canvas.height = rows * tileH
  const ctx = canvas.getContext('2d')
  ctx.imageSmoothingEnabled = false

  Promise.all(slots.map((tileIdx, pos) => {
    if (tileIdx === null || tileIdx === undefined || !tiles[tileIdx]) return Promise.resolve()
    return new Promise(res => {
      const img = new Image()
      img.onload = () => {
        ctx.drawImage(img, (pos % cols) * tileW, Math.floor(pos / cols) * tileH, tileW, tileH)
        res()
      }
      img.src = `data:image/png;base64,${tiles[tileIdx]}`
    })
  })).then(() => canvas.toBlob(blob => downloadBlob(blob, filename), 'image/png'))
}

// ---- Main ----
export function TilesetTab() {
  const [file, setFile] = useState(null)
  const [tileW, setTileW] = useState(32)
  const [tileH, setTileH] = useState(32)
  const [cols, setCols] = useState(9)
  const [rows, setRows] = useState(1)
  const [slotLabels, setSlotLabels] = useState([])
  const [result, setResult] = useState(null)
  const [slots, setSlots] = useState(Array(9).fill(null))
  const [selectedTile, setSelectedTile] = useState(null)
  const [showHelp, setShowHelp] = useState(false)
  const [showSave, setShowSave] = useState(false)
  const [presets, setPresets] = useState([])
  const [activePresetId, setActivePresetId] = useState(null)
  const [defaultIds, setDefaultIds] = useState(new Set())
  const { loading, error, run } = useFetch()

  const dTileW = useDebounce(tileW, 500)
  const dTileH = useDebounce(tileH, 500)

  const fetchPresets = () =>
    fetch(`${API}/presets`).then(r => r.json()).then(p => {
      setPresets(p)
      setDefaultIds(new Set(p.filter(x => x.is_default).map(x => x.id)))
    }).catch(() => {})

  useEffect(() => { fetchPresets() }, [])

  useEffect(() => {
    if (file) slice(file, dTileW, dTileH)
  }, [dTileW, dTileH])

  const resetSlots = (c, r) => setSlots(Array(c * r).fill(null))

  const slice = async (f, tw, th) => {
    const fd = new FormData()
    fd.append('file', f)
    fd.append('tile_width', tw ?? tileW)
    fd.append('tile_height', th ?? tileH)
    const data = await run(async () => {
      const res = await fetch(`${API}/tileset/slice`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      return res.json()
    })
    if (data) { setResult(data); setSelectedTile(null) }
  }

  const handleFile = (f) => {
    setFile(f); setResult(null); resetSlots(cols, rows); slice(f)
  }

  const handleColsChange = (v) => { setCols(v); resetSlots(v, rows) }
  const handleRowsChange = (v) => { setRows(v); resetSlots(cols, v) }

  const handleLoadPreset = async (id) => {
    const p = await fetch(`${API}/presets/${id}`).then(r => r.json())
    setTileW(p.tile_w); setTileH(p.tile_h)
    setCols(p.cols); setRows(p.rows)
    setSlots(p.slots?.length === p.cols * p.rows ? p.slots : Array(p.cols * p.rows).fill(null))
    setSlotLabels(p.slot_labels || [])
    setActivePresetId(id)
    if (file) slice(file, p.tile_w, p.tile_h)
  }

  const handleSavePreset = async (id, name) => {
    const body = { name, tile_w: tileW, tile_h: tileH, cols, rows, slots, slot_labels: slotLabels.length ? slotLabels : undefined }
    await fetch(`${API}/presets/${id}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    fetchPresets(); setActivePresetId(id); setShowSave(false)
  }

  const handleDeletePreset = async (id) => {
    if (defaultIds.has(id)) return
    await fetch(`${API}/presets/${id}`, { method: 'DELETE' })
    fetchPresets()
    if (activePresetId === id) setActivePresetId(null)
  }

  return (
    <div className="tab-content">
      {showHelp && <HelpModal onClose={() => setShowHelp(false)}/>}
      {showSave && <SaveModal onSave={handleSavePreset} onClose={() => setShowSave(false)}/>}

      <div className="tileset-layout">
        <div className="tileset-left">
          <DropZone onFile={handleFile} label="Drop tileset image"/>

          <div className="field-row">
            <div className="field"><label className="field-label">tile w</label>
              <input type="number" className="field-input" value={tileW} min={8} max={256}
                onChange={e => setTileW(Number(e.target.value))}/></div>
            <div className="field"><label className="field-label">tile h</label>
              <input type="number" className="field-input" value={tileH} min={8} max={256}
                onChange={e => setTileH(Number(e.target.value))}/></div>
          </div>

          <div className="field-row">
            <div className="field"><label className="field-label">cols</label>
              <input type="number" className="field-input" value={cols} min={1} max={32}
                onChange={e => handleColsChange(Number(e.target.value))}/></div>
            <div className="field"><label className="field-label">rows</label>
              <input type="number" className="field-input" value={rows} min={1} max={32}
                onChange={e => handleRowsChange(Number(e.target.value))}/></div>
          </div>

          <div className="preset-section">
            <p className="section-label">presets</p>
            <PresetList
              presets={presets}
              defaultIds={defaultIds}
              activePresetId={activePresetId}
              onLoad={handleLoadPreset}
              onDelete={handleDeletePreset}
              currentState={{ tileW, tileH, cols, rows, slots }}
            />
            <button className="btn-secondary preset-save-btn" onClick={() => setShowSave(true)}>
              <Save size={12}/> save as preset
            </button>
          </div>

          {error && <p className="error-msg">{error}</p>}

          {result && (
            <div className="source-section">
              <p className="section-label">
                source — {result.tile_count} tiles
                {selectedTile !== null
                  ? <span className="selected-hint"> · tile {selectedTile} selected — click a slot</span>
                  : <span className="selected-hint"> · click a tile to select</span>
                }
              </p>
              <SourceSheet
                b64={result.source}
                sourceW={result.source_w}
                sourceH={result.source_h}
                tileW={result.tile_width}
                tileH={result.tile_height}
                selectedTile={selectedTile}
                onTileClick={i => setSelectedTile(prev => prev === i ? null : i)}
              />
            </div>
          )}
        </div>

        <div className="tileset-right">
          <div className="tileset-toolbar">
            <span className="section-label">
              {result ? `output — ${cols}×${rows}` : 'no tileset loaded'}
            </span>
            <div style={{ display: 'flex', gap: 6 }}>
              {result && <>
                <button className="btn-ghost" onClick={() => resetSlots(cols, rows)}>clear</button>
                <button className="btn-primary-sm" onClick={() =>
                  buildAndDownload(result.tiles, slots, cols, rows, result.tile_width, result.tile_height,
                    `${file.name.replace(/\.[^.]+$/, '')}_arranged.png`)}
                  disabled={slots.every(s => s === null)}>
                  download
                </button>
              </>}
              <button className="help-btn" onClick={() => setShowHelp(true)}><Info size={15}/></button>
            </div>
          </div>

          {!result && !loading && <div className="empty-state"><p>drop a tileset to start arranging</p></div>}
          {loading && <div className="empty-state"><div className="spinner"/><p>slicing…</p></div>}

          {result && (
            <>
              {selectedTile !== null && (
                <div className="place-hint">
                  tile {selectedTile} selected — click a slot to place it
                  <button className="btn-ghost" onClick={() => setSelectedTile(null)}>cancel</button>
                </div>
              )}
              <OutputGrid
                slots={slots} setSlots={setSlots}
                cols={cols} rows={rows}
                tiles={result.tiles}
                selectedTile={selectedTile} setSelectedTile={setSelectedTile}
                slotLabels={slotLabels}
              />
            </>
          )}
        </div>
      </div>
    </div>
  )
}```

----

# frontend/src/tabs/convertTab.jsx
```jsx
import { useState, useEffect, useRef } from 'react'
import './ConvertTab.css'
import { DropZone } from '../components/DropZone'
import { ZoomableImage } from '../components/ZoomableImage'
import { WalkAnimation } from '../components/WalkAnimation'
import { ResultCard } from '../components/ResultCard'
import { PaletteStrip } from '../components/PaletteStrip'
import { useFetch } from '../hooks/useFetch'
import { downloadBlob } from '../utils'
import { X, Upload, Trash2, RefreshCw, Layers } from 'lucide-react'

const API = '/api'

function GridIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
      <rect x="0" y="0" width="6" height="6" rx="1"/>
      <rect x="8" y="0" width="6" height="6" rx="1"/>
      <rect x="0" y="8" width="6" height="6" rx="1"/>
      <rect x="8" y="8" width="6" height="6" rx="1"/>
    </svg>
  )
}

function ListIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
      <rect x="0" y="1" width="14" height="3" rx="1"/>
      <rect x="0" y="6" width="14" height="3" rx="1"/>
      <rect x="0" y="11" width="14" height="3" rx="1"/>
    </svg>
  )
}

// ---- Palette Management Modal ----
function PaletteModal({ palettes, selected, onToggle, onSelectAll, onDeselectAll, onReload, onUpload, onDelete, onClose, reloading }) {
  const fileRef = useRef()
  const allSelected = palettes.length > 0 && palettes.every(p => selected.has(p.name))

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box modal-palettes" onClick={e => e.stopPropagation()}>

        <div className="modal-header">
          <span className="modal-title">manage palettes</span>
          <div className="modal-header-actions">
            <button
              className="icon-btn"
              title="reload from disk"
              onClick={onReload}
              disabled={reloading}
            >
              <RefreshCw size={12} className={reloading ? 'spinning' : ''} />
            </button>
            <button
              className="icon-btn"
              title="upload .pal files"
              onClick={() => fileRef.current?.click()}
            >
              <Upload size={12} />
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".pal"
              multiple
              className="hidden-input"
              onChange={e => { onUpload(e.target.files); e.target.value = '' }}
            />
            <button className="modal-close" onClick={onClose}><X size={16} /></button>
          </div>
        </div>

        <div className="modal-body">
          {palettes.length === 0 ? (
            <p className="palette-empty">
              no palettes loaded — drop <code>.pal</code> files into <code>palettes/</code> or upload above
            </p>
          ) : (
            <>
              <div className="palette-select-all">
                <label className="palette-checkbox-row">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={e => e.target.checked ? onSelectAll() : onDeselectAll()}
                  />
                  <span>{allSelected ? 'deselect all' : 'select all'}</span>
                  <span className="palette-count-badge">{selected.size}/{palettes.length} active</span>
                </label>
              </div>

              <div className="palette-list">
                {palettes.map(p => (
                  <div key={p.name} className={`palette-row ${selected.has(p.name) ? 'active' : ''}`}>
                    <label className="palette-row-label">
                      <input
                        type="checkbox"
                        checked={selected.has(p.name)}
                        onChange={() => onToggle(p.name)}
                      />
                      <div className="palette-row-info">
                        <span className="palette-name">{p.name.replace('.pal', '')}</span>
                        <PaletteStrip colors={p.colors} usedIndices={p.colors.map((_, i) => i)} />
                      </div>
                    </label>
                    <button
                      className="icon-btn icon-btn--danger"
                      title="delete palette"
                      onClick={() => onDelete(p.name)}
                    >
                      <Trash2 size={11} />
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

      </div>
    </div>
  )
}

// ---- Main ----
export function ConvertTab() {
  const [file, setFile] = useState(null)
  const [originalB64, setOriginalB64] = useState(null)
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(null)
  const [viewMode, setViewMode] = useState('grid')
  const [isOWSprite, setIsOWSprite] = useState(false)

  const [palettes, setPalettes] = useState([])
  const [selectedPalettes, setSelectedPalettes] = useState(new Set())
  const [reloading, setReloading] = useState(false)
  const [showPaletteModal, setShowPaletteModal] = useState(false)

  const { loading, error, run } = useFetch()

  const fetchPalettes = async () => {
    const data = await fetch(`${API}/palettes`).then(r => r.json()).catch(() => [])
    setPalettes(data)
    // Auto-select any newly discovered palettes
    setSelectedPalettes(prev => {
      const next = new Set(prev)
      data.forEach(p => { if (!next.has(p.name)) next.add(p.name) })
      return next
    })
  }

  useEffect(() => { fetchPalettes() }, [])

  useEffect(() => {
    if (!originalB64) { setIsOWSprite(false); return }
    const img = new window.Image()
    img.onload = () => setIsOWSprite(img.width / img.height >= 7.5 && img.width / img.height <= 10.5)
    img.src = `data:image/png;base64,${originalB64}`
  }, [originalB64])

  const convert = async (f) => {
    if (selectedPalettes.size === 0) return
    const fd = new FormData()
    fd.append('file', f)
    const data = await run(async () => {
      const res = await fetch(`${API}/convert`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      return res.json()
    })
    if (data) {
      setOriginalB64(data.original)
      const filtered = data.results.filter(r => selectedPalettes.has(r.palette_name))
      setResults(filtered)
      setSelected(filtered.findIndex(r => r.best))
    }
  }

  const handleFile = (f) => {
    setFile(f); setResults([]); setSelected(null); setOriginalB64(null)
    convert(f)
  }

  const handleReload = async () => {
    setReloading(true)
    await fetch(`${API}/palettes/reload`, { method: 'POST' })
    await fetchPalettes()
    setReloading(false)
  }

  const handleUpload = async (files) => {
    await Promise.all(Array.from(files).map(async (f) => {
      const fd = new FormData()
      fd.append('file', f)
      await fetch(`${API}/palettes/upload`, { method: 'POST', body: fd }).catch(() => {})
    }))
    await handleReload()
  }

  const handleDelete = async (name) => {
    await fetch(`${API}/palettes/${encodeURIComponent(name)}`, { method: 'DELETE' }).catch(() => {})
    setSelectedPalettes(prev => { const n = new Set(prev); n.delete(name); return n })
    await fetchPalettes()
  }

  const handleToggle = (name) => {
    setSelectedPalettes(prev => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })
  }

  const handleDownload = async (paletteName) => {
    const fd = new FormData()
    fd.append('file', file); fd.append('palette_name', paletteName)
    const res = await fetch(`${API}/convert/download`, { method: 'POST', body: fd })
    if (!res.ok) return
    downloadBlob(await res.blob(), `${file.name.replace(/\.[^.]+$/, '')}_${paletteName.replace('.pal', '')}.png`)
  }

  const handleDownloadAll = async () => {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch(`${API}/convert/download-all`, { method: 'POST', body: fd })
    if (!res.ok) return
    downloadBlob(await res.blob(), `${file.name.replace(/\.[^.]+$/, '')}_all_palettes.zip`)
  }

  return (
    <div className="tab-content">
      {showPaletteModal && (
        <PaletteModal
          palettes={palettes}
          selected={selectedPalettes}
          onToggle={handleToggle}
          onSelectAll={() => setSelectedPalettes(new Set(palettes.map(p => p.name)))}
          onDeselectAll={() => setSelectedPalettes(new Set())}
          onReload={handleReload}
          onUpload={handleUpload}
          onDelete={handleDelete}
          onClose={() => setShowPaletteModal(false)}
          reloading={reloading}
        />
      )}

      <div className="convert-layout">

        <div className="convert-left">
          <DropZone onFile={handleFile} label="Drop your sprite" />

          {originalB64 && (
            <div className="original-preview">
              <p className="section-label">original</p>
              <ZoomableImage src={originalB64} alt="original" />
              {isOWSprite && <WalkAnimation spriteB64={originalB64} />}
            </div>
          )}

          {results.length > 0 && (
            <button className="btn-secondary" onClick={handleDownloadAll}>
              download all as zip
            </button>
          )}
          <button className="btn-ghost-subtle" disabled={!file || loading || selectedPalettes.size === 0} onClick={() => convert(file)}>
            {loading ? 'converting…' : '↺ re-process'}
          </button>
          {error && <p className="error-msg">{error}</p>}
        </div>

        <div className="convert-right">
          <div className="results-toolbar">
            <span className="results-count">
              {results.length > 0 ? `${results.length} palettes` : ''}
            </span>
            <div className="toolbar-right">
              <button
                className={`palette-mgr-btn ${selectedPalettes.size < palettes.length ? 'filtered' : ''}`}
                onClick={() => setShowPaletteModal(true)}
                title="manage palettes"
              >
                <Layers size={12} />
                <span>palettes</span>
                <span className="palette-mgr-badge">{selectedPalettes.size}/{palettes.length}</span>
              </button>
              {results.length > 0 && (
                <div className="view-toggle">
                  <button className={`view-btn ${viewMode === 'grid' ? 'active' : ''}`}
                    onClick={() => setViewMode('grid')} title="grid view"><GridIcon /></button>
                  <button className={`view-btn ${viewMode === 'list' ? 'active' : ''}`}
                    onClick={() => setViewMode('list')} title="list view"><ListIcon /></button>
                </div>
              )}
            </div>
          </div>

          {results.length === 0 && !loading && (
            <div className="empty-state"><p>drop a sprite to see all palette conversions</p></div>
          )}
          {loading && (
            <div className="empty-state"><div className="spinner" /><p>processing…</p></div>
          )}

          <div className={viewMode === 'grid' ? 'results-grid' : 'results-list'}>
            {results.map((r, i) => (
              <ResultCard
                key={r.palette_name}
                result={r}
                selected={selected === i}
                onSelect={() => setSelected(i)}
                onDownload={handleDownload}
                listMode={viewMode === 'list'}
              />
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}```

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
Supports two color spaces for clustering:
  - 'oklab'  (default) — perceptually uniform, groups colors as humans see them
  - 'rgb'              — raw euclidean distance in sRGB space

Usage:
    extractor = PaletteExtractor()
    palette = extractor.extract("my_sprite.png", n_colors=15, bg_color="#73C5A4")
    palette.to_jasc_pal(Path("palettes/my_sprite.pal"))
"""

from __future__ import annotations
import logging
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

from model.palette import Color, Palette


# ---------------------------------------------------------------------------
# Oklab conversion (vectorized numpy)
# Reference: https://bottosson.github.io/posts/oklab/
# ---------------------------------------------------------------------------

def _srgb_to_linear(c: np.ndarray) -> np.ndarray:
    """sRGB gamma → linear (in-place safe, float32 input expected, 0–1 range)."""
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(c: np.ndarray) -> np.ndarray:
    """Linear → sRGB gamma (0–1 range)."""
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1.0 / 2.4) - 0.055)


def rgb_to_oklab(pixels: np.ndarray) -> np.ndarray:
    """
    Convert (N, 3) uint8 RGB → (N, 3) float32 Oklab.
    L in ~[0, 1], a/b in ~[-0.5, 0.5].
    """
    rgb = pixels.astype(np.float32) / 255.0
    lin = _srgb_to_linear(rgb)

    # Linear RGB → LMS cone responses
    l = 0.4122214708 * lin[:, 0] + 0.5363325363 * lin[:, 1] + 0.0514459929 * lin[:, 2]
    m = 0.2119034982 * lin[:, 0] + 0.6806995451 * lin[:, 1] + 0.1073969566 * lin[:, 2]
    s = 0.0883024619 * lin[:, 0] + 0.2817188376 * lin[:, 1] + 0.6299787005 * lin[:, 2]

    # Cube root (avoid NaN on negatives, though values should be ≥ 0)
    l_ = np.cbrt(np.maximum(l, 0))
    m_ = np.cbrt(np.maximum(m, 0))
    s_ = np.cbrt(np.maximum(s, 0))

    L =  0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a =  1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b =  0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_

    return np.stack([L, a, b], axis=1).astype(np.float32)


def oklab_to_rgb(lab: np.ndarray) -> np.ndarray:
    """
    Convert (N, 3) float32 Oklab → (N, 3) uint8 RGB.
    Values are clamped to valid range.
    """
    L, a, b = lab[:, 0], lab[:, 1], lab[:, 2]

    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b

    l = l_ ** 3
    m = m_ ** 3
    s = s_ ** 3

    r =  4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    b_ = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s

    rgb = np.stack([r, g, b_], axis=1)
    rgb = _linear_to_srgb(np.clip(rgb, 0, 1))
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------

class PaletteExtractor:
    """
    Extract a palette from a sprite using k-means clustering.

    Slot 0 is always the explicit bg_color (the transparent color).
    n_colors refers to the number of *non-transparent* colors to cluster,
    so the final palette has n_colors + 1 entries total (max 16 for GBA).

    color_space controls the space in which distance is measured:
      'oklab'  — perceptually uniform (default, recommended)
      'rgb'    — raw sRGB euclidean distance
    """

    VALID_COLOR_SPACES = ("oklab", "rgb")

    def __init__(self, random_state: int = 42):
        self.random_state = random_state

    def extract(
        self,
        image_path: str | Path,
        n_colors: int = 15,
        bg_color: str = "#73C5A4",
        color_space: str = "oklab",
        name: str | None = None,
    ) -> Palette:
        """
        Extract a palette from image_path.

        Args:
            image_path:   Path to any image Pillow can open.
            n_colors:     Number of sprite colors to cluster (NOT including transparent).
                          Final palette size = n_colors + 1. Max 15 for GBA (16 total).
            bg_color:     Hex string for the transparent color forced into slot 0.
            color_space:  'oklab' (default) or 'rgb'.
            name:         Palette name. Defaults to the image filename stem.

        Returns:
            A Palette with (n_colors + 1) entries, index 0 = bg_color.
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

        if color_space not in self.VALID_COLOR_SPACES:
            raise ValueError(f"color_space must be one of {self.VALID_COLOR_SPACES}, got {color_space!r}")

        max_sprite_colors = Palette.MAX_COLORS - 1  # 15
        if n_colors < 1 or n_colors > max_sprite_colors:
            raise ValueError(f"n_colors must be 1–{max_sprite_colors}, got {n_colors}")

        transparent_color = self._parse_hex(bg_color)
        transparent_rgb = np.array(
            [transparent_color.r, transparent_color.g, transparent_color.b],
            dtype=np.float32,
        )

        img = Image.open(path).convert("RGBA")
        pixels = np.array(img)          # (H, W, 4)
        alpha = pixels[:, :, 3]
        rgb   = pixels[:, :, :3]

        # Collect fully opaque pixels, excluding the transparent color
        opaque_mask = alpha.flatten() >= 255
        flat_rgb = rgb.reshape(-1, 3)
        opaque_pixels = flat_rgb[opaque_mask].astype(np.float32)

        non_transparent_mask = ~np.all(opaque_pixels == transparent_rgb, axis=1)
        sprite_pixels_rgb = opaque_pixels[non_transparent_mask].astype(np.uint8)

        if len(sprite_pixels_rgb) == 0:
            logging.warning("Image has no sprite pixels — returning palette with transparent only")
            return Palette(name=name or path.stem, colors=[transparent_color])

        # Convert to clustering space
        if color_space == "oklab":
            cluster_pixels = rgb_to_oklab(sprite_pixels_rgb)
        else:
            cluster_pixels = sprite_pixels_rgb.astype(np.float32)

        unique_colors = len(np.unique(sprite_pixels_rgb, axis=0))
        actual_clusters = min(n_colors, unique_colors)

        kmeans = KMeans(
            n_clusters=actual_clusters,
            random_state=self.random_state,
            n_init="auto",
        )
        kmeans.fit(cluster_pixels)
        centers = kmeans.cluster_centers_   # float, in cluster space

        # Convert centroids back to uint8 RGB
        if color_space == "oklab":
            centers_rgb = oklab_to_rgb(centers.astype(np.float32))
        else:
            centers_rgb = np.clip(centers, 0, 255).astype(np.uint8)

        # Sort by cluster size (most-used color first)
        labels = kmeans.labels_
        cluster_sizes = np.bincount(labels, minlength=actual_clusters)
        order = np.argsort(-cluster_sizes)
        sorted_centers = centers_rgb[order]

        colors = [transparent_color] + [
            Color(int(c[0]), int(c[1]), int(c[2])) for c in sorted_centers
        ]

        palette = Palette(name=name or path.stem, colors=colors)
        logging.info(
            f"Extracted {len(colors)} colors from '{path.name}' "
            f"(space={color_space}, transparent={bg_color}, "
            f"{len(sprite_pixels_rgb)} sprite pixels, {actual_clusters} clusters)"
        )
        return palette

    def extract_batch(
        self,
        image_paths: list[Path],
        n_colors: int = 15,
        bg_color: str = "#73C5A4",
        color_space: str = "oklab",
    ) -> list[Palette]:
        """Extract palettes from a list of images. Returns one Palette per image."""
        results = []
        for path in image_paths:
            try:
                results.append(self.extract(path, n_colors=n_colors, bg_color=bg_color, color_space=color_space))
            except Exception as e:
                logging.error(f"Failed to extract palette from {path}: {e}")
        return results

    # ---------- Helpers ----------

    @staticmethod
    def _parse_hex(hex_color: str) -> Color:
        """Parse a hex color string like '#73C5A4' into a Color."""
        h = hex_color.lstrip("#")
        if len(h) != 6:
            raise ValueError(f"Invalid hex color: {hex_color!r}")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return Color(r, g, b)```

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

# server/api/__init__.py
```python
# server/api/__init__.py```

----

# server/api/batch.py
```python
"""
server/api/batch.py

Routes: /api/batch
"""

from __future__ import annotations
import io
import os
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from server.state import state

router = APIRouter(prefix="/api/batch", tags=["batch"])


@router.post("")
async def batch_convert(
    files: list[UploadFile] = File(...),
    palette_name: str = Form(...),
):
    """Convert multiple sprites against one palette. Returns a zip of all results."""
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
    )```

----

# server/api/convert.py
```python
"""
server/api/convert.py

Routes: /api/convert
"""

from __future__ import annotations
import io
import os
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from PIL import Image

from server.helpers import pil_to_b64
from server.state import state

router = APIRouter(prefix="/api/convert", tags=["convert"])


@router.post("")
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
        Image.open(io.BytesIO(data))
    except Exception as e:
        raise HTTPException(400, f"Cannot open image: {e}")

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


@router.post("/download")
async def download_converted(
    file: UploadFile = File(...),
    palette_name: str = Form(...),
):
    """Convert and return a single GBA-compatible indexed PNG for download."""
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


@router.post("/download-all")
async def download_all_converted(file: UploadFile = File(...)):
    """Convert against all palettes and return a zip of all results."""
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
        os.unlink(tmp_path)```

----

# server/api/extract.py
```python
"""
server/api/extract.py

Routes: /api/extract
"""

from __future__ import annotations
import io
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from server.state import state

router = APIRouter(prefix="/api/extract", tags=["extract"])


def _make_pal_content(palette) -> str:
    buf = io.StringIO()
    buf.write("JASC-PAL\n0100\n")
    buf.write(f"{len(palette.colors)}\n")
    for c in palette.colors:
        buf.write(f"{c.r} {c.g} {c.b}\n")
    return buf.getvalue()


@router.post("")
async def extract_palette(
    file: UploadFile = File(...),
    n_colors: int = Form(default=15),
    bg_color: str | None = Form(default="#73C5A4"),
    color_space: str = Form(default="oklab"),
):
    """
    Extract a GBA palette from the uploaded sprite using k-means.
    color_space: 'oklab' (default, perceptually uniform) or 'rgb'.
    Returns the palette as hex colors + JASC .pal content.
    """
    if color_space not in ("oklab", "rgb"):
        raise HTTPException(400, f"color_space must be 'oklab' or 'rgb', got {color_space!r}")

    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        palette = state.extractor.extract(
            tmp_path,
            n_colors=n_colors,
            bg_color=bg_color,
            color_space=color_space,
        )

        if len(palette.colors) > 16:
            raise HTTPException(400, f"Image has too many colors ({len(palette.colors)}); max 16 for GBA")

        return {
            "name": palette.name,
            "colors": [c.to_hex() for c in palette.colors],
            "pal_content": _make_pal_content(palette),
            "color_space": color_space,
        }
    finally:
        os.unlink(tmp_path)


@router.post("/save")
async def save_extracted_palette(
    name: str = Form(...),
    pal_content: str = Form(...),
):
    """
    Save an in-memory extracted palette into palettes/user/.
    Called from the Extract tab after a successful extraction.
    """
    dest_dir = Path("palettes") / "user"
    dest_dir.mkdir(parents=True, exist_ok=True)

    filename = name if name.endswith(".pal") else f"{name}.pal"
    dest = dest_dir / filename

    # Avoid clobbering — append suffix if name already exists
    counter = 1
    while dest.exists():
        stem = filename.removesuffix(".pal")
        dest = dest_dir / f"{stem}_{counter}.pal"
        counter += 1

    dest.write_text(pal_content, encoding="utf-8")
    state.palette_manager.reload()
    return {"saved": dest.name}```

----

# server/api/health.py
```python
"""
server/api/health.py

Routes: /api/health
"""

from fastapi import APIRouter
from server.state import state

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok", "palettes_loaded": len(state.palette_manager.get_palettes())}```

----

# server/api/palettes.py
```python
"""
server/api/palettes.py

Routes: /api/palettes
"""

from __future__ import annotations
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from server.state import state

router = APIRouter(prefix="/api/palettes", tags=["palettes"])


@router.get("")
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


@router.post("/reload")
def reload_palettes():
    """Reload palettes from the palettes/ directory."""
    state.palette_manager.reload()
    return {"loaded": len(state.palette_manager.get_palettes())}


@router.post("/upload")
async def upload_palette(file: UploadFile = File(...)):
    """Upload a .pal file into the palettes/ directory."""
    dest = Path("palettes") / file.filename
    dest.write_bytes(await file.read())
    state.palette_manager.reload()
    return {"uploaded": file.filename}


@router.get("/{name}/download")
def download_palette(name: str):
    """Stream a .pal file back to the client for download."""
    path = Path("palettes") / name
    if not path.exists():
        raise HTTPException(404, f"Palette '{name}' not found")
    return FileResponse(
        path=str(path),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.delete("/{name}")
def delete_palette(name: str):
    """Delete a user palette. Refuses if marked as default."""
    path = Path("palettes") / name
    if not path.exists():
        raise HTTPException(404, f"Palette '{name}' not found")
    path.unlink()
    state.palette_manager.reload()
    return {"deleted": name}```

----

# server/api/presets.py
```python
"""
server/api/presets.py

Routes: /api/presets
"""

from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.presets import list_presets, load_preset, save_preset, delete_preset

router = APIRouter(prefix="/api/presets", tags=["presets"])


class PresetBody(BaseModel):
    name: str
    tile_w: int = 32
    tile_h: int = 32
    cols: int = 9
    rows: int = 1
    slots: list
    slot_labels: Optional[list] = None


@router.get("")
def get_presets():
    return list_presets()


@router.get("/{preset_id}")
def get_preset(preset_id: str):
    p = load_preset(preset_id)
    if not p:
        raise HTTPException(404, f"Preset '{preset_id}' not found")
    return p


@router.post("/{preset_id}")
def upsert_preset(preset_id: str, body: PresetBody):
    return save_preset(preset_id, body.model_dump())


@router.delete("/{preset_id}")
def remove_preset(preset_id: str):
    p = load_preset(preset_id)
    if not p:
        raise HTTPException(404, f"Preset '{preset_id}' not found")
    if p.get("is_default", False):
        raise HTTPException(403, f"Preset '{preset_id}' is a default preset and cannot be deleted")
    if not delete_preset(preset_id):
        raise HTTPException(500, "Failed to delete preset")
    return {"deleted": preset_id}```

----

# server/api/tileset.py
```python
"""
server/api/tileset.py

Routes: /api/tileset
"""

from __future__ import annotations
import io
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from PIL import Image as PILImage

from model.tileset_manager import TilesetManager
from server.helpers import pil_to_b64

router = APIRouter(prefix="/api/tileset", tags=["tileset"])


@router.post("/slice")
async def tileset_slice(
    file: UploadFile = File(...),
    tile_width: int = Form(default=32),
    tile_height: int = Form(default=32),
):
    """Slice a tileset into individual tiles. Returns source image + all tile images as base64."""
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
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


@router.post("/arrange")
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
        tmp.write(data)
        tmp_path = tmp.name
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
            buf,
            media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="{stem}_arranged.png"'},
        )
    finally:
        os.unlink(tmp_path)```

----

# server/app.py
```python
"""
server/app.py

FastAPI entrypoint — mounts routers and middleware only.
All route logic lives in server/api/*.py.
"""

from __future__ import annotations
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.api import palettes, convert, extract, batch, tileset, presets, health

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

app = FastAPI(title="Porypal API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- routers ----------

app.include_router(palettes.router)
app.include_router(convert.router)
app.include_router(extract.router)
app.include_router(batch.router)
app.include_router(tileset.router)
app.include_router(presets.router)
app.include_router(health.router)

# ---------- static files ----------

example_dir = Path(__file__).parent.parent / "example"
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"

if example_dir.exists():
    app.mount("/example", StaticFiles(directory=str(example_dir)), name="example")

if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")```

----

# server/helpers.py
```python
"""
server/helpers.py

Shared utility functions used across routers.
"""

from __future__ import annotations
import base64
import io

from PIL import Image


def pil_to_b64(img: Image.Image) -> str:
    """Convert a PIL image to a base64-encoded PNG string."""
    buf = io.BytesIO()
    img.convert("RGBA").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()```

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

# server/state.py
```python
"""
server/state.py

Shared application state — single instance imported by all routers.
Keeps PaletteManager, ImageManager, and PaletteExtractor alive across requests.
"""

from __future__ import annotations
from pathlib import Path

from model.palette_manager import PaletteManager
from model.image_manager import ImageManager
from model.palette_extractor import PaletteExtractor


def _load_config() -> dict:
    cfg_path = Path("config.yaml")
    if cfg_path.exists():
        import yaml
        return yaml.safe_load(cfg_path.read_text()) or {}
    return {}


class AppState:
    def __init__(self):
        self.config = _load_config()
        self.palette_manager = PaletteManager(self.config)
        self.image_manager = ImageManager(self.config)
        self.extractor = PaletteExtractor()


state = AppState()```

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