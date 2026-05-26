#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║    DEMO ỨNG DỤNG HỆ THỐNG PHÁT HIỆN VI PHẠM GIAO THÔNG (ITS)             ║
║    Application Demo: Intelligent Traffic Violation Detection System        ║
║                                                                            ║
║    Chương 4.5: Xây dựng ứng dụng demo dễ hình dung bằng lời văn           ║
║    Module: Interactive Visual Demo with Text-based Visualization          ║
║                                                                            ║
║    Tác giả: Sinh viên Chuyên đề HT Giao thông thông minh                 ║
║    Ngày: 2026                                                             ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import csv
import time
import random
import json
import threading
from datetime import datetime
from collections import defaultdict, deque
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_CYAN = '\033[46m'
    BG_GRAY = '\033[47m'


class VehicleType(Enum):
    """Loại phương tiện"""
    MOTORCYCLE = "Xe máy"
    CAR = "Ô tô"
    BUS = "Xe buýt"
    TRUCK = "Xe tải"


class LaneType(Enum):
    """Loại làn đường"""
    LANE_1 = "Làn 1 (Xe máy)"
    LANE_2 = "Làn 2 (Xe máy)"
    LANE_3 = "Làn 3 (Ô tô)"
    LANE_4 = "Làn 4 (Ô tô)"


class ViolationType(Enum):
    """Loại vi phạm"""
    WRONG_LANE = "Sai làn"
    SPEEDING = "Vượt tốc độ"
    UNSAFE_TURN = "Rẽ không an toàn"
    SAFE = "Tuân thủ quy tắc"


@dataclass
class DetectionResult:
    """Kết quả phát hiện một frame"""
    frame_id: int
    timestamp: float
    vehicles: List['Vehicle'] = field(default_factory=list)
    processing_time: float = 0.0
    fps: float = 0.0
    vehicle_count: int = 0


@dataclass
class Vehicle:
    """Thông tin phương tiện"""
    track_id: int
    vehicle_type: VehicleType
    x: float
    y: float
    width: float
    height: float
    confidence: float
    frame_entered: int
    current_lane: Optional[LaneType] = None
    violations: List['Violation'] = field(default_factory=list)
    trajectory: deque = field(default_factory=lambda: deque(maxlen=30))
    
    def bottom_center(self) -> Tuple[float, float]:
        """Lấy điểm Bottom-Center (điểm tiếp xúc bánh xe với đường)"""
        return (self.x + self.width / 2, self.y + self.height)


@dataclass
class Violation:
    """Thông tin vi phạm"""
    violation_type: ViolationType
    frame_id: int
    timestamp: float
    lane_id: int
    confidence: float
    debounce_count: int = 0


class LaneConfiguration:
    """Cấu hình làn đường"""
    
    def __init__(self):
        # Làn 1 (Xe máy): 0-25%
        # Làn 2 (Xe máy): 25-50%
        # Làn 3 (Ô tô): 50-75%
        # Làn 4 (Ô tô): 75-100%
        self.lane_boundaries = [0.0, 0.25, 0.50, 0.75, 1.0]
        self.lane_types = [
            VehicleType.MOTORCYCLE,  # Lane 1
            VehicleType.MOTORCYCLE,  # Lane 2
            VehicleType.CAR,         # Lane 3
            VehicleType.CAR,         # Lane 4
        ]
        self.lanes_info = [
            LaneType.LANE_1,
            LaneType.LANE_2,
            LaneType.LANE_3,
            LaneType.LANE_4,
        ]
    
    def get_lane_for_position(self, position_ratio: float) -> Tuple[int, LaneType]:
        """
        Xác định làn đường từ tọa độ
        position_ratio: 0.0 (trái) -> 1.0 (phải)
        """
        for i in range(len(self.lane_boundaries) - 1):
            if self.lane_boundaries[i] <= position_ratio < self.lane_boundaries[i + 1]:
                return i, self.lanes_info[i]
        return 3, self.lanes_info[3]
    
    def is_allowed_vehicle(self, lane_id: int, vehicle_type: VehicleType) -> bool:
        """Kiểm tra xe có được phép chạy trên làn này không"""
        if lane_id >= len(self.lane_types):
            return True
        allowed_type = self.lane_types[lane_id]
        return vehicle_type == allowed_type


