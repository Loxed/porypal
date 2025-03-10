# model/draggable_tile.py
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QRectF
from PyQt5.QtGui import QImage, QPixmap, QPainter
from PyQt5.QtWidgets import QGraphicsScene

from PyQt5.QtGui import QPixmap

from PyQt5.QtWidgets import QGraphicsPixmapItem
from PyQt5.QtGui import QPixmap

class DraggableTile(QGraphicsPixmapItem):
    def __init__(self, pixmap, tile_id, tile_x, tile_y):
        super().__init__(pixmap)  # Initialize the base class with the pixmap
        self.tile_id = tile_id
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.pixmap = pixmap
        self.setPos(tile_x, tile_y)  # Set the position of the tile
        self.setFlag(QGraphicsPixmapItem.ItemIsSelectable, True)  # Enable selection

    

    # ------------ GETTERS ------------ #
    def get_pos(self):
        return (self.tile_x, self.tile_y)
    
    # ------------ SETTERS ------------ #
    def set_pos(self, tile_x, tile_y):
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.setPos(tile_x, tile_y)