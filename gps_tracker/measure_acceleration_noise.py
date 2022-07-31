#!/usr/bin/env python3
import redis
import json
import numpy as np
from collections import deque
import time


g = 9.80665


def measure_acceleration_noise(duration=60):
    redis_connection = redis.Redis(decode_responses=True)
    acceleration_history = deque()
    _pubsub = redis_connection.pubsub()
    _pubsub.subscribe("imu")
    t_start = None
    for item in _pubsub.listen():
        if not item["type"] == "message":
            continue
        if item["channel"] == "imu":
            _data = json.loads(item["data"])
            acceleration_history.append(_data["vertical_acceleration"])
            if t_start is None:
                t_start = _data["i_utc"]
            elif _data["i_utc"] > t_start + duration:
                t_stop = _data["i_utc"]
                break
    print(
        "### measured {} samples in {:.2f}s ###".format(
            len(acceleration_history), t_stop - t_start
        )
    )
    print(
        "acc_mean = {:.3f} +/- {:.3f} m/s^2, diff to g: {:.3f} m/s^2".format(
            np.mean(acceleration_history),
            np.std(acceleration_history),
            np.mean(acceleration_history) - g,
        )
    )


while True:
    measure_acceleration_noise()
