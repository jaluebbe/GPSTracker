#!venv/bin/python3
import json
import math
import redis
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
        self.rotations = rotations
        self._old_heading = None
        self.heading = None
        self.yaw_invert = True

    def set_calibrated_yaw(self, yaw_deg: float):
        heading = -yaw_deg if self.yaw_invert else yaw_deg
        if heading <= -180:
            heading += 360
        elif heading > 180:
            heading -= 360
        self.heading = heading
        if self._old_heading is not None:
            self.rotations += (
                heading_diff(self.heading, self._old_heading) / 360
            )
        self._old_heading = self.heading


class RotationAnalysis:
    def __init__(self):
        self.redis_connection = redis.Redis(decode_responses=True)
        self._pubsub = self.redis_connection.pubsub()
        self._pubsub.subscribe("imu", "imu_barometer")
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
        self.rpm = 0

    def _get_stored_value(self, key, default):
        stored_value = self.redis_connection.get(key)
        return json.loads(stored_value) if stored_value is not None else default

    def process_message(self, item):
        if item["type"] != "message":
            return
        data = json.loads(item["data"])
        self.process_imu_data(data)

    def process_imu_data(self, data):
        trip_duration = 0
        angular_rate = data["gyro"][2]
        timestamp = data["i_utc"]
        self.rpm = angular_rate * 60 / (2 * math.pi)
        self.compass.set_calibrated_yaw(data["yaw"])

        if self.on_trip:
            trip_duration = data["i_utc"] - self.trip_start

        if self.rpm > self.min_trip_speed and not self.on_trip:
            self.on_trip = True
            self.trip_start = timestamp
            trip_duration = 0
        elif self.rpm < self.min_trip_speed and self.on_trip:
            self.on_trip = False
            if trip_duration > self.min_trip_duration:
                self.trips += 1
            self.archive = True

        if self.compass.rotations > self.old_compass_rotations + 1:
            self.redis_connection.set(
                "compass_rotations", json.dumps(self.compass.rotations)
            )
            self.old_compass_rotations = self.compass.rotations

        msg = {
            "utc": timestamp,
            "compass_rotations": int(self.compass.rotations),
            "rpm": round(self.rpm, 3),
            "heading": round(self.compass.heading, 3),
            "trips": self.trips,
            "on_trip": self.on_trip,
            "trip_start": self.trip_start,
        }

        if self.on_trip:
            msg["trip_duration"] = int(trip_duration)

        if self.last_msg is None or timestamp - self.last_msg > 1.0:
            self.redis_connection.publish("rotation", json.dumps(msg))
            self.last_msg = timestamp

        if self.archive:
            self.archive = False
            msg["trip_stop"] = timestamp
            key = f"rotation:{data['i_hostname']}:{time.strftime('%Y%m%d')}"
            for _key in ("rpm", "on_trip", "heading"):
                msg.pop(_key, None)
            if msg["trip_stop"] - msg["trip_start"] > 10:
                self.redis_connection.lpush(key, json.dumps(msg))
                print(json.dumps(msg))
            self.redis_connection.set("trips", json.dumps(self.trips))

    def run(self):
        for item in self._pubsub.listen():
            self.process_message(item)


if __name__ == "__main__":
    gyr_calibration.calibrate()
    rotation_analysis = RotationAnalysis()
    rotation_analysis.run()
