#!/usr/bin/env python3
# code is partly based on https://gist.github.com/ViennaMike/d8b8f9636694c7edf4f115b28c9378c0
import time
import json
import numpy as np
from lsm303d import Lsm303d


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
        "a_offset_x": a_offset[0],
        "a_offset_y": a_offset[1],
        "a_offset_z": a_offset[2],
        "scale_a_x": scale_a_x,
        "scale_a_y": scale_a_y,
        "scale_a_z": scale_a_z,
        "g": g,
    }
    print(json.dumps(calibration, indent=4))
    with open("lsm303d_calibration.json", "w") as json_file:
        json.dump(calibration, json_file)


def perform_calibration():
    sensor = Lsm303d()
    measuring_duration = 5
    g = 9.80665  # could be changed to local conditions during calibration.
    running_a_min = (32767, 32767, 32767)
    running_a_max = (-32768, -32768, -32768)
    input("press (enter) to start calibration: ")
    t_start = time.time()
    while True:
        now = time.time()
        if t_start + measuring_duration < now:
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
            else:
                t_start = time.time()
        data = sensor.get_raw_acceleration()
        running_a_min = tuple(map(lambda x, y: min(x, y), running_a_min, data))
        running_a_max = tuple(map(lambda x, y: max(x, y), running_a_max, data))
        time.sleep(0.02)


if __name__ == "__main__":
    perform_calibration()
