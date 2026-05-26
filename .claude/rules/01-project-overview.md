# Rule 01 — Tổng quan dự án ITS

## Mục tiêu hệ thống

Hệ thống phát hiện vi phạm sai làn đường (Intelligent Traffic System - ITS) nhằm:

1. **Nhận diện xe** theo thời gian thực qua camera/video
2. **Xác định làn đường** dựa trên polygon mặt đường do người dùng calibrate
3. **Kiểm tra luật làn** — xe có đi đúng làn dành cho loại phương tiện đó không
4. **Ghi log vi phạm** ra CSV để phân tích và báo cáo
5. **Lưu bằng chứng** (ảnh crop xe vi phạm) để xác minh

---

## Kiến trúc module

```
ITS-main/
├── CLAUDE.md                          # Hướng dẫn chính cho AI
├── .claude/rules/                     # Bộ rule chi tiết
├── README.md                          # Tài liệu người dùng
│
├── traffic_ai/                        # Source code chính
│   ├── detect_lanes_roadpoly.py       # ⭐ Pipeline chính (production)
│   ├── demo_app.py                    # Giao diện demo đầy đủ (Tkinter)
│   ├── auto_calibrate_lanes.py        # Auto-detect làn (experimental)
│   ├── auto_lanes_config.json         # Config cho auto calibration
│   │
│   ├── pick_road_poly.py              # Tool chọn polygon mặt đường
│   ├── pick_lane_boundaries.py        # Tool chọn vạch phân làn
│   │
│   ├── detect_basic.py                # Prototype ban đầu (đơn giản)
│   ├── detect_lanes.py                # Version cũ hơn
│   ├── detect_tracking.py             # Phiên bản chỉ tracking
│   ├── detect_lanes_bytetrack_adaptive_mask.py  # Experimental (ByteTrack)
│   ├── training_evaluation_demo.py    # Demo huấn luyện/đánh giá model
│   │
│   ├── data/
│   │   └── video/                     # Video đầu vào (test 1.mp4, test 3.mp4, ...)
│   └── output/
│       ├── violations_log.csv         # Log vi phạm (tự sinh)
│       └── evidence/                  # Ảnh bằng chứng vi phạm (tự sinh)
│
├── yolov8n.pt                         # Model YOLO nhỏ (nhanh, CPU)
├── yolov8s.pt                         # Model YOLO nhỏ-vừa
├── yolo11n.pt                         # YOLOv11 nano
├── yolo11s.pt                         # YOLOv11 small
├── rtdetr-l.pt                        # RT-DETR large (thử nghiệm)
└── datasets/                          # Dữ liệu training (nếu có)
```

---

## Luồng xử lý chính (`detect_lanes_roadpoly.py`)

```
Video Frame
    │
    ▼
YOLOv8 Detection
    │  (car, bus, truck, motorbike)
    ▼
SimpleTracker (IOU-based)
    │  Gán track_id ổn định cho mỗi xe
    ▼
Lane Assignment
    │  Tính tọa độ tâm bbox → xác định xe thuộc làn nào
    │  Dùng cv2.pointPolygonTest với polygon làn
    ▼
Violation Check
    │  So sánh loại xe với LANE_TYPES[lane_id]
    │  Nếu không khớp → WRONG LANE
    ▼
Evidence Saving
    │  Crop ảnh xe vi phạm → lưu vào output/evidence/
    ▼
CSV Logging
    │  Ghi frame, time, track_id, class, lane_id, lane_type
    ▼
Visual Overlay
    │  Vẽ polygon làn (màu xanh/đỏ), bbox xe, HUD thống kê
    ▼
Display (cv2.imshow)
```

---

## File entry point theo use case

| Tình huống | File cần chạy |
|-----------|--------------|
| Calibrate mặt đường mới | `pick_road_poly.py` → `pick_lane_boundaries.py` |
| Chạy phát hiện vi phạm | `detect_lanes_roadpoly.py` |
| Demo giao diện đầy đủ | `demo_app.py` |
| Test tracking đơn giản | `detect_tracking.py` |
| Đánh giá model | `training_evaluation_demo.py` |
| Auto-calibrate (thử nghiệm) | `auto_calibrate_lanes.py` |

---

## Model YOLO được sử dụng

| Model | Kích thước | Tốc độ | Độ chính xác | Khuyến nghị |
|-------|-----------|--------|-------------|-------------|
| `yolov8n.pt` | 6 MB | ⚡⚡⚡ | ★★☆ | Demo CPU |
| `yolov8s.pt` | 22 MB | ⚡⚡ | ★★★ | Balanced |
| `yolo11n.pt` | 5.6 MB | ⚡⚡⚡ | ★★☆ | Thử nghiệm |
| `yolo11s.pt` | 19 MB | ⚡⚡ | ★★★ | Thử nghiệm |
| `rtdetr-l.pt` | 66 MB | ⚡ | ★★★★ | GPU only |

> **Mặc định**: Dùng `yolov8n.pt` cho phát hiện xe trên CPU.

---

## Các lớp phương tiện được nhận diện

```python
VEHICLE_CLASSES = {
    "car":        2,   # COCO class ID
    "motorbike":  3,   # = motorcycle
    "bus":        5,
    "truck":      7,
}
```

> **Lưu ý**: YOLO COCO dùng `motorcycle` (không phải `motorbike`). Code đã có mapping xử lý điều này.
