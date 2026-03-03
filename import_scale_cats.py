"""
import_scale_cats.py
====================
Scans raw/source_images/ for image files, scales each so its width is at most
640 pixels (preserving aspect ratio, no upscaling), and saves the result as a
JPEG into assets/images/ with sequential filenames: cat_001.jpg, cat_002.jpg, …

A manifest at assets/manifest.json tracks every processed image so that
re-running the script never re-processes a file that was already imported.
Numbering for new entries continues from the highest index already in the
manifest.

Usage
-----
    python import_scale_cats.py [--source-dir PATH] [--output-dir PATH]
                                [--manifest PATH] [--max-width INT] [--dry-run]

Arguments
---------
    --source-dir   Directory to scan for source images (default: raw/source_images)
    --output-dir   Directory to write scaled JPEGs into   (default: assets/images)
    --manifest     Path to the JSON manifest file          (default: assets/manifest.json)
    --max-width    Maximum output width in pixels          (default: 640)
    --dry-run      Print what would happen without writing any files
"""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".heif"}
MAX_WIDTH_DEFAULT = 640

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_manifest(manifest_path: Path) -> dict:
    """Load manifest JSON from disk, or return an empty structure."""
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    return {"images": []}


def save_manifest(manifest_path: Path, manifest: dict) -> None:
    """Write manifest to disk as pretty-printed JSON."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")  # trailing newline for clean diffs


def already_imported_sources(manifest: dict) -> set:
    """Return a set of source filenames that are already in the manifest."""
    return {entry["source"] for entry in manifest.get("images", [])}


def next_sequence_number(manifest: dict) -> int:
    """Return the next available sequential index (1-based)."""
    entries = manifest.get("images", [])
    if not entries:
        return 1
    # Parse the numeric suffix from IDs like "cat_007"
    max_index = 0
    for entry in entries:
        id_str = entry.get("id", "")
        parts = id_str.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            max_index = max(max_index, int(parts[1]))
    return max_index + 1


def collect_source_images(source_dir: Path) -> list[Path]:
    """
    Return all image files found (non-recursively) in source_dir,
    sorted by name for deterministic ordering.
    """
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")
    found = [
        p
        for p in source_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return sorted(found, key=lambda p: p.name.lower())


def scale_and_save(
    source_path: Path,
    output_path: Path,
    max_width: int,
) -> tuple[int, int]:
    """
    Open source_path, scale so width <= max_width (preserving aspect ratio,
    no upscaling), and save as JPEG at output_path.

    Returns (output_width, output_height).
    """
    with Image.open(source_path) as img:
        # Convert to RGB so we can always save as JPEG (handles RGBA / palette modes)
        img = img.convert("RGB")
        orig_width, orig_height = img.size

        if orig_width > max_width:
            scale_factor = max_width / orig_width
            new_width = max_width
            new_height = int(orig_height * scale_factor)
            img = img.resize((new_width, new_height), Image.LANCZOS)
        else:
            new_width, new_height = orig_width, orig_height

        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, format="JPEG", quality=85, optimize=True)

    return new_width, new_height


# ---------------------------------------------------------------------------
# Main processing logic
# ---------------------------------------------------------------------------


def run(
    source_dir: Path,
    output_dir: Path,
    manifest_path: Path,
    max_width: int,
    dry_run: bool,
) -> None:
    """Core processing loop."""
    # --- gather source images -----------------------------------------------
    try:
        source_images = collect_source_images(source_dir)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if not source_images:
        print("No image files found in source directory. Nothing to do.")
        return

    # --- load manifest -------------------------------------------------------
    manifest = load_manifest(manifest_path)
    already_done = already_imported_sources(manifest)

    # --- partition into new vs skipped --------------------------------------
    to_process = [p for p in source_images if p.name not in already_done]
    to_skip = [p for p in source_images if p.name in already_done]

    print(f"Found {len(source_images)} image(s) in {source_dir}")
    print(f"  Already in manifest (skip): {len(to_skip)}")
    print(f"  New (to process):           {len(to_process)}")

    if not to_process:
        print("Nothing new to process.")
        return

    # --- process new images -------------------------------------------------
    seq = next_sequence_number(manifest)
    new_entries: list[dict] = []

    for source_path in to_process:
        cat_id = f"cat_{seq:03d}"
        output_filename = f"{cat_id}.jpg"
        output_path = output_dir / output_filename

        if dry_run:
            print(f"  [DRY-RUN] {source_path.name} -> {output_filename}")
            seq += 1
            continue

        try:
            width, height = scale_and_save(source_path, output_path, max_width)
        except Exception as exc:  # noqa: BLE001
            print(f"  WARNING: Could not process {source_path.name}: {exc}", file=sys.stderr)
            continue

        entry = {
            "id": cat_id,
            "source": source_path.name,
            "file": output_filename,
            "width": width,
            "height": height,
        }
        new_entries.append(entry)
        print(f"  {source_path.name} -> {output_filename}  ({width}x{height})")
        seq += 1

    # --- update manifest ----------------------------------------------------
    if new_entries and not dry_run:
        manifest["images"].extend(new_entries)
        save_manifest(manifest_path, manifest)

    # --- summary ------------------------------------------------------------
    processed_count = len(new_entries)
    skipped_count = len(to_skip)
    print()
    print("Summary")
    print("-------")
    print(f"  Processed : {processed_count}")
    print(f"  Skipped   : {skipped_count}")
    if not dry_run and new_entries:
        print(f"  Output dir: {output_dir.resolve()}")
        print(f"  Manifest  : {manifest_path.resolve()}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    project_root = Path(__file__).parent
    parser = argparse.ArgumentParser(
        description=(
            "Scale source images to max 640px wide and import them into "
            "assets/images/ with sequential filenames, updating a JSON manifest."
        )
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=project_root / "raw" / "source_images",
        help="Directory containing source images (default: raw/source_images)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "assets" / "images",
        help="Directory to write scaled JPEGs into (default: assets/images)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=project_root / "assets" / "manifest.json",
        help="Path to the JSON manifest file (default: assets/manifest.json)",
    )
    parser.add_argument(
        "--max-width",
        type=int,
        default=MAX_WIDTH_DEFAULT,
        help=f"Maximum output width in pixels (default: {MAX_WIDTH_DEFAULT})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without writing any files",
    )
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    run(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        manifest_path=args.manifest,
        max_width=args.max_width,
        dry_run=args.dry_run,
    )
