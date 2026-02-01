# camera_side.py
import cv2
import config
import utils
from benchmark import FPSMeter

fps_meter_side = FPSMeter()
last_latency_ms = 0.0
def gen_frames_side():
    cap = cv2.VideoCapture(1) # Lưu ý ID Cam Side (0, 1 hoặc 2)
    cap.set(3, 1280); cap.set(4, 720)
    pose = utils.make_pose_detector()
    
    while True:
        success, frame = cap.read()
        if not success:
            # Gửi frame rỗng nếu lỗi cam
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + b'' + b'\r\n')
            continue
            
        st = config.state

        if st["is_absent"] and st["is_monitoring"]:
            cv2.putText(frame, "TAM DUNG", (50, 360), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            # Reset lỗi cam cạnh khi vắng mặt
            st["current_realtime_errors"].discard('neck')
            st["current_realtime_errors"].discard('back')
        else:
            h, w, _ = frame.shape
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image)
            frame = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            
            if results.pose_landmarks and st["is_monitoring"]:
                lm = results.pose_landmarks.landmark
                # Lấy tọa độ Tai - Vai - Hông
                p_ear = (int(lm[utils.mp_pose.PoseLandmark.LEFT_EAR.value].x * w), int(lm[utils.mp_pose.PoseLandmark.LEFT_EAR.value].y * h))
                p_sh = (int(lm[utils.mp_pose.PoseLandmark.LEFT_SHOULDER.value].x * w), int(lm[utils.mp_pose.PoseLandmark.LEFT_SHOULDER.value].y * h))
                p_hip = (int(lm[utils.mp_pose.PoseLandmark.LEFT_HIP.value].x * w), int(lm[utils.mp_pose.PoseLandmark.LEFT_HIP.value].y * h))
                
                # Vẽ khung xương
                cv2.line(frame, p_ear, p_sh, (0, 255, 255), 2)
                cv2.line(frame, p_sh, p_hip, (0, 255, 255), 2)
                
                # Reset danh sách lỗi realtime
                st["current_realtime_errors"].discard('neck')
                st["current_realtime_errors"].discard('back')
                detected_issues = []
                
                # --- THUẬT TOÁN LEARNOPENCV ---
                # 1. Neck Inclination: Góc (Vai->Tai) so với Trục dọc
                neck_angle = utils.find_angle(p_sh[0], p_sh[1], p_ear[0], p_ear[1])
                
                # 2. Torso Inclination: Góc (Hông->Vai) so với Trục dọc
                torso_angle = utils.find_angle(p_hip[0], p_hip[1], p_sh[0], p_sh[1])
                
                # Logic kiểm tra lỗi
                # Gù Cổ (Text Neck)
                if neck_angle > config.SIDE_NECK_THRESH: 
                    detected_issues.append(f"GU CO ({int(neck_angle)})")
                    st["current_realtime_errors"].add('neck')
                
                # Gù Lưng (Slouching / Leaning Forward)
                if torso_angle > config.SIDE_TORSO_THRESH: 
                    detected_issues.append(f"GU LUNG ({int(torso_angle)})")
                    st["current_realtime_errors"].add('back')
                
                # Hiển thị
                if detected_issues:
                    st["posture_status"]["side"] = False
                    cv2.putText(frame, "|".join(detected_issues), (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
                else:
                    st["posture_status"]["side"] = True
                    cv2.putText(frame, f"OK (N:{int(neck_angle)} T:{int(torso_angle)})", (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
            else:
                st["posture_status"]["side"] = None
        fps_meter_side.tick()

        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
def get_fps_side():
    return fps_meter_side.get_fps()
def get_latency_side():
    return round(last_latency_ms, 2)