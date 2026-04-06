"""
server/api/library.py
"""

from __future__ import annotations
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from model.palette import Palette
from server.state import state

router = APIRouter(prefix="/api/palette-library", tags=["library"])

LIBRARY_DIR:   Path = Path("palette_library").resolve()
PROJECTS_FILE: Path = Path("projects.json").resolve()

POKEMON_PAL_NAMES       = {"normal.pal", "shiny.pal", "overworld_normal.pal", "overworld_shiny.pal"}
POKEMON_SPRITE_PRIORITY = ["icon.png", "front.png", "anim_front.png", "back.png", "overworld.png", "overworldf.png"]
POKEMON_FOLDER_EXCLUDES = {"icon_palettes"}

PAGE_SIZE = 20

_pal_cache:        dict[str, tuple[float, list[str]]] = {}
_candidates_cache: dict[str, tuple[float, list[Path]]] = {}
_tree_cache:       dict = {"sig": "", "tree": []}


# ---------------------------------------------------------------------------
# Projects registry
# ---------------------------------------------------------------------------

def _load_projects() -> list[dict]:
    if not PROJECTS_FILE.exists():
        return []
    try:
        return json.loads(PROJECTS_FILE.read_text())
    except Exception:
        return []


def _save_projects(projects: list[dict]) -> None:
    PROJECTS_FILE.write_text(json.dumps(projects, indent=2))


# ---------------------------------------------------------------------------
# Path normalisation
# ---------------------------------------------------------------------------

def _is_wsl() -> bool:
    p = Path("/proc/version")
    return p.exists() and "microsoft" in p.read_text().lower()


def _normalise_path(raw: str) -> str:
    """
    Convert any path format to something Python can open on the current OS.
      Windows:  C:\\Users\\lox\\pokeemerald  →  /mnt/c/Users/lox/pokeemerald  (WSL)
                                            →  C:\\Users\\lox\\pokeemerald     (native Windows)
      UNC:      \\\\wsl$\\Ubuntu\\home\\...  →  /home/...  (via wslpath)
      Linux:    /home/lox/pokeemerald        →  unchanged
      Tilde:    ~/pokeemerald                →  expanded
    """
    raw = raw.strip()
    if not raw:
        return raw

    # Tilde
    if raw.startswith("~"):
        return str(Path(raw).expanduser())

    # Windows drive letter  C:\ or C:/
    if re.match(r"^[A-Za-z]:[/\\]", raw):
        if _is_wsl():
            drive = raw[0].lower()
            rest  = raw[2:].replace("\\", "/").lstrip("/")
            return f"/mnt/{drive}/{rest}"
        return raw.replace("/", "\\")

    # UNC  \\wsl$\Ubuntu\...
    if raw.startswith("\\\\") or raw.startswith("//"):
        if _is_wsl():
            try:
                r = subprocess.run(
                    ["wslpath", "-u", raw.replace("\\", "/")],
                    capture_output=True, text=True, timeout=5,
                )
                if r.returncode == 0 and r.stdout.strip():
                    return r.stdout.strip()
            except Exception:
                pass
        return raw

    return raw


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wildcard_match(pattern: str, text: str) -> bool:
    p = pattern.lower()
    t = text.lower()
    if "*" not in p and "?" not in p:
        return p in t
    regex = re.escape(p).replace(r"\*", ".*").replace(r"\?", ".")
    return bool(re.fullmatch(regex, t))


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


POKEMON_FOLDER_NAMES  = {"pokemon"}
TRAINERS_FOLDER_NAMES = {"trainers"}
ITEMS_FOLDER_NAMES    = {"items"}

def _classify_subdir(sub: Path) -> str:
    name = sub.name.lower()
    if name in ITEMS_FOLDER_NAMES:
        return "items"
    if name in POKEMON_FOLDER_NAMES:
        return "pokemon_parent"
    if name in TRAINERS_FOLDER_NAMES:
        return "trainers"
    return "folder"


def _rel_to(base: Path, path: Path) -> str:
    return str(path.relative_to(base))


def _guard_path(base: Path, target: Path) -> None:
    base_str   = str(base.resolve())
    target_str = str(target.resolve())
    if not (target_str == base_str or target_str.startswith(base_str + os.sep) or target_str.startswith(base_str + "/")):
        raise HTTPException(400, "Invalid path")


