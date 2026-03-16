"""
model/palette.py

Pure-Python palette types — no Qt dependency.
The view layer is responsible for converting Color → QColor / any other UI color type.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import logging


@dataclass(frozen=True)
class Color:
    """Immutable RGB color. No Qt, no GUI dependency."""
    r: int
    g: int
    b: int

    def __post_init__(self):
        for ch, v in (("r", self.r), ("g", self.g), ("b", self.b)):
            if not 0 <= v <= 255:
                raise ValueError(f"Color channel {ch}={v} out of range [0, 255]")

    def to_tuple(self) -> tuple[int, int, int]:
        return (self.r, self.g, self.b)

    def to_hex(self) -> str:
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}"

    def distance_sq(self, other: "Color") -> int:
        """Squared Euclidean distance in RGB space. No sqrt needed for comparisons."""
        return (self.r - other.r) ** 2 + (self.g - other.g) ** 2 + (self.b - other.b) ** 2

    @classmethod
    def from_hex(cls, hex_str: str) -> "Color":
        hex_str = hex_str.lstrip("#")
        return cls(int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))


@dataclass
class Palette:
    """
    A named list of up to 16 Colors.
    Index 0 is always the transparent/background color by GBA convention.
    """
    name: str
    colors: list[Color] = field(default_factory=list)

    MAX_COLORS = 16

    def __post_init__(self):
        if len(self.colors) > self.MAX_COLORS:
            raise ValueError(
                f"Palette '{self.name}' has {len(self.colors)} colors — GBA max is {self.MAX_COLORS}"
            )

    @property
    def transparent_color(self) -> Color | None:
        return self.colors[0] if self.colors else None

    @property
    def opaque_colors(self) -> list[Color]:
        """All colors except index 0 (transparent)."""
        return self.colors[1:]

    def is_gba_compatible(self) -> bool:
        return len(self.colors) <= self.MAX_COLORS

    # ---------- Serialisation ----------

    @classmethod
    def from_jasc_pal(cls, path: Path) -> "Palette":
        """
        Load from a JASC-PAL file.
        Format:
            JASC-PAL
            0100
            16
            R G B
            ...
        """
        lines = path.read_text(encoding="utf-8").splitlines()
        # Skip the 3-line JASC header
        color_lines = [l.strip() for l in lines[3:] if l.strip()]
        colors = []
        for line in color_lines:
            parts = line.split()
            if len(parts) >= 3:
                try:
                    colors.append(Color(int(parts[0]), int(parts[1]), int(parts[2])))
                except ValueError as e:
                    logging.warning(f"Skipping malformed color line '{line}' in {path.name}: {e}")
        return cls(name=path.name, colors=colors)

    def to_jasc_pal(self, path: Path) -> None:
        """Write palette back to JASC-PAL format."""
        lines = ["JASC-PAL", "0100", str(len(self.colors))]
        lines += [f"{c.r} {c.g} {c.b}" for c in self.colors]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def to_hex_list(self) -> list[str]:
        return [c.to_hex() for c in self.colors]
