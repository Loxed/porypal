from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QImage, QPixmap, QMouseEvent
from PyQt5.QtWidgets import (
    QGraphicsScene, QGraphicsView, QLabel, QWidget, 
    QMessageBox, QVBoxLayout, QHBoxLayout, QSizePolicy, QSpacerItem, QPushButton
)
from PyQt5 import uic
from model.palette_manager import Palette
from view.palette_display import PaletteDisplay
from view.zoomable_graphics_view import ZoomableGraphicsView

class PorypalView(QWidget):
    """Main application view."""

    CONFIRM_ON_EXIT = False

    def __init__(self, palettes: list[Palette]):
        super().__init__()
        
        # Load UI without showing it yet
        uic.loadUi("view/porypalette.ui", self)

        # Initialize state
        self.selected_index = None
        self.best_indices = []
        self.dynamic_views = []
        self.dynamic_labels = []

        # Set minimum size before showing
        self.setMinimumSize(800, 600)

        # Setup all views while window is hidden
        self._setup_original_view()
        self._setup_dynamic_views(palettes)

        # Show the window only once everything is ready
        self.show()

    def _setup_original_view(self):
        """Replace the original QGraphicsView with a ZoomableGraphicsView."""
        layout = self.original_image_layout
        index = layout.indexOf(self.original_view)
        
        # Remove old view without showing intermediate states
        layout.removeWidget(self.original_view)
        self.original_view.hide()  # Hide before deletion
        self.original_view.deleteLater()

        # Create new view
        self.original_view = ZoomableGraphicsView(self)
        self.original_view.setMinimumSize(320, 210)
        layout.insertWidget(index, self.original_view)

    def _setup_dynamic_views(self, palettes: list[Palette]):
        """Setup layout for dynamic content."""
        # Clear existing widgets
        while self.dynamic_layout.count():
            item = self.dynamic_layout.takeAt(0)
            if item.widget():
                item.widget().hide()  # Hide before deletion
                item.widget().deleteLater()

        # Create all widgets before adding them to layout
        for palette in palettes:
            container = QWidget(self)
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)

            label = QLabel(f"{palette.get_name()} ({len(palette.get_colors())} colors)", container)
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            label.setMinimumWidth(150)

            palette_4x4 = PaletteDisplay(palette.get_colors(), container)
            
            view = ZoomableGraphicsView(container)
            view.setMinimumHeight(300)

            # Add widgets to layout
            container_layout.addWidget(label)
            container_layout.addWidget(palette_4x4)
            container_layout.addWidget(view)
            container_layout.setStretch(2, 1)  # Give stretch to the view

            self.dynamic_views.append(view)
            self.dynamic_labels.append(label)

            # Add container to main layout
            self.dynamic_layout.addWidget(container)

        # Add spacer at the end
        self.dynamic_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding))

    def update_original_image(self, image):
        """Update main preview image."""
        if image and not image.isNull():
            pixmap = QPixmap.fromImage(image)
            self.original_view.set_scene_content(pixmap)

    def update_dynamic_images(self, images, labels, palettes, highlights):
        """Update conversion results."""
        self.best_indices = highlights.get('best_indices', [])
        
        if self.selected_index is None and self.best_indices:
            self.selected_index = self.best_indices[0]

        for i, (image, label, palette) in enumerate(zip(images, labels, palettes)):
            if i >= len(self.dynamic_views):
                break
                
            pixmap = QPixmap.fromImage(image)
            self.dynamic_views[i].set_scene_content(pixmap, palette)
            self.dynamic_labels[i].setText(label)
            
        self._update_highlights()

    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() == Qt.Key_Escape:
            self._handle_exit()
        else:
            super().keyPressEvent(event)

    def _handle_exit(self):
        """Handle application exit with optional confirmation."""
        if self.CONFIRM_ON_EXIT:
            reply = QMessageBox.question(
                self,
                'Confirm Exit',
                'Are you sure you want to exit?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.close()
        else:
            self.close()

    def _update_highlights(self):
        """Update view highlighting."""
        for i, view in enumerate(self.dynamic_views):
            style = "border: 3px solid #4CAF50" if i == self.selected_index else ""
            style = style or ("border: 2px solid #2196F3" if i in self.best_indices else "")
            view.setStyleSheet(f"QGraphicsView {{ {style} }}")

    def show_error(self, title, message):
        """Display error message."""
        QMessageBox.critical(self, title, message)