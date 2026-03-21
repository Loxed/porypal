"""
server/presets_store.py

Routes: /api/presets

Preset logic is inlined here to avoid the server.presets / server.api.presets
naming collision that causes a circular import when frozen with PyInstaller.
"""

from __future__ import annotations
import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/presets", tags=["presets"])

_PRESETS_DIR = Path("presets")
_bundle = os.environ.get("PORYPAL_BUNDLE_DIR")
_BUNDLED_DIR: Path | None = Path(_bundle) / "presets" if _bundle else None


def _ensure_dir() -> None:
    _PRESETS_DIR.mkdir(exist_ok=True)


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


def _list_presets() -> list[dict]:
    _ensure_dir()
    seen: set[str] = set()
    result: list[dict] = []
    default_src = _BUNDLED_DIR or _PRESETS_DIR
    if default_src.exists():
        for f in sorted(default_src.glob("*.json")):
            p = _read_preset(f, is_default=True)
            if p and p["id"] not in seen:
                seen.add(p["id"])
                result.append(p)
    if _BUNDLED_DIR is not None and _PRESETS_DIR.exists():
        for f in sorted(_PRESETS_DIR.glob("*.json")):
            if f.stem in seen:
                continue
            p = _read_preset(f, is_default=False)
            if p:
                seen.add(p["id"])
                result.append(p)
    return result


def _load_preset(preset_id: str) -> dict | None:
    _ensure_dir()
    f = _PRESETS_DIR / f"{preset_id}.json"
    if f.exists():
        return json.loads(f.read_text())
    if _BUNDLED_DIR:
        fb = _BUNDLED_DIR / f"{preset_id}.json"
        if fb.exists():
            return json.loads(fb.read_text())
    return None


def _save_preset(preset_id: str, data: dict) -> dict:
    _ensure_dir()
    (_PRESETS_DIR / f"{preset_id}.json").write_text(json.dumps(data, indent=2))
    return data


def _delete_preset(preset_id: str) -> bool:
    _ensure_dir()
    f = _PRESETS_DIR / f"{preset_id}.json"
    if f.exists():
        f.unlink()
        return True
    return False


@router.get("")
def get_presets():
    return _list_presets()


@router.get("/{preset_id}")
def get_preset(preset_id: str):
    preset = _load_preset(preset_id)
    if not preset:
        raise HTTPException(404, f"Preset '{preset_id}' not found")
    return preset


@router.post("/{preset_id}")
def create_preset(preset_id: str, data: dict):
    return _save_preset(preset_id, data)


@router.delete("/{preset_id}")
def remove_preset(preset_id: str):
    if not _delete_preset(preset_id):
        raise HTTPException(404, f"Preset '{preset_id}' not found")
    return {"deleted": preset_id}
load_preset = _load_preset
list_presets = _list_presets
save_preset = _save_preset
delete_preset = _delete_preset
