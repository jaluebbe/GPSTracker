#!venv/bin/python3
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


class RotationAnalysis:
    def __init__(self):
        self.redis_connection = redis.Redis(decode_responses=True)
        self._pubsub = self.redis_connection.pubsub()
        self._pubsub.subscribe("imu")
        self.old_rotations = self._get_stored_value("rotations", 0)
        self.old_compass_rotations = self._get_stored_value(
            "compass_rotations", 0
        )
        self.trips = self._get_stored_value("trips", 0)
        self.on_trip = False
        self.trip_start = None
        self.min_trip_speed = 1
        self.min_trip_duration = 120
        self.archive = False
        self.last_msg = None
        self.compass = Compass(self.old_compass_rotations)
        self.gyro = Gyro(self.old_rotations)

    def _get_stored_value(self, key, default):
        stored_value = self.redis_connection.get(key)
        return json.loads(stored_value) if stored_value is not None else default

    def process_message(self, item):
        if item["type"] != "message":
            return

        data = json.loads(item["data"])

        if item["channel"] == "imu":
            self.process_imu_data(data)

    def process_imu_data(self, data):
        angular_rate = data["gyro"][2]
        timestamp = data["i_utc"]
        self.gyro.set_gyro_data(angular_rate, timestamp)
        mag_x = data["raw_magnetometer"][0]
        mag_y = data["raw_magnetometer"][1]
        self.compass.set_mag_data(mag_x, mag_y)

        if self.on_trip:
            trip_duration = data["i_utc"] - self.trip_start

        if self.gyro.rpm > self.min_trip_speed and not self.on_trip:
            self.on_trip = True
            self.trip_start = timestamp
            trip_duration = 0
        elif self.gyro.rpm < self.min_trip_speed and self.on_trip:
            self.on_trip = False
            if trip_duration > self.min_trip_duration:
                self.trips += 1
            self.archive = True

        if self.gyro.rotations > self.old_rotations + 1:
            self.redis_connection.set(
                "rotations", json.dumps(self.gyro.rotations)
            )
            self.old_rotations = self.gyro.rotations

        if self.compass.rotations > self.old_compass_rotations + 1:
            self.redis_connection.set(
                "compass_rotations", json.dumps(self.compass.rotations)
            )
            self.old_compass_rotations = self.compass.rotations

        msg = {
            "rotations": int(self.gyro.rotations),
            "compass_rotations": int(self.compass.rotations),
            "rpm": round(self.gyro.rpm, 3),
            "heading": round(self.compass.heading, 3),
            "trips": self.trips,
            "on_trip": self.on_trip,
            "trip_start": self.trip_start,
        }

        if self.on_trip:
            msg["trip_duration"] = int(trip_duration)

        if self.last_msg is None or timestamp - self.last_msg > 0.3:
            self.redis_connection.publish("rotation", json.dumps(msg))
            self.last_msg = timestamp

        if self.archive:
            self.archive = False
            msg["trip_stop"] = timestamp
            key = f"rotation:{data['i_hostname']}:{time.strftime('%Y%m%d')}"
            for _key in ("rpm", "on_trip", "heading"):
                msg.pop(_key, None)
            self.redis_connection.lpush(key, json.dumps(msg))
            print(json.dumps(msg))
            self.redis_connection.set("trips", json.dumps(self.trips))

    def run(self):
        for item in self._pubsub.listen():
            self.process_message(item)
            time.sleep(0.05)


if __name__ == "__main__":
    gyr_calibration.calibrate()
    rotation_analysis = RotationAnalysis()
    rotation_analysis.run()