def _resolve_base(path_str: str) -> tuple[Path, Path]:
    """
    Returns (abs_folder_root, resolved_abs_path) for a given virtual path string.

    For project folders the virtual path is "{fid}/{rel_within_folder}",
    e.g. "pokeemerald/items/icons/foo.png" where fid="pokeemerald/items".
    abs_folder_root is the abs_path of the matched folder — used as base for
    _guard_path and _rel_to (which will produce "{fid}/{rel}" when combined
    with the fid prefix in _proj_rel_to).

    For library paths it falls back to LIBRARY_DIR as before.
    """
    for proj in _load_projects():
        for folder in proj.get("folders", []):
            abs_path = Path(folder["abs_path"])
            fid = folder["id"]
            if path_str == fid or path_str.startswith(fid + "/") or path_str.startswith(fid + os.sep):
                rel = path_str[len(fid):].lstrip("/\\")
                resolved = (abs_path / rel).resolve()
                # Use abs_path as base so _guard_path works,
                # and callers know the fid prefix to reconstruct virtual paths.
                return abs_path.resolve(), resolved

    resolved = (LIBRARY_DIR / path_str).resolve()
    return LIBRARY_DIR, resolved


def _proj_path(fid: str, abs_folder: Path, file_abs: Path) -> str:
    """Build the virtual path for a file inside a project folder."""
    try:
        rel = str(file_abs.relative_to(abs_folder)).replace("\\", "/")
    except ValueError:
        rel = file_abs.name
    return f"{fid}/{rel}" if rel else fid

def _fid_for_path(path_str: str) -> str | None:
    """Return the folder ID if path_str belongs to a loaded project, else None."""
    for proj in _load_projects():
        for folder in proj.get("folders", []):
            fid = folder["id"]
            if path_str == fid or path_str.startswith(fid + "/") or path_str.startswith(fid + os.sep):
                return fid
    return None




def _walk_depth1(base: Path, directory: Path, fid: str | None = None) -> list[dict]:
    files, subdirs = _scan_dir(directory)
    nodes: list[dict] = []

    def _p(p: Path) -> str:
        rel = _rel_to(base, p)
        return f"{fid}/{rel}" if fid else rel

    for f in files:
        ext = f.suffix.lower()
        if ext == ".pal":
            colors = _read_colors(f)
            if colors is not None:
                nodes.append({"type": "palette", "name": f.name, "path": _p(f), "colors": colors})
        elif ext == ".png":
            nodes.append({"type": "sprite", "name": f.name, "path": _p(f)})
    for sub in subdirs:
        kind = _classify_subdir(sub)
        rel  = _p(sub)
        if kind == "items":
            nodes.append({"type": "items_folder",    "name": sub.name, "path": rel})
        elif kind in ("pokemon", "pokemon_parent"):
            nodes.append({"type": "pokemon_folder",  "name": sub.name, "path": rel})
        elif kind == "trainers":
            nodes.append({"type": "trainers_folder", "name": sub.name, "path": rel})
        else:
            nodes.append({"type": "folder",          "name": sub.name, "path": rel})
    return nodes


def _read_pokemon_node(base: Path, directory: Path, fid: str | None = None) -> dict:
    """
    base:      filesystem base for _rel_to  (abs_folder for projects, LIBRARY_DIR for local)
    fid:       folder ID prefix for project paths, or None for library paths
    """
    files, subdirs = _scan_dir(directory)
    palettes, sprites, subforms = [], [], {}

    def _path(p: Path) -> str:
        rel = _rel_to(base, p)
        return f"{fid}/{rel}" if fid else rel

    for f in files:
        ext = f.suffix.lower()
        if ext == ".pal":
            colors = _read_colors(f)
            if colors is not None:
                palettes.append({"name": f.name, "path": _path(f), "colors": colors})
        elif ext == ".png":
            sprites.append({"name": f.name, "path": _path(f)})
    for sub in subdirs:
        subforms[sub.name] = _read_pokemon_node(base, sub, fid)
    priority_map = {n: i for i, n in enumerate(POKEMON_SPRITE_PRIORITY)}
    sprites.sort(key=lambda s: priority_map.get(s["name"].lower(), len(POKEMON_SPRITE_PRIORITY)))
    return {
        "type": "pokemon", "name": directory.name, "path": _path(directory),
        "palettes": palettes, "sprites": sprites, "subforms": subforms,
    }


def _get_pokemon_candidates(base: Path, parent: Path, q: str = "") -> list[Path]:
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
        candidates = [d for d in subdirs if d.name.lower() not in POKEMON_FOLDER_EXCLUDES]
        _candidates_cache[key] = (mtime, candidates)
    if q:
        return [d for d in candidates if _wildcard_match(q, d.name)]
    return candidates


def _get_item_candidates(parent: Path, q: str = "") -> list[Path]:
    icons_dir = parent / "icons"
    if not icons_dir.exists():
        return []
    sprites = sorted(icons_dir.glob("*.png"), key=lambda p: p.name.lower())
    if q:
        sprites = [s for s in sprites if _wildcard_match(q, s.stem)]
    return sprites


