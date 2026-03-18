"""
model/palette_manager.py

Loads and manages .pal palette files. Pure Python, no Qt.

Folder layout (searched in order, duplicates skipped):
  palettes/defaults/*.pal   — shipped palettes, cannot be deleted
  palettes/user/*.pal       — user-uploaded or extracted palettes
  palettes/*.pal            — legacy flat files (still supported)
"""

from __future__ import annotations
import logging
from pathlib import Path

from model.palette import Palette


class PaletteManager:
    """Loads and manages palettes from a directory of JASC-PAL files."""

    def __init__(self):
        self._palettes: list[Palette] = []
        self._meta: dict[str, dict] = {}  # name → {path, is_default, source}
        self._load_palettes()

    def _load_palettes(self) -> None:
        palette_dir = Path("palettes")
        if not palette_dir.exists():
            logging.warning("palettes/ directory not found — creating it")
            palette_dir.mkdir(parents=True, exist_ok=True)

        # Gather candidates in priority order: defaults → user → legacy root
        candidates: list[tuple[Path, bool, str]] = []

        defaults_dir = palette_dir / "defaults"
        if defaults_dir.exists():
            for f in sorted(defaults_dir.glob("*.pal")):
                candidates.append((f, True, "default"))

        user_dir = palette_dir / "user"
        if user_dir.exists():
            for f in sorted(user_dir.glob("*.pal")):
                candidates.append((f, False, "user"))

        for f in sorted(palette_dir.glob("*.pal")):
            candidates.append((f, False, "legacy"))

        self._palettes = []
        self._meta = {}
        seen: set[str] = set()

        for path, is_default, source in candidates:
            if path.name in seen:
                continue  # first occurrence wins (default > user > legacy)
            seen.add(path.name)
            try:
                p = Palette.from_jasc_pal(path)
                self._palettes.append(p)
                self._meta[p.name] = {
                    "path": path,
                    "is_default": is_default,
                    "source": source,
                }
                logging.debug(f"Loaded palette [{source}]: {path.name}")
            except Exception as e:
                logging.error(f"Failed to load palette {path}: {e}")

        logging.info(f"Loaded {len(self._palettes)} palettes")

    # ---------- public getters ----------

    def get_palettes(self) -> list[Palette]:
        return self._palettes

    def get_palette_by_index(self, index: int) -> Palette:
        return self._palettes[index]

    def get_palette_by_name(self, name: str) -> Palette | None:
        return next((p for p in self._palettes if p.name == name), None)

    def get_meta(self, name: str) -> dict | None:
        """Return {path, is_default, source} for a palette by name."""
        return self._meta.get(name)

    def is_default(self, name: str) -> bool:
        meta = self._meta.get(name)
        return meta["is_default"] if meta else False

    def get_path(self, name: str) -> Path | None:
        meta = self._meta.get(name)
        return meta["path"] if meta else None

    def reload(self) -> None:
        """Reload palettes from disk."""
        self._load_palettes()