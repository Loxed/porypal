"""
server/api/library.py

Routes: /api/palette-library

Performance design:
  GET /api/palette-library          → depth-1 ONLY. Cached by mtime.
  GET /api/palette-library/folder   → depth-1 children of any sub-folder (lazy expand).
  GET /api/palette-library/pokemon  → paginated list of pokemon inside a pokemon_folder.
  GET /api/palette-library/pokemon-node → full data for one pokemon (called on card open).
  GET /api/palette-library/sprite   → serve a PNG or .pal file from the library.
"""

from __future__ import annotations
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from model.palette import Palette
from server.state import state

router = APIRouter(prefix="/api/palette-library", tags=["library"])

LIBRARY_DIR: Path = Path("palette_library").resolve()

POKEMON_PAL_NAMES = {"normal.pal", "shiny.pal", "overworld_normal.pal", "overworld_shiny.pal"}

POKEMON_SPRITE_PRIORITY = [
    "icon.png", "front.png", "anim_front.png",
    "back.png", "overworld.png", "overworldf.png",
]

PAGE_SIZE = 20

# Caches
_pal_cache:        dict[str, tuple[float, list[str]]] = {}
_candidates_cache: dict[str, tuple[float, list[Path]]] = {}
_tree_cache:       dict = {"mtime": -1.0, "tree": []}


def _read_colors(path: Path) -> list[str] | None:
    key = str(path)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    cached = _pal_cache.get(key)
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        colors = [c.to_hex() for c in Palette.from_jasc_pal(path).colors]
        _pal_cache[key] = (mtime, colors)
        return colors
    except Exception as e:
        logging.warning(f"Could not read library palette {path}: {e}")
        return None


def _scan_dir(directory: Path) -> tuple[list[Path], list[Path]]:
    files, dirs = [], []
    try:
        for item in directory.iterdir():
            if item.is_file():
                files.append(item)
            elif item.is_dir():
                dirs.append(item)
    except (PermissionError, OSError):
        pass
    files.sort(key=lambda p: p.name.lower())
    dirs.sort(key=lambda p: p.name.lower())
    return files, dirs


def _is_pokemon_dir(files: list[Path]) -> bool:
    names = {f.name.lower() for f in files}
    return bool(names & POKEMON_PAL_NAMES)


def _rel(path: Path) -> str:
    return str(path.relative_to(LIBRARY_DIR))


def _guard(target: Path) -> None:
    if not str(target).startswith(str(LIBRARY_DIR)):
        raise HTTPException(400, "Invalid path")


def _classify_subdir(sub: Path) -> str:
    sub_files, sub_subdirs = _scan_dir(sub)
    if _is_pokemon_dir(sub_files):
        return 'pokemon'
    if sub_subdirs:
        first_child_files, _ = _scan_dir(sub_subdirs[0])
        if _is_pokemon_dir(first_child_files):
            return 'pokemon_parent'
    return 'folder'


def _walk_depth1(directory: Path) -> list[dict]:
    files, subdirs = _scan_dir(directory)
    nodes: list[dict] = []
    for f in files:
        if f.suffix.lower() == ".pal":
            colors = _read_colors(f)
            if colors is not None:
                nodes.append({"type": "palette", "name": f.name, "path": _rel(f), "colors": colors})
    for sub in subdirs:
        kind = _classify_subdir(sub)
        if kind in ('pokemon', 'pokemon_parent'):
            nodes.append({"type": "pokemon_folder", "name": sub.name, "path": _rel(sub)})
        else:
            nodes.append({"type": "folder", "name": sub.name, "path": _rel(sub)})
    return nodes


def _read_pokemon_node(directory: Path) -> dict:
    files, subdirs = _scan_dir(directory)
    palettes: list[dict] = []
    sprites:  list[dict] = []
    subforms: dict       = {}
    for f in files:
        ext = f.suffix.lower()
        if ext == ".pal":
            colors = _read_colors(f)
            if colors is not None:
                palettes.append({"name": f.name, "path": _rel(f), "colors": colors})
        elif ext == ".png":
            sprites.append({"name": f.name, "path": _rel(f)})
    for sub in subdirs:
        subforms[sub.name] = _read_pokemon_node(sub)
    priority_map = {n: i for i, n in enumerate(POKEMON_SPRITE_PRIORITY)}
    sprites.sort(key=lambda s: priority_map.get(s["name"].lower(), len(POKEMON_SPRITE_PRIORITY)))
    return {
        "type": "pokemon", "name": directory.name, "path": _rel(directory),
        "palettes": palettes, "sprites": sprites, "subforms": subforms,
    }


