"""
cli.py

Porypal v3 CLI — palette toolchain for Gen 3 ROM hacking.

Commands:
    porypal convert   Remap a sprite to the nearest colors in a .pal file
    porypal extract   Extract a GBA palette from any sprite
    porypal batch     Apply a palette to every image in a folder
    porypal info      Inspect a .pal file

Install: pip install porypal[gui]   (GUI)
         pip install porypal        (CLI only)
"""

from __future__ import annotations
import logging
import sys
from pathlib import Path

import click
import yaml

from model.palette import Palette
from model.palette_manager import PaletteManager
from model.image_manager import ImageManager
from model.palette_extractor import PaletteExtractor


# ---------- CLI root ----------

@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging.")
def main(debug: bool):
    """Porypal — palette toolchain for Gen 3 Pokémon ROM hacking."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        format="[%(levelname)s] %(message)s",
    )


# ---------- convert ----------

@main.command()
@click.argument("image", type=click.Path(exists=True, path_type=Path))
@click.argument("palette", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None,
              help="Output path. Default: <image_stem>_<palette_stem>.png next to source.")
def convert(image: Path, palette: Path, output: Path | None):
    """Remap IMAGE pixels to the nearest colors in PALETTE (.pal file)."""
    pal = Palette.from_jasc_pal(palette)
    mgr = ImageManager(config={})
    mgr.load_image(image)
    results = mgr.process_all_palettes([pal])
    result = results[0]

    out_path = output or mgr.auto_output_path(result)
    if mgr.save_image(result, out_path):
        click.echo(f"Saved: {out_path}  ({result.colors_used} colors used)")
    else:
        click.echo("Error: failed to save image.", err=True)
        sys.exit(1)


# ---------- extract ----------

@main.command()
@click.argument("image", type=click.Path(exists=True, path_type=Path))
@click.option("-n", "--n-colors", default=16, show_default=True,
              help="Total palette size (including transparent slot). Max 16 for GBA.")
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None,
              help="Output .pal path. Default: <image_stem>.pal next to source.")
@click.option("--hex", "show_hex", is_flag=True, help="Print hex values to stdout as well.")
def extract(image: Path, n_colors: int, output: Path | None, show_hex: bool):
    """Extract a GBA-compatible palette from IMAGE using k-means clustering."""
    extractor = PaletteExtractor()
    palette = extractor.extract(image, n_colors=n_colors)

    out_path = output or image.parent / f"{image.stem}.pal"
    palette.to_jasc_pal(out_path)
    click.echo(f"Extracted {len(palette.colors)}-color palette → {out_path}")

    if show_hex:
        for i, color in enumerate(palette.colors):
            label = " (transparent)" if i == 0 else ""
            click.echo(f"  [{i:2d}] {color.to_hex()}{label}")


# ---------- batch ----------

@main.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("palette", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=None,
              help="Output directory. Default: same as input folder.")
@click.option("--report", is_flag=True, help="Print a summary table of colors used per file.")
def batch(folder: Path, palette: Path, output_dir: Path | None, report: bool):
    """Apply PALETTE to every PNG/JPG image in FOLDER."""
    pal = Palette.from_jasc_pal(palette)
    mgr = ImageManager(config={})
    out_dir = output_dir or folder
    out_dir.mkdir(parents=True, exist_ok=True)

    image_files = sorted(
        p for p in folder.iterdir()
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}
    )

    if not image_files:
        click.echo(f"No images found in {folder}")
        return

    rows = []
    for img_path in image_files:
        try:
            mgr.load_image(img_path)
            results = mgr.process_all_palettes([pal])
            result = results[0]
            out_path = out_dir / f"{img_path.stem}_{Path(palette).stem}.png"
            mgr.save_image(result, out_path)
            rows.append((img_path.name, result.colors_used, str(out_path.name)))
            click.echo(f"  ✓ {img_path.name} → {out_path.name} ({result.colors_used} colors)")
        except Exception as e:
            click.echo(f"  ✗ {img_path.name}: {e}", err=True)

    if report:
        click.echo(f"\n{'File':<30} {'Colors':>6}")
        click.echo("-" * 38)
        for name, colors, _ in rows:
            click.echo(f"{name:<30} {colors:>6}")
        click.echo(f"\nProcessed {len(rows)}/{len(image_files)} files.")


# ---------- info ----------

@main.command()
@click.argument("palette", type=click.Path(exists=True, path_type=Path))
def info(palette: Path):
    """Print details of a JASC-PAL file."""
    pal = Palette.from_jasc_pal(palette)
    click.echo(f"Palette: {pal.name}")
    click.echo(f"Colors:  {len(pal.colors)} / {Palette.MAX_COLORS}")
    click.echo(f"GBA compatible: {'yes' if pal.is_gba_compatible() else 'NO — too many colors'}")
    click.echo("")
    for i, color in enumerate(pal.colors):
        label = " ← transparent slot" if i == 0 else ""
        click.echo(f"  [{i:2d}] {color.to_hex()}  rgb({color.r}, {color.g}, {color.b}){label}")


if __name__ == "__main__":
    main()
