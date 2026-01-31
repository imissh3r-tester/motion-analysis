# config.py
import cv2

# --- CẤU HÌNH NGƯỠNG (THRESHOLDS) ---
# Theo LearnOpenCV:
# - Neck > 40 độ là Text Neck.
# - Torso > 10 độ là bắt đầu đổ người/gù lưng.
SIDE_NECK_THRESH = 40             
SIDE_TORSO_THRESH = 10            

FRONT_TILT_THRESH = 20            # Nghiêng đầu (Cam trước)
FRONT_OFFSET_Y = 30               # Khoảng cách Dí mắt (Cam trước)
ALARM_DELAY = 3                   # Giây (Chờ 3s mới báo lỗi)

# --- BIẾN TRẠNG THÁI (State) ---
state = {
    "posture_status": {"front": None, "side": None},
    "front_ref": {"nose_y": 0, "shoulder_y": 0, "calibrated": False},
    "is_monitoring": False,
    
    # Biến đếm lỗi & Vắng mặt
    "error_counts": {"neck": 0, "back": 0, "tilt": 0, "close": 0},
    "current_realtime_errors": set(),
    "bad_posture_start_time": None,
    "current_error_counted": False,
    
    "is_absent": False,
    "absent_start_time": None,
    "total_break_seconds": 0
}

# Thông tin phiên học
session = {
    "start_time": None,
    "user_name": "",
    "user_age": "",
    "target_duration": 0
}