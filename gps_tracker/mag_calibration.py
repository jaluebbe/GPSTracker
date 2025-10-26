#!/usr/bin/env python3
import json
import redis
import numpy as np

redis_connection = redis.Redis(decode_responses=True)


def _process_and_save(m_min, m_max):
    m_offset = tuple(map(lambda x1, x2: (x1 + x2) / 2, m_min, m_max))
    calibration = {
        "m_offset": m_offset,
    }
    print(json.dumps(calibration, indent=4))
    redis_connection.set("m_offset", json.dumps(m_offset))
    print("saved m_offset to Redis.")


def perform_calibration():
    redis_connection = redis.Redis(decode_responses=True)
    measuring_duration = 30
    running_m_min = (32767, 32767, 32767)
    running_m_max = (-32768, -32768, -32768)
    print(
        "Rotate the device around its axes for calibration."
    )
    input(f"Press (enter) to start a calibration for {measuring_duration}s: ")
    while True:
        _pubsub = redis_connection.pubsub()
        _pubsub.subscribe("imu", "imu_barometer")
        t_start = None
        for item in _pubsub.listen():
            if not item["type"] == "message":
                continue
            _data = json.loads(item["data"])
            if t_start is None:
                t_start = _data["i_utc"]
            elif _data["i_utc"] > t_start + measuring_duration:
                t_stop = _data["i_utc"]
                break
            m_data = _data["raw_magnetometer"]
            running_m_min = tuple(
                map(lambda x, y: min(x, y), running_m_min, m_data)
            )
            running_m_max = tuple(
                map(lambda x, y: max(x, y), running_m_max, m_data)
            )
        response = input(
            f"{measuring_duration}s of calibration completed.\n"
            f"min values: {running_m_min}\nmax values: {running_m_max}\n"
            "Press (a) to abort, (s) to save or (enter) to continue: "
        )
        if response == "a":
            break
        elif response == "s":
            _process_and_save(running_m_min, running_m_max)
            break


if __name__ == "__main__":
    perform_calibration()
