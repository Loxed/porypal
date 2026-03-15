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
            self.view.close() 