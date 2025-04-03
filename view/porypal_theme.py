from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication
import yaml

class PorypalTheme:
    def __init__(self, app: QApplication, config: dict):
        self.app = app
        self.config = config
        self.app.setStyle('Fusion')  # OS agnostic style
        self._dark_mode = self.config.get('dark_mode')
        self.apply_theme()

    def set_dark_theme(self):
        self._dark_mode = True
        self.apply_theme()

    def set_light_theme(self):
        self._dark_mode = False
        self.apply_theme()

    def toggle_theme(self):
        self._dark_mode = not self._dark_mode
        self.apply_theme()

    def _hex_to_QColor(self, hex: str) -> QColor:
        return QColor(hex)

    def apply_theme(self):
        palette = QPalette()
        theme = dark_theme if self._dark_mode else light_theme

        for item in theme:
            if len(item) == 2:
                # Standard color setting
                palette.setColor(item[0], self._hex_to_QColor(item[1]))
            elif len(item) == 3:
                # Disabled state color setting (ColorGroup first, then ColorRole)
                palette.setColor(item[1], item[0], self._hex_to_QColor(item[2]))

        self.app.setPalette(palette)
        self.config['dark_mode'] = 'dark' if self._dark_mode else 'light'

        with open('config.yaml', 'w') as file:
            yaml.dump(self.config, file, default_flow_style=False)

# ----- THEMES ----- #
dark_theme = [
    (QPalette.Window, "#22272e"),
    (QPalette.WindowText, "#e6edf3"),
    (QPalette.Base, "#2d333b"),
    (QPalette.Text, "#cdd6e0"),
    (QPalette.Button, "#373e47"),
    (QPalette.ButtonText, "#e6edf3"),
    # Disabled state
    (QPalette.Button, QPalette.Disabled, "#2d3238"),
    (QPalette.ButtonText, QPalette.Disabled, "#abbfd0"),
]

light_theme = [
    (QPalette.Window, "#eae9f3"),
    (QPalette.WindowText, "#2b304b"),
    (QPalette.Base, "#ffffff"),
    (QPalette.Text, "#353549"),
    (QPalette.Button, "#dcdfec"),
    (QPalette.ButtonText, "#2b304b"),
    # Disabled state
    (QPalette.Button, QPalette.Disabled, "#a5acc8"),
    (QPalette.ButtonText, QPalette.Disabled, "#252839"),
]
