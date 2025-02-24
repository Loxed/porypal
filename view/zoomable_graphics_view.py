from PyQt5.QtWidgets import QGraphicsView, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QMouseEvent
import logging

class ZoomableGraphicsView(QGraphicsView):
    def __init__(self, parent=None, view=None, index=None):
        super().__init__(parent)
        self.clicked = QMouseEvent


        self.parent_view = view
        self.index = index

        # Disable antialiasing for sharp pixel edges
        self.setRenderHint(QPainter.Antialiasing, False)
        self.setRenderHint(QPainter.SmoothPixmapTransform, False)
        self.setRenderHint(QPainter.TextAntialiasing, False)
        
        # Set transform anchor to keep pixel alignment
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # Disable scrollbar animation for precise movement
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        
        # Set drag mode
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        
        # Initialize zoom parameters
        self.zoom_factor = 2.0  # Changed to 2.0 for pixel-perfect scaling
        self.current_zoom = 1.0
        
        # Create reset button
        self.reset_button = QPushButton("Reset View", self)
        self.reset_button.clicked.connect(self.reset_view)
        self.reset_button.setFixedSize(80, 30)
        self.reset_button.hide()  # Initially hidden
        
        # Store initial transform
        self.initial_transform = self.transform()
        
        # Initialize pan parameters
        self.panning = False
        self.last_pos = None
        
        # Set viewport update mode
        self.setViewportUpdateMode(QGraphicsView.MinimalViewportUpdate)

    def check_reset_button_visibility(self):
        """Check if the view needs the reset button."""
        if not self.scene():
            return

        # Check if we're zoomed
        is_default = abs(self.current_zoom - 1.0) < 0.001
        
        # Show/hide reset button accordingly
        self.reset_button.setVisible(not is_default)

    # ---- EVENTS ----- #

    def resizeEvent(self, event):
        super().resizeEvent(event)
        button_x = self.width() - self.reset_button.width() - 10
        self.reset_button.move(button_x, 10)
        # self.reset_view() # caused glitch due to false-positive with selection border

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            old_pos = self.mapToScene(event.pos())

            # Zoom in or out with power of 2 scaling
            if event.angleDelta().y() > 0:
                zoom_factor = self.zoom_factor
            else:
                zoom_factor = 1 / self.zoom_factor

            self.scale(zoom_factor, zoom_factor)
            self.current_zoom *= zoom_factor

            new_pos = self.mapToScene(event.pos())
            delta = new_pos - old_pos
            self.translate(delta.x(), delta.y())
            
            self.check_reset_button_visibility()
            event.accept()
        else:
            super().wheelEvent(event)

    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.panning = True
            self.last_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            logging.debug("Selected index: %s", self.index)
            self.parent_view._handle_view_click(self.index) if self.parent_view else None
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        # Check if panning is enabled
        if self.panning and self.last_pos is not None:
            # Calculate the delta between the current and last mouse positions
            delta = event.pos() - self.last_pos
            
            # Update the scroll bars to move the view by the delta
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y())
            
            # Update the last mouse position
            self.last_pos = event.pos()
            
            # Accept the event to prevent further processing
            event.accept()

    def reset_view(self):
        self.setTransform(self.initial_transform)
        self.current_zoom = 1.0
        
        if self.scene():
            self.setSceneRect(self.scene().itemsBoundingRect())
            self.fitInView(self.scene().itemsBoundingRect(), Qt.KeepAspectRatio)
        
        self.check_reset_button_visibility()
        self.update()

    def setScene(self, scene):
        super().setScene(scene)
        if scene:
            self.setSceneRect(scene.itemsBoundingRect())
            self.fitInView(scene.itemsBoundingRect(), Qt.KeepAspectRatio)
            self.initial_transform = self.transform()
            self.check_reset_button_visibility()