class ViolationDetector:
    """
    ╔════════════════════════════════════════════════════════════╗
    ║  MODULE 3: KIỂM TRA VI PHẠM (VIOLATION LOGIC)             ║
    ║                                                            ║
    ║  Cơ chế Dual-Check:                                       ║
    ║  1. Spatial Check: Kiểm tra không gian (vehicle ở làn nào?)║
    ║  2. Temporal Check: Kiểm tra thời gian (debouncing 3-5 frame) ║
    ╚════════════════════════════════════════════════════════════╝
    """
    
    def __init__(self, lanes: LaneConfiguration):
        self.lanes = lanes
        self.debounce_threshold = 3  # Frames to confirm violation
        self.vehicle_counters = defaultdict(int)
    
    def check_vehicle_violation(self, vehicle: Vehicle) -> Optional[Violation]:
        """
        SPATIAL CHECK + TEMPORAL CHECK
        Kiểm tra vi phạm với Debouncing
        """
        # SPATIAL CHECK: Lấy điểm Bottom-Center
        bottom_center_x, _ = vehicle.bottom_center()
        position_ratio = bottom_center_x / 1920.0  # Normalize to 0-1
        
        lane_id, lane_info = self.lanes.get_lane_for_position(position_ratio)
        vehicle.current_lane = lane_info
        
        # Kiểm tra loại xe có được phép ở làn này không
        is_allowed = self.lanes.is_allowed_vehicle(lane_id, vehicle.vehicle_type)
        
        if not is_allowed:
            # TEMPORAL CHECK: Debouncing
            self.vehicle_counters[vehicle.track_id] += 1
            
            if self.vehicle_counters[vehicle.track_id] >= self.debounce_threshold:
                return Violation(
                    violation_type=ViolationType.WRONG_LANE,
                    frame_id=0,
                    timestamp=time.time(),
                    lane_id=lane_id,
                    confidence=vehicle.confidence,
                    debounce_count=self.vehicle_counters[vehicle.track_id]
                )
        else:
            # Reset counter khi xe chạy đúng làn
            self.vehicle_counters[vehicle.track_id] = 0
        
        return None


class SimulatedYOLODetector:
    """
    ╔════════════════════════════════════════════════════════════╗
    ║  MODULE 1: PHÁT HIỆN (DETECTION)                         ║
    ║                                                            ║
    ║  Mô phỏng YOLO Detection:                                 ║
    ║  - Nhận vào: Frame từ video                               ║
    ║  - Xử lý: Chạy YOLO inference                            ║
    ║  - Xuất ra: Bounding boxes + Class labels                ║
    ╚════════════════════════════════════════════════════════════╝
    """
    
    def __init__(self, confidence_threshold=0.5):
        self.confidence_threshold = confidence_threshold
        self.frame_count = 0
    
    def detect(self, frame_id: int) -> List[Tuple]:
        """
        Mô phỏng YOLO detection
        Trả về danh sách: (x, y, w, h, class_id, confidence)
        """
        # Simulate detection on random positions
        detections = []
        num_vehicles = random.randint(2, 6)
        
        for i in range(num_vehicles):
            # Random position and size
            x = random.randint(100, 1820)
            y = random.randint(400, 1000)
            w = random.randint(40, 120)
            h = random.randint(50, 150)
            class_id = random.randint(0, 3)  # 4 vehicle types
            confidence = random.uniform(0.6, 0.99)
            
            if confidence >= self.confidence_threshold:
                detections.append((x, y, w, h, class_id, confidence))
        
        return detections


