"""
PoryPal
A tool for managing and automating Pokemon game tileset and palette operations.
"""

__version__ = '2.0.0'
__author__ = 'Lox'
__license__ = 'MIT'

from . import controller
from . import view
from . import model

__all__ = [
    'controller',
    'view',
    'model'
]
