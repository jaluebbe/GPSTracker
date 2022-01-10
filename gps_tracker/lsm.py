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
    def __init__(self):
        self.hostname = socket.gethostname()

    def get_raw_acceleration(self):
        # in order to read multiple bytes the high bit of the sub address must be
        # asserted so we |0x80 to enable register auto-increment
        raw = self.bus.read_i2c_block_data(
            self.i2c_address, self.OUT_X_L_A | 0x80, 6
        )
        return list(struct.unpack("<hhh", bytearray(raw)))

    def get_raw_magnetometer(self):
        raw = self.bus.read_i2c_block_data(
            self.i2c_address, self.OUT_X_L_M | 0x80, 6
        )
        return list(struct.unpack("<hhh", bytearray(raw)))

    def get_acceleration(self):
        """ returns acceleration as [[x, y, z]] in units of m/s^2.
        """
        data = self.get_raw_acceleration()
        calibration = self.calibration
        scaling = self.ACCEL_SCALE * calibration["g"] * 2 ** -15
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
        scaling = self.MAG_SCALE * 2 ** -15
        return np.array([data]) * scaling

    def get_sensor_data(self):
        timestamp = time.time()
        roll, pitch, yaw = Tilt(
            self.get_acceleration() * [1, -1, 1], as_angles=True
        ).Q[0]
        raw_magnetometer = self.get_raw_magnetometer()
        sensor_data = {
            "hostname": self.hostname,
            "i_utc": round(timestamp, 3),
            "roll": round(roll, 1),
            "pitch": round(pitch, 1),
            "raw_magnetometer": raw_magnetometer,
        }
        return sensor_data
