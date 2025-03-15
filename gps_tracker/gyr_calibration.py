#!venv/bin/python3
import json
import redis
import numpy as np
from collections import deque


def calibrate(measuring_duration=5):
    redis_connection = redis.Redis(decode_responses=True)
    gyro_data = deque()
    temp_data = deque()
    _pubsub = redis_connection.pubsub()
    _pubsub.subscribe("imu")
    t_start = None
    for item in _pubsub.listen():
        if not item["type"] == "message":
            continue
        if item["channel"] == "imu":
            _data = json.loads(item["data"])
            if t_start is None:
                t_start = _data["i_utc"]
            elif _data["i_utc"] > t_start + measuring_duration:
                break
            gyro_data.append(_data["raw_gyro"])
            temp_data.append(_data["raw_gyro_temp"])
    g_offset = np.median(gyro_data, axis=0).astype(int).tolist()
    g_temp = int(np.median(temp_data))
    redis_connection.set("g_offset", json.dumps(g_offset))
    redis_connection.set("g_temp", g_temp)
    redis_connection.set("calibration_updated", 1)
    calibration = {
        "timestamp": t_start,
        "g_offset": g_offset,
        "g_temp": g_temp,
    }
    redis_connection.rpush("gyr_calibration_history", json.dumps(calibration))
    return calibration


if __name__ == "__main__":
    calibration = calibrate(measuring_duration=5)
    print(f"Saved calibration: {json.dumps(calibration)} to Redis.")