def _cache_sig() -> str:
    """Include library dir mtime + projects.json mtime + project list."""
    sigs = []
    try:
        sigs.append(str(os.path.getmtime(LIBRARY_DIR)))
    except OSError:
        sigs.append("0")
    try:
        sigs.append(str(os.path.getmtime(PROJECTS_FILE)))
    except OSError:
        sigs.append("0")
    projects = _load_projects()
    sigs.append(str(len(projects)))
    return "|".join(sigs)


def _build_tree() -> list[dict]:
    nodes = []
    if LIBRARY_DIR.exists():
        nodes.extend(_walk_depth1(LIBRARY_DIR, LIBRARY_DIR))
    for proj in _load_projects():
        for folder in proj.get("folders", []):
            abs_path = Path(folder["abs_path"])
            if not abs_path.exists():
                continue
            kind = _classify_subdir(abs_path)
            fid  = folder["id"]
            node: dict = {"name": folder["name"], "path": fid, "project": proj["name"]}
            if kind == "items":
                node["type"] = "items_folder"
            elif kind in ("pokemon", "pokemon_parent"):
                node["type"] = "pokemon_folder"
            elif kind == "trainers":
                node["type"] = "trainers_folder"
            else:
                node["type"] = "folder"
            nodes.append(node)
    return nodes


# ---------------------------------------------------------------------------
# Routes: library tree
# ---------------------------------------------------------------------------

@router.get("")
def list_library():
    sig = _cache_sig()
    if _tree_cache["sig"] == sig:
        return _tree_cache["tree"]
    tree = _build_tree()
    _tree_cache["sig"]  = sig
    _tree_cache["tree"] = tree
    return tree


@router.get("/folder")
def list_folder(path: str):
    base, target = _resolve_base(path)
    _guard_path(base, target)
    if not target.exists() or not target.is_dir():
        raise HTTPException(404, f"Folder not found: {path}")
    fid = _fid_for_path(path)
    return _walk_depth1(base, target, fid)


@router.get("/pokemon")
def list_pokemon(folder: str, offset: int = 0, limit: int = PAGE_SIZE, q: str = ""):
    base, parent = _resolve_base(folder)
    _guard_path(base, parent)
    if not parent.exists() or not parent.is_dir():
        raise HTTPException(404, f"Folder not found: {folder}")
    # Determine fid: if folder is a project path, use it as the fid prefix root
    fid = _fid_for_path(folder)
    candidates = _get_pokemon_candidates(base, parent, q)
    total = len(candidates)
    page  = candidates[offset: offset + limit]
    if not page:
        return {"items": [], "total": total, "offset": offset, "limit": limit, "has_more": False}
    with ThreadPoolExecutor(max_workers=min(len(page), 8)) as pool:
        items = list(pool.map(lambda d: _read_pokemon_node(base, d, fid), page))
    return {"items": items, "total": total, "offset": offset, "limit": limit, "has_more": offset + limit < total}


@router.get("/pokemon-node")
def get_pokemon_node(path: str):
    base, target = _resolve_base(path)
    _guard_path(base, target)
    if not target.exists() or not target.is_dir():
        raise HTTPException(404, f"Pokemon not found: {path}")
    fid = _fid_for_path(path)
    return _read_pokemon_node(base, target, fid)


@router.get("/items")
def list_items(folder: str, offset: int = 0, limit: int = PAGE_SIZE, q: str = ""):
    base, parent = _resolve_base(folder)
    _guard_path(base, parent)
    if not parent.exists() or not parent.is_dir():
        raise HTTPException(404, f"Folder not found: {folder}")
    fid          = _fid_for_path(folder)
    palettes_dir = parent / "icon_palettes"
    sprites      = _get_item_candidates(parent, q)
    total        = len(sprites)
    page         = sprites[offset: offset + limit]

    def _path(p: Path) -> str:
        rel = _rel_to(base, p)
        return f"{fid}/{rel}" if fid else rel

    items = []
    for sprite_path in page:
        pal_path = palettes_dir / (sprite_path.stem + ".pal")
        colors   = _read_colors(pal_path) if pal_path.exists() else None
        items.append({
            "name":                  sprite_path.stem,
            "sprite_path":           _path(sprite_path),
            "palette_path":          _path(pal_path) if pal_path.exists() else None,
            "colors":                colors,
            "expected_palette_path": _path(pal_path),
        })
    return {"items": items, "total": total, "offset": offset, "limit": limit, "has_more": offset + limit < total}