class SimulatedByteTracker:
    """
    ╔════════════════════════════════════════════════════════════╗
    ║  MODULE 2: THEO DÕI (TRACKING)                           ║
    ║                                                            ║
    ║  Mô phỏng ByteTrack:                                      ║
    ║  - Nhận vào: Bounding boxes từ YOLO                       ║
    ║  - Xử lý: Gán ID, tracking quỹ đạo                       ║
    ║  - Xuất ra: Vehicles with consistent IDs                 ║
    ╚════════════════════════════════════════════════════════════╝
    """
    
    def __init__(self):
        self.next_id = 0
        self.tracked_vehicles: Dict[int, Vehicle] = {}
        self.max_age = 30  # Frames to keep track without detection
    
    def update(self, detections: List[Tuple], frame_id: int) -> List[Vehicle]:
        """
        Update tracks with new detections
        detections: [(x, y, w, h, class_id, confidence), ...]
        """
        matched_tracks = set()
        updated_vehicles = []
        
        # Match detections to existing tracks (simple IOU matching)
        for det in detections:
            x, y, w, h, class_id, conf = det
            vehicle_types = [VehicleType.MOTORCYCLE, VehicleType.CAR, 
                           VehicleType.BUS, VehicleType.TRUCK]
            
            # Find closest existing track
            best_match = None
            best_iou = 0.0
            
            for track_id, vehicle in self.tracked_vehicles.items():
                if track_id in matched_tracks:
                    continue
                
                # Simple IOU calculation
                iou = self._calculate_iou(
                    (vehicle.x, vehicle.y, vehicle.width, vehicle.height),
                    (x, y, w, h)
                )
                
                if iou > best_iou and iou > 0.3:
                    best_iou = iou
                    best_match = track_id
            
            # Update existing track or create new one
            if best_match is not None:
                vehicle = self.tracked_vehicles[best_match]
                vehicle.x = x
                vehicle.y = y
                vehicle.width = w
                vehicle.height = h
                vehicle.confidence = conf
                vehicle.trajectory.append((x + w/2, y + h))
                matched_tracks.add(best_match)
                updated_vehicles.append(vehicle)
            else:
                # Create new track
                new_vehicle = Vehicle(
                    track_id=self.next_id,
                    vehicle_type=vehicle_types[class_id],
                    x=x, y=y, width=w, height=h,
                    confidence=conf,
                    frame_entered=frame_id
                )
                new_vehicle.trajectory.append((x + w/2, y + h))
                self.tracked_vehicles[self.next_id] = new_vehicle
                updated_vehicles.append(new_vehicle)
                self.next_id += 1
        
        # Remove old tracks
        for track_id in list(self.tracked_vehicles.keys()):
            if track_id not in matched_tracks:
                del self.tracked_vehicles[track_id]
        
        return updated_vehicles
    
    @staticmethod
    def _calculate_iou(box1: Tuple, box2: Tuple) -> float:
        """Calculate IOU between two boxes"""
        x1_min, y1_min, w1, h1 = box1
        x2_min, y2_min, w2, h2 = box2
        
        x1_max, y1_max = x1_min + w1, y1_min + h1
        x2_max, y2_max = x2_min + w2, y2_min + h2
        
        inter_x_min = max(x1_min, x2_min)
        inter_y_min = max(y1_min, y2_min)
        inter_x_max = min(x1_max, x2_max)
        inter_y_max = min(y1_max, y2_max)
        
        if inter_x_max <= inter_x_min or inter_y_max <= inter_y_min:
            return 0.0
        
        inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
        union_area = w1 * h1 + w2 * h2 - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0


