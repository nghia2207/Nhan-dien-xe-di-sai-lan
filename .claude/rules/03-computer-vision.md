# Rule 03 — Computer Vision & YOLO Patterns

## YOLO Model Loading

### Pattern chuẩn

```python
from ultralytics import YOLO

# Load model (đường dẫn tương đối từ project root hoặc tuyệt đối)
model = YOLO(os.path.join(BASE_DIR, "..", "yolov8n.pt"))

# Inference trên frame
results = model(
    frame,
    conf=0.4,        # Confidence threshold
    iou=0.5,         # NMS IoU threshold
    classes=[2, 3, 5, 7],  # car, motorcycle, bus, truck (COCO IDs)
    verbose=False,   # Tắt log mỗi frame
)[0]
```

### Classes filter — COCO IDs

```python
# COCO class IDs cho phương tiện giao thông
VEHICLE_CLASS_IDS = [2, 3, 5, 7]
VEHICLE_CLASS_NAMES = {
    2: "car",
    3: "motorbike",   # COCO gọi là "motorcycle", ta remap thành "motorbike"
    5: "bus",
    7: "truck",
}

# Remap class name khi xử lý kết quả
def normalize_class_name(raw_name: str) -> str:
    return "motorbike" if raw_name == "motorcycle" else raw_name
```

### Trích xuất bounding box từ kết quả YOLO

```python
for box in results.boxes:
    cls_id = int(box.cls[0])
    conf = float(box.conf[0])
    x1, y1, x2, y2 = map(int, box.xyxy[0])

    class_name = normalize_class_name(results.names[cls_id])
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2  # Tâm bbox
```

---

## SimpleTracker (IOU-based)

Dự án dùng tracker tự implement, không dùng thư viện ngoài cho tracking.

### Nguyên tắc

- Gán `track_id` ổn định qua các frame dựa trên IoU của bounding boxes
- Xe mới (IoU thấp với mọi track hiện có) → tạo track_id mới
- Track không xuất hiện quá `MAX_AGE` frames → xóa

### Pattern chuẩn

```python
class SimpleTracker:
    def __init__(self, max_age: int = 30, iou_threshold: float = 0.3):
        self.tracks: Dict[int, dict] = {}
        self.next_id: int = 1
        self.max_age = max_age
        self.iou_threshold = iou_threshold

    def update(self, detections: List[Tuple]) -> List[dict]:
        """
        Args:
            detections: List of (x1, y1, x2, y2, class_name, conf)
        Returns:
            List of matched tracks with track_id added
        """
        ...

def compute_iou(bbox1, bbox2) -> float:
    """Tính IoU giữa 2 bounding box (x1, y1, x2, y2)."""
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])

    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
    area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
    union = area1 + area2 - inter

    return inter / union if union > 0 else 0.0
```

---

## Road Polygon & Lane Geometry

### Quy ước tọa độ chuẩn hóa (normalized)

- Tất cả tọa độ polygon lưu dạng **tỉ lệ 0.0–1.0** (không phải pixel)
- Chuyển sang pixel khi render: `px = norm_x * frame_width`

```python
# Chuẩn hóa → pixel
def norm_to_pixel(norm_pt, frame_w, frame_h):
    return (int(norm_pt[0] * frame_w), int(norm_pt[1] * frame_h))

# Pixel → chuẩn hóa
def pixel_to_norm(px_pt, frame_w, frame_h):
    return (px_pt[0] / frame_w, px_pt[1] / frame_h)
```

### Thứ tự điểm trong ROAD_POLY_NORM (quan trọng!)

```
ROAD_POLY_NORM = [
    left_bottom,   # [0] — góc trái phía dưới (gần camera)
    right_bottom,  # [1] — góc phải phía dưới (gần camera)
    right_top,     # [2] — góc phải phía trên (xa camera)
    left_top,      # [3] — góc trái phía trên (xa camera)
]
```

> ⚠️ Thứ tự này khác với polygon thông thường. Không thay đổi thứ tự điểm.

### Linear interpolation để sinh làn

```python
def lerp(p1, p2, t: float):
    """Nội suy tuyến tính giữa 2 điểm."""
    return (p1[0] + (p2[0] - p1[0]) * t,
            p1[1] + (p2[1] - p1[1]) * t)
```

### Kiểm tra điểm trong polygon

```python
# Dùng OpenCV — trả về dương nếu trong, 0 nếu trên cạnh, âm nếu ngoài
poly_px = np.array([norm_to_pixel(p, fw, fh) for p in lane["poly_norm"]], dtype=np.int32)
result = cv2.pointPolygonTest(poly_px, (cx, cy), measureDist=False)
is_inside = result >= 0
```

---

## Vẽ overlay (Visual Rendering)

### Màu sắc chuẩn (BGR cho OpenCV)

```python
COLOR_LANE_OK   = (0, 255, 0)    # Xanh lá — xe đúng làn
COLOR_LANE_WARN = (0, 165, 255)  # Cam — không xác định được làn
COLOR_VIOLATION = (0, 0, 255)    # Đỏ — xe sai làn (WRONG LANE)
COLOR_LANE_FILL = (255, 255, 0)  # Vàng — polygon làn (fill mờ)
COLOR_TEXT_HUD  = (255, 255, 255) # Trắng — text HUD
```

### Vẽ polygon làn có transparency

```python
def draw_lane_overlay(frame, lane_polys_px, alpha=0.25):
    overlay = frame.copy()
    for lane in lane_polys_px:
        pts = np.array(lane["poly_px"], dtype=np.int32)
        cv2.fillPoly(overlay, [pts], COLOR_LANE_FILL)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
```

### HUD (Head-Up Display) — góc trái màn hình

```python
def draw_hud(frame, frame_count, time_sec, n_vehicles, n_violations):
    lines = [
        f"Frame: {frame_count}",
        f"Time:  {time_sec:.2f}s",
        f"Vehicles:   {n_vehicles}",
        f"Violations: {n_violations}",
    ]
    y = 30
    for line in lines:
        cv2.putText(frame, line, (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                    COLOR_TEXT_HUD, 2, cv2.LINE_AA)
        y += 28
```

---

## Display & Scale

```python
DISPLAY_SCALE = 0.6  # Hiển thị ở 60% kích thước gốc

# Áp dụng khi hiển thị (không resize frame gốc để tính toán)
display_frame = cv2.resize(frame, (0, 0), fx=DISPLAY_SCALE, fy=DISPLAY_SCALE)
cv2.imshow("ITS - Lane Violation Detection", display_frame)

# Thoát bằng phím 'q'
if cv2.waitKey(1) & 0xFF == ord('q'):
    break
```

---

## Performance tips

| Kỹ thuật | Ghi chú |
|---------|---------|
| `verbose=False` trong YOLO | Tắt log per-frame, tăng FPS đáng kể |
| `DISPLAY_SCALE = 0.5~0.7` | Resize chỉ khi hiển thị, giữ gốc để xử lý |
| `classes=[2,3,5,7]` | Lọc sớm bằng class filter thay vì post-process |
| `conf=0.4` | Threshold đủ cao để loại false detection |
| `cv2.waitKey(1)` | Không dùng `waitKey(0)` trong video loop |
| YOLO model nhỏ nhất | `yolov8n.pt` cho CPU, `yolov8s.pt` cho demo mượt |
