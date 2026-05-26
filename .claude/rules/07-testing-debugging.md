# Rule 07 — Testing & Debugging

## Chiến lược kiểm tra

Dự án không có unit test framework chính thức. Kiểm tra được thực hiện theo cách **visual + log inspection**.

---

## Quick Sanity Check

### Kiểm tra môi trường

```bash
# Kiểm tra Python và dependencies
python --version          # Cần >= 3.9
python -c "import cv2; print(cv2.__version__)"
python -c "import ultralytics; print(ultralytics.__version__)"
python -c "import numpy; print(numpy.__version__)"

# Kiểm tra model tồn tại
ls yolov8n.pt yolov8s.pt  # Windows: dir *.pt
```

### Kiểm tra video đầu vào

```python
# Quick test: mở video và đọc 1 frame
import cv2
cap = cv2.VideoCapture("traffic_ai/data/video/test 3.mp4")
ret, frame = cap.read()
print(f"Video OK: {ret}, Size: {frame.shape if ret else 'N/A'}")
print(f"FPS: {cap.get(cv2.CAP_PROP_FPS)}, Frames: {cap.get(cv2.CAP_PROP_FRAME_COUNT)}")
cap.release()
```

### Kiểm tra polygon logic

```python
# Chạy nhanh để kiểm tra lane generation
from traffic_ai.detect_lanes_roadpoly import ROAD_POLY_NORM, BOUNDARY_TS, LANE_TYPES, generate_lane_polys_norm

lanes = generate_lane_polys_norm(ROAD_POLY_NORM, BOUNDARY_TS, LANE_TYPES)
for lane in lanes:
    print(f"Lane {lane['id']}: type={lane['type']}, points={len(lane['poly_norm'])}")

# Expected output:
# Lane 1: type=motorbike, points=4
# Lane 2: type=car, points=4
# Lane 3: type=car, points=4
```

---

## Lỗi phổ biến & Cách xử lý

### ❌ `FileNotFoundError: Video not found`

```
Nguyên nhân: VIDEO_SOURCE sai đường dẫn hoặc file không tồn tại
```

```python
# Kiểm tra
import os
print(os.path.exists(VIDEO_SOURCE))
print(os.path.abspath(VIDEO_SOURCE))

# Fix: kiểm tra tên file (khoảng trắng, đuôi file)
VIDEO_SOURCE = os.path.join(BASE_DIR, "data", "video", "test 3.mp4")
#                                                              ↑ space ở đây
```

---

### ❌ `Model not found` / YOLO load error

```
Nguyên nhân: File .pt không tồn tại ở đường dẫn tương đối
```

```python
# Kiểm tra
model_path = os.path.join(BASE_DIR, "..", "yolov8n.pt")
print(os.path.abspath(model_path))  # Xem path thực tế
print(os.path.exists(model_path))

# Fix: Đảm bảo chạy từ thư mục gốc project, không phải từ traffic_ai/
```

---

### ❌ Polygon làn không hiển thị đúng

```
Nguyên nhân: ROAD_POLY_NORM không phù hợp với video hiện tại
```

```
Triệu chứng:
- Polygon che phủ sai vùng
- Làn bị méo, lệch
- Xe không bao giờ được assign vào làn nào

Fix: Chạy lại pick_road_poly.py → pick_lane_boundaries.py với video đúng
```

---

### ❌ Tất cả xe đều bị WRONG LANE

```
Nguyên nhân 1: LANE_TYPES không khớp với số làn
Nguyên nhân 2: ENFORCE_Y_MIN_NORM quá thấp (kiểm tra vùng quá rộng)
Nguyên nhân 3: Thứ tự điểm trong ROAD_POLY_NORM bị sai
```

```python
# Debug: In lane assignment cho mỗi xe
print(f"Track {track_id}: center=({cx},{cy}), lane={lane_id}, type={lane['type']}, class={class_name}")

# Kiểm tra LANE_TYPES vs số làn
n_lanes = len(BOUNDARY_TS) - 1
assert len(LANE_TYPES) == n_lanes, f"Cần {n_lanes} LANE_TYPES, có {len(LANE_TYPES)}"
```

---

### ❌ Xe bị mất track (track_id thay đổi liên tục)

```
Nguyên nhân: IoU threshold quá cao hoặc FPS xử lý quá thấp
```

```python
# Giảm iou_threshold
tracker = SimpleTracker(max_age=30, iou_threshold=0.2)  # từ 0.3 xuống 0.2

# Tăng max_age nếu xe tạm thời bị che khuất
tracker = SimpleTracker(max_age=50, iou_threshold=0.3)
```

---

### ❌ CSV output rỗng / không có dòng vi phạm

```
Nguyên nhân 1: Tất cả xe đang đi đúng làn (đúng hành vi!)
Nguyên nhân 2: ENFORCE_Y_MIN_NORM quá cao (vùng kiểm tra quá hẹp)
Nguyên nhân 3: LANE_TYPES đặt thành "any" cho tất cả
Nguyên nhân 4: violation_logged đã có track_id từ lần chạy trước (nếu không reset)
```

```python
# Debug: bỏ tạm điều kiện ENFORCE_Y_MIN_NORM
if True:  # Thay if cy > frame_h * ENFORCE_Y_MIN_NORM:
    check_violation(...)
```

---

### ❌ FPS quá thấp, giật lag

```
Giải pháp (thứ tự ưu tiên):
1. Giảm DISPLAY_SCALE (ví dụ: 0.6 → 0.5)
2. Dùng model nhỏ hơn (yolov8n thay vì yolov8s)
3. Tăng confidence threshold để loại bớt detection (conf=0.4 → 0.5)
4. Thêm frame skip (chỉ xử lý frame chẵn)
```

```python
# Frame skip (nếu cần)
FRAME_SKIP = 2  # Xử lý 1 trong 2 frame
if frame_count % FRAME_SKIP != 0:
    frame_count += 1
    continue
```

---

## Debug Mode

Thêm flag `DEBUG = True` vào đầu file để kích hoạt logs chi tiết:

```python
DEBUG = False  # Đặt True để debug

# Sử dụng trong code
if DEBUG:
    print(f"[DEBUG] Frame {frame_count}: {len(detections)} detections")
    for d in detections:
        print(f"  → {d['class']} conf={d['conf']:.2f} bbox={d['bbox']}")
```

---

## Kiểm tra CSV output

```python
import csv

def inspect_csv(csv_path: str, max_rows: int = 20):
    """Đọc và in CSV để kiểm tra."""
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Tổng số vi phạm: {len(rows)}")
    for row in rows[:max_rows]:
        print(f"  Frame {row['frame']:>5} | Track {row['track_id']:>4} | "
              f"{row['class']:>10} | Lane {row['lane_id']} ({row['lane_type']})")

inspect_csv("traffic_ai/output/violations_log.csv")
```

---

## Checklist debug khi có vấn đề

```
Video không mở được?
    → Kiểm tra đường dẫn, tên file (khoảng trắng)

Polygon sai?
    → Re-calibrate với pick_road_poly.py

Quá nhiều/ít vi phạm?
    → Điều chỉnh ENFORCE_Y_MIN_NORM

Track không ổn định?
    → Giảm iou_threshold trong SimpleTracker

CSV rỗng?
    → Kiểm tra LANE_TYPES và violation_logged

Chạy chậm?
    → Dùng yolov8n.pt, giảm DISPLAY_SCALE
```
