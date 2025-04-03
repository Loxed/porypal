# controller/tileset_editor_controller.py

from PyQt5.QtGui import QImage, QPixmap, QPen, QColor, QPainter, QBrush
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QGraphicsPixmapItem, QGraphicsRectItem, QApplication
from PyQt5.QtCore import QObject, pyqtSlot, QRectF, Qt, QPoint
import logging

from view.tileset_editor_view import TilesetEditorView

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
            'size': (tile_width, tile_height)  # Store scaled size
        }

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
            "<p><b>Arranging Tiles:</b> Drag tiles from the input view to the output view.</p>"
            "<p><b>Saving:</b> Click 'Save Tileset' to save the arranged tiles as a new image.</p>"
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
                
            # Update view with the loaded image (no scaling for input)
            self.show_image(self.input_image, self.view.input_scene, self.view.input_view)
            
            # Update UI state
            self.view.btn_apply_grid.setEnabled(True)
            self.view.btn_create_layout.setEnabled(False)  # Disable until grid is applied
            self.view.btn_clear_layout.setEnabled(False)   # Disable until grid is applied
            self.view.btn_save_tileset.setEnabled(False)   # Disable until layout is created
            
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
