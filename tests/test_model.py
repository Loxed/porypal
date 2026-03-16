"""
tests/test_model.py

Tests for the Qt-free model layer.
Run with: pytest tests/
"""

import pytest
from pathlib import Path
from model.palette import Color, Palette
from model.image_manager import ImageManager
from model.palette_extractor import PaletteExtractor


# ---------- Color ----------

class TestColor:
    def test_round_trip_hex(self):
        c = Color(255, 128, 0)
        assert Color.from_hex(c.to_hex()) == c

    def test_distance_sq_self(self):
        c = Color(100, 100, 100)
        assert c.distance_sq(c) == 0

    def test_distance_sq_known(self):
        a = Color(0, 0, 0)
        b = Color(1, 0, 0)
        assert a.distance_sq(b) == 1

    def test_invalid_channel(self):
        with pytest.raises(ValueError):
            Color(256, 0, 0)


# ---------- Palette ----------

class TestPalette:
    def test_max_colors(self):
        colors = [Color(i, i, i) for i in range(17)]
        with pytest.raises(ValueError):
            Palette("too_many", colors)

    def test_transparent_color(self):
        colors = [Color(255, 0, 255), Color(0, 0, 0)]
        p = Palette("test", colors)
        assert p.transparent_color == Color(255, 0, 255)

    def test_opaque_colors(self):
        colors = [Color(255, 0, 255), Color(1, 2, 3), Color(4, 5, 6)]
        p = Palette("test", colors)
        assert p.opaque_colors == [Color(1, 2, 3), Color(4, 5, 6)]

    def test_jasc_round_trip(self, tmp_path):
        colors = [Color(255, 0, 255)] + [Color(i * 10, i * 5, i * 2) for i in range(1, 10)]
        p = Palette("round_trip", colors)
        pal_path = tmp_path / "test.pal"
        p.to_jasc_pal(pal_path)
        loaded = Palette.from_jasc_pal(pal_path)
        assert loaded.colors == p.colors

    def test_is_gba_compatible(self):
        p16 = Palette("ok", [Color(i, 0, 0) for i in range(16)])
        assert p16.is_gba_compatible()


# ---------- ImageManager ----------

class TestImageManager:
    @pytest.fixture
    def simple_palette(self):
        return Palette("test", [
            Color(255, 0, 255),   # transparent (magenta)
            Color(255, 255, 255), # white
            Color(0, 0, 0),       # black
            Color(255, 0, 0),     # red
        ])

    @pytest.fixture
    def simple_png(self, tmp_path):
        """Create a tiny 4x4 RGBA PNG with known colors."""
        from PIL import Image
        img = Image.new("RGBA", (4, 4), (255, 255, 255, 255))
        # Make top-left pixel transparent
        img.putpixel((0, 0), (255, 0, 255, 0))
        img.putpixel((1, 1), (0, 0, 0, 255))
        path = tmp_path / "test.png"
        img.save(path)
        return path

    def test_load_image(self, simple_png):
        mgr = ImageManager({})
        img = mgr.load_image(simple_png)
        assert img.width == 4
        assert img.height == 4

    def test_unsupported_format(self, tmp_path):
        fake = tmp_path / "file.xyz"
        fake.write_bytes(b"")
        mgr = ImageManager({})
        with pytest.raises(ValueError, match="Unsupported format"):
            mgr.load_image(fake)

    def test_process_all_palettes(self, simple_png, simple_palette):
        mgr = ImageManager({})
        mgr.load_image(simple_png)
        results = mgr.process_all_palettes([simple_palette])
        assert len(results) == 1
        r = results[0]
        assert r.palette is simple_palette
        assert r.colors_used >= 1

    def test_save_and_reload(self, simple_png, simple_palette, tmp_path):
        mgr = ImageManager({})
        mgr.load_image(simple_png)
        results = mgr.process_all_palettes([simple_palette])
        out = tmp_path / "out.png"
        assert mgr.save_image(results[0], out)
        assert out.exists()

    def test_get_best_indices(self, simple_png, simple_palette):
        mgr = ImageManager({})
        mgr.load_image(simple_png)
        mgr.process_all_palettes([simple_palette])
        best = mgr.get_best_indices()
        assert isinstance(best, list)
        assert 0 in best


# ---------- PaletteExtractor ----------

class TestPaletteExtractor:
    @pytest.fixture
    def gradient_png(self, tmp_path):
        """Create a gradient PNG with more than 16 colors."""
        from PIL import Image
        import numpy as np
        arr = np.zeros((16, 16, 4), dtype=np.uint8)
        for i in range(16):
            arr[i, :, 0] = i * 16   # R gradient
            arr[i, :, 1] = 128
            arr[i, :, 2] = 255
            arr[i, :, 3] = 255
        arr[0, 0, 3] = 0            # one transparent pixel
        img = Image.fromarray(arr, "RGBA")
        path = tmp_path / "gradient.png"
        img.save(path)
        return path

    def test_extract_count(self, gradient_png):
        ext = PaletteExtractor()
        p = ext.extract(gradient_png, n_colors=16)
        assert 1 <= len(p.colors) <= 16

    def test_extract_gba_compatible(self, gradient_png):
        ext = PaletteExtractor()
        p = ext.extract(gradient_png, n_colors=16)
        assert p.is_gba_compatible()

    def test_extract_invalid_n_colors(self, gradient_png):
        ext = PaletteExtractor()
        with pytest.raises(ValueError):
            ext.extract(gradient_png, n_colors=17)

    def test_extract_saves_pal(self, gradient_png, tmp_path):
        ext = PaletteExtractor()
        p = ext.extract(gradient_png)
        out = tmp_path / "out.pal"
        p.to_jasc_pal(out)
        assert out.exists()
        loaded = Palette.from_jasc_pal(out)
        assert loaded.colors == p.colors
