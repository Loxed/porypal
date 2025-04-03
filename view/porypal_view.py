# view/porypal_view.py
from PyQt5.QtCore import Qt, QRectF, QEvent
from PyQt5.QtGui import QPixmap, QScreen, QCursor
from PyQt5.QtWidgets import (
    QGraphicsScene, QGraphicsView, QLabel, QWidget, 
    QMessageBox, QHBoxLayout, QSizePolicy, 
    QApplication
)
from PyQt5 import uic
from model.palette_manager import Palette
from model.QNotificationWidget import QNotificationWidget

from view.palette_display import PaletteDisplay
from view.zoomable_graphics_view import ZoomableGraphicsView

import logging

class PorypalView(QWidget):
    """Main application view with dynamic resizing support."""

    CONFIRM_ON_EXIT = True
    MIN_WIDTH = 540
    MIN_HEIGHT = 600

    def __init__(self, parent, palettes: list[Palette]):
        super().__init__()
        uic.loadUi("view/porypalette.ui", self)

        self.parent = parent

        self.notification = QNotificationWidget(self)
        
        self.selected_index = None
        self.best_indices = []
        self.dynamic_views = []
        self.dynamic_labels = []
        self.dynamic_frames = []

        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)
        # self.setFixedSize(self.MIN_WIDTH, self.MIN_HEIGHT)

        # Get the screen where the mouse cursor is located
        cursor_pos = QCursor.pos()
        cursor_screen = QApplication.screenAt(cursor_pos)
        
        if cursor_screen:
            # Get the screen geometry
            screen_geometry = cursor_screen.availableGeometry()
            
            # Set window geometry to match the screen
            self.setGeometry(screen_geometry)
            
            # Position window at the top-left corner of the screen
            self.move(screen_geometry.x(), screen_geometry.y())
        else:
            # Fallback to primary screen if cursor screen can't be determined
            screen = QApplication.primaryScreen()
            screen_size = screen.availableGeometry()
            self.setGeometry(screen_size)
            self.move(cursor_pos.x(), cursor_pos.y())

        self._setup_original_view()
        self._setup_dynamic_views(palettes)

        self.content_layout.setStretch(0, 1)
        self.content_layout.setStretch(1, 1)


        self.show()

    def _setup_original_view(self):
        """Replace original QGraphicsView with a ZoomableGraphicsView."""
        layout = self.original_image_layout
        index = layout.indexOf(self.original_view)

        layout.removeWidget(self.original_view)
        self.original_view.hide()
        self.original_view.deleteLater()

        self.original_view = ZoomableGraphicsView(view=self)
        self.original_view.setMinimumWidth((int)(self.MIN_WIDTH*0.4))
        self.original_view.setMinimumHeight((int)(self.MIN_HEIGHT*0.3))
        self.original_view.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred
        )

        # self.original_view.setBorder(Qt.black, 1)

        layout.insertWidget(index, self.original_view, 1)

    def _setup_dynamic_views(self, palettes: list[Palette]):
        """Setup dynamic content with proper resizing behavior."""
        while self.dynamic_layout.count():
            item = self.dynamic_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()

        # # add label
        # label_output = QLabel("Output Images", self)
        # label_instruction = QLabel("🟢 = Selected Image\n🔵 = Recommended Image(s)",self)

        # self.dynamic_layout.addWidget(label_output)
        # self.dynamic_layout.addWidget(label_instruction)

        for palette in palettes:
            container = QWidget(self)
            container.setSizePolicy(
                QSizePolicy.Minimum, QSizePolicy.Minimum
            )
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(5, 5, 5, 5)
            container_layout.setSpacing(10)

            # Label: Only as wide as its text needs
            text = f"{palette.get_name()} ({len(palette.get_colors())} colors)"
            label = QLabel(text, container)
            preferred_width = self._get_text_width(text, label)
            label.setMaximumWidth(preferred_width)
            label.setMinimumWidth(min(60, preferred_width))
            label.setWordWrap(True)
            label.setSizePolicy(
                QSizePolicy.MinimumExpanding, QSizePolicy.Preferred
            )

            # Palette display: Square that maintains minimum size
            palette_4x4 = PaletteDisplay(palette.get_colors(), container)

            
            # View: Takes remaining horizontal space
            output_view = ZoomableGraphicsView(container, self, palettes.index(palette))
            # output_view.setMinimumWidth(int(self.MIN_HEIGHT * 0.2))
            # output_view.setMinimumHeight(int(self.MIN_HEIGHT * 0.2))
            # output_view.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
            # output_view.clicked.connect(lambda: self._handle_view_click(len(self.dynamic_views)))

            # Define frame to put view into
            frame = QWidget(container)
            frame.setStyleSheet("border: 1px solid transparent;")
            frame.setMaximumWidth((int)(self.width() * 0.4)) if self.width() == self.MIN_WIDTH else frame.setMaximumWidth((int)(self.width() * 0.6))
            frame.setMaximumHeight((int)(self.height()/len(palettes) * 0.6)) if self.height() == self.MIN_HEIGHT else frame.setMaximumHeight((int)(self.height() * 0.4))
            frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            frame_layout = QHBoxLayout(frame)
            frame_layout.addWidget(output_view)
            frame_layout.setContentsMargins(0, 0, 0, 0)
            # set 1px transparent border
            frame_layout.setSpacing(0)


            # Add widgets to layout
            container_layout.addWidget(label, 0)       # No stretch
            container_layout.addWidget(palette_4x4, 0) # No stretch
            # container_layout.addWidget(output_view, 1) # Takes remaining space
            container_layout.addWidget(frame, 1)

            self.dynamic_frames.append(frame)
            self.dynamic_views.append(output_view)
            self.dynamic_labels.append(label)
            self.dynamic_layout.addWidget(container)

    def _get_text_width(self, text: str, label: QLabel) -> int:
        return label.fontMetrics().boundingRect(text).width()

    def update_original_image(self, image):
        """Update the main preview image."""
        if image and not image.isNull():
            pixmap = QPixmap.fromImage(image)
            scene = QGraphicsScene(self.original_view)
            self.original_view.setScene(scene)
            scene.addPixmap(pixmap)
            scene.setSceneRect(QRectF(pixmap.rect()))

            self.original_view.resetTransform()
            self.original_view.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
            self.original_view.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)

    def update_dynamic_images(self, images, labels, palettes, highlights):
        """Update conversion results."""
        if not images:
            return

        max_colors = -1
        self.best_indices = []

        # Find images with most colors
        for i, label in enumerate(labels):
            color_count = int(label.split('(')[1].split(' ')[0])
            if color_count > max_colors:
                max_colors = color_count
                self.best_indices = [i]
            elif color_count == max_colors:
                self.best_indices.append(i)

        # Set selected index to first best index
        self.selected_index = self.best_indices[0] if self.best_indices else None

        # Update images and labels
        for i, (image, label, palette) in enumerate(zip(images, labels, palettes)):
            if i >= len(self.dynamic_views):
                break

            view = self.dynamic_views[i]
            pixmap = QPixmap.fromImage(image)
            
            scene = QGraphicsScene(view)
            view.setScene(scene)
            scene.addPixmap(pixmap)
            scene.setSceneRect(QRectF(pixmap.rect()))
            
            view.resetTransform()
            view.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
            view.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)

            self.dynamic_labels[i].setText(label)

        # Update highlights
        self._update_highlights()

    def _update_highlights(self):
        """Update view highlighting."""
        for i, view in enumerate(self.dynamic_frames):
            style = ""
            if i == self.selected_index:
                # style = "background-color: #458447; QGraphicsView {background-color: #22272e}" if self.parent._config.get('dark_mode') == "dark" \
                # else    "background-color: #7ebc80; QGraphicsView {background-color: #f2f2f2}"
                style = "border: 1px solid #458447"
            elif i in self.best_indices:
                style = "border: 1px solid #2196F3"  # Blue for best alternatives

            view.setStyleSheet(style)

    def _handle_view_click(self, index: int):
        """Handle click on a view."""
        if index is not None and self.parent.image_manager.get_original_image() is not None:
            self.selected_index = index
            self._update_highlights()

    # ------------ EVENT HANDLERS ------------ #
    def eventFilter(self, source, event):
        if event.type() == QEvent.MouseButtonPress:
            logging.debug("Event filter triggered")
            if source in self.dynamic_layout:
                index = self.dynamic_layout.index(source)
                logging.debug(f'View clicked: {index}')
                self._handle_view_click(index)
                return True
        return super().eventFilter(source, event)
    
    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() == Qt.Key_Escape:
            # Instead of showing the dialog here, just call close()
            # The confirmation will be handled by closeEvent
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Handle window close events."""
        if self.CONFIRM_ON_EXIT:
            reply = QMessageBox.question(
                self,
                'Confirm Exit',
                'Are you sure you want to exit?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
    # ------------ GETTERS ------------ #

    def get_selected_index(self) -> int:
        """Return currently selected view index."""
        return self.selected_index

