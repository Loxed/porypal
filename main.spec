# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all submodules from our local packages
controller_modules = collect_submodules('controller')
model_modules = collect_submodules('model')
view_modules = collect_submodules('view')

# Collect UI files
view_data_files = collect_data_files('view')

a = Analysis(
    ['main.py'],
    pathex=[os.path.abspath(SPECPATH)],  # Add the spec file's directory to the path
    binaries=[],
    datas=[
        ('palettes', 'palettes'),
        ('presets', 'presets'),
        ('ressources', 'ressources'),
        ('config.yaml', '.'),
        ('controller', 'controller'),
        ('model', 'model'),
        ('view', 'view'),
        ('presets', 'presets'),
        ('example', 'example'),
        ('docs', 'docs'),
    ],
    hiddenimports=[
        'encodings',
        'controller',
        'model',
        'view',
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.uic',
        'PIL',
        'yaml',
        *controller_modules,
        *model_modules,
        *view_modules
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Changed to True temporarily for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['ressources\\porypal.ico'],
)
