# app.py
from flask import Flask, render_template, Response, jsonify, request, send_from_directory
import webview
import threading
import cv2
import time
import csv
import os
from datetime import datetime
import config
import utils
import camera_front
import camera_side
from benchmark import ResourceMonitor, BenchmarkLogger

app = Flask(__name__)
LOG_FILE = 'nhat_ky_be_hoc.csv'

# Tạo file CSV
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w', newline='', encoding='utf-8-sig') as f:
        csv.writer(f).writerow(["Thời gian", "Tên Bé", "Tuổi", "Mục tiêu(p)", "Thực học(p)", "Tổng Lỗi", "Gù Cổ", "Gù Lưng", "Nghiêng Đầu", "Dí Mắt"])

@app.route('/static/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype = 'image/vnd.microsoft.icon')

@app.route('/start_session', methods=['POST'])
def start_session():
    data = request.json
    st = config.state
    ss = config.session
    
    ss["user_name"] = data.get('name', 'Bé')
    ss["user_age"] = data.get('age', '')
    ss["target_duration"] = float(data.get('duration', 0))
    ss["start_time"] = datetime.now()
    
    st["is_monitoring"] = True
    st["total_break_seconds"] = 0
    st["is_absent"] = False
    st["absent_start_time"] = None
    st["bad_posture_start_time"] = None
    st["current_error_counted"] = False
    st["current_realtime_errors"] = set()
    st["error_counts"] = {"neck": 0, "back": 0, "tilt": 0, "close": 0}
    
    return jsonify({"status": "started"})

@app.route('/stop_session', methods=['POST'])
def stop_session():
    st = config.state
    ss = config.session
    
    if st["is_monitoring"] and ss["start_time"]:
        end_time = datetime.now()
        if st["is_absent"] and st["absent_start_time"]:
            st["total_break_seconds"] += (time.time() - st["absent_start_time"])

        total_min = round((end_time - ss["start_time"]).total_seconds() / 60, 2)
        break_min = round(st["total_break_seconds"] / 60, 2)
        actual_min = round(total_min - break_min, 2)
        total_errors = sum(st["error_counts"].values())

        with open(LOG_FILE, 'a', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerow([
                ss["start_time"].strftime("%Y-%m-%d %H:%M"),
                ss["user_name"], ss["user_age"], ss["target_duration"], actual_min,
                total_errors, 
                st["error_counts"]['neck'], st["error_counts"]['back'], 
                st["error_counts"]['tilt'], st["error_counts"]['close']
            ])
        
        st["is_monitoring"] = False
        return jsonify({"status": "stopped", "actual": actual_min, "errors": st["error_counts"]})
    return jsonify({"status": "error"})

@app.route('/check_status')
def check_status():
    st = config.state
    if not st["is_monitoring"] or st["is_absent"]:
        return jsonify({"active": st["is_monitoring"], "absent": st["is_absent"], "alarm": False, "counts": st["error_counts"]})

    is_bad = len(st["current_realtime_errors"]) > 0
    alarm = False
    
    if is_bad:
        if st["bad_posture_start_time"] is None: st["bad_posture_start_time"] = time.time()
        elif time.time() - st["bad_posture_start_time"] > config.ALARM_DELAY:
            alarm = True
            if not st["current_error_counted"]:
                for err in st["current_realtime_errors"]:
                    if err in st["error_counts"]: st["error_counts"][err] += 1
                st["current_error_counted"] = True 
    else:
        st["bad_posture_start_time"] = None
        st["current_error_counted"] = False 
        
    return jsonify({
        "active": True, "absent": False, 
        "front": st["posture_status"]["front"], "side": st["posture_status"]["side"], 
        "alarm": alarm, "counts": st["error_counts"]
    })

@app.route('/calibrate_front')
def calibrate_front():
    # Helper gọi nhanh CV2 để calib
    frame = camera_front.latest_frame
    if frame is None:
        return jsonify({"status": "no_frame"})
    pose = utils.make_pose_detector()
    res = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    if res.pose_landmarks:
        h, w, _ = frame.shape
        lm = res.pose_landmarks.landmark
        config.state["front_ref"]["nose_y"] = int(lm[utils.mp_pose.PoseLandmark.NOSE.value].y * h)
        l_y = lm[utils.mp_pose.PoseLandmark.LEFT_SHOULDER.value].y
        r_y = lm[utils.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y
        config.state["front_ref"]["shoulder_y"] = int(((l_y + r_y)/2) * h)
        config.state["front_ref"]["calibrated"] = True
        config.state["current_realtime_errors"].clear()
        config.state["bad_postures_start_time"] = None
        config.state["current_error_counted"] = False
        return jsonify({"status": "success"})
    return jsonify({"status": "failed"})

@app.route('/get_history')
def get_history():
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader: logs.append(row)
    return jsonify(logs[-5:][::-1])

@app.route('/')
def index(): return render_template('index.html')
@app.route('/video_front')
def video_front(): return Response(camera_front.gen_frames_front(), mimetype='multipart/x-mixed-replace; boundary=frame')
@app.route('/video_side')
def video_side(): return Response(camera_side.gen_frames_side(), mimetype='multipart/x-mixed-replace; boundary=frame')

def start_flask():
    app.run(host = "127.0.0.1", port = 5000, debug = False, threaded = True, use_reloader = False)

@app.route('/benchmark')
def benchmark():
    fps_front = camera_front.get_fps_front()
    fps_side = camera_side.get_fps_side()
    latency_front = camera_front.get_latency_front()
    latency_side = camera_side.get_latency_side()
    monitor.log(fps_front = fps_front, fps_side = fps_side, latency_front = latency_front, latency_side = latency_side)
    return jsonify({
        "fps_front": fps_front,
        "fps_side": fps_side,
        "cpu percent": monitor.last_cpu if monitor else None,
        "ram_mb": monitor.last_ram if monitor else None,
        "latency_front_ms": latency_front,
        "latency_side_ms": latency_side,
    })

if __name__ == '__main__':
    monitor = ResourceMonitor(interval = 1.0)
    monitor.start()

    logger = BenchmarkLogger(monitor = monitor, fps_front_cb=camera_front.get_fps_front, latency_front_cb=camera_front.get_latency_front, fps_side_cb=camera_side.get_fps_side, latency_side_cb=camera_side.get_latency_side, interval = 1.0)
    logger.start()

    t = threading.Thread(target=start_flask)
    t.daemon = True
    t.start()

    time.sleep(0.75)
    webview.create_window("AI Kids Monitor", "http://127.0.0.1:5000", width = 1200, height = 800)
    webview.start()

    logger.stop()
    monitor.stop()