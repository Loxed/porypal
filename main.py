#!/usr/bin/env python3
"""
PoryPal - Palette conversion tool for pokeemerald-expansion
Main application entry point.
"""

import sys
import logging
from pathlib import Path
import yaml
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from controller.porypal_controller import PorypalController
from view.porypal_theme import PorypalTheme

# Application metadata
APP_METADATA = {
    'name': "PoryPal",
    'version': "1.1.0",
    'debug': False,
    'config_path': Path("config.yaml"),
    'icon_path': Path("ressources/porypal.ico"),
    'org_name': "prisonlox",
    'org_domain': "porypal"
}

def main() -> int:
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if APP_METADATA['debug'] else logging.INFO,
        format='[%(pathname)s:%(lineno)d] %(levelname)s - %(message)s'
    )
    logging.info(f"Starting {APP_METADATA['name']} v{APP_METADATA['version']}")

    # Initialize Qt application
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_METADATA['name'])
    app.setApplicationVersion(APP_METADATA['version'])
    app.setOrganizationName(APP_METADATA['org_name'])
    app.setOrganizationDomain(APP_METADATA['org_domain'])

    # Set icon if available
    if APP_METADATA['icon_path'].exists():
        app.setWindowIcon(QIcon(str(APP_METADATA['icon_path'])))

    # Windows-specific taskbar icon
    try:
        from ctypes import windll
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            f"{APP_METADATA['org_domain']}.{APP_METADATA['name']}.1"
        )
    except ImportError:
        pass

    # Load configuration
    config = {}
    try:
        if APP_METADATA['config_path'].exists():
            with open(APP_METADATA['config_path'], 'r') as file:
                config = yaml.safe_load(file) or {}
            logging.debug("Configuration loaded successfully")
        else:
            logging.warning(f"Config file not found: {APP_METADATA['config_path']}")
    except Exception as e:
        logging.error(f"Config load failed: {e}")

    # Initialize theme and controller
    theme = PorypalTheme(app, config)
    controller = PorypalController(theme, app, config)
    # controller.view.show()

    # Run application
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())