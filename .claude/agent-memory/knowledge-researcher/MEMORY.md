# Knowledge Researcher Agent Memory

## Project Context
- Project: catpair — processes/crops cat photos
- Working directory: /home/peter/ccode_projects/catpair
- Research logs: /home/peter/ccode_projects/catpair/research/
- Summary index: /home/peter/ccode_projects/catpair/research/SUMMARIES.md

## Key Validated Facts (catpair domain)

### Cat Detection
- Best library for cat full-body detection + bounding box: `ultralytics` (`pip install ultralytics`)
- COCO class 15 = cat (0-indexed, ultralytics convention)
- COCO class 17 = cat in torchvision (1-indexed with background=0)
- OpenCV Haar cascades only detect cat FACES (frontal) — NOT full body
- YOLOv8n GPU latency ~1.3ms/img; Faster R-CNN ~54ms/img (40x slower)
- For 237 images: ultralytics processes in seconds; Faster R-CNN takes minutes on CPU
- YOLO11 is the latest Ultralytics model (2024), same API as YOLOv8, slightly better accuracy

### High-Quality Sources for CV/Detection Topics
- Ultralytics docs: https://docs.ultralytics.com/
- Roboflow comparisons: https://roboflow.com/compare/
- ReadyTensor benchmarks: https://app.readytensor.ai/

## Previous Research Sessions
- 2026-03-03: Python cat detection library comparison → research/python-cat-detection-library-comparison.md
