#!/usr/bin/env python3
import redis
import json
import numpy as np
from collections import deque
import time


def measure_gps_altitude_fluctuations(duration=60):
    redis_connection = redis.Redis(decode_responses=True)
    altitude_history = deque()
    _pubsub = redis_connection.pubsub()
    _pubsub.subscribe(["gps"])
    t_start = None
    for item in _pubsub.listen():
        if not item[u"type"] == "message":
            continue
        if item["channel"] == "gps":
            _data = json.loads(item["data"])
            altitude_history.append(_data["alt"])
            if t_start is None:
                t_start = _data["utc"]
            elif _data["utc"] > t_start + duration:
                t_stop = _data["utc"]
                break
    print(
        "### measured {} samples in {:.2f}s ###".format(
            len(altitude_history), t_stop - t_start
        )
    )
    print(
        "h_mean = {:.2f} +/- {:.2f} m".format(
            np.mean(altitude_history), np.std(altitude_history)
        )
    )


while True:
    measure_gps_altitude_fluctuations()
