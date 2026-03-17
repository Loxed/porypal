"""
server/api/library.py

Routes: /api/palette-library

Serves the read-only palette library from palette_library/.
Expected layout (two levels deep):

  palette_library/
    <game>/
      <category>/
        foo.pal
      bar.pal          ← goes into implicit "misc" category
    <game2>/
      ...

Import copies a palette into palettes/user/ and reloads.
"""

from __future__ import annotations
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from model.palette import Palette
from server.state import state

router = APIRouter(prefix="/api/palette-library", tags=["library"])

LIBRARY_DIR = Path("palette_library")


def _read_colors(path: Path) -> list[str] | None:
    try:
        return [c.to_hex() for c in Palette.from_jasc_pal(path).colors]
    except Exception as e:
        logging.warning(f"Could not read library palette {path}: {e}")
        return None


@router.get("")
def list_library():
    """
    Return the full library tree.
    Shape: [ { game, categories: [ { category, palettes: [ { name, colors } ] } ] } ]
    """
    if not LIBRARY_DIR.exists():
        return []

    tree = []

    for game_dir in sorted(LIBRARY_DIR.iterdir()):
        if not game_dir.is_dir():
            continue

        categories: dict[str, list] = {}

        for item in sorted(game_dir.iterdir()):
            if item.is_file() and item.suffix.lower() == ".pal":
                # No sub-category — put in "misc"
                colors = _read_colors(item)
                if colors is not None:
                    categories.setdefault("misc", []).append({
                        "name": item.name,
                        "path": f"{game_dir.name}/{item.name}",
                        "colors": colors,
                    })
            elif item.is_dir():
                cat_name = item.name
                for pal in sorted(item.glob("*.pal")):
                    colors = _read_colors(pal)
                    if colors is not None:
                        categories.setdefault(cat_name, []).append({
                            "name": pal.name,
                            "path": f"{game_dir.name}/{cat_name}/{pal.name}",
                            "colors": colors,
                        })

        if categories:
            tree.append({
                "game": game_dir.name,
                "categories": [
                    {"category": cat, "palettes": pals}
                    for cat, pals in categories.items()
                ],
            })

    return tree


class ImportBody(BaseModel):
    path: str   # relative path as returned by the tree, e.g. "firered/trainers/brendan.pal"


@router.post("/import")
def import_palette(body: ImportBody):
    """Copy a library palette into palettes/user/ and reload."""
    # Validate path stays inside the library dir (no traversal)
    target = (LIBRARY_DIR / body.path).resolve()
    if not str(target).startswith(str(LIBRARY_DIR.resolve())):
        raise HTTPException(400, "Invalid path")

    if not target.exists():
        raise HTTPException(404, f"Library palette not found: {body.path}")

    dest_dir = Path("palettes") / "user"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / target.name

    # Avoid clobbering
    counter = 1
    while dest.exists():
        stem = target.stem
        dest = dest_dir / f"{stem}_{counter}.pal"
        counter += 1

    dest.write_bytes(target.read_bytes())
    state.palette_manager.reload()
    return {"imported": dest.name}