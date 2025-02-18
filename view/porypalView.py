from PyQt5.QtWidgets import QWidget, QGraphicsScene, QGraphicsView, QLabel, QGridLayout, QFileDialog
from PyQt5.QtGui import QPixmap, QPainter, QImage
from PyQt5.QtCore import Qt
from PyQt5 import uic

class porypalMainView(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi("view/porypalette.ui", self)
        self.original_scene = QGraphicsScene()
        self.original_view.setScene(self.original_scene)
        self.original_view.setRenderHints(QPainter.Antialiasing)

        self.result_views = []
        self.result_scenes = []
        self.result_labels = []
        self.setup_result_components()

    def setup_result_components(self):
        """Setup the dynamic result components."""
        converted_box = self.findChild(QGridLayout, "converted_box")
        for i in range(4):  # Assuming 4 palettes max for simplicity
            scene = QGraphicsScene()
            view = QGraphicsView()
            view.setScene(scene)
            view.setRenderHints(QPainter.Antialiasing)
            view.installEventFilter(self)
            label = QLabel("Loading...")
            label.setAlignment(Qt.AlignCenter)
            converted_box.addWidget(label, 1 + i, 1)
            converted_box.addWidget(view, 1 + i, 2)
            self.result_views.append(view)
            self.result_scenes.append(scene)
            self.result_labels.append(label)

    def update_preview(self, image):
        """Update the preview area with the provided image."""
        self.original_scene.clear()
        pixmap = QPixmap.fromImage(image)
        self.original_scene.addPixmap(pixmap)
        self.original_view.fitInView(self.original_scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def update_converted_images(self, converted_data, labels):
        """Update the converted images and labels."""
        for i, converted in enumerate(converted_data):
            pixmap = QPixmap.fromImage(converted)
            self.result_scenes[i].clear()
            self.result_scenes[i].addPixmap(pixmap)
            self.result_views[i].fitInView(self.result_scenes[i].itemsBoundingRect(), Qt.KeepAspectRatio)
            self.result_labels[i].setText(labels[i])

