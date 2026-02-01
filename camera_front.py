# camera_front.py
import cv2
import time
import config  # Import bộ nhớ chung
import utils   # Import công cụ
import mediapipe as mp
from benchmark import FPSMeter

fps_meter_front = FPSMeter()

last_latency_ms = 0.0
def gen_frames_front():
    global latest_frame
    cap = cv2.VideoCapture(0)
    cap.set(3, 1280); cap.set(4, 720)
    pose = utils.make_pose_detector() # Dùng hàm từ utils
    try:
        while True:
            start_t = time.perf_counter()
            success, frame = cap.read()
            if not success: 
                break
            h, w, _ = frame.shape
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image)
            frame = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            
            st = config.state # Viết tắt cho gọn

            if results.pose_landmarks:
                # Logic: Có người
                if st["is_monitoring"] and st["is_absent"]:
                    st["is_absent"] = False
                    if st["absent_start_time"]: 
                        st["total_break_seconds"] += (time.time() - st["absent_start_time"])
                        st["absent_start_time"] = None

                lm = results.pose_landmarks.landmark
                l_ear = (int(lm[utils.mp_pose.PoseLandmark.LEFT_EAR.value].x * w), int(lm[utils.mp_pose.PoseLandmark.LEFT_EAR.value].y * h))
                r_ear = (int(lm[utils.mp_pose.PoseLandmark.RIGHT_EAR.value].x * w), int(lm[utils.mp_pose.PoseLandmark.RIGHT_EAR.value].y * h))
                l_sh = (int(lm[utils.mp_pose.PoseLandmark.LEFT_SHOULDER.value].x * w), int(lm[utils.mp_pose.PoseLandmark.LEFT_SHOULDER.value].y * h))
                r_sh = (int(lm[utils.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x * w), int(lm[utils.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y * h))
                nose = (int(lm[utils.mp_pose.PoseLandmark.NOSE.value].x * w), int(lm[utils.mp_pose.PoseLandmark.NOSE.value].y * h))
                
                cv2.line(frame, l_ear, r_ear, (0, 255, 255), 2)
                
                if st["is_monitoring"]:
                    st["current_realtime_errors"].discard('tilt')
                    st["current_realtime_errors"].discard('close')
                    detected_issues = []
                    
                    # Check Nghiêng
                    if utils.calculate_tilt(l_ear, r_ear) > config.FRONT_TILT_THRESH: 
                        detected_issues.append("NGHIENG DAU")
                        st["current_realtime_errors"].add('tilt')

                    # Check Dí Mắt
                    if st["front_ref"]["calibrated"]:
                        cv2.line(frame, (0, st["front_ref"]["nose_y"]), (w, st["front_ref"]["nose_y"]), (0, 255, 0), 1)
                        if ((l_sh[1] + r_sh[1]) // 2 - nose[1]) < (st["front_ref"]["shoulder_y"] - st["front_ref"]["nose_y"] - config.FRONT_OFFSET_Y): 
                            detected_issues.append("DI MAT GAN")
                            st["current_realtime_errors"].add('close')
                    else:
                        cv2.putText(frame, "CHUA CALIB!", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)

                    if detected_issues:
                        st["posture_status"]["front"] = False
                        cv2.putText(frame, " | ".join(detected_issues), (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
                    else:
                        st["posture_status"]["front"] = True
                        cv2.putText(frame, "OK", (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
                else:
                    st["posture_status"]["front"] = None
                    cv2.putText(frame, "CHO...", (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200,200,200), 2)
            else:
                # Logic: Vắng mặt
                st["posture_status"]["front"] = None
                if st["is_monitoring"]:
                    if not st["is_absent"]: 
                        st["is_absent"] = True
                        st["absent_start_time"] = time.time()
                    
                    st["current_realtime_errors"].discard('tilt')
                    st["current_realtime_errors"].discard('close')
                    
                    overlay = frame.copy(); cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
                    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
                    cv2.putText(frame, "BE VANG MAT", (w//2-100, h//2), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,255,255), 3)
            fps_meter_front.tick()

            ret, buffer = cv2.imencode('.jpg', frame)
            end_t = time.perf_counter()
            global last_latency_ms
            last_latency_ms = (end_t - start_t) * 1000.0
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    finally:
        cap.release()
def get_fps_front():
    return fps_meter_front.get_fps()
def get_latency_front():
    return round(last_latency_ms, 2)