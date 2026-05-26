# Rule 04 — Cấu hình & Calibration

## Tổng quan

Cấu hình của hệ thống được chia thành 2 loại:

1. **Static config** — Hằng số ở đầu file Python (video path, model, scale)
2. **Calibration data** — Tọa độ polygon và boundary từ công cụ pick_*.py

---

## Các hằng số cấu hình chính

### Video & Paths

```python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_SOURCE = os.path.join(BASE_DIR, "data", "video", "test 3.mp4")

OUTPUT_DIR   = os.path.join(BASE_DIR, "output")
EVIDENCE_DIR = os.path.join(OUTPUT_DIR, "evidence")
VIOLATION_CSV = os.path.join(OUTPUT_DIR, "violations_log.csv")

os.makedirs(EVIDENCE_DIR, exist_ok=True)
```

> ✅ **Luôn dùng `os.path.join` và `BASE_DIR`** — không bao giờ hardcode đường dẫn tuyệt đối.

### Display

```python
DISPLAY_SCALE = 0.6       # Tỉ lệ hiển thị (0.5 → 0.8), không ảnh hưởng xử lý
```

### Detection ROI

```python
ENFORCE_Y_MIN_NORM = 0.65  # Chỉ kiểm tra vi phạm khi cy > frame_h * 0.65
                            # Giảm false positive ở vùng xa camera
                            # Điều chỉnh: 0.45 (rộng) → 0.75 (chặt)
```

### Evidence

```python
SAVE_EVIDENCE  = True     # Có lưu ảnh bằng chứng không
SAVE_FULLFRAME = False    # False → chỉ crop bbox xe; True → lưu cả frame
CROP_PADDING   = 0.25     # Padding quanh bbox khi crop (25%)
```

---

## Calibration Data

### ROAD_POLY_NORM

Tọa độ 4 góc của mặt đường (tỉ lệ 0.0–1.0, từ pick_road_poly.py):

```python
ROAD_POLY_NORM = [
    (0.2250, 0.9583),   # left_bottom  — góc trái gần camera
    (0.7417, 0.9704),   # right_bottom — góc phải gần camera
    (0.5620, 0.4481),   # right_top    — góc phải xa camera
    (0.4354, 0.4574),   # left_top     — góc trái xa camera
]
```

> ⚠️ **Giá trị ví dụ trên chỉ đúng với video "test 3.mp4"**.
> Mỗi video cần calibrate lại bằng `pick_road_poly.py`.

### BOUNDARY_TS

Tỉ lệ vị trí vạch chia làn (từ pick_lane_boundaries.py):

```python
# Ví dụ: 3 làn → cần 4 giá trị boundary
BOUNDARY_TS = [0.0000, 0.3224, 0.6289, 1.0000]
#              ^start  ^lane1-2 ^lane2-3 ^end
```

Quy tắc:
- Luôn bắt đầu bằng `0.0000` và kết thúc bằng `1.0000`
- Số làn = `len(BOUNDARY_TS) - 1`
- Giá trị từ trái sang phải (từ lề trái đường)

### LANE_TYPES

Loại phương tiện được phép cho mỗi làn:

```python
# 3 làn: [làn 1, làn 2, làn 3]
LANE_TYPES = ["motorbike", "car", "car"]

# Giá trị hợp lệ:
# "car"       → chỉ ô tô, xe tải, xe buýt
# "motorbike" → chỉ xe máy
# "any"       → mọi phương tiện (không kiểm tra vi phạm)
```

---

## Quy tắc khi thay đổi cấu hình

### ✅ Được phép

```python
# Đổi video test
VIDEO_SOURCE = os.path.join(BASE_DIR, "data", "video", "test 2.mp4")

# Điều chỉnh ROI để giảm/tăng false positive
ENFORCE_Y_MIN_NORM = 0.55

# Tắt lưu evidence để tăng tốc
SAVE_EVIDENCE = False

# Thay model
model = YOLO(os.path.join(BASE_DIR, "..", "yolov8s.pt"))
```

### ❌ Không được làm

```python
# Không tự ý đặt ROAD_POLY_NORM/BOUNDARY_TS mới mà không calibrate
ROAD_POLY_NORM = [(0, 0), (1, 0), (1, 1), (0, 1)]  # Sai! Không phù hợp với video thực

# Không hardcode số lane type không đúng với số boundary
BOUNDARY_TS = [0.0, 0.5, 1.0]  # 2 làn
LANE_TYPES = ["car", "car", "car"]  # Sai! Phải có 2 phần tử
```

---

## JSON Config (auto_lanes_config.json)

File `auto_lanes_config.json` dùng cho module `auto_calibrate_lanes.py`:

```json
{
  "video_source": "data/video/test 3.mp4",
  "road_poly_norm": [
    [0.225, 0.958],
    [0.741, 0.970],
    [0.562, 0.448],
    [0.435, 0.457]
  ],
  "boundary_ts": [0.0, 0.322, 0.628, 1.0],
  "lane_types": ["motorbike", "car", "car"],
  "enforce_y_min_norm": 0.65,
  "display_scale": 0.6,
  "save_evidence": true
}
```

Khi đọc config JSON:

```python
import json

def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    # Chuyển list → tuple cho tọa độ
    config["road_poly_norm"] = [tuple(p) for p in config["road_poly_norm"]]
    return config
```

---

## Checklist khi thêm video mới

- [ ] Chạy `pick_road_poly.py` → lấy `ROAD_POLY_NORM` mới
- [ ] Chạy `pick_lane_boundaries.py` → lấy `BOUNDARY_TS` mới
- [ ] Xác nhận số `LANE_TYPES` = số làn (= `len(BOUNDARY_TS) - 1`)
- [ ] Điều chỉnh `ENFORCE_Y_MIN_NORM` theo góc camera
- [ ] Điều chỉnh `DISPLAY_SCALE` nếu cần
- [ ] Cập nhật `VIDEO_SOURCE` trỏ đến video mới
