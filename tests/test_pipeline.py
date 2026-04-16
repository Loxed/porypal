import asyncio
import io
import json
import shutil
import zipfile
from pathlib import Path

from PIL import Image

from model.image_manager import detect_background_color
from model.palette import Color, Palette
from server.api import pipeline


def _sample_sprite(bg=(0x11, 0x22, 0x33), fg=(0xAA, 0xAA, 0xAA)):
    img = Image.new("RGBA", (3, 3), (*bg, 255))
    img.putpixel((1, 1), (*fg, 255))
    return img


def _png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class _FakeUploadFile:
    def __init__(self, filename, data):
        self.filename = filename
        self._data = data

    async def read(self):
        return self._data


def test_detect_background_color_prefers_alpha_pixel():
    img = Image.new("RGBA", (3, 3), (0x11, 0x22, 0x33, 255))
    img.putpixel((1, 1), (0xFF, 0x00, 0xFF, 0))

    detected = detect_background_color(img)

    assert detected == Color(0xFF, 0x00, 0xFF)


def test_detect_background_color_falls_back_to_edge_majority():
    img = Image.new("RGBA", (3, 3), (0x11, 0x22, 0x33, 255))
    img.putpixel((1, 1), (0xAA, 0xAA, 0xAA, 255))

    detected = detect_background_color(img)

    assert detected == Color(0x11, 0x22, 0x33)


def test_run_background_step_set_fills_transparent_and_matching_bg():
    img = Image.new("RGBA", (3, 3), (0xFF, 0x00, 0xFF, 255))
    img.putpixel((0, 0), (0xFF, 0x00, 0xFF, 0))
    img.putpixel((1, 1), (0xAA, 0xAA, 0xAA, 255))

    out = pipeline._run_background_step(
        img,
        {"action": "set", "target_mode": "custom", "target_color": "#112233"},
    )

    assert out.mode == "RGBA"
    assert out.getpixel((0, 0)) == (0x11, 0x22, 0x33, 255)
    assert out.getpixel((2, 2)) == (0x11, 0x22, 0x33, 255)
    assert out.getpixel((1, 1)) == (0xAA, 0xAA, 0xAA, 255)


def test_run_background_step_remove_makes_detected_bg_transparent():
    img = _sample_sprite(bg=(0x11, 0x22, 0x33), fg=(0xAA, 0xAA, 0xAA))

    out = pipeline._run_background_step(img, {"action": "remove"})

    assert out.mode == "RGBA"
    assert out.getpixel((0, 0))[3] == 0
    assert out.getpixel((1, 1)) == (0xAA, 0xAA, 0xAA, 255)


def test_run_convert_step_returns_visible_bg_and_palette_name(monkeypatch):
    palette = Palette("winner.pal", [
        Color(0x11, 0x22, 0x33),
        Color(0xAA, 0xAA, 0xAA),
    ])

    monkeypatch.setattr(
        pipeline.state.palette_manager,
        "get_palette_by_name",
        lambda name: palette if name == "winner.pal" else None,
    )

    out, notes, applied_palette = pipeline._run_convert_step(
        _sample_sprite(),
        {
            "palette_source": "loaded",
            "selected_palettes": ["winner.pal"],
            "conflict_mode": "auto_first",
        },
        extracted_palette=None,
    )

    assert notes == ""
    assert applied_palette == "winner.pal"
    assert "transparency" not in out.info
    assert out.convert("RGBA").getpixel((0, 0)) == (0x11, 0x22, 0x33, 255)
    assert out.convert("RGBA").getpixel((1, 1)) == (0xAA, 0xAA, 0xAA, 255)


def test_run_convert_step_reports_actual_tie_break_winner(monkeypatch):
    alpha = Palette("alpha.pal", [
        Color(0x11, 0x22, 0x33),
        Color(0xAA, 0xAA, 0xAA),
    ])
    beta = Palette("beta.pal", [
        Color(0x11, 0x22, 0x33),
        Color(0xAA, 0xAA, 0xAA),
    ])

    monkeypatch.setattr(
        pipeline.state.palette_manager,
        "get_palette_by_name",
        lambda name: {"alpha.pal": alpha, "beta.pal": beta}.get(name),
    )

    _out, notes, applied_palette = pipeline._run_convert_step(
        _sample_sprite(),
        {
            "palette_source": "loaded",
            "selected_palettes": ["beta.pal", "alpha.pal"],
            "conflict_mode": "flag",
        },
        extracted_palette=None,
    )

    assert "conflict:" in notes
    assert applied_palette == "alpha.pal"


