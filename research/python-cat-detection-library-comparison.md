# Python Library for Cat Detection with Bounding Box — Comparison and Recommendation

**Date:** 2026-03-03
**Question:** What is the best Python library for detecting the full body of a cat in photos, returning bounding box coordinates, for the purpose of cropping images to a square around the cat?

## Answer

### Recommendation: Ultralytics YOLO11n (or YOLOv8n)

**Install:** `pip install ultralytics`

The `ultralytics` package is the clear winner for this task. It installs in a single pip command, auto-downloads the pretrained COCO model on first use, detects full cat bodies (not just faces), and can process ~237 images in seconds. COCO class 15 is `cat`, and the model handles typical pet photos well.

---

## Candidate Evaluation

### 1. Ultralytics YOLOv8 / YOLO11 (`pip install ultralytics`)

**Accuracy:** Strong. COCO class 15 is `cat`. YOLOv8n achieves ~37.3 mAP on the full COCO val set (all 80 classes). Cat is a common, large, well-represented class in COCO so per-class accuracy for cats is substantially higher than the overall mAP. YOLO11 (the successor, also in the `ultralytics` package) achieves higher mAP with 22% fewer parameters than YOLOv8m — for this task, either works excellently.

**Detects full body:** Yes. Trained on COCO which annotates the full cat body, not just the face.

**Ease of use:** Excellent. Three lines of code:
```python
from ultralytics import YOLO
model = YOLO("yolov8n.pt")   # or "yolo11n.pt" for latest
results = model.predict("photos/", classes=[15])  # class 15 = cat
```
Bounding boxes come back as `result.boxes.xyxy` (x1, y1, x2, y2 in pixel coordinates), `result.boxes.conf` for confidence scores.

**Pip installability:** Single command: `pip install ultralytics`. No manual compilation, no protobuf fussing.

**Model auto-download:** Yes. On first call to `YOLO("yolov8n.pt")`, the weights (~6MB for nano) download automatically from GitHub releases.

**Speed for 237 images:** Very fast. GPU latency is ~1.3ms/image. On CPU, roughly 20–100ms/image depending on hardware. Batch inference over a directory is natively supported via passing a list or directory path. 237 images on a modern CPU: under 30 seconds for nano model; GPU: under 5 seconds.

**Model size options:** `yolov8n.pt` (nano, fastest, smallest), `yolov8s.pt`, `yolov8m.pt` (balanced), `yolov8l.pt`, `yolov8x.pt` (most accurate). For 237 images where speed doesn't matter much, `yolov8m.pt` is a good balance.

**Known gotchas:**
- When multiple cats are in one image, you get multiple bounding boxes — pick the largest-area or highest-confidence one.
- Occasional false positives on plush toys, cat-shaped objects. Use `conf=0.4` or higher threshold.
- The `ultralytics` package pulls in PyTorch, which is a large dependency (~2GB with CUDA). Pure CPU install is smaller.

---

### 2. torchvision Faster R-CNN / SSD

