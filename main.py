# Main application code (main.py)
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from controller.porypalController import PorypalMainController
from view.porypalTheme import PorypalTheme
import yaml

# --- Load configuration from YAML file --- #
def load_config() -> dict:
    """Load configuration from YAML file."""
    try:
        with open('config.yaml', 'r') as file:
            return yaml.safe_load(file) or {}
    except FileNotFoundError:
        return {}


# --- Main application entry point --- #
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('gui/porypal.ico'))  # Set application icon

    config = load_config()
    
    # Initialize theme handler
    theme_instance = PorypalTheme(app,config)  # Applies theme from config
    
    controller = PorypalMainController(theme_instance, app, config)
    controller.view.show()
    sys.exit(app.exec_())