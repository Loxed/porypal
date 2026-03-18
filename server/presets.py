"""
server/presets.py

Preset management — load/save JSON presets from the presets/ folder.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path

PRESETS_DIR = Path("presets")


def _ensure_dir():
    PRESETS_DIR.mkdir(exist_ok=True)


def list_presets() -> list[dict]:
    _ensure_dir()
    result = []
    for f in sorted(PRESETS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            result.append({
                "id":           f.stem,
                "name":         data.get("name", f.stem),
                "tile_w":       data.get("tile_w", 32),
                "tile_h":       data.get("tile_h", 32),
                "out_tile_w":   data.get("out_tile_w"),   # None if not set
                "out_tile_h":   data.get("out_tile_h"),   # None if not set
                "cols":         data.get("cols", 9),
                "rows":         data.get("rows", 1),
                "slots":        data.get("slots", []),
                "src_cols":     data.get("src_cols"),
                "src_rows":     data.get("src_rows"),
                "is_default":   data.get("is_default", False),
            })
        except Exception as e:
            logging.warning(f"Could not read preset {f.name}: {e}")
    return result


def load_preset(preset_id: str) -> dict | None:
    _ensure_dir()
    f = PRESETS_DIR / f"{preset_id}.json"
    if not f.exists():
        return None
    return json.loads(f.read_text())


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