"""
server/api/presets.py

Routes: /api/presets
"""

from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.presets import list_presets, load_preset, save_preset, delete_preset

router = APIRouter(prefix="/api/presets", tags=["presets"])


class PresetBody(BaseModel):
    name: str
    tile_w: int = 32
    tile_h: int = 32
    cols: int = 9
    rows: int = 1
    slots: list
    slot_labels: Optional[list] = None


@router.get("")
def get_presets():
    return list_presets()


@router.get("/{preset_id}")
def get_preset(preset_id: str):
    p = load_preset(preset_id)
    if not p:
        raise HTTPException(404, f"Preset '{preset_id}' not found")
    return p


@router.post("/{preset_id}")
def upsert_preset(preset_id: str, body: PresetBody):
    return save_preset(preset_id, body.model_dump())


@router.delete("/{preset_id}")
def remove_preset(preset_id: str):
    p = load_preset(preset_id)
    if not p:
        raise HTTPException(404, f"Preset '{preset_id}' not found")
    if p.get("is_default", False):
        raise HTTPException(403, f"Preset '{preset_id}' is a default preset and cannot be deleted")
    if not delete_preset(preset_id):
        raise HTTPException(500, "Failed to delete preset")
    return {"deleted": preset_id}