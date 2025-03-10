# controller/tileset_editor_controller.py

from PyQt5.QtGui import QImage, QPixmap, QPen, QColor, QPainter
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QGraphicsPixmapItem
from PyQt5.QtCore import QObject, pyqtSlot, QRectF, Qt
import logging
from pathlib import Path

from view.tileset_editor_view import TilesetEditorView
from model.draggable_tile import DraggableTile, TileDropArea
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

        self.input_tiles = [] # list of draggable tiles in the input scene
        self.selected_tiles = [] # list of selected tiles in the input scene
        
        # Create our own view - don't accept one from the parent
        self.view = TilesetEditorView(self)
        
        # Connect view signals to controller methods
        self._connect_signals()
        
        # Add handling for when the view is closed
        self.view.closeEvent = self.handle_close_event
        logging.info("Tileset Editor Controller initialized")


    # ------------ METHODS ------------ # 
    def update_selected_tile(self, tile: QImage):
        # preview the selected tiles from the input scene into the preview_scene
        self.view.preview_scene.clear()
        self.view.preview_scene.addPixmap(tile.pixmap)

        # update the status label
        self.view.notification.show_notification(f"Selected tile: {tile.tile_id}")

    # ------------ SIGNALS ------------ #
    def _connect_signals(self):
        """Connect view signals to controller methods."""
        self.view.btn_load_tileset.clicked.connect(self.load_tileset)
        self.view.btn_save_tileset.clicked.connect(self.save_tileset)
        self.view.btn_apply_grid.clicked.connect(self.apply_grid)
        self.view.btn_create_layout.clicked.connect(self.create_output_layout)
        self.view.btn_clear_layout.clicked.connect(self.clear_output_layout)
        self.view.btn_help.clicked.connect(self.show_help)
        
    @pyqtSlot()
    def load_tileset(self):
        """Load tileset image from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self.view, "Load Tileset", "", "Images (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        
        if not file_path:
            return
            
        try:
            self.input_image = QImage(file_path) # loading image, 1x1 Image for now
            if self.input_image.isNull():
                self.view.notification.show_error("Failed to load image")
                raise ValueError("Failed to load image")
                
            # Update view with the loaded image
            self.view.show_image(self.input_image, self.view.input_scene, self.view.input_view)

            # Update UI state
            self.view.btn_apply_grid.setEnabled(True)
            self.view.notification.show_notification(f"Tileset loaded: {Path(file_path).name} ({self.input_image.width()}x{self.input_image.height()})")
            
        except Exception as e:
            logging.error(f"Failed to load tileset: {e}")
            QMessageBox.critical(self.view, "Error", f"Failed to load tileset: {e}")

    @pyqtSlot()
    def apply_grid(self):
        """Apply grid to input image based on tile dimensions."""
        if not self.input_image:
            return

        # Get tile dimensions from view
        tile_width = self.view.spin_tile_width.value()
        tile_height = self.view.spin_tile_height.value()

        # Calculate grid dimensions
        cols = self.input_image.width() // tile_width
        cols += 1 if self.input_image.width() % tile_width > 0 else 0  # round up if there is a remainder

        rows = self.input_image.height() // tile_height
        rows += 1 if self.input_image.height() % tile_height > 0 else 0  # round up if there is a remainder

        # Reset scene and display the original image
        self.view.show_image(self.input_image, self.view.input_scene, self.view.input_view)

        # Set up the pen for grid drawing (transparent red)
        pen = QPen(QColor(255, 0, 0, 100))
        tile_id = 0

        # Clear the preview scene before adding new tiles
        self.view.preview_scene.clear()

        # Loop through the grid to cut out and display the tiles
        for row in range(rows):
            for col in range(cols):
                x = col * tile_width
                y = row * tile_height

                # Cut the tile from the image
                tile_pixmap = QPixmap.fromImage(
                    self.input_image.copy(x, y, tile_width, tile_height)
                )

                # Create a draggable tile object with correct position
                tile = DraggableTile(tile_pixmap, tile_id, x, y)
                self.input_tiles.append(tile)

                # Update the tile id
                tile_id += 1

                # Display the tile in the input scene at the right location
                self.view.input_scene.addPixmap(tile.pixmap).setPos(x, y)

                # Draw the grid cell for visual reference on the input scene
                self.view.input_scene.addRect(x, y, tile_width, tile_height, pen)

        # Update UI state
        self.view.btn_create_layout.setEnabled(True)
        self.view.notification.show_notification(
            f"Grid applied: {cols}x{rows} tiles ({tile_width}x{tile_height} pixels each)"
        )


        
    @pyqtSlot()
    def create_output_layout(self):
        """Create output layout with specified dimensions."""
        # Get layout dimensions
        columns = self.view.spin_columns.value()
        rows = self.view.spin_rows.value()
        
        # Get tile dimensions
        tile_width = self.view.spin_tile_width.value()
        tile_height = self.view.spin_tile_height.value()
        
        # Setup output grid
        width, height = self.view.output_scene.setup_grid(columns, rows, tile_width, tile_height)
        
        # Draw grid on output
        from PyQt5.QtGui import QPen, QColor
        pen = QPen(QColor(200, 200, 200, 100))
        for x in range(0, width + 1, tile_width):
            self.view.output_scene.addLine(x, 0, x, height, pen)
        for y in range(0, height + 1, tile_height):
            self.view.output_scene.addLine(0, y, width, y, pen)
            
        # Fit view to new scene rect
        self.view.output_view.fitInView(self.view.output_scene.sceneRect(), Qt.KeepAspectRatio)
        
        # Update UI state
        self.view.btn_save_tileset.setEnabled(True)
        self.view.btn_clear_layout.setEnabled(True)
        self.view.notification.show_notification(
            f"Output layout created: {columns}x{rows} tiles"
        )
        
    @pyqtSlot()
    def clear_output_layout(self):
        """Clear the output layout."""
        # Get current layout dimensions
        columns, rows = self.view.output_scene.grid_size
        tile_width, tile_height = self.view.output_scene.tile_size
        
        # Clear and recreate the grid
        self.view.output_scene.clear()
        self.view.output_scene.tiles.clear()
        
        # Redraw the grid
        width = columns * tile_width
        height = rows * tile_height
        
        from PyQt5.QtGui import QPen, QColor
        pen = QPen(QColor(200, 200, 200, 100))
        for x in range(0, width + 1, tile_width):
            self.view.output_scene.addLine(x, 0, x, height, pen)
        for y in range(0, height + 1, tile_height):
            self.view.output_scene.addLine(0, y, width, y, pen)
            
        self.view.notification.show_notification("Output layout cleared")
        
    @pyqtSlot()
    def save_tileset(self):
        """Save the output tileset to a file."""
        # Check if there are tiles to save
        if not self.view.output_scene.tiles:
            QMessageBox.warning(self.view, "Warning", "No tiles to save. Please create a layout and arrange tiles first.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self.view, "Save Tileset", "", "PNG Image (*.png)"
        )
        
        if not file_path:
            return
            
        try:
            # Generate the output image
            output_image = self.view.output_scene.get_output_image()
            
            # Save the image
            output_image.save(file_path)
            
            self.view.notification.show_notification(f"Tileset saved to: {file_path}")
            
        except Exception as e:
            logging.error(f"Failed to save tileset: {e}")
            QMessageBox.critical(self.view, "Error", f"Failed to save tileset: {e}")
            
    @pyqtSlot()
    def show_help(self):
        """Show help dialog."""
        help_text = (
            "<h3>Tileset Editor Help</h3>"
            "<p><b>Loading a Tileset:</b> Click 'Load Tileset' to select an image file.</p>"
            "<p><b>Defining Tiles:</b> Set tile width and height, then click 'Apply Grid'.</p>"
            "<p><b>Creating Output Layout:</b> Set columns and rows, then click 'Create Layout'.</p>"
            "<p><b>Arranging Tiles:</b> Drag tiles from the input view to the output view.</p>"
            "<p><b>Saving:</b> Click 'Save Tileset' to save the arranged tiles as a new image.</p>"
        )
        
        QMessageBox.information(self.view, "Tileset Editor Help", help_text)


    # ------------ EVENT HANDLERS ------------ #
    def handle_close_event(self, event):
        """Handle the view's close event to restore the main view."""
        if self.parent_controller and hasattr(self.parent_controller, 'restore_main_view'):
            self.parent_controller.restore_main_view()
        event.accept()

    def selected_tiles_changed(self, selected_tiles):
        """Update the selected tiles in the preview scene with the selected tiles in the input scene."""
        # clear the preview scene
        self.view.preview_scene.clear()
        
        # construct a bigger image with the selected tiles
        if selected_tiles:
            # get the tile size
            tile_width = self.view.output_scene.tile_size[0]
            tile_height = self.view.output_scene.tile_size[1]
            
            # get the max x and y
            max_x = max(tile.x() for tile in selected_tiles)
            max_y = max(tile.y() for tile in selected_tiles)
            
            # create a new image
            output_image = QImage(
                max_x + tile_width, max_y + tile_height, QImage.Format_RGBA8888
            )
            output_image.fill(Qt.transparent)
            
            # draw each tile in the right place
            painter = QPainter(output_image)
            for tile in selected_tiles:
                x = tile.x()
                y = tile.y()
                painter.drawImage(
                    QRectF(x, y, tile_width, tile_height),
                    tile.pixmap.toImage()
                )
            painter.end()
            
            # add the image to the preview scene
            self.view.preview_scene.addPixmap(QPixmap.fromImage(output_image))
            
            # center the view
            self.view.preview_view.centerOn(
                self.view.preview_scene.itemsBoundingRect().center()
            )
