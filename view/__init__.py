"""
PoryPal View Package
This package contains the view components for the PoryPal application's user interface.
"""

from .automation_view import AutomationView
from .palette_automation_view import PaletteAutomationView
from .porypal_view import PorypalView
from .tileset_editor_view import TilesetEditorView
from .zoomable_graphics_view import ZoomableGraphicsView
from .palette_display import PaletteDisplay
from .porypal_theme import PorypalTheme

__all__ = [
    'AutomationView',
    'PaletteAutomationView',
    'PorypalView',
    'TilesetEditorView',
    'ZoomableGraphicsView',
    'PaletteDisplay',
    'PorypalTheme'
]

__version__ = '2.0.0'
