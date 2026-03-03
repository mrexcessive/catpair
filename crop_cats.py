"""
crop_cats.py
============
Detects cats in images from assets/images/, crops a square region around each
cat, resizes to 128×128, and saves the result into assets/tiles/.

A manifest at assets/manifest_tiles.json tracks every processed image so
re-running never re-processes a file. Each entry records whether a cat was
found or not.

Usage
-----
    python3 crop_cats.py [--input-dir PATH] [--output-dir PATH]
                         [--manifest PATH] [--model MODEL]
                         [--conf FLOAT] [--padding FLOAT] [--tile-size INT]
                         [--dry-run]

Arguments
---------
    --input-dir   Directory of scaled source images  (default: assets/images)
    --output-dir  Directory to write 128×128 tiles   (default: assets/tiles)
    --manifest    Path to tile manifest JSON          (default: assets/manifest_tiles.json)
    --model       YOLOv8 model file                   (default: yolov8m.pt)
    --conf        Minimum confidence to accept a cat  (default: 0.45)
    --padding     Fractional padding around bbox      (default: 0.10)
    --tile-size   Output tile size in pixels          (default: 128)
    --dry-run     Print what would happen without writing files

Notes
-----
- If multiple cats are detected in one image the highest-confidence detection
  is used.
- Images where no cat is detected above --conf are recorded in the manifest
  with status "no_cat" and are not written to the output directory.
- YOLOv8 runs on CPU automatically when no GPU is available.
"""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

# COCO class index for "cat" (0-indexed, as used by ultralytics)
CAT_CLASS = 15
TILE_SIZE_DEFAULT = 128
CONF_DEFAULT = 0.45
PADDING_DEFAULT = 0.10
MODEL_DEFAULT = "yolov8m.pt"
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def load_manifest(path: Path) -> dict:
    if path.exists():
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    return {"tiles": []}


def save_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")


def already_processed(manifest: dict) -> set:
    """Return filenames already recorded in the manifest (any status)."""
    return {entry["source"] for entry in manifest.get("tiles", [])}


# ---------------------------------------------------------------------------
# Detection + crop helpers
# ---------------------------------------------------------------------------

def load_model(model_name: str):
    """Load YOLOv8 model (downloads weights automatically on first use)."""
    from ultralytics import YOLO  # imported here so the rest of the module
    return YOLO(model_name)       # works without ultralytics for dry-run help


def detect_cat_bbox(model, image_path: Path, conf: float):
    """
    Run inference on image_path, returning [x1, y1, x2, y2] for the
    highest-confidence cat detection, or None if no cat found above conf.
    """
    results = model.predict(
        str(image_path),
        classes=[CAT_CLASS],
        conf=conf,
        verbose=False,
        device="cpu",
    )
    boxes = results[0].boxes
    if boxes is None or len(boxes) == 0:
        return None
    best_idx = int(boxes.conf.argmax())
    x1, y1, x2, y2 = boxes.xyxy[best_idx].tolist()
    return x1, y1, x2, y2


def make_square_crop(img: Image.Image, bbox, padding: float):
    """
    Given a PIL image and a bounding box (x1,y1,x2,y2), return a new PIL
    image that is a square crop containing the full bounding box.

    Steps:
      1. Expand the bbox by `padding` fraction on each side.
      2. Make it square by growing the shorter dimension.
      3. Shift the square to fit entirely within the image (never resize).
    """
    iw, ih = img.size
    x1, y1, x2, y2 = bbox

    # 1. Add padding
    bw, bh = x2 - x1, y2 - y1
    x1 = x1 - bw * padding
    y1 = y1 - bh * padding
    x2 = x2 + bw * padding
    y2 = y2 + bh * padding

    # 2. Expand to square (grow shorter side, keep center)
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    half = max(x2 - x1, y2 - y1) / 2

    x1 = cx - half
    y1 = cy - half
    x2 = cx + half
    y2 = cy + half

    # 3. Shift to keep square inside image bounds (don't resize)
    side = x2 - x1  # same as y2 - y1
    if x1 < 0:
        x1, x2 = 0, min(side, iw)
    if x2 > iw:
        x1, x2 = max(0, iw - side), iw
    if y1 < 0:
        y1, y2 = 0, min(side, ih)
    if y2 > ih:
        y1, y2 = max(0, ih - side), ih

    crop = img.crop((int(x1), int(y1), int(x2), int(y2)))
    return crop


# ---------------------------------------------------------------------------
# Main processing loop
# ---------------------------------------------------------------------------

