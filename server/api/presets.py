"""
server/presets.py

Preset management – load/save JSON presets from the presets/ folder.

When running as a PyInstaller bundle:
  • Bundled (read-only) defaults live in  PORYPAL_BUNDLE_DIR/presets/
  • User-saved presets live in            CWD/presets/   (next to the exe)

list_presets() merges both sources; bundled ones are always marked
is_default=True and cannot be deleted.
"""

from __future__ import annotations
import json
import logging
import os
from pathlib import Path

# User-writable presets directory (relative to CWD, i.e. next to the exe).
PRESETS_DIR = Path("presets")

# Bundled read-only presets (sys._MEIPASS/presets/ when frozen, else None).
_bundle = os.environ.get("PORYPAL_BUNDLE_DIR")
BUNDLED_PRESETS_DIR: Path | None = Path(_bundle) / "presets" if _bundle else None


def _ensure_dir() -> None:
    PRESETS_DIR.mkdir(exist_ok=True)


def _read_preset(f: Path, is_default: bool = False) -> dict | None:
    try:
        data = json.loads(f.read_text())
        return {
            "id":         f.stem,
            "name":       data.get("name", f.stem),
            "tile_w":     data.get("tile_w", 32),
            "tile_h":     data.get("tile_h", 32),
            "out_tile_w": data.get("out_tile_w"),
            "out_tile_h": data.get("out_tile_h"),
            "cols":       data.get("cols", 9),
            "rows":       data.get("rows", 1),
            "slots":      data.get("slots", []),
            "src_cols":   data.get("src_cols"),
            "src_rows":   data.get("src_rows"),
            "is_default": data.get("is_default", is_default),
        }
    except Exception as e:
        logging.warning(f"Could not read preset {f.name}: {e}")
        return None


def list_presets() -> list[dict]:
    _ensure_dir()
    seen:   set[str]  = set()
    result: list[dict] = []

    # 1. Bundled defaults (from sys._MEIPASS when frozen, or the repo's
    #    presets/ dir in development when PORYPAL_BUNDLE_DIR is not set).
    _default_src = BUNDLED_PRESETS_DIR or PRESETS_DIR
    if _default_src.exists():
        for f in sorted(_default_src.glob("*.json")):
            p = _read_preset(f, is_default=True)
            if p and p["id"] not in seen:
                seen.add(p["id"])
                result.append(p)

    # 2. User presets (only when frozen; in dev the dirs are the same).
    if BUNDLED_PRESETS_DIR is not None and PRESETS_DIR.exists():
        for f in sorted(PRESETS_DIR.glob("*.json")):
            if f.stem in seen:
                continue
            p = _read_preset(f, is_default=False)
            if p:
                seen.add(p["id"])
                result.append(p)

    return result


def load_preset(preset_id: str) -> dict | None:
    # Check user dir first (allows overriding a default by same name).
    _ensure_dir()
    f = PRESETS_DIR / f"{preset_id}.json"
    if f.exists():
        return json.loads(f.read_text())

    # Fall back to bundled defaults.
    if BUNDLED_PRESETS_DIR:
        fb = BUNDLED_PRESETS_DIR / f"{preset_id}.json"
        if fb.exists():
            return json.loads(fb.read_text())

    return None


def save_preset(preset_id: str, data: dict) -> dict:
    _ensure_dir()
    f = PRESETS_DIR / f"{preset_id}.json"
    f.write_text(json.dumps(data, indent=2))
    return data


def delete_preset(preset_id: str) -> bool:
    _ensure_dir()
    f = PRESETS_DIR / f"{preset_id}.json"
    if f.exists():
        f.unlink()
        return True
    return False

from server.preset_store import router