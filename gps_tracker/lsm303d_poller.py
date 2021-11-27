#!/usr/bin/env python3
# code is partly based on https://github.com/pimoroni/enviro-phat/blob/master/library/envirophat/lsm303d.py
import smbus
import time
import json
import socket
import redis
import os
import struct
import numpy as np
from ahrs.filters import Tilt

redis_connection = redis.Redis()

WHO_AM_I = 0x0F
CTRL_REG0 = 0x1F
CTRL_REG1 = 0x20
CTRL_REG2 = 0x21
CTRL_REG3 = 0x22
CTRL_REG4 = 0x23
CTRL_REG5 = 0x24
CTRL_REG6 = 0x25
CTRL_REG7 = 0x26
OUT_X_L_A = 0x28
OUT_X_H_A = 0x29
OUT_Y_L_A = 0x2A
OUT_Y_H_A = 0x2B
OUT_Z_L_A = 0x2C
OUT_Z_H_A = 0x2D

ACCEL_SCALE = 2  # +/- 2g


class DeviceNotFound(IOError):
    pass


class Lsm303d:
    def __init__(self, i2c_address=0x1D, config_path=None):
        self.i2c_address = i2c_address
        self.initialize_sensor()
        self.hostname = socket.gethostname()
        # ensure that the sensor is really initialized to avoid false data
        self.initialize_sensor()
        pwd = os.path.dirname(os.path.abspath(__file__))
        if config_path is None:
            config_path = os.path.join(pwd, "lsm303d_calibration.json")
        if not os.path.isfile(config_path):
            # no calibration data present, using default calibration
            config_path = os.path.join(pwd, "lsm303d_calibration_example.json")
        with open(config_path) as json_file:
            self.calibration = json.load(json_file)

    def initialize_sensor(self):
        # Get I2C bus
        self.bus = smbus.SMBus(1)
        whoami = self.bus.read_byte_data(self.i2c_address, WHO_AM_I)
        if whoami == 0x49:
            self.bus.write_byte_data(self.i2c_address, CTRL_REG1, 0x5F)
            self.bus.write_byte_data(self.i2c_address, CTRL_REG2, 0xC0)
            self.bus.write_byte_data(self.i2c_address, CTRL_REG3, 0x00)
            self.bus.write_byte_data(self.i2c_address, CTRL_REG4, 0x00)
            self.bus.write_byte_data(self.i2c_address, CTRL_REG5, 0x18)
            self.bus.write_byte_data(self.i2c_address, CTRL_REG6, 0x00)
            self.bus.write_byte_data(self.i2c_address, CTRL_REG7, 0x00)
        else:
            raise DeviceNotFound(f"LSM303D not found on {self.i2c_address}")
        time.sleep(0.5)

    def get_raw_acceleration(self):
        # in order to read multiple bytes the high bit of the sub address must be
        # asserted so we |0x80 to enable register auto-increment
        raw = self.bus.read_i2c_block_data(
            self.i2c_address, OUT_X_L_A | 0x80, 6
        )
        return list(struct.unpack("<hhh", bytearray(raw)))

    def get_acceleration(self):
        """ returns acceleration as [[x, y, z]] in units of m/s^2.
        """
        data = self.get_raw_acceleration()
        calibration = self.calibration
        scaling = ACCEL_SCALE * calibration["g"] * 2 ** -15
        corrected = [
            (data[0] - calibration["a_offset_x"]) * calibration["scale_a_x"],
            (data[1] - calibration["a_offset_y"]) * calibration["scale_a_y"],
            (data[2] - calibration["a_offset_z"]) * calibration["scale_a_z"],
        ]
        return np.array([corrected]) * scaling

    def get_sensor_data(self):
        timestamp = time.time()
        roll, pitch, yaw = Tilt(self.get_acceleration(), as_angles=True).Q[0]
        sensor_data = {
            "hostname": self.hostname,
            "i_utc": round(timestamp, 2),
            "roll": round(roll, 1),
            "pitch": round(pitch, 1),
        }
        print(sensor_data)
        return sensor_data


if __name__ == "__main__":

    sensor = Lsm303d()
    while True:
        sensor_data = sensor.get_sensor_data()
        redis_connection.publish("imu", json.dumps(sensor_data))
        time.sleep(0.08)