def run(
    input_dir: Path,
    output_dir: Path,
    manifest_path: Path,
    model_name: str,
    conf: float,
    padding: float,
    tile_size: int,
    dry_run: bool,
) -> None:
    if not input_dir.is_dir():
        print(f"ERROR: input directory not found: {input_dir}", file=sys.stderr)
        sys.exit(1)

    source_images = sorted(
        [p for p in input_dir.iterdir()
         if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS],
        key=lambda p: p.name.lower(),
    )

    if not source_images:
        print("No images found in input directory. Nothing to do.")
        return

    manifest = load_manifest(manifest_path)
    done = already_processed(manifest)

    to_process = [p for p in source_images if p.name not in done]
    to_skip    = [p for p in source_images if p.name in done]

    print(f"Found {len(source_images)} image(s) in {input_dir}")
    print(f"  Already processed (skip) : {len(to_skip)}")
    print(f"  New (to process)         : {len(to_process)}")

    if not to_process:
        print("Nothing new to process.")
        return

    if dry_run:
        for p in to_process:
            print(f"  [DRY-RUN] would process {p.name}")
        return

    # Load model once for all images
    print(f"\nLoading model '{model_name}' (downloads on first use)…")
    model = load_model(model_name)
    print("Model ready.\n")

    output_dir.mkdir(parents=True, exist_ok=True)

    new_entries = []
    count_cat   = 0
    count_nocat = 0

    for img_path in to_process:
        bbox = detect_cat_bbox(model, img_path, conf)

        if bbox is None:
            print(f"  NO CAT  {img_path.name}")
            new_entries.append({
                "source": img_path.name,
                "status": "no_cat",
                "tile": None,
            })
            count_nocat += 1
            continue

        try:
            with Image.open(img_path) as img:
                img = img.convert("RGB")
                square = make_square_crop(img, bbox, padding)
                tile = square.resize((tile_size, tile_size), Image.LANCZOS)
                out_path = output_dir / img_path.name
                tile.save(out_path, format="JPEG", quality=90, optimize=True)

            print(f"  CAT     {img_path.name} -> {out_path.name}  "
                  f"(bbox {int(bbox[0])},{int(bbox[1])}-{int(bbox[2])},{int(bbox[3])})")
            new_entries.append({
                "source": img_path.name,
                "status": "ok",
                "tile": img_path.name,
                "bbox": [round(v) for v in bbox],
                "tile_size": tile_size,
            })
            count_cat += 1

        except Exception as exc:
            print(f"  ERROR   {img_path.name}: {exc}", file=sys.stderr)
            new_entries.append({
                "source": img_path.name,
                "status": "error",
                "tile": None,
                "error": str(exc),
            })

    # Save updated manifest
    manifest["tiles"].extend(new_entries)
    save_manifest(manifest_path, manifest)

    print()
    print("Summary")
    print("-------")
    print(f"  Cat found    : {count_cat}")
    print(f"  No cat found : {count_nocat}")
    print(f"  Skipped      : {len(to_skip)}")
    print(f"  Tiles dir    : {output_dir.resolve()}")
    print(f"  Manifest     : {manifest_path.resolve()}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).parent
    p = argparse.ArgumentParser(
        description="Detect cats, crop to square, resize to 128×128 game tiles."
    )
    p.add_argument("--input-dir",  type=Path, default=root / "assets" / "images")
    p.add_argument("--output-dir", type=Path, default=root / "assets" / "tiles")
    p.add_argument("--manifest",   type=Path, default=root / "assets" / "manifest_tiles.json")
    p.add_argument("--model",      default=MODEL_DEFAULT,
                   help=f"YOLOv8 model weights (default: {MODEL_DEFAULT})")
    p.add_argument("--conf",  type=float, default=CONF_DEFAULT,
                   help=f"Min detection confidence 0–1 (default: {CONF_DEFAULT})")
    p.add_argument("--padding", type=float, default=PADDING_DEFAULT,
                   help=f"Fractional padding around cat bbox (default: {PADDING_DEFAULT})")
    p.add_argument("--tile-size", type=int, default=TILE_SIZE_DEFAULT,
                   help=f"Output tile size in pixels (default: {TILE_SIZE_DEFAULT})")
    p.add_argument("--dry-run", action="store_true",
                   help="Print what would happen without writing files")
    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    run(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        manifest_path=args.manifest,
        model_name=args.model,
        conf=args.conf,
        padding=args.padding,
        tile_size=args.tile_size,
        dry_run=args.dry_run,
    )
