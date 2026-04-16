"""
server/helpers.py

Shared utility functions used across routers.
"""

from __future__ import annotations
import base64
import io

from PIL import Image
from model.palette import Palette


def pil_to_b64(img: Image.Image) -> str:
    """Convert a PIL image to a base64-encoded PNG string."""
    buf = io.BytesIO()
    img.convert("RGBA").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def copy_without_transparency(img: Image.Image) -> Image.Image:
    """
    Return a copy of *img* without PNG transparency metadata.

    This preserves palette indices and colors while making slot 0 render as a
    visible color instead of being hidden by a tRNS chunk.
    """
    clone = img.copy()
    clone.info = dict(getattr(img, "info", {}))
    clone.info.pop("transparency", None)
    return clone


def make_pal_content(palette: Palette) -> str:
    """Serialise a Palette to JASC-PAL format."""
    buf = io.StringIO()
    buf.write("JASC-PAL\n0100\n")
    buf.write(f"{len(palette.colors)}\n")
    for c in palette.colors:
        buf.write(f"{c.r} {c.g} {c.b}\n")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 4bpp / indexed PNG helpers
# ---------------------------------------------------------------------------

def is_4bpp(img: Image.Image) -> bool:
    """Return True if *img* is a paletted image with <=16 colors used (4bpp)."""
    if img.mode != "P":
        return False
    import numpy as np

    arr = np.array(img)
    return int(arr.max()) + 1 <= 16 if arr.size > 0 else False


def is_4bpp_bytes(raw: bytes) -> bool:
    """Return True if *raw* PNG bytes represent a 4bpp paletted image."""
    try:
        img = Image.open(io.BytesIO(raw))
        return is_4bpp(img)
    except Exception:
        return False


def save_png(img: Image.Image, preserve_4bpp: bool = False) -> bytes:
    """
    Serialize *img* to PNG bytes.

    If the image is already paletted (mode "P"), keep it paletted and preserve
    the embedded palette. 4bpp-compatible images are written as indexed 4bpp;
    larger paletted images are written as indexed PNGs.

    If *preserve_4bpp* is True for a non-paletted image, quantize to <=16
    colors and write a 4bpp indexed PNG. Otherwise save as plain RGBA.

    This is the single place in the codebase that decides how PNGs are written.
    """
    buf = io.BytesIO()
    save_kwargs = {"format": "PNG"}

    if img.mode == "P":
        if "transparency" in img.info:
            save_kwargs["transparency"] = img.info["transparency"]
        if is_4bpp(img):
            img.save(buf, bits=4, optimize=True, **save_kwargs)
        else:
            img.save(buf, optimize=True, **save_kwargs)
    elif preserve_4bpp:
        img.convert("RGBA").quantize(colors=16, dither=0).save(
            buf, format="PNG", bits=4, optimize=True
        )
    else:
        img.convert("RGBA").save(buf, **save_kwargs)

    return buf.getvalue()