class ITSDemo:
    """
    ╔════════════════════════════════════════════════════════════════════╗
    ║                                                                    ║
    ║    DEMO ỨNG DỤNG: HỆ THỐNG PHÁT HIỆN VI PHẠM GIAO THÔNG         ║
    ║                                                                    ║
    ║    Luồng xử lý chính:                                             ║
    ║    1. Mở video → đọc frame                                        ║
    ║    2. Preprocess (enhancement nếu tối)                            ║
    ║    3. Chạy YOLO → nhận dạng xe                                    ║
    ║    4. ByteTrack → gán ID theo dõi                                 ║
    ║    5. Kiểm tra lane → so sánh loại xe                             ║
    ║    6. Debouncing → xác nhận vi phạm                               ║
    ║    7. Lưu log CSV + vẽ khung xanh/đỏ                              ║
    ║    8. Hiển thị frame trực tiếp                                    ║
    ║                                                                    ║
    ╚════════════════════════════════════════════════════════════════════╝
    """
    
    def __init__(self):
        self.lanes = LaneConfiguration()
        self.detector = SimulatedYOLODetector(confidence_threshold=0.5)
        self.tracker = SimulatedByteTracker()
        self.violation_detector = ViolationDetector(self.lanes)
        
        self.frame_count = 0
        self.violation_count = 0
        self.violations_log = []
        self.start_time = time.time()
    
    def process_frame(self, frame_id: int, current_time: float) -> DetectionResult:
        """
        Xử lý một frame hoàn chỉnh
        """
        start_processing = time.time()
        
        # Step 1: DETECTION - Chạy YOLO
        detections = self.detector.detect(frame_id)
        
        # Step 2: TRACKING - Chạy ByteTrack
        vehicles = self.tracker.update(detections, frame_id)
        
        # Step 3: VIOLATION CHECK - Kiểm tra vi phạm
        for vehicle in vehicles:
            violation = self.violation_detector.check_vehicle_violation(vehicle)
            if violation:
                vehicle.violations.append(violation)
                self.violation_count += 1
                self.violations_log.append({
                    'frame': frame_id,
                    'time': current_time,
                    'track_id': vehicle.track_id,
                    'vehicle_type': vehicle.vehicle_type.value,
                    'lane': vehicle.current_lane.value,
                    'violation_type': violation.violation_type.value,
                    'confidence': f"{violation.confidence:.2f}"
                })
        
        processing_time = time.time() - start_processing
        fps = 1.0 / processing_time if processing_time > 0 else 0
        
        return DetectionResult(
            frame_id=frame_id,
            timestamp=current_time,
            vehicles=vehicles,
            processing_time=processing_time,
            fps=fps,
            vehicle_count=len(vehicles)
        )
    
    def print_banner(self):
        """In banner chính"""
        print(f"\n{Colors.CYAN}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}")
        print("╔════════════════════════════════════════════════════════════════════════════╗")
        print("║                                                                            ║")
        print("║    HỆ THỐNG PHÁT HIỆN VI PHẠM GIAO THÔNG THÔNG MINH (ITS)               ║")
        print("║    Intelligent Traffic Violation Detection System                         ║")
        print("║                                                                            ║")
        print("║    Chương 4.5: Demo Ứng Dụng                                             ║")
        print("║    Module: Interactive Visual Simulation                                  ║")
        print("║                                                                            ║")
        print("║    Sinh viên Chuyên đề Hệ Thống Giao Thông Thông Minh                    ║")
        print("║    2026                                                                    ║")
        print("║                                                                            ║")
        print("╚════════════════════════════════════════════════════════════════════════════╝")
        print(f"{Colors.RESET}{Colors.CYAN}{'='*80}{Colors.RESET}\n")
    
    def print_section_header(self, title: str, icon: str = "▶"):
        """In header của một section"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{icon} {title}{Colors.RESET}")
        print(f"{Colors.BLUE}{'-'*78}{Colors.RESET}")
    
    def print_lane_info(self):
        """Hiển thị thông tin cấu hình làn đường"""
        self.print_section_header("CẤU HÌNH LÀN ĐƯỜNG (LANE CONFIGURATION)", "🛣️")
        
        print(f"\n{Colors.BOLD}Tổng số làn:{Colors.RESET} 4 làn")
        print(f"{Colors.BOLD}Hướng lưu thông:{Colors.RESET} Từ trái sang phải\n")
        
        for i in range(4):
            lane_type = self.lanes.lanes_info[i]
            allowed_vehicle = self.lanes.lane_types[i]
            start_pos = self.lanes.lane_boundaries[i]
            end_pos = self.lanes.lane_boundaries[i + 1]
            
            print(f"{Colors.BOLD}{lane_type.value}{Colors.RESET}")
            print(f"  • Vị trí: {start_pos*100:.0f}% - {end_pos*100:.0f}% chiều rộng đường")
            print(f"  • Phương tiện được phép: {Colors.GREEN}{allowed_vehicle.value}{Colors.RESET}")
            print()
    
    def print_detection_module(self):
        """Mô tả MODULE 1: DETECTION"""
        self.print_section_header("MODULE 1: PHÁT HIỆN (DETECTION)", "🔍")
        
        print(f"""
{Colors.BOLD}Chức năng:{Colors.RESET}
  • Nhận vào: Frame video từ camera
  • Xử lý: Chạy mô hình YOLO để phát hiện phương tiện
  • Xuất ra: Bounding boxes + Class labels (loại xe)
  
