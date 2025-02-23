# code is partly based on https://github.com/ozzmaker/BerryIMU
import smbus2
import time
import struct
from lsm import Lsm

MAG_ADDRESS = 0x1E
ACC_ADDRESS = 0x1E
GYR_ADDRESS = 0x6A

OUT_X_L_M = 0x08
OUT_X_L_A = 0x28
OUT_X_L_G = 0x28

WHO_AM_I = 0x0F

CTRL_REG1_XM = 0x20
CTRL_REG2_XM = 0x21
CTRL_REG5_XM = 0x24
CTRL_REG6_XM = 0x25
CTRL_REG7_XM = 0x26
CTRL_REG1_G = 0x20
CTRL_REG4_G = 0x23

ACCEL_SCALE = 6.1e-5  # +/- 2g full scale
MAG_SCALE = 8.0e-6  # +/- 0.2 mT full scale
GYR_SCALE = 70e-3  # +/- 2000 dps full scale

class DeviceNotFound(IOError):
    pass


class Lsm9ds0(Lsm):
    def __init__(self, config_path=None):
        super().__init__(config_path)
        self.sensor = "LSM9DS0"
        self.ACCEL_SCALE = ACCEL_SCALE
        self.MAG_SCALE = MAG_SCALE
        self.GYR_SCALE = GYR_SCALE
        self.OUT_X_L_A = OUT_X_L_A
        self.OUT_X_L_M = OUT_X_L_M
        self.OUT_X_L_G = OUT_X_L_G
        self.MAG_ADDRESS = MAG_ADDRESS
        self.ACC_ADDRESS = ACC_ADDRESS
        self.GYR_ADDRESS = GYR_ADDRESS
        self.initialize_sensor()
        # ensure that the sensor is really initialized to avoid false data
        self.initialize_sensor()

    def initialize_sensor(self):
        # Get I2C bus
        self.bus = smbus2.SMBus(1)
        whoami_mag = self.bus.read_byte_data(self.MAG_ADDRESS, WHO_AM_I)
        whoami_gyr = self.bus.read_byte_data(self.GYR_ADDRESS, WHO_AM_I)
        if whoami_mag != 0x49 or whoami_gyr != 0xD4:
            raise DeviceNotFound("LSM9DS0 not found")

        # initialise the accelerometer
        # z,y,x axis enabled, 50Hz data rate
        self.bus.write_byte_data(self.ACC_ADDRESS, CTRL_REG1_XM, 0b0101_0_111)
        # +/- 2G full scale
        self.bus.write_byte_data(self.ACC_ADDRESS, CTRL_REG2_XM, 0b00_000_000)

        # initialise the magnetometer
        # Temp enable, low resolution, 50Hz data rate
        self.bus.write_byte_data(self.MAG_ADDRESS, CTRL_REG5_XM, 0b1_00_10000)
        # +/- 2gauss
        self.bus.write_byte_data(self.MAG_ADDRESS, CTRL_REG6_XM, 0b0_00_00000)
        # Continuous-conversion mode
        self.bus.write_byte_data(self.MAG_ADDRESS, CTRL_REG7_XM, 0b00000000)

        # initialise the gyroscope
        # normal mode, ODR 95Hz, cutoff 12.5, x, y, z enabled
        self.bus.write_byte_data(self.GYR_ADDRESS, CTRL_REG1_G, 0b00_00_1_111)
        # 2000 dps full scale
        self.bus.write_byte_data(self.GYR_ADDRESS, CTRL_REG4_G, 0b0_0_10_0_00_0)
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
