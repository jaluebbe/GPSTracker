#!/usr/bin/env python3
# code is partly based on https://github.com/pimoroni/enviro-phat/blob/master/library/envirophat/lsm303d.py
import smbus
import time
import struct
from lsm import Lsm

ACC_ADDRESS = 0x1D
MAG_ADDRESS = 0x1D
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
OUT_X_L_M = 0x08

ACCEL_SCALE = 6.1e-5  # +/- 2g full scale
MAG_SCALE = 8.0e-6  # +/- 0.2 mT full scale


class DeviceNotFound(IOError):
    pass


class Lsm303d(Lsm):
    def __init__(self, config_path=None):
        super().__init__(config_path)
        self.sensor = "LSM303D"
        self.ACCEL_SCALE = ACCEL_SCALE
        self.MAG_SCALE = MAG_SCALE
        self.OUT_X_L_A = OUT_X_L_A
        self.OUT_X_L_M = OUT_X_L_M
        self.ACC_ADDRESS = ACC_ADDRESS
        self.MAG_ADDRESS = MAG_ADDRESS
        self.initialize_sensor()
        # ensure that the sensor is really initialized to avoid false data
        self.initialize_sensor()

    def initialize_sensor(self):
        # Get I2C bus
        self.bus = smbus.SMBus(1)
        whoami = self.bus.read_byte_data(self.ACC_ADDRESS, WHO_AM_I)
        if whoami == 0x49:
            self.bus.write_byte_data(self.ACC_ADDRESS, CTRL_REG1, 0x57)
            self.bus.write_byte_data(self.ACC_ADDRESS, CTRL_REG2, 0xC0)
            self.bus.write_byte_data(self.ACC_ADDRESS, CTRL_REG3, 0x00)
            self.bus.write_byte_data(self.ACC_ADDRESS, CTRL_REG4, 0x00)
            self.bus.write_byte_data(self.ACC_ADDRESS, CTRL_REG5, 0x10)
            self.bus.write_byte_data(self.ACC_ADDRESS, CTRL_REG6, 0x00)
            self.bus.write_byte_data(self.ACC_ADDRESS, CTRL_REG7, 0x00)
        else:
            raise DeviceNotFound(f"LSM303D not found on {self.i2c_address}")
        time.sleep(0.5)

    def update_raw_acceleration(self):
        # in order to read multiple bytes the high bit of the sub address must be
        # asserted so we |0x80 to enable register auto-increment
        raw = self.bus.read_i2c_block_data(
            self.ACC_ADDRESS, self.OUT_X_L_A | 0x80, 6
        )
        self.raw_acceleration = list(struct.unpack("<hhh", bytearray(raw)))
        return self.raw_acceleration

    def update_raw_magnetometer(self):
        raw = self.bus.read_i2c_block_data(
            self.MAG_ADDRESS, self.OUT_X_L_M | 0x80, 6
        )
        self.raw_magnetometer = list(struct.unpack("<hhh", bytearray(raw)))
        return self.raw_magnetometer

    def update_raw_gyro(self):
        raw = self.bus.read_i2c_block_data(
            self.GYR_ADDRESS, self.OUT_X_L_G | 0x80, 6
        )
        self.raw_gyro = list(struct.unpack("<hhh", bytearray(raw)))
        return self.raw_gyro