{Colors.BOLD}Các loại phương tiện được phát hiện:{Colors.RESET}
  1. {Colors.YELLOW}Xe máy (Motorcycle){Colors.RESET} - ID 0
  2. {Colors.RED}Ô tô (Car){Colors.RESET} - ID 1
  3. {Colors.CYAN}Xe buýt (Bus){Colors.RESET} - ID 2
  4. {Colors.RED}Xe tải (Truck){Colors.RESET} - ID 3

{Colors.BOLD}Tham số YOLO:{Colors.RESET}
  • Model: YOLO11s.pt (pre-trained on COCO dataset)
  • Input size: 640×640 pixels
  • Confidence threshold: 0.20 - 0.45
  • NMS IoU threshold: 0.45

{Colors.BOLD}Thời gian xử lý:{Colors.RESET}
  • CPU: ~100-150ms per frame
  • GPU NVIDIA: ~20-50ms per frame
        """)
    
    def print_tracking_module(self):
        """Mô tả MODULE 2: TRACKING"""
        self.print_section_header("MODULE 2: THEO DÕI (TRACKING)", "👁️")
        
        print(f"""
{Colors.BOLD}Chức năng:{Colors.RESET}
  • Nhận vào: Bounding boxes từ YOLO
  • Xử lý: Gán ID cho từng phương tiện, theo dõi quỹ đạo
  • Xuất ra: Vehicles với consistent Track IDs

{Colors.BOLD}Thuật toán:{Colors.RESET}
  • ByteTrack - Tối ưu hóa để xử lý video giao thông
  • Ưu điểm:
    - Xử lý xe bị che khuất một phần
    - Duy trì ID ổn định
    - Hiệu suất tốt trên video chất lượng thấp
    
{Colors.BOLD}Cách hoạt động:{Colors.RESET}
  1. Tính IOU (Intersection over Union) giữa detection và track cũ
  2. Ghép nối (match) dựa trên IOU cao nhất
  3. Tạo track mới cho detection không có ghép nối
  4. Loại bỏ track quá cũ (> 30 frames)

{Colors.BOLD}Output của ByteTrack:{Colors.RESET}
  • Track ID: Số hiệu duy nhất cho mỗi phương tiện
  • Trajectory: Lịch sử vị trí qua các frame
  • Confidence: Độ tin cậy phát hiện
        """)
    
    def print_violation_module(self):
        """Mô tả MODULE 3: VIOLATION CHECK"""
        self.print_section_header("MODULE 3: KIỂM TRA VI PHẠM (VIOLATION LOGIC)", "⚠️")
        
        print(f"""
{Colors.BOLD}Cơ chế Dual-Check:{Colors.RESET}

{Colors.BOLD}PHẦN 1: KIỂM TRA KHÔNG GIAN (Spatial Check){Colors.RESET}
  1. Lấy điểm Bottom-Center của bounding box
     └─ Điểm tiếp xúc bánh xe với mặt đường
  
  2. Xác định vị trí tương đối trên đường (0-100%)
  
  3. Xác định xe đang ở làn nào (Lane detection)
  
  4. So sánh loại xe với loại xe được phép ở làn đó
     ✓ Khớp → Xe an toàn (Safe)
     ✗ Không khớp → Xe sai làn (Violation)

