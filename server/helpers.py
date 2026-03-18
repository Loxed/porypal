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


def make_pal_content(palette: Palette) -> str:
    """
    Serialise a Palette to JASC-PAL format.
    Accepts a Palette object — uses its colors as-is.
    state.extractor.extract() never produces duplicates or padding,
    so no trimming is needed here.
    """
    buf = io.StringIO()
    buf.write("JASC-PAL\n0100\n")
    buf.write(f"{len(palette.colors)}\n")
    for c in palette.colors:
        buf.write(f"{c.r} {c.g} {c.b}\n")
    return buf.getvalue()