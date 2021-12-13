#!/usr/bin/env python3
import time
import json
from collections import deque
import numpy as np
import redis

redis_connection = redis.Redis(decode_responses=True)
pressure_buffer = deque(maxlen=700)
buffer_time = None
pressure_data = None
_pubsub = redis_connection.pubsub()
_pubsub.subscribe(["bmp280", "bme280", "bmp388", "transfer_data"])
old_pressure = 0
old_pressure_utc = 0
log_altitude = True
log_pressure = True
log_pressure_minutes = [20, 50]

for item in _pubsub.listen():
    if not item[u"type"] == "message":
        continue
    # the last transfer_data message represents the last data dump to Redis.
    if item["channel"] == "transfer_data":
        _transfer_data = json.loads(item["data"])
        if _transfer_data["utc"] > old_pressure_utc:
            old_pressure = _transfer_data["pressure"]
            old_pressure_utc = _transfer_data["utc"]
        continue
    data = json.loads(item["data"])
    utc = data["p_utc"]
    utc_ceil_minute = utc - utc % 60 + 60
    next_minute = time.gmtime(utc_ceil_minute).tm_min
    if buffer_time is None:
        buffer_time = utc_ceil_minute
    elif utc_ceil_minute > buffer_time and len(pressure_buffer) > 0:
        pressure_data = {
            "pressure": int(round(np.mean(pressure_buffer))),
            "temperature": round(data["temperature"], 1),
            "utc": int(buffer_time),
            "hostname": data["hostname"],
        }
        if item["channel"] == "bme280":
            pressure_data["humidity"] = int(round(data["humidity"]))
        if (
            log_pressure
            and time.gmtime(buffer_time).tm_min in log_pressure_minutes
        ):
            key = "pressure:{}:{}".format(
                data["hostname"], time.strftime("%Y%m")
            )
            redis_connection.lpush(key, json.dumps(pressure_data))
        pressure_buffer.clear()
        buffer_time = utc_ceil_minute
    elif utc_ceil_minute > buffer_time and len(pressure_buffer) == 0:
        buffer_time = utc_ceil_minute
    pressure_buffer.append(data["pressure"])
    # Add pressure values to altitude log if a significant pressure difference
    # occurs which was not considered by the tracking log.
    # Ignore small deviations from the mean value.
    # Skip logging if no mean value is available, yet.
    # Don't log more frequently than one second.
    if pressure_data is None:
        pass
    elif data["p_utc"] < old_pressure_utc + 1:
        pass
    elif np.abs(np.diff([data["pressure"], pressure_data["pressure"]])) < 10:
        pass
    elif (
        log_altitude and np.abs(np.diff([data["pressure"], old_pressure])) > 10
    ):
        key = "altitude:{}:{}".format(data["hostname"], time.strftime("%Y%m%d"))
        redis_connection.lpush(key, json.dumps(data))
        old_pressure = data["pressure"]
        old_pressure_utc = data["p_utc"]
    time.sleep(0.05)
    continue
