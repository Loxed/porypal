"""
server/api/palettes.py

Routes: /api/palettes
"""

from __future__ import annotations
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from server.state import state

router = APIRouter(prefix="/api/palettes", tags=["palettes"])


@router.get("")
def list_palettes():
    """Return all loaded palettes with their colors and metadata."""
    result = []
    for p in state.palette_manager.get_palettes():
        meta = state.palette_manager.get_meta(p.name) or {}
        result.append({
            "name": p.name,
            "colors": [c.to_hex() for c in p.colors],
            "count": len(p.colors),
            "is_default": meta.get("is_default", False),
            "source": meta.get("source", "legacy"),
        })
    return result


@router.post("/reload")
def reload_palettes():
    """Reload palettes from disk."""
    state.palette_manager.reload()
    return {"loaded": len(state.palette_manager.get_palettes())}


@router.post("/upload")
async def upload_palette(file: UploadFile = File(...)):
    """Upload a .pal file into palettes/user/."""
    if not file.filename.endswith(".pal"):
        raise HTTPException(400, "Only .pal files are accepted")
    dest_dir = Path("palettes") / "user"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / file.filename
    dest.write_bytes(await file.read())
    state.palette_manager.reload()
    return {"uploaded": file.filename, "source": "user"}


@router.get("/{name}/download")
def download_palette(name: str):
    """Stream a .pal file back to the client for download."""
    path = state.palette_manager.get_path(name)
    if not path or not path.exists():
        raise HTTPException(404, f"Palette '{name}' not found")
    return FileResponse(
        path=str(path),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.delete("/{name}")
def delete_palette(name: str):
    """Delete a user or legacy palette. Refuses defaults."""
    if state.palette_manager.is_default(name):
        raise HTTPException(403, f"'{name}' is a default palette and cannot be deleted")
    path = state.palette_manager.get_path(name)
    if not path or not path.exists():
        raise HTTPException(404, f"Palette '{name}' not found")
    path.unlink()
    state.palette_manager.reload()
    return {"deleted": name}