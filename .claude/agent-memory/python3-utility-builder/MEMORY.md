# Python3 Utility Builder - Project Memory

## Project: catpair (/home/peter/ccode_projects/catpair)

### Key Paths
- Source images input : `raw/source_images/`
- Scaled JPEG output  : `assets/images/`
- Manifest           : `assets/manifest.json`
- Scripts live in project root

### Dependencies
- `Pillow>=10.0.0` — used for image open/resize/save and placeholder generation
- requirements.txt is at project root; entries sorted alphabetically

### Established Patterns
- Manifest keyed on original source filename to detect duplicates across runs
- Sequential IDs use zero-padded 3-digit format: `cat_001`, `cat_002`, …
- Next sequence number derived by parsing numeric suffix of existing manifest IDs
- All source images converted to RGB before JPEG save (handles RGBA / palette modes)
- Downscale uses `Image.LANCZOS`; images already <= max_width are copied as-is (no upscale)
- Manifest written with `json.dump(..., indent=2)` + trailing newline for clean diffs
- CLI uses `argparse`; defaults resolved relative to `Path(__file__).parent`

### Font Strategy (create_test_images.py)
- Try DejaVuSans-Bold.ttf, Arial.ttf, Helvetica.ttf in order via ImageFont.truetype
- Fall back to ImageFont.load_default() if none available
- Text centred using draw.textbbox() bounding box arithmetic