def test_background_step_can_run_before_convert(monkeypatch):
    palette = Palette("winner.pal", [
        Color(0x11, 0x22, 0x33),
        Color(0xAA, 0xAA, 0xAA),
    ])

    monkeypatch.setattr(
        pipeline.state.palette_manager,
        "get_palette_by_name",
        lambda name: palette if name == "winner.pal" else None,
    )

    background_set = pipeline._run_background_step(
        Image.new("RGBA", (3, 3), (0xFF, 0x00, 0xFF, 255)),
        {"action": "set", "target_mode": "custom", "target_color": "#112233"},
    )
    background_set.putpixel((1, 1), (0xAA, 0xAA, 0xAA, 255))

    converted, notes, applied_palette = pipeline._run_convert_step(
        background_set,
        {
            "palette_source": "loaded",
            "selected_palettes": ["winner.pal"],
            "conflict_mode": "auto_first",
        },
        extracted_palette=None,
    )

    assert notes == ""
    assert applied_palette == "winner.pal"
    assert converted.convert("RGBA").getpixel((0, 0)) == (0x11, 0x22, 0x33, 255)


def test_background_step_can_run_after_convert(monkeypatch):
    palette = Palette("winner.pal", [
        Color(0x11, 0x22, 0x33),
        Color(0xAA, 0xAA, 0xAA),
    ])

    monkeypatch.setattr(
        pipeline.state.palette_manager,
        "get_palette_by_name",
        lambda name: palette if name == "winner.pal" else None,
    )

    converted, _notes, _applied_palette = pipeline._run_convert_step(
        _sample_sprite(),
        {
            "palette_source": "loaded",
            "selected_palettes": ["winner.pal"],
            "conflict_mode": "auto_first",
        },
        extracted_palette=None,
    )

    removed = pipeline._run_background_step(converted, {"action": "remove"})

    assert removed.getpixel((0, 0))[3] == 0
    assert removed.getpixel((1, 1)) == (0xAA, 0xAA, 0xAA, 255)


def test_preview_pipeline_returns_background_preview():
    response = asyncio.run(pipeline.preview_pipeline(
        file=_FakeUploadFile("sprite.png", _png_bytes(_sample_sprite())),
        steps=json.dumps([{"type": "background", "action": "remove"}]),
    ))

    assert response["filename"] == "sprite.png"
    assert response["previews"][1]["type"] == "background"
    assert response["previews"][1]["label"] == "background → remove"
    assert response["previews"][1]["image"]


def test_execute_job_forces_png_output_when_background_step():
    job_id = "job-background-output"
    pipeline._jobs[job_id] = {
        "status": "running",
        "total": 1,
        "done": 0,
        "current_file": "",
        "results": [],
        "zip_path": None,
        "work_dir": None,
    }

    try:
        pipeline._execute_job(
            job_id,
            [("sprite.bmp", _png_bytes(_sample_sprite()))],
            [{"type": "background", "action": "remove"}],
        )

        job = pipeline._jobs[job_id]
        zip_path = Path(job["zip_path"])
        with zipfile.ZipFile(zip_path, "r") as zf:
            assert "sprites/sprite.png" in zf.namelist()
            manifest = json.loads(zf.read("manifest.json"))
            assert manifest["steps"][0]["type"] == "background"

            out = Image.open(io.BytesIO(zf.read("sprites/sprite.png"))).convert("RGBA")
            assert out.getpixel((0, 0))[3] == 0
    finally:
        work_dir = pipeline._jobs.get(job_id, {}).get("work_dir")
        if work_dir:
            shutil.rmtree(work_dir, ignore_errors=True)
        pipeline._jobs.pop(job_id, None)
