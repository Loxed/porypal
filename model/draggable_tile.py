# model/draggable_tile.py
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QRectF
from PyQt5.QtGui import QImage, QPixmap, QPainter
from PyQt5.QtWidgets import QGraphicsScene

from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QGraphicsPixmapItem

class DraggableTile(QGraphicsPixmapItem):
    def __init__(self, pixmap, tile_id, tile_x, tile_y, controller):
        super().__init__(pixmap)  # Initialize the base class with the pixmap
        self.tile_id = tile_id
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.controller = controller
        self.pixmap = pixmap
        self.setPos(tile_x, tile_y)  # Set the position of the tile
        self.setFlag(QGraphicsPixmapItem.ItemIsSelectable, True)  # Enable selection
        self.is_selected = False  # Track selection state

    # ------------ GETTERS ------------ #
    def get_pos(self):
        return (self.tile_x, self.tile_y)
    
    # ------------ SETTERS ------------ #
    def set_pos(self, tile_x, tile_y):
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.setPos(tile_x, tile_y)

    # ------------ EVENT HANDLERS ------------ #
    def mousePressEvent(self, event):
        """Handles mouse press for tile selection."""
        if event.button() == Qt.LeftButton:
            # If shift is not pressed, clear previous selection
            if not event.modifiers() & Qt.ShiftModifier:
                self.controller.clear_selection()
            
            # Toggle selection state
            self.is_selected = not self.is_selected
            
            # Update visual selection state
            if self.is_selected:
                self.setOpacity(0.7)  # Visual feedback for selection
                self.controller.selected_tiles.append(self)
            else:
                self.setOpacity(1.0)
                if self in self.controller.selected_tiles:
                    self.controller.selected_tiles.remove(self)
            
            # Update preview scene
            self.controller.update_selected_tile()