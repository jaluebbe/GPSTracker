#!/usr/bin/env python3
import json
import redis
import numpy as np

redis_connection = redis.Redis(decode_responses=True)

Z_RANGE_RATIO_THRESHOLD = 0.2  # motion ratio threshold for 2D suggestion


def _compute_midpoints(m_min, m_max):
    return tuple((mn + mx) / 2 for mn, mx in zip(m_min, m_max))


def _compute_offsets(m_min, m_max, previous_offset=None):
    """Return (3D_offset, 2D_offset)."""
    m_offset_3d = _compute_midpoints(m_min, m_max)
    prev_z = 0.0 if previous_offset is None else previous_offset[2]
    m_offset_2d = (m_offset_3d[0], m_offset_3d[1], prev_z)
    return m_offset_3d, m_offset_2d


def _save_offset(chosen_offset, is_3d):
    redis_connection.set("m_offset", json.dumps(chosen_offset))
    key = "m_offset_3d" if is_3d else "m_offset_2d"
    redis_connection.set(key, json.dumps(chosen_offset))
    print(f"saved m_offset and {key} to Redis (other offset preserved)")


def perform_calibration():
    measuring_duration = 15.0
    running_m_min = (32767, 32767, 32767)
    running_m_max = (-32768, -32768, -32768)
    print("Rotate (3D) or spin (2D) for calibration.")
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
        avg_xy_range = (x_range + y_range) / 2 or 1.0
        ratio = z_range / avg_xy_range if avg_xy_range else 0.0
        prev_offset_raw = redis_connection.get("m_offset")
        previous_offset = json.loads(prev_offset_raw) if prev_offset_raw else None
        m_offset_3d, m_offset_2d = _compute_offsets(
            running_m_min, running_m_max, previous_offset
        )
        print(
            f"Ranges x:{x_range} y:{y_range} z:{z_range} "
            f"(z/avg_xy={ratio:.3f})"
        )
        print(f"3D offset: {m_offset_3d}")
        print(
            "2D offset (z kept "
            f"{'previous' if previous_offset else '0.0'}): {m_offset_2d}"
        )
        suggested = "3" if ratio >= Z_RANGE_RATIO_THRESHOLD else "2"
        response = input(
            "(Enter)=continue, (r)=reset, (s)=save suggested, (3)=save 3D, "
            "(2)=save 2D, (a)=abort "
            f"[suggested {suggested}]: "
        ).strip()
        if response not in {"a", "s", "3", "2", "r"}:
            continue
        if response == "r":
            running_m_min = (32767, 32767, 32767)
            running_m_max = (-32768, -32768, -32768)
            print("Min/Max reset.")
            continue
        if response == "a":
            print("Aborted.")
            return
        if response == "s":
            is_3d = suggested == "3"
            chosen = m_offset_3d if is_3d else m_offset_2d
        elif response == "3":
            is_3d = True
            chosen = m_offset_3d
        elif response == "2":
            is_3d = False
            chosen = m_offset_2d
        _save_offset(chosen, is_3d)
        return


if __name__ == "__main__":
    perform_calibration()
