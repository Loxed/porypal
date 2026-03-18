"""
server/api/palettes.py

Routes: /api/palettes
"""

from __future__ import annotations
import io
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from server.state import state

router = APIRouter(prefix="/api/palettes", tags=["palettes"])

USER_DIR = Path("palettes") / "user"


# ---------- helpers ----------

def _safe_path(name: str) -> Path | None:
    """Resolve a palette name/key to its path, guarding against traversal."""
    path = state.palette_manager.get_path(name)
    return path


def _user_path_for_key(key: str) -> Path:
    """Turn a key like 'folder/name.pal' or 'name.pal' into an absolute user path."""
    parts = key.split("/", 1)
    if len(parts) == 2:
        return USER_DIR / parts[0] / parts[1]
    return USER_DIR / parts[0]


# ---------- routes ----------

@router.get("")
def list_palettes():
    """Return all loaded palettes with their colors, folder, and metadata."""
    result = []
    for p in state.palette_manager.get_palettes():
        meta = state.palette_manager.get_meta(p.name) or {}
        result.append({
            "name":       p.name,
            "path":       p.name,           # stable key — same as name after the manager refactor
            "folder":     meta.get("folder"),
            "colors":     [c.to_hex() for c in p.colors],
            "count":      len(p.colors),
            "is_default": meta.get("is_default", False),
            "source":     meta.get("source", "legacy"),
        })
    return result


@router.get("/folders")
def list_folders():
    """Return the current user subfolder names."""
    return state.palette_manager.get_folders()


@router.post("/reload")
def reload_palettes():
    """Reload palettes from disk."""
    state.palette_manager.reload()
    return {"loaded": len(state.palette_manager.get_palettes())}


@router.post("/upload")
async def upload_palette(
    file: UploadFile = File(...),
    folder: str | None = None,
):
    """Upload a .pal file into palettes/user/ (or a subfolder)."""
    if not file.filename.endswith(".pal"):
        raise HTTPException(400, "Only .pal files are accepted")
    dest_dir = USER_DIR / folder if folder else USER_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / file.filename
    dest.write_bytes(await file.read())
    state.palette_manager.reload()
    return {"uploaded": file.filename, "folder": folder, "source": "user"}


class FolderBody(BaseModel):
    name: str


@router.post("/folders")
def create_folder(body: FolderBody):
    """Create a subfolder in palettes/user/."""
    name = body.name.strip()
    if not name or "/" in name or "\\" in name or name.startswith("."):
        raise HTTPException(400, "Invalid folder name")
    folder = USER_DIR / name
    folder.mkdir(parents=True, exist_ok=True)
    state.palette_manager.reload()
    return {"created": name}


@router.delete("/folders/{name}")
def delete_folder(name: str):
    """Delete a subfolder if it's empty (no .pal files)."""
    folder = USER_DIR / name
    if not folder.exists():
        raise HTTPException(404, f"Folder '{name}' not found")
    pals = list(folder.glob("*.pal"))
    if pals:
        raise HTTPException(400, f"Folder '{name}' still contains {len(pals)} palette(s)")
    folder.rmdir()
    state.palette_manager.reload()
    return {"deleted": name}


class RenameBody(BaseModel):
    new_name: str    # just the stem, no .pal extension


@router.patch("/{palette_path:path}/rename")
def rename_palette(palette_path: str, body: RenameBody):
    """Rename a palette file on disk."""
    if state.palette_manager.is_default(palette_path):
        raise HTTPException(403, "Cannot rename a default palette")

    path = _safe_path(palette_path)
    if not path or not path.exists():
        raise HTTPException(404, f"Palette '{palette_path}' not found")

    new_stem = body.new_name.strip()
    if not new_stem or "/" in new_stem:
        raise HTTPException(400, "Invalid palette name")

    new_filename = new_stem if new_stem.endswith(".pal") else f"{new_stem}.pal"
    new_path = path.parent / new_filename
    if new_path.exists() and new_path != path:
        raise HTTPException(409, f"A palette named '{new_filename}' already exists in this folder")

    path.rename(new_path)
    state.palette_manager.reload()
    return {"renamed": new_filename}


class MoveBody(BaseModel):
    target_folder: str | None = None   # None = root of palettes/user/


@router.patch("/{palette_path:path}/move")
def move_palette(palette_path: str, body: MoveBody):
    """Move a palette to a different folder."""
    if state.palette_manager.is_default(palette_path):
        raise HTTPException(403, "Cannot move a default palette")

    path = _safe_path(palette_path)
    if not path or not path.exists():
        raise HTTPException(404, f"Palette '{palette_path}' not found")

    dest_dir = USER_DIR / body.target_folder if body.target_folder else USER_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    new_path = dest_dir / path.name

    if new_path == path:
        return {"moved": palette_path}

    if new_path.exists():
        raise HTTPException(409, f"A palette named '{path.name}' already exists in the target folder")

    path.rename(new_path)
    state.palette_manager.reload()
    new_key = f"{body.target_folder}/{path.name}" if body.target_folder else path.name
    return {"moved": new_key}


class ColorsBody(BaseModel):
    colors: list[str]   # list of hex strings


@router.put("/{palette_path:path}/colors")
def update_palette_colors(palette_path: str, body: ColorsBody):
    """Overwrite the colors in a palette file."""
    if state.palette_manager.is_default(palette_path):
        raise HTTPException(403, "Cannot edit a default palette")

    path = _safe_path(palette_path)
    if not path or not path.exists():
        raise HTTPException(404, f"Palette '{palette_path}' not found")

    if len(body.colors) > 16:
        raise HTTPException(400, "GBA palettes cannot exceed 16 colors")

    lines = ["JASC-PAL", "0100", str(len(body.colors))]
    for hex_color in body.colors:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        lines.append(f"{r} {g} {b}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    state.palette_manager.reload()
    return {"updated": palette_path}


@router.get("/{name}/download")
def download_palette(name: str):
    """Stream a .pal file back to the client for download."""
    path = _safe_path(name)
    if not path or not path.exists():
        raise HTTPException(404, f"Palette '{name}' not found")
    filename = path.name
    return FileResponse(
        path=str(path),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{palette_path:path}")
def delete_palette(palette_path: str):
    """Delete a user or legacy palette. Refuses defaults."""
    if state.palette_manager.is_default(palette_path):
        raise HTTPException(403, f"'{palette_path}' is a default palette and cannot be deleted")
    path = _safe_path(palette_path)
    if not path or not path.exists():
        raise HTTPException(404, f"Palette '{palette_path}' not found")
    path.unlink()
    state.palette_manager.reload()
    return {"deleted": palette_path}