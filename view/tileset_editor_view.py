# view/tileset_editor_view.py
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtWidgets import QWidget, QGraphicsScene, QApplication, QMessageBox
from PyQt5.QtGui import QImage, QPixmap
from PyQt5 import uic
import logging
from model.draggable_tile import DraggableTile, TileDropArea
from model.QNotificationWidget import QNotificationWidget

class TilesetEditorView(QWidget):
    """
    View for the tileset editor that displays the UI using the existing UI file.
    """
    CONFIRM_ON_EXIT = True
    
    def __init__(self, controller):
        super().__init__()
        
        # Load UI from file
        uic.loadUi("view/tileset_editor.ui", self)
        
        self.controller = controller


        # Initialize scenes
        self.input_scene = QGraphicsScene(self)
        self.input_view.setScene(self.input_scene)

        # Preview view 
        self.preview_scene = QGraphicsScene(self)
        self.preview_view.setScene(self.preview_scene)
        
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
        
        # Get screen geometry and set the default size
        screen = QApplication.primaryScreen()
        screen_size = screen.availableGeometry()
        self.setGeometry(screen_size)

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
            super().keyPressEvent(event)


    def mousePressEvent(self, event):
            """Handles mouse press for single tile selection."""
            if event.button() == Qt.LeftButton:
                clicked_item = self.input_scene.itemAt(event.pos(), self.input_view.transform())
                if isinstance(clicked_item, DraggableTile):
                    # Toggle selection of clicked tile
                    if clicked_item.isSelected():
                        clicked_item.setSelected(False)
                        self.controller.selected_tiles.remove(clicked_item)
                    else:
                        clicked_item.setSelected(True)
                        self.controller.selected_tiles.append(clicked_item)

                # Refresh preview scene with selected tiles
                self.update_preview_scene()

    def mouseReleaseEvent(self, event):
            """Handles mouse release to select multiple tiles."""
            if event.button() == Qt.LeftButton:
                # Update the preview scene with selected tiles
                self.update_preview_scene()