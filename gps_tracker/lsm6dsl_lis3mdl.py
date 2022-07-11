#!/usr/bin/env python3
# code is partly based on https://github.com/ozzmaker/BerryIMU
import smbus
import time
import struct
from lsm import Lsm

ACC_ADDRESS = 0x6A
GYR_ADDRESS = 0x6A
MAG_ADDRESS = 0x1C

OUT_X_L_G = 0x22
OUT_X_L_A = 0x28
OUT_X_L_M = 0x28

WHO_AM_I = 0x0F

CTRL_1_XL = 0x10
CTRL_2_G = 0x11
CTRL_3_C = 0x12
CTRL_6_C = 0x15
CTRL_7_G = 0x16
CTRL_8_XL = 0x17
CTRL_REG1_M = 0x20
CTRL_REG2_M = 0x21
CTRL_REG3_M = 0x22

ACCEL_SCALE = 24.4e-5  # +/- 8g full scale
GYR_SCALE = 70e-3  # +/- 2000 dps full scale
MAG_SCALE = 14.6156e-6  # +/- 0.4 mT full scale


class DeviceNotFound(IOError):
    pass


class Lsm6dsl_Lis3mdl(Lsm):
    def __init__(self, config_path=None):
        super().__init__(config_path)
        self.sensor = "LSM6DSL+LIS3MDL"
        self.ACCEL_SCALE = ACCEL_SCALE
        self.GYR_SCALE = GYR_SCALE
        self.MAG_SCALE = MAG_SCALE
        self.OUT_X_L_A = OUT_X_L_A
        self.OUT_X_L_G = OUT_X_L_G
        self.OUT_X_L_M = OUT_X_L_M
        self.ACC_ADDRESS = ACC_ADDRESS
        self.GYR_ADDRESS = GYR_ADDRESS
        self.MAG_ADDRESS = MAG_ADDRESS
        self.initialize_sensor()
        # ensure that the sensor is really initialized to avoid false data
        self.initialize_sensor()

    def initialize_sensor(self):
        # Get I2C bus
        self.bus = smbus.SMBus(1)
        whoami_gyr = self.bus.read_byte_data(self.GYR_ADDRESS, WHO_AM_I)
        if whoami_gyr != 0x6A:
            raise DeviceNotFound("LSM6DSL not found")
        whoami_mag = self.bus.read_byte_data(self.MAG_ADDRESS, WHO_AM_I)
        if whoami_mag != 0x3D:
            raise DeviceNotFound("LIS3MDL not found")
        # accelerometer: 104Hz data rate, +/- 8g full scale
        self.bus.write_byte_data(self.ACC_ADDRESS, CTRL_1_XL, 0b0100_11_0_0)
        # gyro: 104Hz data rate, 2000 dps full scale
        self.bus.write_byte_data(self.GYR_ADDRESS, CTRL_2_G, 0b0100_11_0_0)
        # default values
        self.bus.write_byte_data(self.ACC_ADDRESS, CTRL_3_C, 0b00000100)
        # accelerometer high-performance mode disabled
        self.bus.write_byte_data(self.ACC_ADDRESS, CTRL_6_C, 0b0_0_0_1_0_0_00)
        # gyro high-performance mode disabled
        self.bus.write_byte_data(self.GYR_ADDRESS, CTRL_7_G, 0b1_0_00_0_0_0_0)
        # default values
        self.bus.write_byte_data(self.ACC_ADDRESS, CTRL_8_XL, 0b00000000)

        # initialise the magnetometer
        # Temp enable, medium performance, 80Hz data rate
        self.bus.write_byte_data(self.MAG_ADDRESS, CTRL_REG1_M, 0b1_01_111_0_0)
        # +/- 4 gauss
        self.bus.write_byte_data(self.MAG_ADDRESS, CTRL_REG2_M, 0b0_00_00000)
        # Continuous-conversion mode
        self.bus.write_byte_data(self.MAG_ADDRESS, CTRL_REG3_M, 0b000000_00)
        time.sleep(0.5)

    def update_raw_acceleration(self):
        raw = self.bus.read_i2c_block_data(self.ACC_ADDRESS, self.OUT_X_L_A, 6)
        self.raw_acceleration = list(struct.unpack("<hhh", bytearray(raw)))
        return self.raw_acceleration

    def update_raw_gyro(self):
        raw = self.bus.read_i2c_block_data(self.GYR_ADDRESS, self.OUT_X_L_G, 6)
        self.raw_gyro = list(struct.unpack("<hhh", bytearray(raw)))
        return self.raw_gyro

    def update_raw_magnetometer(self):
        raw = self.bus.read_i2c_block_data(self.MAG_ADDRESS, self.OUT_X_L_M, 6)
        self.raw_magnetometer = list(struct.unpack("<hhh", bytearray(raw)))
        return self.raw_magnetometer
