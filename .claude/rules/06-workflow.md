# Rule 06 — Quy trình làm việc (Workflow)

## Quy trình chuẩn cho video mới

```
Video mới
   │
   ▼
[Bước 1] pick_road_poly.py
   │  → Click 4 điểm biên mặt đường
   │  → Copy ROAD_POLY_NORM vào detect_lanes_roadpoly.py
   │
   ▼
[Bước 2] pick_lane_boundaries.py
   │  → Click vạch phân làn (N-1 lần cho N làn)
   │  → Copy BOUNDARY_TS vào detect_lanes_roadpoly.py
   │
   ▼
[Bước 3] Cập nhật LANE_TYPES
   │  → Xác định loại xe được phép ở mỗi làn
   │  → Ví dụ: ["motorbike", "car", "car"]
   │
   ▼
[Bước 4] detect_lanes_roadpoly.py
   │  → Chạy thử, quan sát overlay
   │  → Fine-tune ENFORCE_Y_MIN_NORM nếu quá nhiều false positive
   │
   ▼
[Bước 5] Kiểm tra output
      → violations_log.csv có dữ liệu hợp lý không?
      → evidence/ có ảnh xe vi phạm không?
```

---

## Lệnh chạy từng bước

### Môi trường

```bash
# Tạo và kích hoạt virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Linux/Mac

# Cài dependencies
pip install ultralytics opencv-python numpy
```

### Bước 1 — Chọn mặt đường

```bash
cd "d:\Chuyên đề hệ thống giao thông thông minh\ITS-main (1)"
python traffic_ai/pick_road_poly.py
```

**Hướng dẫn click**: Click **theo thứ tự** — trái dưới → phải dưới → phải trên → trái trên  
**Output**: In ra terminal, copy vào `detect_lanes_roadpoly.py`

### Bước 2 — Chọn vạch làn

```bash
python traffic_ai/pick_lane_boundaries.py
```

**Hướng dẫn**: Click vào vị trí **vạch kẻ đường** chia các làn (từ trái sang phải)  
**Output**: In ra terminal, copy vào `detect_lanes_roadpoly.py`

### Bước 3 — Chạy phát hiện chính

```bash
python traffic_ai/detect_lanes_roadpoly.py
```

**Thoát**: Nhấn `q` để dừng

### Chạy giao diện demo

```bash
python traffic_ai/demo_app.py
```

---

## Quy trình phát triển tính năng mới

```
1. Đọc rule liên quan trong .claude/rules/
   │
   ▼
2. Tạo branch / backup file cũ
   │
   ▼
3. Implement trong file tương ứng
   │  - Thêm logic trong detect_lanes_roadpoly.py (production)
   │  - Hoặc tạo file prototype mới (detect_lanes_*.py)
   │
   ▼
4. Test với video ngắn
   │  - Kiểm tra overlay có đúng không
   │  - Kiểm tra CSV output
   │
   ▼
5. Cập nhật documentation nếu thay đổi behavior
```

---

## Quy trình fine-tune calibration

```
Quá nhiều false positive?
   ├── Tăng ENFORCE_Y_MIN_NORM (ví dụ: 0.65 → 0.70)
   ├── Tăng conf threshold YOLO (ví dụ: 0.4 → 0.5)
   └── Kiểm tra lại ROAD_POLY_NORM (polygon có bao đủ mặt đường không?)

Bỏ sót vi phạm?
   ├── Giảm ENFORCE_Y_MIN_NORM (ví dụ: 0.65 → 0.55)
   ├── Giảm conf threshold YOLO (ví dụ: 0.4 → 0.3)
   └── Kiểm tra lại BOUNDARY_TS (vạch có đúng vị trí không?)

Xe không được track ổn định?
   ├── Tăng max_age trong SimpleTracker
   ├── Giảm iou_threshold (0.3 → 0.2) nếu xe di chuyển nhanh
   └── Chuyển sang model lớn hơn (yolov8s → yolov8m)
```

---

## Git Workflow

```bash
# Trước khi sửa calibration data
git add -A
git commit -m "backup: calibration cho test 3.mp4"

# Sau khi calibrate xong video mới
git add traffic_ai/detect_lanes_roadpoly.py
git commit -m "calibrate: ROAD_POLY + BOUNDARY_TS cho test 5.mp4"

# Commit convention
# feat:     Tính năng mới
# fix:      Sửa lỗi
# calibrate: Cập nhật tham số calibration
# refactor: Tái cấu trúc code
# docs:     Cập nhật tài liệu
# chore:    Công việc phụ (deps, config)
```

---

## File nào KHÔNG được sửa tùy tiện

| File | Lý do |
|------|-------|
| `pick_road_poly.py` | Tool UI đã ổn định |
| `pick_lane_boundaries.py` | Tool UI đã ổn định |
| `auto_lanes_config.json` | Config của module auto-calibrate riêng biệt |
| `violation_log.csv` (ở root) | File output thực tế — không chỉnh sửa thủ công |

---

## Checklist trước khi commit

- [ ] Code chạy không lỗi với video hiện tại
- [ ] CSV output có dữ liệu hợp lý
- [ ] Không có đường dẫn tuyệt đối hardcode
- [ ] Không có API key hay thông tin nhạy cảm
- [ ] LANE_TYPES khớp với số làn trong BOUNDARY_TS
- [ ] Comment đã cập nhật nếu logic thay đổi
