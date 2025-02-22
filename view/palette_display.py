from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtCore import Qt, QSize

class PaletteDisplay(QWidget):
    """Widget to display a 4x4 grid of palette colors."""

    def __init__(self, colors=None, parent=None):
        super().__init__(parent)
        self.colors = colors or []
        
        # Set fixed size for the widget
        self.setMinimumSize(60, 60)
        self.setVisible(bool(self.colors))

    def paintEvent(self, event):
        """Paint the 4x4 grid of colors."""
        if not self.colors:
            return

        painter = QPainter(self)
        
        # Calculate cell size
        cell_size = self.width() // 4
        
        # Draw grid
        for i in range(16):
            row, col = divmod(i, 4)
            x, y = col * cell_size, row * cell_size
            
            # Draw color if available, otherwise draw empty cell
            if i < len(self.colors):
                color = self.colors[i]
                # Handle both QColor objects and RGB tuples
                if isinstance(color, QColor):
                    painter.fillRect(x, y, cell_size, cell_size, color)
                else:
                    painter.fillRect(x, y, cell_size, cell_size, QColor(*color))
            else:
                # Draw empty cell with border
                painter.setPen(Qt.gray)
                painter.drawRect(x, y, cell_size, cell_size)

            # Draw border around each cell
            painter.setPen(Qt.black)
            painter.drawRect(x, y, cell_size, cell_size)

    def sizeHint(self):
        """Return the recommended size for the widget."""
        return QSize(60, 60)

    def minimumSizeHint(self):
        """Return the minimum recommended size for the widget."""
        return QSize(60, 60)

    def set_palette(self, colors):
        """Update the palette colors."""
        self.colors = colors or []
        self.setVisible(bool(self.colors))
        self.update()