#!/usr/bin/env python3
# code is partly based on https://github.com/pimoroni/enviro-phat/blob/master/library/envirophat/lsm303d.py
import time
import json
import os
import socket
import numpy as np
from ahrs.filters import Complementary
from ahrs import Quaternion, RAD2DEG, DEG2RAD


class Lsm:
    def __init__(self, config_path=None):
        self.hostname = socket.gethostname()
        self.GYR_ADDRESS = None
        self.MAG_ADDRESS = None
        self.ACC_ADDRESS = None
        self.raw_acceleration = None
        self.raw_magnetometer = None
        self.raw_gyro = None
        self.old_q = None
        self.old_timestamp = None
        self.complementary = Complementary()
        pwd = os.path.dirname(os.path.abspath(__file__))
        if config_path is None:
            config_path = os.path.join(pwd, "lsm_calibration.json")
        if not os.path.isfile(config_path):
            # no calibration data present, using default calibration
            config_path = os.path.join(pwd, "lsm_calibration_example.json")
        with open(config_path) as json_file:
            self.calibration = json.load(json_file)

    def get_acceleration(self):
        """returns acceleration as [x, y, z] in units of m/s^2."""
        self.update_raw_acceleration()
        data = np.array(self.raw_acceleration)
        calibration = self.calibration
        scaling = self.ACCEL_SCALE * calibration["g"]
        centered = data - calibration["a_offset"]
        corrected = np.array(self.calibration["a_matrix"]).dot(centered)
        return corrected * scaling * calibration["a_sign"]

    def get_magnetometer(self):
        """returns magnetic flux density as [x, y, z] in units of mT."""
        self.update_raw_magnetometer()
        data = np.array(self.raw_magnetometer)
        calibration = self.calibration
        scaling = self.MAG_SCALE
        centered = data - calibration["m_offset"]
        corrected = np.array(self.calibration["m_matrix"]).dot(centered)
        return corrected * scaling * calibration["m_sign"]

    def get_gyro(self):
        """returns angular velocity as [x, y, z] in units of rad/s."""
        self.update_raw_gyro()
        data = np.array(self.raw_gyro)
        calibration = self.calibration
        scaling = self.GYR_SCALE * DEG2RAD
        corrected = data - calibration["g_offset"]
        return corrected * scaling * calibration["g_sign"]

    def get_sensor_data(self):
        timestamp = time.time()
        acc = self.get_acceleration()
        if self.MAG_ADDRESS is not None:
            magnetometer = self.get_magnetometer()
        else:
            magnetometer = None
        q_am = self.complementary.am_estimation(acc, magnetometer)
        if self.old_timestamp is not None and self.GYR_ADDRESS is not None:
            dt = timestamp - self.old_timestamp
            self.complementary.Dt = dt
            gyr = np.array(self.get_gyro())
            q_omega = self.complementary.attitude_propagation(self.old_q, gyr)
            roll_gyr, pitch_gyr, yaw_gyr = (
                Quaternion(q_omega).to_angles() * RAD2DEG
            )

            # Complementary Estimation
            gain = 0.02
            if np.linalg.norm(q_omega + q_am) < np.sqrt(2):
                q_est = (1.0 - gain) * q_omega - gain * q_am
            else:
                q_est = (1.0 - gain) * q_omega + gain * q_am
            q = q_est / np.linalg.norm(q_est)
        else:
            q = q_am
            yaw_gyr = 0
        roll_acc, pitch_acc, yaw_acc = Quaternion(q_am).to_angles() * RAD2DEG
        roll, pitch, yaw = Quaternion(q).to_angles() * RAD2DEG
        sensor_data = {
            "i_sensor": self.sensor,
            "i_hostname": self.hostname,
            "i_utc": round(timestamp, 3),
            "roll": round(roll, 2),
            "pitch": round(pitch, 2),
            "roll_acc": round(roll_acc, 2),
            "yaw_gyr": round(yaw_gyr, 2),
        }
        if self.MAG_ADDRESS is not None:
            sensor_data["raw_magnetometer"] = self.raw_magnetometer
            sensor_data["yaw"] = round(yaw, 2)
        self.old_timestamp = timestamp
        self.old_q = q
        return sensor_data