{Colors.BOLD}PHẦN 2: KIỂM TRA THỜI GIAN (Temporal Check){Colors.RESET}
  • Kỹ thuật Debouncing: Tránh cảnh báo sai do dao động nhỏ
  • Xe phải nằm sai làn liên tục ít nhất N frames (N = 3-5)
  • Chỉ kích hoạt cảnh báo khi đạt ngưỡng

{Colors.BOLD}Pseudocode:{Colors.RESET}
  Với mỗi xe trong video:
    1. Lấy điểm Bottom-Center (x, y)
    2. Kiểm tra điểm nằm trong lane nào
    3. Nếu không khớp với loại xe:
         • Tăng counter lên 1
         • Nếu counter >= 3:
           → Log vi phạm
           → Vẽ khung đỏ + chữ "WRONG LANE"
           → Đánh dấu cảnh báo
    4. Nếu khớp:
         • Reset counter về 0
         • Vẽ khung xanh (bình thường)

{Colors.BOLD}Ưu điểm:{Colors.RESET}
  ✓ Giảm False Positive (cảnh báo sai)
  ✓ Đảm bảo độ chính xác cao
  ✓ Xử lý thời gian thực
        """)
    
    def print_logging_module(self):
        """Mô tả MODULE 4: LOGGING"""
        self.print_section_header("MODULE 4: LƯU TRỮ (LOGGING)", "💾")
        
        print(f"""
{Colors.BOLD}Chức năng:{Colors.RESET}
  • Ghi log vi phạm vào file CSV
  • Lưu ảnh minh chứng
  • Hỗ trợ báo cáo và thống kê

{Colors.BOLD}File violations_log.csv chứa:{Colors.RESET}
  • Frame số: Vị trí trong video
  • Thời gian: Giây trong video
  • Track ID: Số hiệu phương tiện
  • Loại xe: Motorcycle, Car, Bus, Truck
  • Lane ID: Làn đường vi phạm
  • Confidence score: Độ tin cậy (0-1)

{Colors.BOLD}Cấu trúc dữ liệu:{Colors.RESET}
  violations_log.csv:
    ├─ Frame, Time(s), Track_ID, Vehicle_Type, Lane, Violation_Type, Confidence
    ├─ 150, 5.00, 1, Motorcycle, Lane 3, Wrong Lane, 0.92
    ├─ 155, 5.17, 1, Motorcycle, Lane 3, Wrong Lane, 0.94
    └─ 160, 5.33, 1, Motorcycle, Lane 3, Wrong Lane, 0.91

{Colors.BOLD}Sử dụng dữ liệu:{Colors.RESET}
  • Báo cáo hành vi vi phạm theo thời gian
  • Phân tích xu hướng giao thông
  • Hỗ trợ phạt nguội (smart ticketing)
  • Cải thiện an toàn giao thông
        """)
    
    def print_main_pipeline(self):
        """Mô tả luồng xử lý chính"""
        self.print_section_header("LUỒNG XỬ LÝ CHÍNH (MAIN PIPELINE)", "⚙️")
        
        pipeline = f"""
┌─────────────────────────────────────────────────────────────┐
│                   LUỒNG XỬ LÝ ĐẦY ĐỦ                      │
└─────────────────────────────────────────────────────────────┘

{Colors.BOLD}Step 1: MỞ VIDEO & ĐỌC FRAME{Colors.RESET}
  [🎥 Input] Video file
  {Colors.YELLOW}└─ Đọc frame theo frame{Colors.RESET}

{Colors.BOLD}Step 2: TIỀN XỬ LÝ (PREPROCESSING){Colors.RESET}
  {Colors.YELLOW}┌─ Kiểm tra độ sáng{Colors.RESET}
  {Colors.YELLOW}├─ Nếu tối: Áp dụng CLAHE (Adaptive Enhancement){Colors.RESET}
  {Colors.YELLOW}├─ Chuẩn hóa kích thước 640×640{Colors.RESET}
  {Colors.YELLOW}└─ Chuyển sang không gian màu RGB{Colors.RESET}

