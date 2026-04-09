# porypal.spec
# ─────────────────────────────────────────────────────────────────────────────
# PyInstaller build spec for Porypal.
#
# Usage (run from repo root after building the frontend):
#   pip install pyinstaller
#   cd frontend && npm run build && cd ..
#   pyinstaller porypal.spec
#
# Output: dist/porypal/   (a folder – zip it up for distribution)
# ─────────────────────────────────────────────────────────────────────────────

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# ── Data files bundled into _MEIPASS ─────────────────────────────────────────
# Format: (source_path, dest_path_inside_bundle)
_root = Path(".").resolve()

datas = []

# Frontend (built by `npm run build`)
_frontend_dist = _root / "frontend" / "dist"
if _frontend_dist.exists():
    datas.append((str(_frontend_dist), "frontend/dist"))
else:
    import sys as _s
    print("WARNING: frontend/dist not found – run `cd frontend && npm run build` first",
          file=_s.stderr)

# Example sprites
_example = _root / "example"
if _example.exists():
    datas.append((str(_example), "example"))

# Bundled read-only palettes
_defaults = _root / "palettes" / "defaults"
if _defaults.exists():
    datas.append((str(_defaults), "palettes/defaults"))

# Default presets (gen_4_ow_sprites etc.)
_presets = _root / "presets"
if _presets.exists():
    datas.append((str(_presets), "presets"))

# Model data files used at runtime (for Oklab conversion/k-means extraction)
_model_data = _root / "model" / "data"
if _model_data.exists():
    datas.append((str(_model_data), "model/data"))

# ── scikit-learn (needs special collection) ───────────────────────────────────
sklearn_datas, sklearn_binaries, sklearn_hiddenimports = collect_all("sklearn")

# ── PIL / Pillow ──────────────────────────────────────────────────────────────
pil_datas, pil_binaries, pil_hiddenimports = collect_all("PIL")

# ── Hidden imports ────────────────────────────────────────────────────────────
hiddenimports = [
    # uvicorn
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan.on",
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    # ASGI / HTTP
    "h11",
    "h11._connection",
    "h11._events",
    "anyio",
    "anyio._backends._asyncio",
    "anyio.streams.memory",
    # FastAPI / Starlette
    "starlette.routing",
    "starlette.staticfiles",
    "starlette.responses",
    "fastapi.routing",
    "fastapi.staticfiles",
    # multipart (file uploads)
    "multipart",
    "python_multipart",
    # email (used internally by some libs)
    "email.mime.text",
    "email.mime.multipart",
    # numpy
    "numpy",
    "numpy.core._methods",
    # pydantic v2 internals
    "pydantic.v1",
    "pydantic_core",
    # misc
    "typing_extensions",
    "exceptiongroup",
]

hiddenimports += sklearn_hiddenimports
hiddenimports += pil_hiddenimports
hiddenimports += collect_submodules("anyio")
hiddenimports += collect_submodules("starlette")

# Local packages – not installed so collect_submodules won't find them.
hiddenimports += [
    "server",
    "server.app",
    "server.state",
    "server.helpers",
    "server.presets",
    "server.api",
    "server.api.palettes",
    "server.api.convert",
    "server.api.extract",
    "server.api.batch",
    "server.api.tileset",
    "server.api.presets",
    "server.api.health",
    "server.api.library",
    "server.api.pipeline",
    "server.api.items",
    "server.api.shiny",
    "server.preset_store",
    "model",
    "model.palette",
    "model.palette_manager",
    "model.palette_extractor",
    "model.image_manager",
    "model.tileset_manager",
]

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ["main.py"],
    pathex=[str(_root)],
    binaries=sklearn_binaries + pil_binaries,
    datas=datas + sklearn_datas + pil_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "PySide6", "PyQt5", "PyQt6",
        "matplotlib", "jupyter", "notebook",
        "IPython", "tornado", "zmq",
        "wx", "gi",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="porypal",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,        # shows a terminal window so users can see the server is running
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Windows icon (optional – add a .ico file to the repo root)
    icon=str(_root / "frontend" / "public" / "porypal.ico")
        if (_root / "frontend" / "public" / "porypal.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="porypal",
)
