from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication
import yaml

class PorypalTheme:
    def __init__(self, app: QApplication, config: dict):
        self.app = app
        self.config = config
        self.app.setStyle('Fusion') # OS agnostic style
        self._dark_mode = self.config.get('dark_mode', 'light') == 'dark'
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
        if self._dark_mode:
            for item in dark_theme:
                palette.setColor(item[0], self._hex_to_QColor(item[1]))
            self.config['dark_mode'] = 'dark'
        else:
            for item in light_theme:
                palette.setColor(item[0], self._hex_to_QColor(item[1]))
            self.config['dark_mode'] = 'light'
        
        self.app.setPalette(palette)

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
]

light_theme = [
    (QPalette.Window, "#eae9f3"),
    (QPalette.WindowText, "#2b304b"),
    (QPalette.Base, "#ffffff"),
    (QPalette.Text, "#353549"),
    (QPalette.Button, "#dcdfec"),
    (QPalette.ButtonText, "#2b304b"),
]