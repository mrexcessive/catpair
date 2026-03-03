"""
prepare_tiles.py
================
Reads cat tile JPEGs from assets/tiles/, applies a bevelled stone-frame style
with rounded corners and transparent background, and outputs styled PNGs for
the web game.

Each tile gets:
  1. Rounded-corner photo inset (112×112 visible area, 8px corner radius)
  2. Bevelled sandstone frame (3D carved-stone look)
  3. Transparent outer corners
  4. A 64×64 mobile-sized downscale

Output
------
    html/assets/playtiles/cat_XXX.png      128×128
    html/assets/playtiles/64/cat_XXX.png    64×64
    html/assets/playtiles/tilelist.json     JSON array of filenames

Usage
-----
    python3 prepare_tiles.py [--input-dir PATH] [--output-dir PATH]
                              [--dry-run]
"""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

# Tile dimensions
TILE_SIZE = 128
MOBILE_SIZE = 64
BORDER = 8
RADIUS = 8

# Bevel colours (sandstone palette)
COLOR_BASE = (194, 164, 128)
COLOR_HIGHLIGHT = (220, 195, 160)
COLOR_SHADOW = (145, 120, 90)
COLOR_LIP = (100, 80, 55)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def rounded_rect_mask(size, radius):
    """Return an L-mode image usable as an alpha mask with rounded corners."""
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), (size[0] - 1, size[1] - 1)],
                           radius=radius, fill=255)
    return mask


def make_bevel_frame(size, border, radius):
    """
    Build a 128×128 RGBA bevelled stone frame.

    Layers (back to front):
      - Shadow fill (bottom/right feel)
      - Highlight fill (top/left feel)
      - Base fill (main stone colour)
      - Inner lip (dark carved recess)
    All rounded-rect shapes, offset to create a 3D bevel illusion.
    """
    frame = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)

    # Outer rounded rect — shadow colour (appears at bottom-right edges)
    draw.rounded_rectangle(
        [(0, 0), (size - 1, size - 1)],
        radius=radius, fill=COLOR_SHADOW + (255,),
    )

    # Highlight layer — shifted 2px up-left so it peeks at top-left edges
    draw.rounded_rectangle(
        [(0, 0), (size - 3, size - 3)],
        radius=radius, fill=COLOR_HIGHLIGHT + (255,),
    )

    # Base stone fill — inset 2px, covers most of the frame
    draw.rounded_rectangle(
        [(2, 2), (size - 3, size - 3)],
        radius=max(1, radius - 1), fill=COLOR_BASE + (255,),
    )

    # Inner lip — dark carved edge where photo sits
    inner = border - 1
    draw.rounded_rectangle(
        [(inner, inner), (size - inner - 1, size - inner - 1)],
        radius=max(1, radius - 2), fill=COLOR_LIP + (255,),
    )

    # Clear the photo area (transparent hole for the photo)
    photo_area = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pa_draw = ImageDraw.Draw(photo_area)
    pa_draw.rounded_rectangle(
        [(border, border), (size - border - 1, size - border - 1)],
        radius=max(1, radius - 2), fill=(255, 255, 255, 255),
    )
    # Use the photo area as an eraser on the frame
    # Where photo_area is white, set frame alpha to 0
    frame_pixels = frame.load()
    pa_pixels = photo_area.load()
    for y in range(size):
        for x in range(size):
            if pa_pixels[x, y][3] > 0:
                frame_pixels[x, y] = (0, 0, 0, 0)

    return frame


def process_tile(src_path, out_128, out_64):
    """Apply bevel frame to a single tile, save 128px and 64px versions."""
    tile_size = TILE_SIZE
    border = BORDER
    radius = RADIUS

    # Load and ensure exactly 128×128 RGB
    with Image.open(src_path) as img:
        img = img.convert("RGB")
        if img.size != (tile_size, tile_size):
            img = img.resize((tile_size, tile_size), Image.LANCZOS)

        # Create rounded-corner photo inset
        photo = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))
        photo.paste(img, (0, 0))

        # Mask photo to inner rounded rect
        photo_mask = Image.new("L", (tile_size, tile_size), 0)
        pm_draw = ImageDraw.Draw(photo_mask)
        pm_draw.rounded_rectangle(
            [(border, border),
             (tile_size - border - 1, tile_size - border - 1)],
            radius=max(1, radius - 2), fill=255,
        )
        photo.putalpha(photo_mask)

        # Build the bevel frame
        frame = make_bevel_frame(tile_size, border, radius)

        # Composite: photo behind frame
        result = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))
        result = Image.alpha_composite(result, photo)
        result = Image.alpha_composite(result, frame)

        # Apply outer rounded-rect alpha mask (transparent corners)
        outer_mask = rounded_rect_mask((tile_size, tile_size), radius)
        result.putalpha(outer_mask)

        # Save 128×128
        out_128.parent.mkdir(parents=True, exist_ok=True)
        result.save(out_128, format="PNG")

        # Save 64×64
        small = result.resize((MOBILE_SIZE, MOBILE_SIZE), Image.LANCZOS)
        out_64.parent.mkdir(parents=True, exist_ok=True)
        small.save(out_64, format="PNG")


def run(input_dir: Path, output_dir: Path, dry_run: bool) -> None:
    if not input_dir.is_dir():
        print(f"ERROR: input directory not found: {input_dir}", file=sys.stderr)
        sys.exit(1)

    tiles = sorted(
        [p for p in input_dir.iterdir()
         if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS],
        key=lambda p: p.name.lower(),
    )

    if not tiles:
        print("No tile images found. Nothing to do.")
        return

    print(f"Found {len(tiles)} tile(s) in {input_dir}")

    if dry_run:
        for t in tiles:
            stem = t.stem
            print(f"  [DRY-RUN] {t.name} -> {stem}.png + 64/{stem}.png")
        print(f"  [DRY-RUN] Would write tilelist.json with {len(tiles)} entries")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    mobile_dir = output_dir / "64"
    mobile_dir.mkdir(parents=True, exist_ok=True)

    filenames = []

    for i, tile_path in enumerate(tiles, 1):
        stem = tile_path.stem
        out_name = f"{stem}.png"
        out_128 = output_dir / out_name
        out_64 = mobile_dir / out_name

        process_tile(tile_path, out_128, out_64)
        filenames.append(out_name)

        if i % 20 == 0 or i == len(tiles):
            print(f"  Processed {i}/{len(tiles)}")

    # Write tilelist.json
    tilelist_path = output_dir / "tilelist.json"
    with tilelist_path.open("w", encoding="utf-8") as fh:
        json.dump(filenames, fh, indent=2)
        fh.write("\n")

    print()
    print("Done!")
    print(f"  128px tiles : {output_dir}  ({len(filenames)} files)")
    print(f"  64px tiles  : {mobile_dir}  ({len(filenames)} files)")
    print(f"  Tile list   : {tilelist_path}")


def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).parent
    p = argparse.ArgumentParser(
        description="Apply bevelled stone frame to cat tiles for the web game."
    )
    p.add_argument("--input-dir", type=Path,
                   default=root / "assets" / "tiles",
                   help="Directory of source 128×128 tile JPEGs")
    p.add_argument("--output-dir", type=Path,
                   default=root / "html" / "assets" / "playtiles",
                   help="Directory for styled PNG output")
    p.add_argument("--dry-run", action="store_true",
                   help="Print what would happen without writing files")
    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    run(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )
