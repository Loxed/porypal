from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QGraphicsView, QPushButton, QGraphicsScene
from PyQt5.QtCore import Qt, QRectF
from view.palette_display import PaletteDisplay

class ZoomableGraphicsView(QGraphicsView):
    """Custom QGraphicsView with zoom and pan functionality."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        
        self.zoom_factor = 1.25
        self.current_zoom = 1.0
        self.initial_rect = None
        self.initial_transform = None
        
        # Create and setup reset button
        self.reset_button = QPushButton("Reset View", self)
        self.reset_button.hide()
        self.reset_button.clicked.connect(self.reset_view)
        self.reset_button.setFixedSize(80, 25)

    def resizeEvent(self, event):
        """Handle resize events to reposition the reset button."""
        super().resizeEvent(event)
        self.reset_button.move(self.width() - self.reset_button.width() - 10, 10)

    def wheelEvent(self, event):
        """Handle zooming with scroll wheel."""
        zoom_factor = self.zoom_factor if event.angleDelta().y() > 0 else 1 / self.zoom_factor
        self.current_zoom *= zoom_factor
        self.scale(zoom_factor, zoom_factor)
        self.reset_button.show()

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            fake_event = QMouseEvent(event.type(), event.pos(), Qt.LeftButton, Qt.LeftButton, event.modifiers())
            super().mousePressEvent(fake_event)
            self.reset_button.show()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if event.button() == Qt.MiddleButton:
            fake_event = QMouseEvent(event.type(), event.pos(), Qt.LeftButton, Qt.LeftButton, event.modifiers())
            super().mouseReleaseEvent(fake_event)
            self.setDragMode(QGraphicsView.NoDrag)
        else:
            super().mouseReleaseEvent(event)

    def set_scene_content(self, pixmap, palette=None):
        """Set the scene content and palette."""
        scene = self.scene() or QGraphicsScene()
        self.setScene(scene)
        
        scene.clear()
        scene.addPixmap(pixmap)
        scene.setSceneRect(QRectF(pixmap.rect()))
        
        self.initial_rect = scene.sceneRect()
        self.fitInView(self.initial_rect, Qt.KeepAspectRatio)
        self.initial_transform = self.transform()
        self.current_zoom = 1.0
        self.reset_button.hide()

    def reset_view(self):
        """Reset the view to its initial state."""
        if self.initial_transform:
            self.setTransform(self.initial_transform)
            self.current_zoom = 1.0
            self.reset_button.hide()