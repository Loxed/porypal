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
        return output_image