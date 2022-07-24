#!/usr/bin/env python3
import redis
import json
import numpy as np
from collections import deque
import time


def measure_gps_performance(duration=5):
    redis_connection = redis.Redis(decode_responses=True)
    gps_history = deque()
    _pubsub = redis_connection.pubsub()
    _pubsub.subscribe("gps")
    t_start = None
    for item in _pubsub.listen():
        if not item["type"] == "message":
            continue
        if item["channel"] == "gps":
            _data = json.loads(item["data"])
            _data["received_utc"] = time.time()
            gps_history.append(_data)
        if t_start is None:
            t_start = _data["utc"]
        elif _data["utc"] > t_start + duration:
            t_stop = _data["utc"]
            break
    dt = t_stop - t_start
    print(
        "### measured {} samples in {:.2f}s ({:.2f}s/sample) ###".format(
            len(gps_history), dt, dt / (len(gps_history) - 1)
        )
    )
    received = np.array([x["received_utc"] for x in gps_history])
    utc = np.array([x["utc"] for x in gps_history])
    delays = received - utc
    print(
        "Delay ranges from {:.3f}s to {:.3f}s, median {:.3f}s".format(
            delays.min(), delays.max(), np.median(delays)
        )
    )
    altitudes = np.array([x["alt"] for x in gps_history])
    print(
        "h_mean = {:.2f} +/- {:.2f} m".format(
            np.mean(altitudes), np.std(altitudes)
        )
    )
    gps_devices = redis_connection.get("gps_devices")
    if gps_devices is not None:
        print(f"Device information found:\n{gps_devices}")


while True:
    measure_gps_performance()
    continue
