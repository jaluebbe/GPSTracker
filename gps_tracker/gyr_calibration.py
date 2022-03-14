#!/usr/bin/env python3
import time
import json
import numpy as np
from collections import deque
import lsm_poller

if __name__ == "__main__":
    measuring_duration = 5
    sensor = lsm_poller.get_lsm_sensor()
    d = deque()
    t_start = time.time()
    while True:
        now = time.time()
        if t_start + measuring_duration < now:
            print(list(np.median(d, axis=0)))
            break
        d.append(sensor.update_raw_gyro())
        time.sleep(0.02)
