#!venv/bin/python3
import time
import json
from collections import deque
import numpy as np
import redis


class PressureLogger:
    def __init__(self):
        self.redis_connection = redis.Redis(decode_responses=True)
        self.pressure_buffer = deque(maxlen=700)
        self.buffer_time = None
        self.pressure_data = None
        self.old_pressure = 0
        self.old_pressure_utc = 0
        self.log_altitude = True
        self.log_pressure = True
        self.log_pressure_minutes = {0, 10, 20, 30, 40, 50}
        self._pubsub = self.redis_connection.pubsub()
        self._pubsub.subscribe(["barometer", "transfer_data"])

    def process_transfer_data(self, data):
        if data["utc"] > self.old_pressure_utc:
            self.old_pressure = data["pressure"]
            self.old_pressure_utc = data["utc"]

    def log_pressure_data(self, data):
        key = f"pressure:{data['p_hostname']}:{time.strftime('%Y%m')}"
        self.redis_connection.lpush(key, json.dumps(data))

    def log_altitude_data(self, data):
        key = f"altitude:{data['p_hostname']}:{time.strftime('%Y%m%d')}"
        self.redis_connection.lpush(key, json.dumps(data))

    def process_message(self, item):
        if item["type"] != "message":
            return
        data = json.loads(item["data"])
        if "pressure" not in data or "p_utc" not in data:
            return
        # The last transfer_data message represents the last data dump to Redis.
        if item["channel"] == "transfer_data":
            self.process_transfer_data(data)
            return
        utc = data["p_utc"]
        utc_ceil_minute = utc - utc % 60 + 60
        if self.buffer_time is None:
            self.buffer_time = utc_ceil_minute
        elif utc_ceil_minute > self.buffer_time and self.pressure_buffer:
            self.pressure_data = {
                "pressure": int(round(np.mean(self.pressure_buffer))),
                "temperature": round(data["temperature"], 1),
                "utc": int(self.buffer_time),
                "hostname": data["p_hostname"],
            }
            if "humidity" in data:
                self.pressure_data["humidity"] = int(round(data["humidity"]))

            if (
                self.log_pressure
                and time.gmtime(self.buffer_time).tm_min
                in self.log_pressure_minutes
            ):
                self.log_pressure_data(self.pressure_data)
            self.pressure_buffer.clear()
            self.buffer_time = utc_ceil_minute
        elif utc_ceil_minute > self.buffer_time and not self.pressure_buffer:
            self.buffer_time = utc_ceil_minute
        self.pressure_buffer.append(data["pressure"])
        # Add pressure values to altitude log if a significant pressure
        # difference occurs which was not considered by the tracking log.
        # Ignore small deviations from the mean value.
        # Skip logging if no mean value is available, yet.
        # Don't log more frequently than one second.
        if self.pressure_data and data["p_utc"] >= self.old_pressure_utc + 1:
            pressure_diff = abs(
                data["pressure"] - self.pressure_data["pressure"]
            )
            if (
                pressure_diff >= 10
                and self.log_altitude
                and abs(data["pressure"] - self.old_pressure) > 10
            ):
                self.log_altitude_data(data)
                self.old_pressure = data["pressure"]
                self.old_pressure_utc = data["p_utc"]

    def run(self):
        for item in self._pubsub.listen():
            self.process_message(item)
            time.sleep(0.05)


if __name__ == "__main__":
    logger = PressureLogger()
    logger.run()