def _get_pokemon_candidates(parent: Path, q: str = "") -> list[Path]:
    key = str(parent)
    try:
        mtime = os.path.getmtime(parent)
    except OSError:
        return []
    cached = _candidates_cache.get(key)
    if cached and cached[0] == mtime:
        candidates = cached[1]
    else:
        _, subdirs = _scan_dir(parent)
        candidates = subdirs
        _candidates_cache[key] = (mtime, candidates)
    if q:
        q_lower = q.lower()
        return [d for d in candidates if q_lower in d.name.lower()]
    return candidates


@router.get("")
def list_library():
    if not LIBRARY_DIR.exists():
        return []
    try:
        mtime = os.path.getmtime(LIBRARY_DIR)
    except OSError:
        return []
    if _tree_cache["mtime"] == mtime:
        return _tree_cache["tree"]
    tree = _walk_depth1(LIBRARY_DIR)
    _tree_cache["mtime"] = mtime
    _tree_cache["tree"]  = tree
    return tree


@router.get("/folder")
def list_folder(path: str):
    """Lazily expand any folder node. Returns its depth-1 children."""
    target = (LIBRARY_DIR / path).resolve()
    _guard(target)
    if not target.exists() or not target.is_dir():
        raise HTTPException(404, f"Folder not found: {path}")
    return _walk_depth1(target)


@router.get("/pokemon")
def list_pokemon(folder: str, offset: int = 0, limit: int = PAGE_SIZE, q: str = ""):
    parent = (LIBRARY_DIR / folder).resolve()
    _guard(parent)
    if not parent.exists() or not parent.is_dir():
        raise HTTPException(404, f"Folder not found: {folder}")
    candidates = _get_pokemon_candidates(parent, q)
    total = len(candidates)
    page  = candidates[offset: offset + limit]
    if not page:
        return {"items": [], "total": total, "offset": offset, "limit": limit, "has_more": False}
    with ThreadPoolExecutor(max_workers=min(len(page), 8)) as pool:
        items = list(pool.map(_read_pokemon_node, page))
    return {"items": items, "total": total, "offset": offset, "limit": limit, "has_more": offset + limit < total}


@router.get("/pokemon-node")
def get_pokemon_node(path: str):
    """Full data for a single pokemon (called when PokemonCard is opened)."""
    target = (LIBRARY_DIR / path).resolve()
    _guard(target)
    if not target.exists() or not target.is_dir():
        raise HTTPException(404, f"Pokemon not found: {path}")
    return _read_pokemon_node(target)


@router.get("/sprite")
def get_sprite(path: str):
    """Serve PNG sprites or .pal palette files from the library."""
    target = (LIBRARY_DIR / path).resolve()
    _guard(target)
    if not target.exists():
        raise HTTPException(404, "File not found")
    ext = target.suffix.lower()
    if ext == ".png":
        return FileResponse(target, media_type="image/png")
    elif ext == ".pal":
        return FileResponse(
            target,
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="{target.name}"'},
        )
    raise HTTPException(400, f"Unsupported file type: {ext}")


class ImportBody(BaseModel):
    path: str
    target_folder: str | None = None


@router.post("/import")
def import_palette(body: ImportBody):
    target = (LIBRARY_DIR / body.path).resolve()
    _guard(target)
    if not target.exists():
        raise HTTPException(404, f"Library palette not found: {body.path}")
    dest_dir = Path("palettes") / "user"
    if body.target_folder:
        dest_dir = dest_dir / body.target_folder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / target.name
    counter = 1
    while dest.exists():
        dest = dest_dir / f"{target.stem}_{counter}.pal"
        counter += 1
    dest.write_bytes(target.read_bytes())
    state.palette_manager.reload()
    return {"imported": dest.name, "folder": body.target_folder}


class ImportFolderBody(BaseModel):
    folder_path: str
    target_folder: str | None = None


@router.post("/import-folder")
def import_folder(body: ImportFolderBody):
    folder = (LIBRARY_DIR / body.folder_path).resolve()
    _guard(folder)
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(404, f"Library folder not found: {body.folder_path}")
    dest_dir = Path("palettes") / "user"
    if body.target_folder:
        dest_dir = dest_dir / body.target_folder
    else:
        dest_dir = dest_dir / folder.name
    dest_dir.mkdir(parents=True, exist_ok=True)
    imported = []
    for pal_file in sorted(folder.rglob("*.pal")):
        dest = dest_dir / pal_file.name
        counter = 1
        while dest.exists():
            dest = dest_dir / f"{pal_file.stem}_{counter}.pal"
            counter += 1
        dest.write_bytes(pal_file.read_bytes())
        imported.append(dest.name)
    state.palette_manager.reload()
    return {"imported": imported, "count": len(imported)}