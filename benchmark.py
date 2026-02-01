# benchmark.py
import time
import csv
import os
import psutil
import threading

class FPSMeter:
    def __init__(self):
        self.last_time = None
        self.last_fps = 0.0

    def tick(self):
        now = time.time()
        if self.last_time is not None:
            dt = now - self.last_time
            if dt > 0:
                self.last_fps = 1.0 / dt
        self.last_time = now

    def get_fps(self):
        return round(self.last_fps, 2)


class ResourceMonitor(threading.Thread):
    def __init__(self, interval=1.0):
        super().__init__(daemon=True)
        self.interval = interval
        self.process = psutil.Process(os.getpid())
        self.last_cpu = 0.0
        self.last_ram = 0.0
        self.running = True

    def run(self):
        # initialize internal counters so first reading is meaningful
        try:
            self.process.cpu_percent(interval=None)
        except Exception:
            pass

        while self.running:
            # process.cpu_percent can exceed 100 when the process uses
            # more than one CPU core (e.g. 179% means ~1.79 cores used).
            # Normalize to overall CPU usage (0-100%) by dividing by cpu_count().
            cpu = self.process.cpu_percent(interval=None)
            try:
                self.last_cpu = cpu / psutil.cpu_count()
            except Exception:
                self.last_cpu = cpu

            self.last_ram = self.process.memory_info().rss / 1024 / 1024
            time.sleep(self.interval)

    def stop(self):
        self.running = False


class BenchmarkLogger(threading.Thread):
    def __init__(self, monitor, fps_front_cb, latency_front_cb, fps_side_cb, latency_side_cb,
                 csv_file="benchmark_log.csv", interval=1.0):
        super().__init__(daemon=True)
        self.monitor = monitor
        self.fps_front_cb = fps_front_cb
        self.latency_front_cb = latency_front_cb
        self.fps_side_cb = fps_side_cb
        self.latency_side_cb = latency_side_cb
        self.interval = interval
        self.csv_file = csv_file
        self.running = True

        if not os.path.exists(csv_file):
            with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
                csv.writer(f).writerow([
                    "Timestamp", "CPU(%)", "RAM(MB)",
                    "fps_front", "latency_front(ms)", "fps_side", "latency_side(ms)"
                ])

    def run(self):
        while self.running:
            with open(self.csv_file, "a", newline="", encoding="utf-8-sig") as f:
                csv.writer(f).writerow([
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    round(self.monitor.last_cpu, 2),
                    round(self.monitor.last_ram, 2),
                    self.fps_front_cb(),
                    self.latency_front_cb(),
                    self.fps_side_cb(),
                    self.latency_side_cb()
                ])
            time.sleep(self.interval)

    def stop(self):
        self.running = False
