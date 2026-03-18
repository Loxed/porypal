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
GET    /api/pipeline/download/{job_id} → zip stream
DELETE /api/pipeline/{job_id}          → cleanup
"""

from __future__ import annotations

import io
import json
import logging
import os
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
from server.presets import load_preset
from server.state import state

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

# In-memory job store (single-user local tool)
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Helpers
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
) -> tuple[Image.Image, Any]:
    """Extract palette. Returns (unchanged image, Palette | None)."""
    bg_mode  = step.get("bg_mode", "auto")
    bg_color = step.get("bg_color", "#73C5A4")
    if bg_mode == "auto":
        bg_color = _auto_detect_bg(img)
    elif bg_mode == "default":
        bg_color = "#73C5A4"
    # else: use provided bg_color

    n_colors    = int(step.get("n_colors", 15))
    color_space = step.get("color_space", "oklab")

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        img.save(tmp.name, format="PNG")
        tmp_path = tmp.name

    try:
        extractor = PaletteExtractor()
        palette   = extractor.extract(
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
        filename = f"{stem}_{color_space}.pal"
        dest = pal_dir / filename
        counter = 1
        while dest.exists():
            dest = pal_dir / f"{stem}_{color_space}_{counter}.pal"
            counter += 1
        # Write JASC-PAL
        lines = ["JASC-PAL", "0100", str(len(palette.colors))]
        lines += [f"{c.r} {c.g} {c.b}" for c in palette.colors]
        dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        # Also reload manager so the palette is immediately available
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

    # Slice source into tiles
    src = img.convert("RGBA")
    src_cols = max(1, src.width  // tile_w)
    src_rows = max(1, src.height // tile_h)
    tiles: list[Image.Image] = []
    for r in range(src_rows):
        for c in range(src_cols):
            tile = src.crop((c * tile_w, r * tile_h, (c+1) * tile_w, (r+1) * tile_h))
            tiles.append(tile)

    # Arrange into output
    out = Image.new("RGBA", (cols * tile_w, rows * tile_h), (0, 0, 0, 0))
    for slot_pos, tile_idx in enumerate(slots):
        if tile_idx is None or tile_idx >= len(tiles):
            continue
        out_col = slot_pos % cols
        out_row = slot_pos // cols
        out.paste(tiles[tile_idx], (out_col * tile_w, out_row * tile_h))

    return out


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

    # Save PIL image to temp so ImageManager can load it
    img_mgr = ImageManager()  # fixed: was ImageManager({})
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        img.save(tmp.name, format="PNG")
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
        # Either way, pick first alphabetically
        best.sort(key=lambda r: r.palette.name)

    return best[0].image.convert("RGBA"), notes


# ---------------------------------------------------------------------------
# Background job executor
# ---------------------------------------------------------------------------

def _execute_job(job_id: str, file_data: list[tuple[str, bytes]], steps: list[dict]) -> None:
    work_dir = Path(tempfile.mkdtemp(prefix=f"porypal_{job_id}_"))
    out_dir  = work_dir / "processed"
    pal_dir  = work_dir / "palettes"
    out_dir.mkdir()
    pal_dir.mkdir()

    with _jobs_lock:
        _jobs[job_id].update({"work_dir": str(work_dir), "total": len(file_data)})

    for i, (filename, raw_bytes) in enumerate(file_data):
        with _jobs_lock:
            _jobs[job_id]["current_file"] = filename

        result: dict[str, str] = {"file": filename, "status": "ok", "notes": ""}

        try:
            img   = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
            stem  = Path(filename).stem
            ext   = Path(filename).suffix or ".png"
            extracted_palette = None

            for step in steps:
                stype = step.get("type")
                if stype == "extract":
                    img, extracted_palette = _run_extract_step(img, stem, step, pal_dir)
                elif stype == "tileset":
                    img = _run_tileset_step(img, step)
                elif stype == "convert":
                    img, notes = _run_convert_step(img, step, extracted_palette)
                    if notes:
                        result["notes"] = notes
                        result["status"] = "conflict" if "conflict" in notes else "ok"

            out_path = out_dir / f"{stem}_processed{ext}"
            img.save(str(out_path), format="PNG")

        except Exception as e:
            result["status"] = "error"
            result["notes"]  = str(e)
            logging.error(f"Pipeline [{job_id}] error on {filename}: {e}")

        with _jobs_lock:
            _jobs[job_id]["results"].append(result)
            _jobs[job_id]["done"] = i + 1

    # Build zip
    zip_path = work_dir / "results.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(out_dir.glob("*")):
            zf.write(f, f"processed/{f.name}")
        for f in sorted(pal_dir.glob("*.pal")):
            zf.write(f, f"palettes/{f.name}")
        summary = json.dumps(_jobs[job_id]["results"], indent=2)
        zf.writestr("summary.json", summary)

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
    steps: str = Form(...),   # JSON-encoded list of step dicts
):
    """Start a pipeline job. Returns job_id immediately."""
    try:
        parsed_steps = json.loads(steps)
    except json.JSONDecodeError:
        raise HTTPException(400, "steps must be valid JSON")

    if not parsed_steps:
        raise HTTPException(400, "steps cannot be empty")

    # Read all file bytes eagerly (UploadFile is consumed in async context)
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

    background_tasks.add_task(_execute_job, job_id, file_data, parsed_steps)
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