{Colors.BOLD}Step 3: PHÁT HIỆN (MODULE 1 - YOLO){Colors.RESET}
  {Colors.CYAN}┌─ Input: Frame đã xử lý{Colors.RESET}
  {Colors.CYAN}├─ YOLO Inference{Colors.RESET}
  {Colors.CYAN}└─ Output: Bounding boxes + Classes{Colors.RESET}

{Colors.BOLD}Step 4: TRACKING (MODULE 2 - ByteTrack){Colors.RESET}
  {Colors.GREEN}┌─ Input: Detection results{Colors.RESET}
  {Colors.GREEN}├─ Match với track cũ (IOU-based){Colors.RESET}
  {Colors.GREEN}├─ Gán/Cập nhật Track ID{Colors.RESET}
  {Colors.GREEN}└─ Output: Vehicles with IDs{Colors.RESET}

{Colors.BOLD}Step 5: KIỂM TRA VI PHẠM (MODULE 3){Colors.RESET}
  {Colors.YELLOW}┌─ Spatial Check: Xe ở làn nào?{Colors.RESET}
  {Colors.YELLOW}├─ Kiểm tra loại xe được phép{Colors.RESET}
  {Colors.YELLOW}├─ Temporal Check: Debouncing{Colors.RESET}
  {Colors.YELLOW}└─ Output: Violation flags{Colors.RESET}

{Colors.BOLD}Step 6: LƯU TRỮ (MODULE 4){Colors.RESET}
  {Colors.BOLD}{Colors.RED}┌─ Ghi log vi phạm vào CSV{Colors.RESET}
  {Colors.BOLD}{Colors.RED}├─ Lưu ảnh bằng chứng{Colors.RESET}
  {Colors.BOLD}{Colors.RED}└─ Update thống kê{Colors.RESET}

{Colors.BOLD}Step 7: VẼ HÌNH & HIỂN THỊ{Colors.RESET}
  {Colors.BOLD}{Colors.CYAN}┌─ Vẽ làn đường{Colors.RESET}
  {Colors.BOLD}{Colors.CYAN}├─ Khung xanh: Xe an toàn{Colors.RESET}
  {Colors.BOLD}{Colors.CYAN}├─ Khung đỏ: Xe vi phạm{Colors.RESET}
  {Colors.BOLD}{Colors.CYAN}├─ Hiển thị Track ID + Loại xe{Colors.RESET}
  {Colors.BOLD}{Colors.CYAN}└─ Hiển thị FPS + Thông tin hệ thống{Colors.RESET}

{Colors.BOLD}Step 8: LẶP LẠI{Colors.RESET}
  {Colors.BOLD}{Colors.WHITE}└─ Quay lại Step 1 cho frame tiếp theo{Colors.RESET}

┌─────────────────────────────────────────────────────────────┐
│              {Colors.GREEN}✓ PIPELINE HOÀN CHỈNH{Colors.RESET}                 │
└─────────────────────────────────────────────────────────────┘
"""
        print(pipeline)
    
    def simulate_and_display(self, num_frames: int = 300):
        """Chạy mô phỏng với các frame"""
        self.print_banner()
        self.print_lane_info()
        self.print_detection_module()
        self.print_tracking_module()
        self.print_violation_module()
        self.print_logging_module()
        self.print_main_pipeline()
        
        # Chạy mô phỏng
        self.print_section_header("CHẠY MÔ PHỎNG (SIMULATION)", "▶️")
        
        fps_history = deque(maxlen=30)
        
        for frame_id in range(num_frames):
            current_time = frame_id / 30.0  # Giả sử 30 FPS
            
            # Process frame
            result = self.process_frame(frame_id, current_time)
            fps_history.append(result.fps)
            avg_fps = sum(fps_history) / len(fps_history)
            
            # Print progress every 30 frames
            if frame_id % 30 == 0:
                print(f"\n{Colors.BOLD}Frame {frame_id:4d} | "
                      f"Time: {current_time:6.2f}s | "
                      f"Vehicles: {result.vehicle_count} | "
                      f"Violations: {self.violation_count} | "
                      f"FPS: {avg_fps:6.1f}{Colors.RESET}")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """In tóm tắt kết quả"""
        self.print_section_header("TÓM TẮT KẾT QUẢ (SUMMARY)", "📊")
        
        total_time = time.time() - self.start_time
        
        summary = f"""
{Colors.BOLD}Thống kê xử lý:{Colors.RESET}
  • Tổng frame xử lý: {Colors.CYAN}{self.frame_count}{Colors.RESET}
  • Tổng vi phạm phát hiện: {Colors.RED}{self.violation_count}{Colors.RESET}
  • Thời gian xử lý: {Colors.YELLOW}{total_time:.2f}s{Colors.RESET}
  • Hiệu suất: {Colors.GREEN}{self.frame_count / total_time:.1f} FPS{Colors.RESET}

