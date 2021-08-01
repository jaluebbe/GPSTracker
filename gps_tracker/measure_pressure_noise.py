#!/usr/bin/env python3
import redis
import json
import numpy as np
from collections import deque
import time


def measure_pressure_noise(duration=60):
    redis_connection = redis.Redis(decode_responses=True)
    pressure_history = deque()
    temperature_history = deque()
    _pubsub = redis_connection.pubsub()
    _pubsub.subscribe(["bmp280", "bmp388"])
    t_start = None
    for item in _pubsub.listen():
        if not item[u"type"] == "message":
            continue
        if item["channel"] in ["bmp280", "bmp388"]:
            _data = json.loads(item["data"])
            pressure_history.append(_data["pressure"])
            temperature_history.append(_data["temperature"])
            if t_start is None:
                t_start = _data["p_utc"]
            elif _data["p_utc"] > t_start + duration:
                t_stop = _data["p_utc"]
                break
    print(
        "### measured {} samples in {:.2f}s ###".format(
            len(pressure_history), t_stop - t_start
        )
    )
    print(
        "p_mean = {:.2f} +/- {:.2f} Pa".format(
            np.mean(pressure_history), np.std(pressure_history)
        )
    )
    print(
        "t_mean = {:.2f} +/- {:.2f} °C".format(
            np.mean(temperature_history), np.std(temperature_history)
        )
    )


while True:
    measure_pressure_noise()
