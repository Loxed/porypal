"""
server/helpers.py

Shared utility functions used across routers.
"""

from __future__ import annotations
import base64
import io

from PIL import Image


def pil_to_b64(img: Image.Image) -> str:
    """Convert a PIL image to a base64-encoded PNG string."""
    buf = io.BytesIO()
    img.convert("RGBA").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()