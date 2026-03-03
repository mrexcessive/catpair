# CatPair — How To Guide

This document describes the Python utility scripts used to build the cat tile
assets for the CatPair game.

---

## Prerequisites

Install dependencies once:

```bash
pip3 install -r requirements.txt
```

`requirements.txt` includes:
- `Pillow` — image processing
- `pillow-heif` — HEIC/HEIF support for iPhone photos
- `ultralytics` — YOLOv8 object detection (installed separately; see below)

For `ultralytics` (YOLOv8), install it with:

```bash
pip3 install ultralytics
```

> **GPU note:** All scripts run on CPU by default. A GPU is not required.

---

## Pipeline overview

```
raw/source_images/          (original photos, any size, JPG or HEIC)
        |
        v
  import_scale_cats.py
        |
        v
assets/images/              (scaled to max 640px wide, cat_001.jpg …)
assets/manifest.json        (tracks imported files)
        |
        v
  crop_cats.py
        |
        v
assets/tiles/               (128×128 JPEG tiles, one per detected cat)
assets/manifest_tiles.json  (tracks detection results)
```

---

## Scripts

### `create_test_images.py`

Generates three placeholder images in `raw/source_images/` for testing the
pipeline without real photos.

```bash
python3 create_test_images.py
```

Creates:
- `test_cat_1.jpg` — 1200×900 orange placeholder
- `test_cat_2.jpg` — 800×600 grey placeholder
- `test_cat_3.jpg` — 400×300 blue placeholder (already under 640px)

Add `--force` to overwrite existing placeholders.

---

### `import_scale_cats.py`

Scans `raw/source_images/` for image files, scales each so its width is at
most 640 pixels (preserving aspect ratio, never upscaling), and saves the
result as a JPEG into `assets/images/` with sequential filenames
(`cat_001.jpg`, `cat_002.jpg`, …).

Keeps a manifest at `assets/manifest.json` so re-running never re-processes
a file that was already imported. Numbering continues from the highest index
already in the manifest.

**Supported input formats:** JPG, JPEG, PNG, GIF, BMP, WebP, HEIC, HEIF

#### Basic usage

```bash
python3 import_scale_cats.py
```

#### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--source-dir PATH` | `raw/source_images` | Directory containing source photos |
| `--output-dir PATH` | `assets/images` | Where to write scaled JPEGs |
| `--manifest PATH` | `assets/manifest.json` | Path to the JSON manifest |
| `--max-width INT` | `640` | Maximum output width in pixels |
| `--dry-run` | off | Preview what would happen without writing files |

#### Example: preview only

```bash
python3 import_scale_cats.py --dry-run
```

#### Example: use a wider output size

```bash
python3 import_scale_cats.py --max-width 800
```

#### `assets/manifest.json` format

```json
{
  "images": [
    {
      "id": "cat_001",
      "source": "IMG_0491.HEIC",
      "file": "cat_001.jpg",
      "width": 640,
      "height": 853
    }
  ]
}
```

---

### `crop_cats.py`

Detects cats in the scaled images in `assets/images/` using a YOLOv8 neural
network, crops a square region tightly around each detected cat, resizes it to
128×128 pixels, and saves the result into `assets/tiles/`.

On first run the YOLOv8 medium model (`yolov8m.pt`, ~50 MB) is downloaded
automatically from the internet and cached locally.

Images where no cat is detected above the confidence threshold are recorded in
the manifest with `"status": "no_cat"` and are skipped (no tile is written).
The manifest ensures no image is processed more than once.

#### Basic usage

```bash
python3 crop_cats.py
```

#### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--input-dir PATH` | `assets/images` | Directory of scaled source images |
| `--output-dir PATH` | `assets/tiles` | Where to write 128×128 tiles |
| `--manifest PATH` | `assets/manifest_tiles.json` | Path to the tile manifest |
| `--model MODEL` | `yolov8m.pt` | YOLOv8 model file to use |
| `--conf FLOAT` | `0.45` | Minimum detection confidence (0–1) |
| `--padding FLOAT` | `0.10` | Fractional padding added around the cat bounding box |
| `--tile-size INT` | `128` | Output tile size in pixels (square) |
| `--dry-run` | off | Preview what would happen without writing files |

#### Example: lower confidence to catch more cats

Some photos where the cat is small or partially obscured may fall just below
the default threshold. Try:

```bash
python3 crop_cats.py --conf 0.30
```

> If you want to re-process images previously recorded as `no_cat`, delete
> their entries from `assets/manifest_tiles.json` first (or delete the whole
> file to start fresh).

#### Example: use the faster nano model

```bash
python3 crop_cats.py --model yolov8n.pt
```

The nano model is ~6 MB and faster on CPU but slightly less accurate.

#### `assets/manifest_tiles.json` format

```json
{
  "tiles": [
    {
      "source": "cat_005.jpg",
      "status": "ok",
      "tile": "cat_005.jpg",
      "bbox": [42, 18, 598, 840],
      "tile_size": 128
    },
    {
      "source": "cat_006.jpg",
      "status": "no_cat",
      "tile": null
    }
  ]
}
```

`status` values:
- `"ok"` — cat detected; tile written to `assets/tiles/`
- `"no_cat"` — no cat detected above the confidence threshold
- `"error"` — an unexpected error occurred (details in the `"error"` field)

---

## Typical first-run workflow

```bash
# 1. Put photos into raw/source_images/ (JPG or HEIC)

# 2. Scale and import
python3 import_scale_cats.py

# 3. Detect, crop, and tile
python3 crop_cats.py

# 4. Check results
ls assets/tiles/
cat assets/manifest_tiles.json | python3 -m json.tool | grep status | sort | uniq -c
```

---

## File layout

```
catpair/
├── raw/
│   └── source_images/          original photos (gitignored)
├── assets/
│   ├── images/                 scaled 640px-wide JPEGs
│   ├── tiles/                  128×128 cat tile JPEGs
│   ├── manifest.json           import manifest
│   └── manifest_tiles.json     tile manifest
├── import_scale_cats.py
├── create_test_images.py
├── crop_cats.py
├── requirements.txt
└── docs/
    └── HowTo.md                (this file)
```
