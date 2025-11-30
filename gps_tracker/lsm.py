# code is partly based on https://github.com/pimoroni/enviro-phat/blob/master/library/envirophat/lsm303d.py
import time
import json
import socket
import redis
import numpy as np
from fusion_offset import FusionOffset
import math


class Lsm:
    def __init__(self, config_path=None):
        self.hostname = socket.gethostname()
        self.redis_connection = redis.Redis(decode_responses=True)
        self.GYR_ADDRESS = None
        self.MAG_ADDRESS = None
        self.ACC_ADDRESS = None
        self.raw_acceleration = None
        self.raw_magnetometer = None
        self.raw_gyro = None
        self.old_q = None
        self.old_timestamp = None
        self.gyro_offset = FusionOffset(25, threshold=0.9)
        self.calibration = {
            "g": 9.80665,
            "g_offset": [0.0, 0.0, 0.0],
            "a_offset": [0.0, 0.0, 0.0],
            "m_offset": [0.0, 0.0, 0.0],
            "m_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
            "rotation": [[0, -1, 0], [1, 0, 0], [0, 0, 1]],
        }
        self.use_ellipsoid_correction = False
        self.load_calibration()

    def load_calibration(self):
        for _key in self.calibration:
            _raw = self.redis_connection.get(_key)
            if _raw is None:
                continue
            _value = json.loads(_raw)
            if _key == "g_offset":
                if self.calibration[_key] != _value:
                    self.calibration[_key] = _value
                    self.gyro_offset = FusionOffset(25, threshold=0.9)
                continue
            self.calibration[_key] = _value
        self.redis_connection.set("calibration_updated", 0)

    def check_calibration(self):
        if self.redis_connection.get("calibration_updated") == "1":
            self.load_calibration()

    def get_acceleration(self):
        """returns acceleration as [x, y, z] in units of m/s^2."""
        self.update_raw_acceleration()
        data = np.array(self.raw_acceleration)
        calibration = self.calibration
        scaling = self.ACCEL_SCALE * self.calibration["g"]
        centered = data - calibration["a_offset"]
        rotated = np.array(self.calibration["rotation"]).dot(centered)
        return rotated * scaling

    def get_magnetometer(self):
        """returns magnetic flux density as [x, y, z] in units of mT."""
        self.update_raw_magnetometer()
        data = np.array(self.raw_magnetometer)
        calibration = self.calibration
        scaling = self.MAG_SCALE
        centered = data - calibration["m_offset"]
        if self.use_ellipsoid_correction:
            corrected = np.array(self.calibration["m_matrix"]).dot(centered)
        else:
            corrected = centered
        rotated = np.array(self.calibration["rotation"]).dot(corrected)
        return rotated * scaling

    def get_gyro_deg(self):
        """returns angular velocity as [x, y, z] in units of deg/s."""
        self.update_raw_gyro()
        data = np.array(self.raw_gyro)
        calibration = self.calibration
        corrected = data - calibration["g_offset"]
        rotated = np.array(self.calibration["rotation"]).dot(corrected)
        return self.gyro_offset.update(rotated * self.GYR_SCALE)

    def get_gyro(self):
        """returns angular velocity as [x, y, z] in units of rad/s."""
        return np.deg2rad(self.get_gyro_deg())

    def get_raw_gyro_temperature(self):
        self.update_raw_gyro_temperature()
        return self.raw_temperature

    def get_sensor_data(
        self, sensor_fusion: bool = True, use_mag: bool = False
    ) -> dict:
        """
        Collects and returns sensor data. May perform sensor fusion and
        add the combined sensor data to the output. The consideration of
        magnetometer data for sensor fusion is optional.

        :param bool sensor_fusion: perform sensor fusion defaults True
        :param bool use_mag: use magnetometer for sensor fusion defaults False
        :return: sensor data as dict
        """
        timestamp = time.time()
        sensor_data = {
            "i_sensor": self.sensor,
            "i_hostname": self.hostname,
            "i_utc": round(timestamp, 3),
        }
        self.check_calibration()
        if self.ACC_ADDRESS is not None:
            acc = self.get_acceleration()
            sensor_data["raw_acceleration"] = self.raw_acceleration
            sensor_data["acc"] = np.round(acc, 4).tolist()
            # Simple tilt (roll/pitch) if no fusion
            if not sensor_fusion:
                ax, ay, az = acc
                # hypot gives sqrt(ay^2 + az^2) (stable)
                denom = math.hypot(ay, az)
                if denom < 1e-6:  # avoid division issues in near free-fall
                    denom = 1e-6
                roll_deg = math.degrees(math.atan2(-ay, az))
                pitch_deg = math.degrees(math.atan2(ax, denom))
                sensor_data["roll"] = round(roll_deg, 2)
                sensor_data["pitch"] = round(pitch_deg, 2)
        if self.MAG_ADDRESS is not None:
            magnetometer = self.get_magnetometer()
            sensor_data["raw_magnetometer"] = self.raw_magnetometer
            mx, my = magnetometer[0], magnetometer[1]
            yaw_deg = math.degrees(math.atan2(my, mx))
            sensor_data["yaw"] = round(yaw_deg, 2)
        else:
            magnetometer = None
        if self.GYR_ADDRESS is not None:
            gyr = self.get_gyro()
            sensor_data["raw_gyro"] = self.raw_gyro
            sensor_data["gyro"] = np.round(gyr, 3).tolist()
            sensor_data["raw_gyro_temp"] = self.get_raw_gyro_temperature()
        if self.ACC_ADDRESS is not None and sensor_fusion:
            if self.old_timestamp is not None and self.GYR_ADDRESS is not None:
                dt = (
                    timestamp - self.old_timestamp
                )  # placeholder for future fusion
        return sensor_data
