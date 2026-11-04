# CLAUDE.md — ITS Intelligent Lane Violation Detection

> **Dành cho Claude Code và AI assistants**: Đây là file hướng dẫn chính cho dự án.
> Mọi quy tắc chi tiết được tách thành các file riêng biệt trong `.claude/rules/`.

---

## Tổng quan dự án

**Tên dự án**: Intelligent Lane Violation Detection System  
**Mục tiêu**: Phát hiện xe đi sai làn đường theo thời gian thực bằng YOLOv8 + Computer Vision  
**Ngôn ngữ chính**: Python 3.9+  
**Framework AI**: Ultralytics YOLOv8 / YOLOv11  

---

## Cấu trúc rules (`.claude/rules/`)

| File | Chủ đề | Mô tả ngắn |
|------|--------|------------|
| [`01-project-overview.md`](.claude/rules/01-project-overview.md) | Tổng quan dự án | Kiến trúc, module, luồng xử lý chính |
| [`02-code-style.md`](.claude/rules/02-code-style.md) | Phong cách code | Naming, structure, Python conventions |
| [`03-computer-vision.md`](.claude/rules/03-computer-vision.md) | Computer Vision | YOLO, OpenCV, lane detection patterns |
| [`04-configuration.md`](.claude/rules/04-configuration.md) | Cấu hình | Tham số calibration, polygon, video |
| [`05-data-logging.md`](.claude/rules/05-data-logging.md) | Dữ liệu & Logging | CSV output, evidence saving, logging |
| [`06-workflow.md`](.claude/rules/06-workflow.md) | Quy trình làm việc | Bước chạy, debug, calibrate hệ thống |
| [`07-testing-debugging.md`](.claude/rules/07-testing-debugging.md) | Testing & Debug | Cách kiểm tra, xử lý lỗi phổ biến |

---

## Lệnh khởi chạy nhanh

```bash
# Bước 1: Chọn vùng mặt đường
python traffic_ai/pick_road_poly.py

# Bước 2: Chọn vạch phân làn
python traffic_ai/pick_lane_boundaries.py

# Bước 3: Chạy phát hiện vi phạm
python traffic_ai/detect_lanes_roadpoly.py

# Chạy giao diện demo đầy đủ
python traffic_ai/demo_app.py
```
