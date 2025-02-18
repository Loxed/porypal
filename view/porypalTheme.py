# view/PorypalTheme.py
import yaml
from dataclasses import dataclass
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette

@dataclass
class ThemeTemplate:
    """Dataclass holding all color properties for application theming."""
    window: QColor
    window_text: QColor
    base: QColor
    alternate_base: QColor
    tooltip_base: QColor
    tooltip_text: QColor
    text: QColor
    button: QColor
    button_text: QColor
    highlight: QColor
    highlighted_text: QColor

# Theme presets with improved color schemes
light_theme = ThemeTemplate(
    window=QColor(234, 233, 239),       # Soft lavender gray
    window_text=QColor(43, 48, 59),     # Deep slate
    base=QColor(255, 255, 255),         # Pure white
    alternate_base=QColor(245, 245, 247), # Warm light gray
    tooltip_base=QColor(255, 247, 231), # Warm off-white
    tooltip_text=QColor(88, 82, 123),   # Muted purple
    text=QColor(53, 53, 69),            # Dark navy
    button=QColor(220, 223, 228),       # Cool medium gray
    button_text=QColor(43, 48, 59),     # Matching window text
    highlight=QColor(140, 170, 203),    # Soft denim blue
    highlighted_text=Qt.white
)

dark_theme = ThemeTemplate(
    window=QColor(34, 39, 46),          # Deep space gray
    window_text=QColor(230, 237, 243),  # Frost white
    base=QColor(45, 51, 59),            # Dark slate
    alternate_base=QColor(38, 43, 51),  # Slightly darker slate
    tooltip_base=QColor(24, 26, 31),    # Near-black
    tooltip_text=QColor(170, 178, 189), # Medium gray
    text=QColor(205, 214, 224),         # Light steel blue
    button=QColor(55, 62, 71),          # Medium slate
    button_text=QColor(230, 237, 243),  # Matching window text
    highlight=QColor(114, 137, 218),    # Periwinkle blue
    highlighted_text=Qt.black
)

# Alternative theme options (can be added to config)
midnight_theme = ThemeTemplate(
    window=QColor(16, 20, 31),          # Deep ocean
    window_text=QColor(167, 215, 255),  # Ice blue
    base=QColor(23, 30, 45),            # Dark navy
    alternate_base=QColor(30, 38, 58),  # Medium navy
    tooltip_base=QColor(11, 14, 22),    # Near-black
    tooltip_text=QColor(140, 170, 200), # Medium steel blue
    text=QColor(200, 220, 240),         # Pale blue
    button=QColor(40, 50, 70),          # Steel blue
    button_text=QColor(180, 200, 220),  # Soft blue
    highlight=QColor(92, 188, 182),     # Tropical teal
    highlighted_text=QColor(16, 20, 31) # Dark ocean
)

sunset_theme = ThemeTemplate(
    window=QColor(255, 243, 229),       # Warm cream
    window_text=QColor(90, 45, 70),     # Deep plum
    base=QColor(255, 251, 245),         # Bright white
    alternate_base=QColor(255, 235, 215), # Peach
    tooltip_base=QColor(255, 225, 195), # Light peach
    tooltip_text=QColor(150, 75, 50),   # Terracotta
    text=QColor(100, 50, 40),           # Dark terracotta
    button=QColor(255, 215, 185),       # Warm sand
    button_text=QColor(150, 75, 50),    # Matching tooltip text
    highlight=QColor(255, 150, 100),    # Coral orange
    highlighted_text=Qt.white
)

class PorypalTheme:
    """Handles application theme management and configuration."""
    
    def __init__(self, app, config: dict) -> None:
        self.app = app
        self.config = config

        # OS Agnostic theme
        self.app.setStyle("Fusion")

        # init theme to previously saved value (stored in config.yaml)
        self.is_dark_theme = self.config.get('dark_mode', 'light') == 'dark'
        self.set_dark_theme() if self.is_dark_theme else self.set_light_theme()

    # save theme state to config.yaml
    def _save_config(self) -> None:
        """Save current configuration to YAML file."""
        with open('config.yaml', 'w') as file:
            yaml.dump(self.config, file, default_flow_style=False)

    def toggle_theme(self) -> None:
        """Switch between dark and light themes."""
        self.is_dark_theme = not self.is_dark_theme
        self.set_dark_theme() if self.is_dark_theme else self.set_light_theme()
        self.config['dark_mode'] = 'dark' if self.is_dark_theme else 'light'
        self._save_config()

    def set_dark_theme(self) -> None:
        """Apply dark theme preset."""
        theme = self._load_theme(dark_theme)
        self.app.setPalette(theme)

    def set_light_theme(self) -> None:
        """Apply light theme preset."""
        theme = self._load_theme(light_theme)
        self.app.setPalette(theme)

    def set_midnight_theme(self) -> None:
        """Apply midnight theme preset."""
        theme = self._load_theme(midnight_theme)
        self.app.setPalette(theme)

    def set_sunset_theme(self) -> None:
        """Apply sunset theme preset."""
        theme = self._load_theme(sunset_theme)
        self.app.setPalette(theme)

    def _load_theme(self, theme: ThemeTemplate) -> QPalette:
        """Create QPalette from theme template."""
        palette = QPalette()
        palette.setColor(QPalette.Window, theme.window)
        palette.setColor(QPalette.WindowText, theme.window_text)
        palette.setColor(QPalette.Base, theme.base)
        palette.setColor(QPalette.AlternateBase, theme.alternate_base)
        palette.setColor(QPalette.ToolTipBase, theme.tooltip_base)
        palette.setColor(QPalette.ToolTipText, theme.tooltip_text)
        palette.setColor(QPalette.Text, theme.text)
        palette.setColor(QPalette.Button, theme.button)
        palette.setColor(QPalette.ButtonText, theme.button_text)
        palette.setColor(QPalette.Highlight, theme.highlight)
        palette.setColor(QPalette.HighlightedText, theme.highlighted_text)
        return palette