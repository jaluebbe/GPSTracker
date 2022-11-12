#!/usr/bin/env python3
import json
import redis
import numpy as np
from collections import deque


if __name__ == "__main__":
    measuring_duration = 5
    redis_connection = redis.Redis(decode_responses=True)
    d = deque()
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
                t_stop = _data["i_utc"]
                break
            d.append(_data["raw_gyro"])
    g_offset = list(np.median(d, axis=0))
    redis_connection.set("g_offset", json.dumps(g_offset))
    print(f"saved g_offset={g_offset} to Redis.")
