from PyQt5.QtWidgets import QDockWidget, QLabel, QApplication, QWidget, QVBoxLayout, QSizePolicy
from PyQt5.QtCore import Qt, QRect, QPropertyAnimation
from PyQt5.QtGui import QPalette
import sys
import json
from pathlib import Path
from view.porypal_theme import PorypalTheme

def warn(message: str):
    print("\n" + '\033[1m' + 'WARN:' + '\033[93m' + f' {message}' + '\033[0m')

class QNotificationWidget(QDockWidget):
    """Custom dock widget that displays a scrolling notification message."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)

        # Make dock background transparent
        self.setStyleSheet("background-color: transparent; border: 0; padding: 0; margin: 0;")

        self.setFixedHeight(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.message_label = QLabel(self)
        self.message_label.setAlignment(Qt.AlignCenter)
        self._update_style()
        self.message_label.setFixedHeight(self.message_label.sizeHint().height() + 10)

        # Scrolling text
        self.scroll_animation = QPropertyAnimation(self.message_label, b"geometry", self)
        self.scroll_animation.finished.connect(self.scroll_finished)

    def _update_style(self):
        """Update style using application palette colors"""
        palette = QApplication.instance().palette()
        
        # Use theme colors from palette
        bg_color = palette.color(QPalette.Base).name()
        text_color = palette.color(QPalette.Text).name()
        
        self.message_label.setStyleSheet(
            f"background-color: {bg_color};"
            f"color: {text_color};"
            "font-size: 20px;"
            "border: 0;"
            "padding: 0;"
            "margin: 0;"
        )

    def resizeEvent(self, event):
        """Ensure the widget takes the full width of the parent window."""
        if self.parent:
            self.setFixedWidth(self.parent.width())
        super().resizeEvent(event)

    def show_notification(self, message, speed=50):
        """Show the notification with a fixed scrolling speed (default 50 pixels per second)."""
        self._update_style()  # Update style before showing
        self.message_label.setText((message + 16 * " ") * 20)
        self.message_label.setFixedWidth(self.message_label.sizeHint().width())

        label_width, label_height = self.message_label.sizeHint().width(), self.message_label.sizeHint().height()
        self.setFixedHeight(label_height)

        # Calculate duration based on fixed speed

        self.scroll_animation.stop()
        self.scroll_animation.setDuration(5000)
        self.scroll_animation.setStartValue(QRect(0, 0, label_width, label_height))
        self.scroll_animation.setEndValue(QRect(-(int)(label_width/10), 0, label_width, label_height))
        self.scroll_animation.start()

        self.show()


    def hide_notification(self):
        self.scroll_animation.stop()
        self.setFixedHeight(0)
        self.hide()

    def scroll_finished(self):
        self.hide_notification()

    def notify(self, message, error=None):
        self.hide_notification()
        self.show_notification(message)
        if error:
            warn(f'{message}, {error}')