**Accuracy:** Good. `fasterrcnn_resnet50_fpn(weights="DEFAULT")` is pretrained on COCO and detects cats (class 17 in torchvision's COCO label map, which is 1-indexed and includes a background class). Per-class accuracy for cats on typical photos is comparable to YOLOv8.

**Detects full body:** Yes, same COCO training annotations.

**Ease of use:** Moderate. More boilerplate than ultralytics:
```python
import torchvision, torch
from PIL import Image
from torchvision.transforms import functional as F

model = torchvision.models.detection.fasterrcnn_resnet50_fpn(weights="DEFAULT")
model.eval()

img = Image.open("cat.jpg").convert("RGB")
tensor = F.to_tensor(img).unsqueeze(0)
with torch.no_grad():
    preds = model(tensor)[0]

# COCO class 17 = cat (1-indexed with background)
cat_indices = [i for i, l in enumerate(preds["labels"]) if l == 17]
boxes = preds["boxes"][cat_indices]  # Nx4 xyxy
scores = preds["scores"][cat_indices]
```

**Pip installability:** `pip install torchvision` — but torchvision version must match your torch version. This version pinning is a common source of environment conflicts.

**Model auto-download:** Yes, weights download automatically on first use.

**Speed for 237 images:** Significantly slower than YOLO. GPU latency: ~54ms/image vs. ~1.3ms for YOLOv8. On CPU: several hundred ms per image. For 237 images on CPU, expect 2–10 minutes depending on hardware.

**Known gotchas:**
- torch + torchvision version pairing must match exactly or you get cryptic import errors.
- No directory-level batch inference utility; you must loop images yourself.
- `pretrained=True` is deprecated in newer torchvision; must use `weights=` parameter.
- COCO class indexing is 1-based with a background class (0), so cat = class 17, not 15.

---

### 3. OpenCV Haar Cascades

**Accuracy:** Poor for this task. OpenCV ships with `haarcascade_frontalcatface.xml` and `haarcascade_frontalcatface_extended.xml`, which detect cat **faces** only, viewed frontally. There is no full-body cat Haar cascade in the standard OpenCV distribution.

**Detects full body:** No. Face-only, frontal view only.

**Ease of use:** Simple API, but the output is only useful for face crops, not full-body crops.

**Pip installability:** `pip install opencv-python` — clean single install.

**Speed:** Very fast (it's classical CV, not deep learning), but the accuracy tradeoff makes it unsuitable.

**Known gotchas:**
- High false positive rate.
- Cannot detect cats from the side, rear, or when curled up.
- Haar features are not descriptive enough to reliably isolate cat bodies.

**Verdict:** Eliminate from consideration for full-body detection.

---

### 4. TensorFlow Object Detection API

**Accuracy:** Potentially very high with the right pretrained model (EfficientDet, SSD, etc.), all of which support COCO cat detection.

**Detects full body:** Yes.

**Ease of use:** Poor. Installation requires protobuf compilation, PYTHONPATH manipulation, and multiple manual steps. While wrapper pip packages (`tf-object-detection`, `tensorflow-object-detection-api`) exist, they have version compatibility issues and inconsistent maintenance. Even with them, the inference API is significantly more verbose than ultralytics.

**Pip installability:** Painful. Standard instructions involve:
1. `pip install tensorflow`
2. Clone `tensorflow/models` repo
3. Compile protobuf files with `protoc`
4. `pip install` from within the cloned repo

**Model auto-download:** Requires manually downloading model checkpoints from the TF Model Zoo.

**Speed:** Comparable to or better than Faster R-CNN; SSD variants are faster.

**Known gotchas:**
- TensorFlow 1.x vs 2.x API fragmentation causes frequent tutorial rot.
- Much larger ecosystem burden than ultralytics for the same COCO pretrained result.
- TF + CUDA version pairing is as fiddly as torch + torchvision.

**Verdict:** Not worth the setup complexity when ultralytics exists.

---

## Summary Comparison Table

| Criterion               | Ultralytics YOLO11/v8 | torchvision Faster R-CNN | OpenCV Haar | TF OD API |
|------------------------|----------------------|--------------------------|-------------|-----------|
| Full body detection    | Yes                  | Yes                      | **No** (face only) | Yes    |
| pip installability     | Excellent (1 cmd)    | Good (version pinning)   | Excellent   | Poor      |
| Model auto-download    | Yes                  | Yes                      | Bundled     | Manual    |
| API simplicity         | Excellent            | Moderate                 | Simple      | Poor      |
| Speed (237 imgs, CPU)  | ~10-30s              | ~2-10min                 | <5s (unusable) | ~2-10min |
| Speed (237 imgs, GPU)  | <5s                  | ~15s                     | N/A         | ~15s      |
| Accuracy on cat photos | High                 | High                     | Low         | High      |
| Handles varied poses   | Yes                  | Yes                      | No          | Yes       |

---

## Recommended Implementation

```python
from ultralytics import YOLO
from pathlib import Path
from PIL import Image

model = YOLO("yolov8m.pt")  # medium model for better accuracy, or yolov8n.pt for speed

CAT_CLASS = 15  # COCO class index for cat

def get_cat_bbox(image_path: str):
    """
    Returns the best bounding box (x1, y1, x2, y2) for a cat in the image,
    or None if no cat is detected.
    """
    results = model.predict(image_path, classes=[CAT_CLASS], conf=0.4, verbose=False)
    result = results[0]

    if result.boxes is None or len(result.boxes) == 0:
        return None

    # If multiple cats, pick the highest-confidence detection
    best_idx = result.boxes.conf.argmax().item()
    box = result.boxes.xyxy[best_idx].tolist()  # [x1, y1, x2, y2]
    return box


def crop_to_square_around_cat(image_path: str, output_path: str, padding: float = 0.15):
    """
    Crops image to a square centered on the detected cat bounding box.
    padding: fractional padding to add around the bounding box (0.15 = 15%).
    """
    bbox = get_cat_bbox(image_path)
    if bbox is None:
        print(f"No cat detected in {image_path}")
        return False

    img = Image.open(image_path)
    w, h = img.size
    x1, y1, x2, y2 = bbox

    # Add padding
    bw, bh = x2 - x1, y2 - y1
    x1 = max(0, x1 - bw * padding)
    y1 = max(0, y1 - bh * padding)
    x2 = min(w, x2 + bw * padding)
    y2 = min(h, y2 + bh * padding)

    # Make it square (expand shorter side to match longer)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    side = max(x2 - x1, y2 - y1) / 2
    x1 = max(0, cx - side)
    y1 = max(0, cy - side)
    x2 = min(w, cx + side)
    y2 = min(h, cy + side)

    cropped = img.crop((int(x1), int(y1), int(x2), int(y2)))
    cropped.save(output_path)
    return True
```

For batch processing all 237 images:
```python
from pathlib import Path

input_dir = Path("raw/")
output_dir = Path("cropped/")
output_dir.mkdir(exist_ok=True)

for img_path in input_dir.glob("*.jpg"):
    crop_to_square_around_cat(str(img_path), str(output_dir / img_path.name))
```

---

## Assumptions Checked

- **"Cat is class 15 in COCO"**: Confirmed for ultralytics YOLO (0-indexed, 80-class COCO). Note: torchvision uses 1-indexed labels with background=0, making cat class 17 there.
- **"OpenCV has a cat full-body cascade"**: Refuted. Only frontal cat face cascades are included in the standard OpenCV Haar cascade collection.
- **"TF OD API is installable via pip cleanly"**: Partially refuted. Wrapper packages exist but the canonical installation is multi-step and fragile. The complexity is not justified when ultralytics achieves the same result in one command.
- **"YOLO detects full cat body, not just face"**: Confirmed. COCO bounding box annotations for cats encompass the full animal body. This is what YOLO is trained on.

## References

1. Ultralytics YOLOv8 documentation — [https://docs.ultralytics.com/models/yolov8/](https://docs.ultralytics.com/models/yolov8/)
2. YOLO11 vs YOLOv8 comparison — [https://docs.ultralytics.com/compare/yolo11-vs-yolov8/](https://docs.ultralytics.com/compare/yolo11-vs-yolov8/)
3. Ultralytics YOLO model evolution paper (arXiv) — [https://arxiv.org/html/2510.09653v2](https://arxiv.org/html/2510.09653v2)
4. YOLOv8 vs Faster R-CNN comparison — [https://roboflow.com/compare/yolov8-vs-faster-r-cnn](https://roboflow.com/compare/yolov8-vs-faster-r-cnn)
5. ReadyTensor: Comparing YOLOv8, SSD, and Faster-RCNN — [https://app.readytensor.ai/publications/comparing-yolov8-ssd-and-fasterrcnn-for-realtime-object-detection-IbA4gAvuaYW8](https://app.readytensor.ai/publications/comparing-yolov8-ssd-and-fasterrcnn-for-realtime-object-detection-IbA4gAvuaYW8)
6. TorchVision Object Detection Tutorial — [https://docs.pytorch.org/tutorials/intermediate/torchvision_tutorial.html](https://docs.pytorch.org/tutorials/intermediate/torchvision_tutorial.html)
7. OpenCV Haar Cascades (PyImageSearch) — [https://pyimagesearch.com/2021/04/12/opencv-haar-cascades/](https://pyimagesearch.com/2021/04/12/opencv-haar-cascades/)
8. OpenCV cat detection forum — [https://answers.opencv.org/question/29495/cat-detection/](https://answers.opencv.org/question/29495/cat-detection/)
9. TF Object Detection API installation — [https://tensorflow-object-detection-api-tutorial.readthedocs.io/en/latest/install.html](https://tensorflow-object-detection-api-tutorial.readthedocs.io/en/latest/install.html)
10. YOLOv8 cat and dog detection guide — [https://www.oreateai.com/blog/yolov8-cat-and-dog-detection-practical-guide-a-complete-implementation-guide-based-on-the-ultralytics-framework-and-gradio/bf00cbbc7fea39f87eb60d5217242feb](https://www.oreateai.com/blog/yolov8-cat-and-dog-detection-practical-guide-a-complete-implementation-guide-based-on-the-ultralytics-framework-and-gradio/bf00cbbc7fea39f87eb60d5217242feb)

## Notes

- For this catpair project, also consider `dog` (class 16) detection if needed in addition to cats.
- If accuracy on difficult cases (cats curled up, partially occluded) is insufficient with the nano model, try `yolov8m.pt` or even `yolov8l.pt`.
- YOLO11 (`yolo11n.pt`, `yolo11m.pt`) is the current latest Ultralytics model (2024) and achieves slightly better accuracy with fewer parameters — same API, just change the filename.
- The `conf=0.4` threshold is a starting point; tune upward to reduce false positives, downward to catch more difficult detections.
