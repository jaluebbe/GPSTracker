#!/usr/bin/env python3
import json
import redis
import numpy as np
import time
import gyr_calibration


def heading_diff(new_heading: float, old_heading: float) -> float:
    difference = new_heading - old_heading
    if difference < -180:
        difference += 360
    elif difference > 180:
        difference -= 360
    return difference


class Compass:
    def __init__(self, rotations: float = 0):
        self.mag_x_min = 32768
        self.mag_x_max = -32768
        self.mag_y_min = 32768
        self.mag_y_max = -32768
        self.rotations = rotations
        self._old_heading = None
        self.heading = None

    def set_mag_data(self, x, y):
        self.mag_x_min = min(self.mag_x_min, x)
        self.mag_x_max = max(self.mag_x_max, x)
        self.mag_y_min = min(self.mag_y_min, y)
        self.mag_y_max = max(self.mag_y_max, y)
        self.heading = (
            np.arctan2(
                -(y - 0.5 * (self.mag_y_min + self.mag_y_max)),
                x - 0.5 * (self.mag_x_min + self.mag_x_max),
            )
            / np.pi
            * 180
        )
        if self._old_heading is not None:
            self.rotations += (
                heading_diff(self.heading, self._old_heading) / 360
            )
        self._old_heading = self.heading


class Gyro:
    def __init__(self, rotations: float = 0):
        self.rotations = rotations
        self.gyro_offset = 0
        self._old_timestamp = None

    def set_gyro_data(self, angular_rate, timestamp):
        self.rpm = (angular_rate + self.gyro_offset) * 60 / (2 * np.pi)
        if self._old_timestamp is not None:
            dt = timestamp - self._old_timestamp
            self.rotations += angular_rate * dt / (2 * np.pi)
        self._old_timestamp = timestamp


if __name__ == "__main__":
    gyr_calibration.calibrate()
    redis_connection = redis.Redis(decode_responses=True)
    _pubsub = redis_connection.pubsub()
    _pubsub.subscribe("imu")
    stored_turns = redis_connection.get("rotations")
    if stored_turns is None:
        old_rotations = 0
    else:
        old_rotations = json.loads(stored_turns)
    stored_compass_turns = redis_connection.get("compass_rotations")
    if stored_compass_turns is None:
        old_compass_rotations = 0
    else:
        old_compass_rotations = json.loads(stored_compass_turns)
    stored_trips = redis_connection.get("trips")
    if stored_trips is None:
        trips = 0
    else:
        trips = json.loads(stored_trips)
    on_trip = False
    trip_start = None
    min_trip_speed = 1
    min_trip_duration = 120
    archive = False
    last_msg = None
    gyro_offset = 0
    compass = Compass(old_compass_rotations)
    gyro = Gyro(old_rotations)
    for item in _pubsub.listen():
        if not item["type"] == "message":
            continue
        if item["channel"] == "imu":
            _data = json.loads(item["data"])
            angular_rate = _data["gyro"][2]
            timestamp = _data["i_utc"]
            gyro.set_gyro_data(angular_rate, timestamp)
            mag_x = _data["raw_magnetometer"][0]
            mag_y = _data["raw_magnetometer"][1]
            compass.set_mag_data(mag_x, mag_y)
            if on_trip:
                trip_duration = _data["i_utc"] - trip_start
            if gyro.rpm > min_trip_speed and not on_trip:
                on_trip = True
                trip_start = timestamp
                trip_duration = 0
            elif gyro.rpm < min_trip_speed and on_trip:
                on_trip = False
                if trip_duration > min_trip_duration:
                    trips += 1
                archive = True
            if gyro.rotations > old_rotations + 1:
                redis_connection.set("rotations", json.dumps(gyro.rotations))
                old_rotations = gyro.rotations
            if compass.rotations > old_compass_rotations + 1:
                redis_connection.set(
                    "compass_rotations", json.dumps(compass.rotations)
                )
                old_compass_rotations = compass.rotations
            msg = {
                "rotations": int(gyro.rotations),
                "compass_rotations": int(compass.rotations),
                "rpm": round(gyro.rpm, 3),
                "heading": round(compass.heading, 3),
                "trips": trips,
                "on_trip": on_trip,
                "trip_start": trip_start,
            }
            if on_trip:
                msg["trip_duration"] = int(trip_duration)
            if last_msg is None or timestamp - last_msg > 0.3:
                redis_connection.publish("rotation", json.dumps(msg))
                last_msg = timestamp
            if archive:
                archive = False
                msg["trip_stop"] = timestamp
                key = "rotation:{}:{}".format(
                    _data["i_hostname"], time.strftime("%Y%m%d")
                )
                for _key in ("rpm", "on_trip", "heading"):
                    msg.pop(_key, None)
                redis_connection.lpush(key, json.dumps(msg))
                print(json.dumps(msg))
                redis_connection.set("trips", json.dumps(trips))
