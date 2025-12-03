#!/usr/bin/env python3
import json
import redis
import numpy as np

redis_connection = redis.Redis(decode_responses=True)


def _compute_offset(m_min, m_max):
    """Compute offset as midpoint between min and max values."""
    return tuple((mn + mx) / 2 for mn, mx in zip(m_min, m_max))


def _save_offset(offset):
    """Save offset to Redis."""
    redis_connection.set("m_offset", json.dumps(offset))
    print(f"Saved m_offset to Redis: {offset}")


def perform_calibration():
    measuring_duration = 30.0
    running_m_min = (32767, 32767, 32767)
    running_m_max = (-32768, -32768, -32768)
    
    print("Move/rotate sensor in all relevant directions for calibration.")
    input(f"Press Enter to start ({measuring_duration}s): ")
    
    while True:
        _pubsub = redis_connection.pubsub()
        _pubsub.subscribe("imu", "imu_barometer")
        t_start = None
        
        for item in _pubsub.listen():
            if item["type"] != "message":
                continue
            _data = json.loads(item["data"])
            if t_start is None:
                t_start = _data["i_utc"]
            elif _data["i_utc"] > t_start + measuring_duration:
                break
            
            m_data = _data["raw_magnetometer"]
            running_m_min = (
                min(running_m_min[0], m_data[0]),
                min(running_m_min[1], m_data[1]),
                min(running_m_min[2], m_data[2]),
            )
            running_m_max = (
                max(running_m_max[0], m_data[0]),
                max(running_m_max[1], m_data[1]),
                max(running_m_max[2], m_data[2]),
            )
        
        x_range = running_m_max[0] - running_m_min[0]
        y_range = running_m_max[1] - running_m_min[1]
        z_range = running_m_max[2] - running_m_min[2]
        
        m_offset = _compute_offset(running_m_min, running_m_max)
        
        print(f"Ranges: x={x_range}, y={y_range}, z={z_range}")
        print(f"Computed offset: {m_offset}")
        
        response = input(
            "(Enter)=continue for +30s, (s)=save, (r)=reset, (a)=abort: "
        ).strip().lower()
        
        if response == "":
            measuring_duration += 30.0
            print(f"Continuing for another 30s (total: {measuring_duration}s)...")
            continue
        elif response == "r":
            running_m_min = (32767, 32767, 32767)
            running_m_max = (-32768, -32768, -32768)
            measuring_duration = 30.0
            print("Min/Max reset. Starting fresh.")
            continue
        elif response == "a":
            print("Calibration aborted.")
            return
        elif response == "s":
            _save_offset(m_offset)
            return
        else:
            print("Invalid input. Please use Enter, s, r, or a.")


if __name__ == "__main__":
    perform_calibration()
