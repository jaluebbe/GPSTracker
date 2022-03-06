#!/usr/bin/env python3
# code is partly based on https://github.com/pimoroni/enviro-phat/blob/master/library/envirophat/lsm303d.py
import smbus
import time
import json
import os
import socket
import struct
import numpy as np
from ahrs.filters import Tilt


class Lsm:
    def __init__(self, config_path=None):
        self.hostname = socket.gethostname()
        self.GYR_ADDRESS = None
        if config_path is None:
            config_path = os.path.join(pwd, "lsm_calibration.json")
        if not os.path.isfile(config_path):
            # no calibration data present, using default calibration
            config_path = os.path.join(pwd, "lsm_calibration_example.json")
        with open(config_path) as json_file:
            self.calibration = json.load(json_file)

    def get_raw_acceleration(self):
        # in order to read multiple bytes the high bit of the sub address must be
        # asserted so we |0x80 to enable register auto-increment
        raw = self.bus.read_i2c_block_data(
            self.ACC_ADDRESS, self.OUT_X_L_A | 0x80, 6
        )
        return list(struct.unpack("<hhh", bytearray(raw)))

    def get_raw_magnetometer(self):
        raw = self.bus.read_i2c_block_data(
            self.MAG_ADDRESS, self.OUT_X_L_M | 0x80, 6
        )
        return list(struct.unpack("<hhh", bytearray(raw)))

    def get_raw_gyro(self):
        raw = self.bus.read_i2c_block_data(
            self.GYR_ADDRESS, self.OUT_X_L_G | 0x80, 6
        )
        return list(struct.unpack("<hhh", bytearray(raw)))

    def get_acceleration(self):
        """ returns acceleration as [[x, y, z]] in units of m/s^2.
        """
        data = self.get_raw_acceleration()
        calibration = self.calibration
        scaling = self.ACCEL_SCALE * calibration["g"]
        corrected = [
            (data[0] - calibration["a_offset_x"]) * calibration["scale_a_x"],
            (data[1] - calibration["a_offset_y"]) * calibration["scale_a_y"],
            (data[2] - calibration["a_offset_z"]) * calibration["scale_a_z"],
        ]
        return np.array([corrected]) * scaling

    def get_magnetometer(self):
        """ returns magnetic flux density as [[x, y, z]] in units of mT.
        """
        data = self.get_raw_magnetometer()
        scaling = self.MAG_SCALE
        return np.array([data]) * scaling

    def get_gyro(self):
        """ returns angular velocity as [[x, y, z]] in units of dps.
        """
        data = self.get_raw_gyro()
        calibration = self.calibration
        scaling = self.GYR_SCALE
        corrected = [
            data[0] - calibration["g_offset_x"],
            data[1] - calibration["g_offset_y"],
            data[2] - calibration["g_offset_z"]
        ]
        return np.array([corrected]) * scaling

    def get_sensor_data(self):
        timestamp = time.time()
        roll, pitch, yaw = Tilt(
            self.get_acceleration() * [1, -1, 1], as_angles=True
        ).Q[0]
        raw_magnetometer = self.get_raw_magnetometer()
        sensor_data = {
            "sensor": self.sensor,
            "hostname": self.hostname,
            "i_utc": round(timestamp, 3),
            "roll": round(roll, 1),
            "pitch": round(pitch, 1),
            "raw_magnetometer": raw_magnetometer,
        }
        return sensor_data
