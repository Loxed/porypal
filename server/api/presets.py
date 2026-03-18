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
    out_tile_w: Optional[int] = None   # output tile width  (None = same as tile_w)
    out_tile_h: Optional[int] = None   # output tile height (None = same as tile_h)
    cols: int = 9
    rows: int = 1
    slots: list
    slot_labels: Optional[list] = None
    src_cols: Optional[int] = None
    src_rows: Optional[int] = None
    # Legacy resize fields — accepted so old presets can be re-saved cleanly
    resize_tile_w: Optional[int] = None
    resize_tile_h: Optional[int] = None
    resize_interpolation: Optional[str] = None


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
    data = body.model_dump(exclude_none=False)

    # Normalise: if out_tile_w/h not set but legacy resize fields are, migrate them
    if data.get("out_tile_w") is None and data.get("resize_tile_w"):
        data["out_tile_w"] = data["resize_tile_w"]
    if data.get("out_tile_h") is None and data.get("resize_tile_h"):
        data["out_tile_h"] = data["resize_tile_h"]

    # Drop legacy keys so the stored JSON stays clean
    data.pop("resize_tile_w", None)
    data.pop("resize_tile_h", None)
    data.pop("resize_interpolation", None)

    # Drop None out_tile_w/h if they match tile_w/h (no-op resize)
    if data.get("out_tile_w") == data["tile_w"]:
        data["out_tile_w"] = None
    if data.get("out_tile_h") == data["tile_h"]:
        data["out_tile_h"] = None

    return save_preset(preset_id, data)


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