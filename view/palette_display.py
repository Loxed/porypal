from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtCore import Qt, QSize

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
        return QSize(120, 120)  # preferred size

    def minimumSizeHint(self) -> QSize:
        return QSize(40, 40)  # minimum size

    def resizeEvent(self, event):
        # Keep the widget square
        size = min(event.size().width(), event.size().height())
        self.setFixedSize(size, size)
        super().resizeEvent(event)  