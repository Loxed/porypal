"""
server/api/pipeline.py

Batch pipeline runner.

Step types
----------
extract  — k-means palette extraction; optionally saves .pal to palettes/user/
tileset  — rearranges tiles according to a saved preset
convert  — remaps pixels to nearest palette colors

Job lifecycle
-------------
POST   /api/pipeline/run               → { job_id }
GET    /api/pipeline/status/{job_id}   → { status, done, total, current_file, results }
POST   /api/pipeline/preview           → { previews }
GET    /api/pipeline/download/{job_id} → zip stream
DELETE /api/pipeline/{job_id}          → cleanup

Filename templating
-------------------
Pass `filename_template` and `palette_template` form fields to /run.
Supported tokens:
  <name>    — original file stem (e.g. "bulbasaur")
  <palette> — palette name stem (convert steps, not used by default)
  <cs>      — color space ("oklab" or "rgb", extract steps only)

Defaults:
  filename_template = "<name>"       → bulbasaur.png   (no suffix)
  palette_template  = "<name>_<cs>" → bulbasaur_oklab.pal
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import shutil
import tempfile
import threading
import zipfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from PIL import Image

from model.image_manager import ImageManager
from model.palette_extractor import PaletteExtractor
from model.tileset_manager import TilesetManager
from server.helpers import pil_to_b64, save_png
from server.preset_store import load_preset
from server.state import state

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()

PORYPAL_VERSION = "3.1.2"

DEFAULT_FILENAME_TEMPLATE = "<name>"
DEFAULT_PALETTE_TEMPLATE  = "<name>_<cs>"

DEFAULT_FILENAME_TEMPLATE = "<name>"
DEFAULT_PALETTE_TEMPLATE  = "<name>_<cs>"


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------

def _sanitise(s: str) -> str:
    """Strip characters that are unsafe in filenames."""
    return re.sub(r'[<>:"/\\|?*]', "_", s).strip(" .")


def _apply_template(template: str, name: str = "", palette: str = "", cs: str = "") -> str:
    result = template
    result = result.replace("<name>",    _sanitise(name))
    result = result.replace("<palette>", _sanitise(palette))
    result = result.replace("<cs>",      _sanitise(cs))
    return result or name   # never return empty string


# ---------------------------------------------------------------------------
# Step helpers
# ---------------------------------------------------------------------------

def _auto_detect_bg(img: Image.Image) -> str:
    """Sample 4 corners, return majority opaque color as hex."""
    rgba = img.convert("RGBA")
    w, h = rgba.size
    samples = [
        rgba.getpixel((0,   0)),
        rgba.getpixel((w-1, 0)),
        rgba.getpixel((0,   h-1)),
        rgba.getpixel((w-1, h-1)),
    ]
    opaque = [(r, g, b) for r, g, b, a in samples if a >= 128]
    if not opaque:
        return "#73C5A4"
    counts: dict[str, int] = {}
    for r, g, b in opaque:
        k = f"#{r:02x}{g:02x}{b:02x}"
        counts[k] = counts.get(k, 0) + 1
    return max(counts, key=counts.get)


def _run_extract_step(
    img: Image.Image,
    stem: str,
    step: dict,
    pal_dir: Path,
    palette_template: str = DEFAULT_PALETTE_TEMPLATE,
) -> tuple[Image.Image, Any]:
    """Extract palette. Returns (unchanged image, Palette)."""
    bg_mode  = step.get("bg_mode", "auto")
    bg_color = step.get("bg_color", "#73C5A4")
    if bg_mode == "auto":
        bg_color = _auto_detect_bg(img)
    elif bg_mode == "default":
        bg_color = "#73C5A4"

    n_colors    = int(step.get("n_colors", 15))
    color_space = step.get("color_space", "oklab")

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(save_png(img))
        tmp_path = tmp.name

    try:
        extractor = PaletteExtractor()
        palette, _method = extractor.extract(
            tmp_path,
            n_colors=n_colors,
            bg_color=bg_color,
            color_space=color_space,
            name=stem,
        )
    finally:
        os.unlink(tmp_path)

    if step.get("save_palette", True):
        pal_dir.mkdir(parents=True, exist_ok=True)
        base_name = _apply_template(palette_template, name=stem, cs=color_space)
        filename  = f"{base_name}.pal"
        dest      = pal_dir / filename
        counter   = 1
        while dest.exists():
            dest = pal_dir / f"{base_name}_{counter}.pal"
            counter += 1
        lines = ["JASC-PAL", "0100", str(len(palette.colors))]
        lines += [f"{c.r} {c.g} {c.b}" for c in palette.colors]
        dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        state.palette_manager.reload()

    return img, palette


def _run_tileset_step(img: Image.Image, step: dict) -> Image.Image:
    """Rearrange tiles according to a preset. Returns new image."""
    preset_id = step.get("preset_id")
    if not preset_id:
        raise ValueError("Tileset step has no preset_id")

    preset = load_preset(preset_id)
    if not preset:
        raise ValueError(f"Preset '{preset_id}' not found")

    tile_w = preset["tile_w"]
    tile_h = preset["tile_h"]
    cols   = preset["cols"]
    rows   = preset["rows"]
    slots  = preset.get("slots", [])

    out_tile_w = preset.get("out_tile_w") or preset.get("resize_tile_w") or tile_w
    out_tile_h = preset.get("out_tile_h") or preset.get("resize_tile_h") or tile_h

    config = {
        "tileset": {
            "input_sprite_size": {"width": tile_w, "height": tile_h},
            "output_sprite_size": {"width": out_tile_w, "height": out_tile_h},
            "sprite_order": slots,
            "resize_tileset": False,
            "resize_to": 128,
            "supported_sizes": [],
        },
        "output": {
            "output_width": cols * out_tile_w,
            "output_height": rows * out_tile_h,
        },
    }

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(save_png(img))
        tmp_path = tmp.name

    try:
        mgr = TilesetManager(config)
        if not mgr.load(tmp_path):
            raise ValueError("Failed to process tileset")
        processed = mgr.get_processed()
        if processed is None:
            raise ValueError("Tileset step produced no image")
        return processed
    finally:
        os.unlink(tmp_path)


def _run_convert_step(
    img: Image.Image,
    step: dict,
    extracted_palette: Any,
) -> tuple[Image.Image, str]:
    """Remap pixels to nearest palette. Returns (image, notes_str)."""
    palette_source = step.get("palette_source", "loaded")

    if palette_source == "extracted":
        if extracted_palette is None:
            raise ValueError("Convert step uses extracted palette but no Extract step ran before it")
        palettes = [extracted_palette]
    else:
        names    = step.get("selected_palettes", [])
        palettes = [state.palette_manager.get_palette_by_name(n) for n in names]
        palettes = [p for p in palettes if p is not None]
        if not palettes:
            raise ValueError("Convert step has no valid palettes selected")

    img_mgr = ImageManager()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(save_png(img))
        tmp_path = tmp.name
    try:
        img_mgr.load_image(tmp_path)
        results = img_mgr.process_all_palettes(palettes)
    finally:
        os.unlink(tmp_path)

    if not results:
        raise ValueError("Conversion produced no results")

    max_colors = max(r.colors_used for r in results)
    best       = [r for r in results if r.colors_used == max_colors]
    notes      = ""
    conflict_mode = step.get("conflict_mode", "auto_first")

    if len(best) > 1:
        tied = sorted(r.palette.name for r in best)
        if conflict_mode == "flag":
            notes = f"conflict: {len(best)} palettes tied ({', '.join(tied)})"
        best.sort(key=lambda r: r.palette.name)

    return best[0].image, notes


# ---------------------------------------------------------------------------
# Preview endpoint
# ---------------------------------------------------------------------------

@router.post("/preview")
async def preview_pipeline(
    file: UploadFile = File(...),
    steps: str = Form(...),
):
    """Dry-run on a single file. Returns per-step preview images."""
    try:
        parsed_steps = json.loads(steps)
    except Exception:
        raise HTTPException(400, "steps must be valid JSON")

    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data)).copy()
    except Exception as e:
        raise HTTPException(400, f"Cannot open image: {e}")

    stem = Path(file.filename).stem

    previews = [{
        "type":    "original",
        "label":   "original",
        "image":   pil_to_b64(img),
        "palette": None,
        "error":   None,
    }]

    extracted_palette = None
    tmp_pal_dir = Path(tempfile.mkdtemp(prefix="porypal_preview_"))

    try:
        for step in parsed_steps:
            stype = step.get("type", "unknown")
            try:
                if stype == "extract":
                    dry_step = {**step, "save_palette": False}
                    img, extracted_palette = _run_extract_step(img, stem, dry_step, tmp_pal_dir)
                    space = step.get("color_space", "oklab")
                    previews.append({
                        "type":    "extract",
                        "label":   f"extract ({space})",
                        "image":   pil_to_b64(img),
                        "palette": [c.to_hex() for c in extracted_palette.colors] if extracted_palette else [],
                        "error":   None,
                    })

                elif stype == "tileset":
                    preset_id   = step.get("preset_id", "")
                    preset      = load_preset(preset_id) if preset_id else None
                    preset_name = preset["name"] if preset else preset_id
                    img = _run_tileset_step(img, step)
                    previews.append({
                        "type":    "tileset",
                        "label":   f"tileset → {preset_name}",
                        "image":   pil_to_b64(img),
                        "palette": None,
                        "error":   None,
                    })

                elif stype == "convert":
                    img, notes = _run_convert_step(img, step, extracted_palette)
                    if step.get("palette_source") == "extracted":
                        label = "convert (extracted pal)"
                    elif step.get("selected_palettes"):
                        first = step["selected_palettes"][0].replace(".pal", "")
                        rest  = len(step["selected_palettes"]) - 1
                        label = f"convert → {first}" + (f" +{rest}" if rest else "")
                    else:
                        label = "convert"
                    previews.append({
                        "type":    "convert",
                        "label":   label,
                        "image":   pil_to_b64(img),
                        "palette": None,
                        "error":   notes or None,
                    })

                else:
                    previews.append({
                        "type":    stype,
                        "label":   stype,
                        "image":   None,
                        "palette": None,
                        "error":   f"Unknown step type: {stype}",
                    })

            except Exception as e:
                previews.append({
                    "type":    stype,
                    "label":   stype,
                    "image":   None,
                    "palette": None,
                    "error":   str(e),
                })

    finally:
        shutil.rmtree(tmp_pal_dir, ignore_errors=True)

    return {"previews": previews, "filename": file.filename}


# ---------------------------------------------------------------------------
# Background job executor
# ---------------------------------------------------------------------------

def _execute_job(
    job_id: str,
    file_data: list[tuple[str, bytes]],
    steps: list[dict],
    filename_template: str = DEFAULT_FILENAME_TEMPLATE,
    palette_template:  str = DEFAULT_PALETTE_TEMPLATE,
) -> None:
    work_dir    = Path(tempfile.mkdtemp(prefix=f"porypal_{job_id}_"))
    sprites_dir = work_dir / "sprites"
    pal_dir     = work_dir / "palettes"
    sprites_dir.mkdir()
    pal_dir.mkdir()

    with _jobs_lock:
        _jobs[job_id].update({"work_dir": str(work_dir), "total": len(file_data)})

    for i, (filename, raw_bytes) in enumerate(file_data):
        with _jobs_lock:
            _jobs[job_id]["current_file"] = filename

        result: dict[str, str] = {"file": filename, "status": "ok", "notes": ""}

        try:
            img   = Image.open(io.BytesIO(raw_bytes)).copy()
            stem  = Path(filename).stem
            ext   = Path(filename).suffix or ".png"
            extracted_palette = None

            for step in steps:
                stype = step.get("type")
                if stype == "extract":
                    img, extracted_palette = _run_extract_step(
                        img, stem, step, pal_dir, palette_template
                    )
                elif stype == "tileset":
                    img = _run_tileset_step(img, step)
                elif stype == "convert":
                    img, notes = _run_convert_step(img, step, extracted_palette)
                    if notes:
                        result["notes"] = notes
                        result["status"] = "conflict" if "conflict" in notes else "ok"

            # Apply filename template for the output sprite
            out_stem = _apply_template(filename_template, name=stem)
            out_path = sprites_dir / f"{out_stem}{ext}"
            counter  = 1
            while out_path.exists():
                out_path = sprites_dir / f"{out_stem}_{counter}{ext}"
                counter += 1
            out_bytes = save_png(img)
            out_path.write_bytes(out_bytes)

        except Exception as e:
            result["status"] = "error"
            result["notes"]  = str(e)
            logging.error(f"Pipeline [{job_id}] error on {filename}: {e}")

        with _jobs_lock:
            _jobs[job_id]["results"].append(result)
            _jobs[job_id]["done"] = i + 1

    # Copy loaded palettes used by convert steps into pal_dir
    already_in_pal_dir = {f.name for f in pal_dir.glob("*.pal")}
    for step in steps:
        if step.get("type") == "convert" and step.get("palette_source") == "loaded":
            for pal_name in step.get("selected_palettes", []):
                if pal_name in already_in_pal_dir:
                    continue
                src_path = state.palette_manager.get_path(pal_name)
                if src_path and src_path.exists():
                    dest = pal_dir / pal_name
                    dest.write_bytes(src_path.read_bytes())
                    already_in_pal_dir.add(pal_name)

    results_snapshot = _jobs[job_id]["results"]

    zip_path = work_dir / "results.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(sprites_dir.glob("*")):
            zf.write(f, f"sprites/{f.name}")
        for f in sorted(pal_dir.glob("*.pal")):
            zf.write(f, f"palettes/{f.name}")
        manifest = {
            "porypal_version":   PORYPAL_VERSION,
            "filename_template": filename_template,
            "palette_template":  palette_template,
            "steps": steps,
            "summary": {
                "total":    len(results_snapshot),
                "ok":       sum(1 for r in results_snapshot if r["status"] == "ok"),
                "conflict": sum(1 for r in results_snapshot if r["status"] == "conflict"),
                "error":    sum(1 for r in results_snapshot if r["status"] == "error"),
            },
            "files": results_snapshot,
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

    with _jobs_lock:
        _jobs[job_id]["status"]   = "done"
        _jobs[job_id]["zip_path"] = str(zip_path)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/run")
async def run_pipeline(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    steps: str = Form(...),
    filename_template: str = Form(default=DEFAULT_FILENAME_TEMPLATE),
    palette_template:  str = Form(default=DEFAULT_PALETTE_TEMPLATE),
):
    """Start a pipeline job. Returns job_id immediately."""
    try:
        parsed_steps = json.loads(steps)
    except json.JSONDecodeError:
        raise HTTPException(400, "steps must be valid JSON")

    if not parsed_steps:
        raise HTTPException(400, "steps cannot be empty")

    file_data: list[tuple[str, bytes]] = []
    for f in files:
        raw = await f.read()
        file_data.append((f.filename, raw))

    if not file_data:
        raise HTTPException(400, "No files provided")

    job_id = str(uuid4())
    with _jobs_lock:
        _jobs[job_id] = {
            "status":       "running",
            "total":        len(file_data),
            "done":         0,
            "current_file": "",
            "results":      [],
            "zip_path":     None,
            "work_dir":     None,
        }

    background_tasks.add_task(
        _execute_job, job_id, file_data, parsed_steps,
        filename_template, palette_template,
    )
    return {"job_id": job_id}


@router.get("/status/{job_id}")
def get_status(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, f"Job '{job_id}' not found")
    return {
        "status":       job["status"],
        "total":        job["total"],
        "done":         job["done"],
        "current_file": job["current_file"],
        "results":      job["results"],
    }


@router.get("/download/{job_id}")
def download_results(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, f"Job '{job_id}' not found")
    if job["status"] != "done":
        raise HTTPException(400, "Job is not done yet")
    zip_path = Path(job["zip_path"])
    if not zip_path.exists():
        raise HTTPException(500, "Result zip not found")

    def iter_zip():
        with open(zip_path, "rb") as f:
            while chunk := f.read(65536):
                yield chunk

    return StreamingResponse(
        iter_zip(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="pipeline_results.zip"'},
    )


@router.delete("/{job_id}")
def cleanup_job(job_id: str):
    with _jobs_lock:
        job = _jobs.pop(job_id, None)
    if not job:
        raise HTTPException(404, f"Job '{job_id}' not found")
    work_dir = job.get("work_dir")
    if work_dir and Path(work_dir).exists():
        shutil.rmtree(work_dir, ignore_errors=True)
    return {"deleted": job_id}