# ---------------------------------------------------------------------------
# Routes: sprite / palette file serving
# ---------------------------------------------------------------------------

@router.get("/sprite")
def get_sprite(path: str):
    base, target = _resolve_base(path)
    _guard_path(base, target)
    if not target.exists():
        raise HTTPException(404, "File not found")
    ext = target.suffix.lower()
    if ext == ".png":
        return FileResponse(target, media_type="image/png")
    elif ext == ".pal":
        return FileResponse(target, media_type="text/plain",
                            headers={"Content-Disposition": f'attachment; filename="{target.name}"'})
    raise HTTPException(400, f"Unsupported file type: {ext}")


# ---------------------------------------------------------------------------
# Routes: generate palette for item without one
# ---------------------------------------------------------------------------

class GeneratePaletteBody(BaseModel):
    sprite_path:           str
    expected_palette_path: str
    n_colors: int = 15
    bg_color: str = "#73C5A4"


@router.post("/items/generate-palette")
def generate_item_palette(body: GeneratePaletteBody):
    import shutil as _shutil
    base, sprite_path = _resolve_base(body.sprite_path)
    _guard_path(base, sprite_path)
    if not sprite_path.exists():
        raise HTTPException(404, f"Sprite not found: {body.sprite_path}")

    base2, dest_path = _resolve_base(body.expected_palette_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        _shutil.copy2(sprite_path, tmp.name)
        tmp_path = tmp.name

    try:
        palette, _method = state.extractor.extract(
            tmp_path,
            n_colors=body.n_colors,
            bg_color=body.bg_color,
            color_space="oklab",
            name=sprite_path.stem,
        )
    finally:
        os.unlink(tmp_path)

    lines = ["JASC-PAL", "0100", str(len(palette.colors))]
    lines += [f"{c.r} {c.g} {c.b}" for c in palette.colors]
    dest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _pal_cache.pop(str(dest_path), None)

    return {
        "palette_path": body.expected_palette_path,
        "colors":       [c.to_hex() for c in palette.colors],
    }


# ---------------------------------------------------------------------------
# Routes: import palette into palettes/user/
# ---------------------------------------------------------------------------

class ImportBody(BaseModel):
    path: str
    target_folder: str | None = None


@router.post("/import")
def import_palette(body: ImportBody):
    base, target = _resolve_base(body.path)
    _guard_path(base, target)
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
    base, folder = _resolve_base(body.folder_path)
    _guard_path(base, folder)
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


# ---------------------------------------------------------------------------
# Routes: project management
# ---------------------------------------------------------------------------

class ScanProjectBody(BaseModel):
    path: str


class LoadProjectBody(BaseModel):
    name: str
    root: str
    folders: list[dict]


def _pick_folder_native() -> str:
    """
    Open a native OS folder picker dialog.
    Returns the chosen path (normalised for the current OS) or raises RuntimeError.

    WSL note: FolderBrowserDialog via PowerShell -NonInteractive times out because
    there is no STA message loop. We use a VBScript written to a temp file and
    executed via cmd.exe instead — this works reliably from WSL.
    """
    wsl = _is_wsl()

    # ── Windows / WSL ──────────────────────────────────────────────────────
    if wsl or sys.platform == "win32":
        # Write a tiny VBScript to a Windows temp path and run it via cmd.exe.
        # VBScript's Shell.BrowseForFolder creates its own message pump so it
        # works even when called from a non-interactive WSL process.
        vbs = (
            'Set objShell = CreateObject("Shell.Application")\n'
            'Set objFolder = objShell.BrowseForFolder(0, '
            '"Select your project or graphics folder", 0, 17)\n'
            'If Not objFolder Is Nothing Then\n'
            '    WScript.Echo objFolder.Self.Path\n'
            'End If\n'
        )

        # Write the script to a Windows-accessible temp location.
        # From WSL we use /mnt/c/Windows/Temp; on native Windows just %TEMP%.
        if wsl:
            vbs_path_linux  = "/mnt/c/Windows/Temp/porypal_pick.vbs"
            vbs_path_win    = r"C:\Windows\Temp\porypal_pick.vbs"
            cmd_exe         = "cmd.exe"
        else:
            import tempfile as _tf
            vbs_path_linux  = str(Path(_tf.gettempdir()) / "porypal_pick.vbs")
            vbs_path_win    = vbs_path_linux
            cmd_exe         = "cmd"

        try:
            Path(vbs_path_linux).write_text(vbs, encoding="utf-8")
        except Exception as e:
            raise RuntimeError(f"Could not write VBScript: {e}")

        try:
            r = subprocess.run(
                [cmd_exe, "/c", f'cscript //NoLogo "{vbs_path_win}"'],
                capture_output=True, text=True, timeout=120,
            )
        finally:
            try:
                Path(vbs_path_linux).unlink(missing_ok=True)
            except Exception:
                pass

        raw = r.stdout.strip()
        if not raw:
            raise RuntimeError("Dialog cancelled or failed")

        if wsl:
            # Convert Windows path → WSL path
            conv = subprocess.run(["wslpath", "-u", raw], capture_output=True, text=True, timeout=5)
            if conv.returncode == 0 and conv.stdout.strip():
                return conv.stdout.strip()
            # Manual fallback: C:\foo\bar → /mnt/c/foo/bar
            raw = raw.replace("\\", "/")
            if len(raw) >= 2 and raw[1] == ":":
                raw = f"/mnt/{raw[0].lower()}{raw[2:]}"

        return raw

    # ── macOS ──────────────────────────────────────────────────────────────
    if sys.platform == "darwin":
        r = subprocess.run(
            ["osascript", "-e",
             'tell app "Finder" to set f to choose folder '
             'with prompt "Select your project or graphics folder"\n'
             'return POSIX path of f'],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip().rstrip("/")
        raise RuntimeError(r.stderr.strip() or "Dialog cancelled")

    # ── Linux ──────────────────────────────────────────────────────────────
    for cmd, name in [
        (["zenity", "--file-selection", "--directory",
          "--title=Select project or graphics folder"], "zenity"),
        (["kdialog", "--getexistingdirectory", str(Path.home()),
          "--title", "Select project or graphics folder"], "kdialog"),
    ]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except FileNotFoundError:
            continue

    # tkinter last resort
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update()
    p = filedialog.askdirectory(title="Select project or graphics folder", parent=root)
    root.destroy()
    if p:
        return p
    raise RuntimeError("No folder selected")


@router.get("/projects/pick-folder")
def pick_folder():
    """
    Open a native OS folder-picker dialog.
    Runs the blocking dialog call in a thread so FastAPI stays responsive.
    Auto-descends into /graphics if the user picked the project root.
    """
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_pick_folder_native)
        try:
            chosen = future.result(timeout=90)
        except concurrent.futures.TimeoutError:
            raise HTTPException(408, "Dialog timed out")
        except RuntimeError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            raise HTTPException(400, str(e))

    # Normalise (handles Windows paths on WSL, etc.)
    chosen = _normalise_path(chosen)

    p = Path(chosen).expanduser().resolve()
    if not p.exists() or not p.is_dir():
        raise HTTPException(404, f"Path not found: {chosen}")

    # Auto-descend into /graphics
    graphics = p / "graphics"
    if graphics.is_dir():
        p = graphics

    logging.info(f"pick_folder: {p}")
    return {"abs_path": str(p)}


@router.post("/projects/scan")
def scan_project(body: ScanProjectBody):
    # Normalise path first (handles Windows paths typed manually)
    normalised = _normalise_path(body.path)
    root = Path(normalised).expanduser().resolve()

    if not root.exists() or not root.is_dir():
        raise HTTPException(404, f"Path not found: {body.path!r}")

    # Auto-descend into /graphics
    graphics = root / "graphics"
    if graphics.is_dir():
        root = graphics

    _, subdirs = _scan_dir(root)
    folders = []
    for sub in subdirs:
        kind = _classify_subdir(sub)
        smart_type = None
        if kind in ("pokemon", "pokemon_parent"):
            smart_type = "pokemon"
        elif kind == "items":
            smart_type = "items"
        elif kind == "trainers":
            smart_type = "trainers"
        folders.append({
            "name":       sub.name,
            "abs_path":   str(sub),
            "smart_type": smart_type,
        })
    return {"root": str(root), "folders": folders}


@router.post("/projects/load")
def load_project(body: LoadProjectBody):
    projects = _load_projects()
    projects = [p for p in projects if p["name"] != body.name]
    entry = {
        "name":    body.name,
        "root":    body.root,
        "folders": [
            {
                "id":         f"{body.name}/{f['name']}",
                "name":       f["name"],
                "abs_path":   f["abs_path"],
                "smart_type": f.get("smart_type"),
            }
            for f in body.folders
        ],
    }
    projects.append(entry)
    _save_projects(projects)
    _tree_cache["sig"] = ""   # bust cache immediately
    return entry


@router.get("/projects")
def list_projects():
    return _load_projects()


@router.delete("/projects/{name}")
def delete_project(name: str):
    projects = [p for p in _load_projects() if p["name"] != name]
    _save_projects(projects)
    _tree_cache["sig"] = ""
    return {"deleted": name}
