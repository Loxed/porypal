"""
server/api/palettes.py

Routes: /api/palettes
"""

from __future__ import annotations
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from server.state import state

router = APIRouter(prefix="/api/palettes", tags=["palettes"])


@router.get("")
def list_palettes():
    """Return all loaded palettes with their colors as hex strings."""
    return [
        {
            "name": p.name,
            "colors": [c.to_hex() for c in p.colors],
            "count": len(p.colors),
        }
        for p in state.palette_manager.get_palettes()
    ]


@router.post("/reload")
def reload_palettes():
    """Reload palettes from the palettes/ directory."""
    state.palette_manager.reload()
    return {"loaded": len(state.palette_manager.get_palettes())}


@router.post("/upload")
async def upload_palette(file: UploadFile = File(...)):
    """Upload a .pal file into the palettes/ directory."""
    dest = Path("palettes") / file.filename
    dest.write_bytes(await file.read())
    state.palette_manager.reload()
    return {"uploaded": file.filename}


@router.get("/{name}/download")
def download_palette(name: str):
    """Stream a .pal file back to the client for download."""
    path = Path("palettes") / name
    if not path.exists():
        raise HTTPException(404, f"Palette '{name}' not found")
    return FileResponse(
        path=str(path),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.delete("/{name}")
def delete_palette(name: str):
    """Delete a user palette. Refuses if marked as default."""
    path = Path("palettes") / name
    if not path.exists():
        raise HTTPException(404, f"Palette '{name}' not found")
    path.unlink()
    state.palette_manager.reload()
    return {"deleted": name}