{Colors.BOLD}Bản ghi vi phạm (Sample):{Colors.RESET}
"""
        print(summary)
        
        if self.violations_log:
            print(f"{Colors.BOLD}{'Frame':<8} {'Time':<10} {'ID':<8} {'Type':<15} {'Lane':<15} {'Confidence':<12}{Colors.RESET}")
            print(f"{Colors.YELLOW}{'-'*70}{Colors.RESET}")
            
            for log in self.violations_log[:10]:  # Show first 10
                print(f"{log['frame']:<8} {log['time']:<10.2f} {log['track_id']:<8} "
                      f"{log['vehicle_type']:<15} {log['lane']:<15} {log['confidence']:<12}")
            
            if len(self.violations_log) > 10:
                print(f"... và {len(self.violations_log) - 10} vi phạm khác")
        
        print(f"\n{Colors.BOLD}Ghi chú:{Colors.RESET}")
        print(f"  • Dữ liệu được lưu vào: {Colors.GREEN}violations_log.csv{Colors.RESET}")
        print(f"  • Ảnh bằng chứng: {Colors.GREEN}output/evidence/{Colors.RESET}")
    
    def save_log_csv(self, output_path: str = "demo_violations_log.csv"):
        """Lưu log vào file CSV"""
        if not self.violations_log:
            print(f"{Colors.YELLOW}Không có vi phạm để lưu{Colors.RESET}")
            return
        
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'frame', 'time', 'track_id', 'vehicle_type', 
                    'lane', 'violation_type', 'confidence'
                ])
                writer.writeheader()
                writer.writerows(self.violations_log)
            
            print(f"\n{Colors.GREEN}✓ Đã lưu log vào: {output_path}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}✗ Lỗi khi lưu log: {e}{Colors.RESET}")


def main():
    """Main entry point"""
    demo = ITSDemo()
    
    # Run simulation with 300 frames (~10 seconds at 30 FPS)
    demo.simulate_and_display(num_frames=300)
    
    # Save results — dùng path tương đối để chạy trên mọi máy
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)

    log_path = os.path.join(output_dir, "demo_violations_log.csv")
    demo.save_log_csv(log_path)
    
    print(f"\n{Colors.BOLD}{Colors.GREEN}")
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║                                                                            ║")
    print("║                    ✓ MÔ PHỎNG HOÀN THÀNH THÀNH CÔNG!                       ║")
    print("║                                                                            ║")
    print("║    Demo ứng dụng ITS đã minh họa các module chính:                        ║")
    print("║    • Module 1: YOLO Detection                                             ║")
    print("║    • Module 2: ByteTrack Tracking                                         ║")
    print("║    • Module 3: Violation Detection (Dual-Check)                           ║")
    print("║    • Module 4: Logging & Reporting                                        ║")
    print("║                                                                            ║")
    print("║    Cảm ơn đã sử dụng hệ thống này!                                        ║")
    print("║                                                                            ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")


if __name__ == "__main__":
    main()
