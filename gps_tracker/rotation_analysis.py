#!/usr/bin/env python3
import json
import redis
import numpy as np
import time


if __name__ == "__main__":
    redis_connection = redis.Redis(decode_responses=True)
    _pubsub = redis_connection.pubsub()
    _pubsub.subscribe("imu")
    t_old = None
    stored_turns = redis_connection.get("rotations")
    if stored_turns is None:
        rotations = 0
    else:
        rotations = json.loads(stored_turns)
    stored_trips = redis_connection.get("trips")
    if stored_trips is None:
        trips = 0
    else:
        trips = json.loads(stored_trips)
    on_trip = False
    trip_start = None
    min_trip_speed = 3
    min_trip_duration = 10
    archive = False
    last_msg = None
    old_rotations = rotations
    for item in _pubsub.listen():
        if not item["type"] == "message":
            continue
        if item["channel"] == "imu":
            _data = json.loads(item["data"])
            angular_rate = _data["gyro"][2]
            rpm = angular_rate * 60 / (2 * np.pi)
            if on_trip:
                trip_duration = _data["i_utc"] - trip_start
            if rpm > min_trip_speed and not on_trip:
                on_trip = True
                trip_start = _data["i_utc"]
                trip_duration = 0
            elif rpm < min_trip_speed and on_trip:
                on_trip = False
                if trip_duration > min_trip_duration:
                    trips += 1
                archive = True
            if t_old is not None:
                dt = _data["i_utc"] - t_old
                rotations += angular_rate * dt / (2 * np.pi)
                if rotations > old_rotations + 1:
                    redis_connection.set("rotations", json.dumps(rotations))
                    old_rotations = rotations
            msg = {
                "rotations": int(rotations),
                "rpm": round(rpm, 3),
                "trips": trips,
                "on_trip": on_trip,
                "trip_start": trip_start,
            }
            if on_trip:
                msg["trip_duration"] = int(trip_duration)
            if last_msg is None or _data["i_utc"] - last_msg > 0.3:
                redis_connection.publish("rotation", json.dumps(msg))
                last_msg = _data["i_utc"]
            if archive:
                archive = False
                msg["trip_stop"] = _data["i_utc"]
                key = "rotation:{}:{}".format(
                    _data["i_hostname"], time.strftime("%Y%m%d")
                )
                for _key in ("rpm", "on_trip"):
                    msg.pop(_key, None)
                redis_connection.lpush(key, json.dumps(msg))
                print(json.dumps(msg))
                redis_connection.set("trips", json.dumps(trips))
            t_old = _data["i_utc"]
