# Rule 05 — Dữ liệu & Logging

## CSV Violation Log

### Vị trí file output

```
traffic_ai/output/violations_log.csv
traffic_ai/output/evidence/          ← Ảnh bằng chứng xe vi phạm
```

### Schema CSV

```csv
frame,time_sec,track_id,class,lane_id,lane_type
240,8.00,12,car,3,motorbike
301,10.03,7,car,3,motorbike
```

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| `frame` | int | Số thứ tự frame trong video |
| `time_sec` | float (2dp) | Thời gian tương ứng (giây) |
| `track_id` | int | ID duy nhất của xe được track |
| `class` | str | Loại xe (`car`, `bus`, `truck`, `motorbike`) |
| `lane_id` | int | ID làn xe đang ở (1-indexed) |
| `lane_type` | str | Loại làn đó được phép cho xe nào |

### Pattern ghi CSV

```python
import csv

def init_csv_writer(csv_path: str):
    """Tạo CSV với header."""
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["frame", "time_sec", "track_id", "class", "lane_id", "lane_type"])

def log_violation(csv_path: str, frame: int, time_sec: float,
                  track_id: int, class_name: str, lane_id: int, lane_type: str):
    """Append 1 dòng vi phạm vào CSV."""
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([frame, f"{time_sec:.2f}", track_id, class_name, lane_id, lane_type])
```

---

## Deduplication Logic

Mỗi xe chỉ được log **một lần** (tránh spam cùng track_id qua nhiều frame):

```python
violation_logged: set = set()  # Tập track_id đã log

def should_log_violation(track_id: int) -> bool:
    if track_id in violation_logged:
        return False
    violation_logged.add(track_id)
    return True
```

> **Lý do**: Một xe vi phạm sẽ xuất hiện trong nhiều frame liên tiếp.
> Log 1 lần là đủ để thống kê số xe, không phải số frame.

---

## Evidence Saving

### Cấu trúc thư mục evidence

```
output/evidence/
├── track_12_car_frame240.jpg
├── track_7_car_frame301.jpg
└── track_23_motorbike_frame445.jpg
```

### Naming convention

```python
def get_evidence_filename(track_id: int, class_name: str, frame: int) -> str:
    return f"track_{track_id}_{class_name}_frame{frame}.jpg"
```

### Pattern lưu evidence

```python
def save_evidence_crop(
    frame: np.ndarray,
    bbox: Tuple[int, int, int, int],
    track_id: int,
    class_name: str,
    frame_count: int,
    evidence_dir: str,
    padding: float = CROP_PADDING,
    save_fullframe: bool = SAVE_FULLFRAME,
):
    x1, y1, x2, y2 = bbox
    h, w = frame.shape[:2]

    if save_fullframe:
        crop = frame
    else:
        # Crop với padding
        pad_x = int((x2 - x1) * padding)
        pad_y = int((y2 - y1) * padding)
        cx1 = max(0, x1 - pad_x)
        cy1 = max(0, y1 - pad_y)
        cx2 = min(w, x2 + pad_x)
        cy2 = min(h, y2 + pad_y)
        crop = frame[cy1:cy2, cx1:cx2]

    filename = f"track_{track_id}_{class_name}_frame{frame_count}.jpg"
    save_path = os.path.join(evidence_dir, filename)
    cv2.imwrite(save_path, crop, [cv2.IMWRITE_JPEG_QUALITY, 85])
```

---

## Print Logging (Console)

Dùng prefix chuẩn để dễ filter:

```python
# Thông tin
print(f"[INFO] Đã mở video: {VIDEO_SOURCE}")
print(f"[INFO] Model loaded: {model_path}")

# Cảnh báo (không critical)
print(f"[WARN] Xe track_id={track_id} không xác định được làn")

# Vi phạm
print(f"[VIOLATION] Frame={frame} | track={track_id} | {class_name} → Lane {lane_id} ({lane_type})")

# Lỗi
print(f"[ERROR] Không thể mở video: {VIDEO_SOURCE}")

# Debug (bật/tắt theo flag)
DEBUG = False
if DEBUG:
    print(f"[DEBUG] bbox={bbox}, center=({cx},{cy}), lane={lane_id}")
```

---

## Thống kê cuối session

```python
def print_session_summary(violation_logged: set, frame_count: int, fps: float):
    total_time = frame_count / fps if fps > 0 else 0
    print("\n" + "="*50)
    print(f"[SUMMARY] Kết thúc phiên phát hiện")
    print(f"  Tổng số frame: {frame_count}")
    print(f"  Thời gian video: {total_time:.1f}s")
    print(f"  Số xe vi phạm: {len(violation_logged)}")
    print(f"  Log CSV: {VIOLATION_CSV}")
    print(f"  Evidence: {EVIDENCE_DIR}")
    print("="*50)
```

---

## Quy tắc output

| Quy tắc | Lý do |
|---------|-------|
| Luôn dùng `encoding="utf-8"` khi mở file CSV | Tránh lỗi tiếng Việt trên Windows |
| Dùng `newline=""` khi mở CSV với `csv.writer` | Tránh dòng trắng thừa trên Windows |
| Tạo thư mục output trước khi ghi (`os.makedirs`) | Tránh `FileNotFoundError` |
| Không xóa CSV cũ mà không có backup | Dữ liệu vi phạm có giá trị |
| JPEG quality = 85 cho evidence | Cân bằng chất lượng và dung lượng |
