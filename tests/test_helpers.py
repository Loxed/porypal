import io

from PIL import Image

from server.helpers import copy_without_transparency, save_png


def _paletted_image_with_transparent_slot_zero():
    img = Image.new("P", (2, 1))
    palette = [
        0x11, 0x22, 0x33,
        0xAA, 0xBB, 0xCC,
    ]
    img.putpalette(palette + [0] * (768 - len(palette)))
    img.putdata([0, 1])
    img.info["transparency"] = 0
    return img


def test_copy_without_transparency_keeps_slot_zero_visible():
    img = _paletted_image_with_transparent_slot_zero()

    visible = copy_without_transparency(img)
    reloaded = Image.open(io.BytesIO(save_png(visible)))

    assert "transparency" not in visible.info
    assert "transparency" not in reloaded.info
    assert reloaded.convert("RGBA").getpixel((0, 0)) == (0x11, 0x22, 0x33, 255)
    assert reloaded.convert("RGBA").getpixel((1, 0)) == (0xAA, 0xBB, 0xCC, 255)
