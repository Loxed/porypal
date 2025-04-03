import sys
import random
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QLabel, QVBoxLayout, QFrame
from PyQt5.QtGui import QPixmap, QPainter, QColor, QDragEnterEvent, QMouseEvent, QDropEvent, QPalette, QDrag
from PyQt5.QtCore import Qt, QMimeData, QPoint

class TileLabel(QLabel):
    def __init__(self, number, size=32):
        super().__init__()
        self.number = number
        self.setFixedSize(size, size)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {'#4CAF50' if number % 2 == 0 else '#2196F3'};
                color: white;
                border: 1px solid black;
                font-weight: bold;
            }}
        """)
        
        # Create pixmap with number
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setPen(Qt.white)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, str(number))
        painter.end()
        
        self.setPixmap(pixmap)
        self.setScaledContents(True)
        self.setAcceptDrops(True)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            # Prepare drag
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(str(self.number))
            drag.setMimeData(mime_data)
            
            # Create pixmap for drag
            pixmap = self.pixmap().copy()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.pos())
            
            # Perform drag
            drag.exec_(Qt.MoveAction)

class TileGridWidget(QFrame):
    def __init__(self, is_source=True):
        super().__init__()
        self.setAcceptDrops(True)
        
        # Create grid layout
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(2)
        self.setLayout(self.grid_layout)
        
        # Create tiles
        if is_source:
            # Ensure exactly 12 numbers
            numbers = list(range(1, 13))
            random.shuffle(numbers)
            
            # Create 4x4 grid
            for i in range(4):
                for j in range(4):
                    index = i * 4 + j
                    tile = TileLabel(numbers[index])
                    self.grid_layout.addWidget(tile, i, j)
        
        self.setStyleSheet("""
            QFrame {
                background-color: #E0E0E0;
                border: 2px dashed #9E9E9E;
                border-radius: 10px;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        # Accept drag if it's a tile
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        # Get the number of the dragged tile
        number = int(event.mimeData().text())
        
        # Find the grid position
        pos = event.pos()
        child = self.childAt(pos)
        
        if child and isinstance(child, TileLabel):
            # If dropped on an existing tile, replace it
            parent_layout = child.parent().layout()
            index = parent_layout.indexOf(child)
            row, column, _, _ = parent_layout.getItemPosition(index)
            
            # Remove existing tile
            parent_layout.removeWidget(child)
            child.deleteLater()
            
            # Add new tile
            new_tile = TileLabel(number)
            parent_layout.addWidget(new_tile, row, column)
        else:
            # If dropped in empty space, find first empty slot
            for i in range(self.grid_layout.rowCount()):
                for j in range(self.grid_layout.columnCount()):
                    if self.grid_layout.itemAtPosition(i, j) is None:
                        tile = TileLabel(number)
                        self.grid_layout.addWidget(tile, i, j)
                        break
                else:
                    continue
                break
        
        event.acceptProposedAction()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Tile Drag and Drop Demo')
        
        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Create source and destination grids
        source_grid = TileGridWidget(is_source=True)
        dest_grid = TileGridWidget(is_source=False)
        
        # Add grids to layout
        main_layout.addWidget(QLabel('Source Grid (Drag from here)'))
        main_layout.addWidget(source_grid)
        main_layout.addWidget(QLabel('Destination Grid (Drag to here)'))
        main_layout.addWidget(dest_grid)
        
        self.resize(400, 600)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()