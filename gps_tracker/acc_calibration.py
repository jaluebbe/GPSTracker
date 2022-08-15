#!/usr/bin/env python3
# code is partly based on https://gist.github.com/ViennaMike/d8b8f9636694c7edf4f115b28c9378c0
import json
import redis
import numpy as np

redis_connection = redis.Redis(decode_responses=True)


def _process_and_save(a_min, a_max, g):
    a_offset = tuple(map(lambda x1, x2: (x1 + x2) / 2, a_min, a_max))
    avg_a_delta = tuple(map(lambda x1, x2: (x2 - x1) / 2, a_min, a_max))
    combined_avg_a_delta = (
        avg_a_delta[0] + avg_a_delta[1] + avg_a_delta[2]
    ) / 3
    scale_a_x = combined_avg_a_delta / avg_a_delta[0]
    scale_a_y = combined_avg_a_delta / avg_a_delta[1]
    scale_a_z = combined_avg_a_delta / avg_a_delta[2]
    calibration = {
        "a_offset": a_offset,
        "a_matrix": np.diag([scale_a_x, scale_a_y, scale_a_z]).tolist(),
        "g": g,
    }
    print(json.dumps(calibration, indent=4))
    redis_connection.set("a_offset", json.dumps(a_offset))
    print("saved a_offset to Redis.")


def perform_calibration():
    redis_connection = redis.Redis(decode_responses=True)
    measuring_duration = 5
    g = 9.80665  # could be changed to local conditions during calibration.
    running_a_min = (32767, 32767, 32767)
    running_a_max = (-32768, -32768, -32768)
    print(
        "Alter the orientation of the device between +/- x/y/z orientation. "
        "Do not move the device during each calibration step."
    )
    input("Press (enter) to start a calibration step: ")
    while True:
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
                a_data = _data["raw_acceleration"]
                running_a_min = tuple(
                    map(lambda x, y: min(x, y), running_a_min, a_data)
                )
                running_a_max = tuple(
                    map(lambda x, y: max(x, y), running_a_max, a_data)
                )
        response = input(
            f"{measuring_duration}s of calibration completed.\n"
            f"min values: {running_a_min}\nmax values: {running_a_max}\n"
            "Press (a) to abort, (s) to save or (enter) to continue: "
        )
        if response == "a":
            break
        elif response == "s":
            _process_and_save(running_a_min, running_a_max, g)
            break


if __name__ == "__main__":
    perform_calibration()
