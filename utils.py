# utils.py
import mediapipe as mp
import math
import numpy as np

mp_pose = mp.solutions.pose

def make_pose_detector():
    return mp_pose.Pose(
        model_complexity=1, 
        smooth_landmarks=True, 
        min_detection_confidence=0.6, 
        min_tracking_confidence=0.6, 
        static_image_mode=False
    )
    """
    Tính góc của đoạn thẳng (P1->P2) so với trục thẳng đứng (Vertical Axis).
    Theo LearnOpenCV: Dùng vector để tính góc kẹp giữa vector P1P2 và vector dọc (0, -1).
    """
def find_angle(x1, y1, x2, y2):
    v1 = (x2-x1, y2-y1)
    v2 = (0, -1) # Vector trục tung hướng lên
    try:
        dot = v1[0]*v2[0] + v1[1]*v2[1]
        mag = math.sqrt(v1[0]**2 + v1[1]**2) * math.sqrt(v2[0]**2 + v2[1]**2)
        # acos trả về radian -> đổi sang degree
        angle = math.degrees(math.acos(dot/mag)) if mag!=0 else 0
        return angle
    except: return 0

def calculate_tilt(p1, p2):
    # Góc nghiêng đầu (so với phương ngang)
    if p1[0] == p2[0]: return 90
    angle = abs(math.degrees(math.atan2(p2[1]-p1[1], p2[0]-p1[0])))
    return 180 - angle if angle > 90 else angle