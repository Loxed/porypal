from PIL import Image

from model.palette import Color, Palette
from server.api import pipeline


def _sample_sprite(bg=(0x11, 0x22, 0x33), fg=(0xAA, 0xAA, 0xAA)):
    img = Image.new("RGBA", (3, 3), (*bg, 255))
    img.putpixel((1, 1), (*fg, 255))
    return img


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
