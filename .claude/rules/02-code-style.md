# Rule 02 — Phong cách code (Code Style)

## Nguyên tắc chung

- **Ngôn ngữ**: Python 3.9+
- **Encoding**: UTF-8 cho mọi file
- **Style guide**: PEP 8 (có điều chỉnh cho computer vision)
- **Comment**: Song ngữ Việt-Anh được chấp nhận, ưu tiên tiếng Anh cho logic phức tạp
- **Không dùng** type annotations ở mức bắt buộc, nhưng nên dùng cho function signatures

---

## Quy ước đặt tên

### Constants — `UPPER_SNAKE_CASE`

```python
# ✅ Đúng
VIDEO_SOURCE = "data/video/test 1.mp4"
ROAD_POLY_NORM = [(0.225, 0.958), ...]
BOUNDARY_TS = [0.0, 0.322, 0.628, 1.0]
LANE_TYPES = ["motorbike", "car", "car"]
ENFORCE_Y_MIN_NORM = 0.65
DISPLAY_SCALE = 0.6
SAVE_EVIDENCE = True

# ❌ Sai
videoSource = "data/video/test.mp4"
road_poly = [(0.225, 0.958)]
```

### Functions — `lower_snake_case`

```python
# ✅ Đúng
def generate_lane_polys_norm(road_poly_norm, boundary_ts, lane_types):
def lerp(p1, p2, t: float):
def point_in_polygon(point, polygon):
def save_evidence_crop(frame, bbox, track_id, class_name):

# ❌ Sai
def GenerateLanePolys():
def generateLanePolys():
```

### Variables — `lower_snake_case`

```python
# ✅ Đúng
track_id = 12
lane_id = 2
bbox_center = (cx, cy)
frame_count = 0
violation_set = set()

# ❌ Sai
trackID = 12
laneId = 2
```

### Classes — `PascalCase`

```python
# ✅ Đúng
@dataclass
class TrackedVehicle:
    track_id: int
    class_name: str
    bbox: Tuple[int, int, int, int]

class SimpleTracker:
    ...
```

### Dataclasses

```python
# ✅ Pattern chuẩn
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional

@dataclass
class LaneViolation:
    frame: int
    time_sec: float
    track_id: int
    class_name: str
    lane_id: int
    lane_type: str
```

---

## Cấu trúc file Python

Thứ tự bắt buộc trong mỗi file:

```python
# 1. Standard library imports
import os
import csv
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional

# 2. Third-party imports
import cv2
import numpy as np
from ultralytics import YOLO

# 3. ---- CONFIGURATION BLOCK ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_SOURCE = ...
DISPLAY_SCALE = ...
# ... các hằng số khác ...

# 4. ---- HELPER FUNCTIONS ----
def lerp(p1, p2, t):
    ...

# 5. ---- CORE CLASSES ----
class SimpleTracker:
    ...

# 6. ---- MAIN LOGIC ----
def main():
    ...

if __name__ == "__main__":
    main()
```

---

## Comments và Docstrings

### Comment inline

```python
# ✅ Giải thích "tại sao", không phải "cái gì"
ENFORCE_Y_MIN_NORM = 0.65  # Chỉ tính vi phạm khi xe ở vùng gần camera (giảm false positive)

# ❌ Thừa
x = x + 1  # tăng x lên 1
```

### Docstring cho function quan trọng

```python
def generate_lane_polys_norm(road_poly_norm, boundary_ts, lane_types):
    """
    Sinh danh sách polygon làn từ polygon mặt đường và boundary ratios.

    Args:
        road_poly_norm: List[Tuple] - 4 điểm [left_bottom, right_bottom, right_top, left_top]
                        tọa độ chuẩn hóa 0..1
        boundary_ts: List[float] - Tỉ lệ vị trí vạch phân làn [0.0, ..., 1.0]
        lane_types: List[str] - Loại xe được phép trong mỗi làn

    Returns:
        List[Dict] - Danh sách làn với keys: id, name, type, poly_norm
    """
```

---

## Xử lý lỗi

```python
# ✅ Fail-fast với thông báo rõ ràng
cap = cv2.VideoCapture(VIDEO_SOURCE)
if not cap.isOpened():
    raise FileNotFoundError(f"Không thể mở video: {VIDEO_SOURCE}")

# ✅ Validate input early
assert len(road_poly_norm) == 4, "ROAD_POLY_NORM phải có đúng 4 điểm"
assert len(boundary_ts) >= 2, "BOUNDARY_TS phải có ít nhất 2 giá trị"

# ✅ Graceful skip với log
try:
    lane_id = find_lane(center_point, lanes)
except Exception as e:
    print(f"[WARN] Bỏ qua frame {frame_count}: {e}")
    continue
```

---

## Anti-patterns cần tránh

```python
# ❌ Magic numbers không có tên
if cy > frame_h * 0.65:  # 0.65 là gì?
    check_violation(...)

# ✅ Dùng constant
if cy > frame_h * ENFORCE_Y_MIN_NORM:
    check_violation(...)

# ❌ Hardcode path tuyệt đối
VIDEO_SOURCE = "C:/Users/ten/video.mp4"

# ✅ Dùng BASE_DIR
VIDEO_SOURCE = os.path.join(BASE_DIR, "data", "video", "test.mp4")

# ❌ Bắt exception quá rộng mà không làm gì
try:
    result = model(frame)
except:
    pass

# ✅ Log cụ thể
try:
    result = model(frame)
except Exception as e:
    print(f"[ERROR] YOLO inference failed: {e}")
    continue
```
