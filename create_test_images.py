"""
create_test_images.py
=====================
Generates three placeholder JPEG images in raw/source_images/ for use when
testing import_scale_cats.py.

Images created
--------------
    test_cat_1.jpg  1200x900  solid orange  labelled "Test Cat 1"
    test_cat_2.jpg   800x600  solid gray    labelled "Test Cat 2"
    test_cat_3.jpg   400x300  solid blue    labelled "Test Cat 3"  (already < 640px wide)

Usage
-----
    python create_test_images.py [--output-dir PATH] [--force]

Arguments
---------
    --output-dir  Where to write the images (default: raw/source_images)
    --force       Overwrite existing files (default: skip if file already exists)
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Image specs
# ---------------------------------------------------------------------------

IMAGES = [
    {
        "filename": "test_cat_1.jpg",
        "size": (1200, 900),
        "bg_color": (255, 140, 0),   # orange
        "label": "Test Cat 1",
    },
    {
        "filename": "test_cat_2.jpg",
        "size": (800, 600),
        "bg_color": (140, 140, 140),  # gray
        "label": "Test Cat 2",
    },
    {
        "filename": "test_cat_3.jpg",
        "size": (400, 300),
        "bg_color": (30, 80, 200),    # blue
        "label": "Test Cat 3",
    },
]

# ---------------------------------------------------------------------------
# Image generation
# ---------------------------------------------------------------------------


def make_placeholder(
    output_path: Path,
    size: tuple[int, int],
    bg_color: tuple[int, int, int],
    label: str,
    force: bool,
) -> None:
    """Create a solid-colour JPEG with a centred text label."""
    if output_path.exists() and not force:
        print(f"  SKIP (already exists): {output_path.name}")
        return

    img = Image.new("RGB", size, color=bg_color)
    draw = ImageDraw.Draw(img)

    # Attempt to load a basic truetype font; fall back to the default bitmap font
    # if none is available on the system.
    font = None
    font_size = max(size[0] // 12, 24)
    for font_name in ("DejaVuSans-Bold.ttf", "Arial.ttf", "Helvetica.ttf"):
        try:
            font = ImageFont.truetype(font_name, size=font_size)
            break
        except (OSError, IOError):
            continue

    if font is None:
        font = ImageFont.load_default()

    # Measure text so we can centre it
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size[0] - text_w) // 2
    y = (size[1] - text_h) // 2

    # Draw a semi-transparent white drop-shadow for legibility
    shadow_offset = max(font_size // 16, 2)
    draw.text((x + shadow_offset, y + shadow_offset), label, fill=(0, 0, 0, 180), font=font)
    draw.text((x, y), label, fill=(255, 255, 255), font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format="JPEG", quality=90)
    print(f"  Created: {output_path.name}  ({size[0]}x{size[1]})")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    project_root = Path(__file__).parent
    parser = argparse.ArgumentParser(
        description="Generate placeholder test images in raw/source_images/."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "raw" / "source_images",
        help="Directory to write test images into (default: raw/source_images)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files instead of skipping them",
    )
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    print(f"Writing test images to: {args.output_dir.resolve()}")
    for spec in IMAGES:
        make_placeholder(
            output_path=args.output_dir / spec["filename"],
            size=spec["size"],
            bg_color=spec["bg_color"],
            label=spec["label"],
            force=args.force,
        )
    print("Done.")
