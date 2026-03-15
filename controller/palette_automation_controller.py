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
            self.view.close() 