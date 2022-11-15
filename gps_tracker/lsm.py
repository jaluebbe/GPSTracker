#!/usr/bin/env python3
# code is partly based on https://github.com/pimoroni/enviro-phat/blob/master/library/envirophat/lsm303d.py
import time
import json
import socket
import redis
import numpy as np
from ahrs.filters import Complementary
from ahrs import Quaternion, RAD2DEG, DEG2RAD


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
        self.complementary = Complementary()
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
        for _key in self.calibration.keys():
            _value = self.redis_connection.get(_key)
            if _value is None:
                continue
            self.calibration[_key] = json.loads(_value)
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

    def get_gyro(self):
        """returns angular velocity as [x, y, z] in units of rad/s."""
        self.update_raw_gyro()
        data = np.array(self.raw_gyro)
        calibration = self.calibration
        scaling = self.GYR_SCALE * DEG2RAD
        corrected = data - calibration["g_offset"]
        rotated = np.array(self.calibration["rotation"]).dot(corrected)
        return rotated * scaling

    def get_sensor_data(self, gain=0.02):
        """
        Collects and returns sensor data. May perform sensor fusion and
        add the combined sensor data to the output. Sensor fusion is disabled
        if the gain is None.

        :param float gain: complementary filter gain (defaults to 0.02)
        :return: sensor data
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
        if self.MAG_ADDRESS is not None:
            magnetometer = self.get_magnetometer()
            sensor_data["raw_magnetometer"] = self.raw_magnetometer
        else:
            magnetometer = None
        if self.GYR_ADDRESS is not None:
            gyr = self.get_gyro()
            sensor_data["raw_gyro"] = self.raw_gyro
            sensor_data["gyro"] = np.round(gyr, 3).tolist()

        if self.ACC_ADDRESS is not None and gain is not None:
            q_am = self.complementary.am_estimation(acc, magnetometer)
            if self.old_timestamp is not None and self.GYR_ADDRESS is not None:
                dt = timestamp - self.old_timestamp
                self.complementary.Dt = dt
                q_omega = self.complementary.attitude_propagation(
                    self.old_q, gyr
                )
                # Complementary Estimation
                if np.linalg.norm(q_omega + q_am) < np.sqrt(2):
                    q_est = (1.0 - gain) * q_omega - gain * q_am
                else:
                    q_est = (1.0 - gain) * q_omega + gain * q_am
                q = q_est / np.linalg.norm(q_est)
            else:
                q = q_am
            roll, pitch, yaw = Quaternion(q).to_angles()
            vertical_acceleration = np.sum(
                np.array(
                    [
                        -np.sin(pitch),
                        np.cos(pitch) * np.sin(roll),
                        np.cos(pitch) * np.cos(roll),
                    ]
                )
                * acc
            )
            sensor_data.update(
                {
                    "roll": -round(roll * RAD2DEG, 2),
                    "pitch": round(pitch * RAD2DEG, 2),
                    "vertical_acceleration": round(vertical_acceleration, 3),
                }
            )
            if self.MAG_ADDRESS is not None:
                sensor_data["yaw"] = -round(yaw * RAD2DEG, 2)
            self.old_timestamp = timestamp
            self.old_q = q
        return sensor_data
