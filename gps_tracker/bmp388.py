#!/usr/bin/env python3
# code is partly based on https://github.com/ozzmaker/BerryIMU
import smbus2
import time
import json
import socket
import redis

I2C_ADD_BMP388_AD0_LOW = 0x76
I2C_ADD_BMP388_AD0_HIGH = 0x77
I2C_ADD_BMP388 = I2C_ADD_BMP388_AD0_HIGH

BMP388_REG_ADD_WIA = 0x00
BMP388_REG_VAL_WIA = 0x50

BMP388_REG_ADD_ERR = 0x02
BMP388_REG_VAL_FATAL_ERR = 0x01
BMP388_REG_VAL_CMD_ERR = 0x02
BMP388_REG_VAL_CONF_ERR = 0x04

BMP388_REG_ADD_STATUS = 0x03
BMP388_REG_VAL_CMD_RDY = 0x10
BMP388_REG_VAL_DRDY_PRESS = 0x20
BMP388_REG_VAL_DRDY_TEMP = 0x40

BMP388_REG_ADD_CMD = 0x7E
BMP388_REG_VAL_EXTMODE_EN = 0x34
BMP388_REG_VAL_FIFI_FLUSH = 0xB0
BMP388_REG_VAL_SOFT_RESET = 0xB6

BMP388_REG_ADD_PWR_CTRL = 0x1B
BMP388_REG_VAL_PRESS_EN = 0x01
BMP388_REG_VAL_TEMP_EN = 0x02
BMP388_REG_VAL_NORMAL_MODE = 0x30

BMP388_REG_ADD_PRESS_XLSB = 0x04
BMP388_REG_ADD_PRESS_LSB = 0x05
BMP388_REG_ADD_PRESS_MSB = 0x06
BMP388_REG_ADD_TEMP_XLSB = 0x07
BMP388_REG_ADD_TEMP_LSB = 0x08
BMP388_REG_ADD_TEMP_MSB = 0x09

BMP388_REG_ADD_T1_LSB = 0x31
BMP388_REG_ADD_T1_MSB = 0x32
BMP388_REG_ADD_T2_LSB = 0x33
BMP388_REG_ADD_T2_MSB = 0x34
BMP388_REG_ADD_T3 = 0x35
BMP388_REG_ADD_P1_LSB = 0x36
BMP388_REG_ADD_P1_MSB = 0x37
BMP388_REG_ADD_P2_LSB = 0x38
BMP388_REG_ADD_P2_MSB = 0x39
BMP388_REG_ADD_P3 = 0x3A
BMP388_REG_ADD_P4 = 0x3B
BMP388_REG_ADD_P5_LSB = 0x3C
BMP388_REG_ADD_P5_MSB = 0x3D
BMP388_REG_ADD_P6_LSB = 0x3E
BMP388_REG_ADD_P6_MSB = 0x3F
BMP388_REG_ADD_P7 = 0x40
BMP388_REG_ADD_P8 = 0x41
BMP388_REG_ADD_P9_LSB = 0x42
BMP388_REG_ADD_P9_MSB = 0x43
BMP388_REG_ADD_P10 = 0x44
BMP388_REG_ADD_P11 = 0x45


class DeviceNotFound(IOError):
    pass


class Bmp388:
    def __init__(self, i2c_address=I2C_ADD_BMP388):
        self.i2c_address = i2c_address
        self.initialize_sensor()
        self.hostname = socket.gethostname()
        # ensure that the sensor is really initialized to avoid false data?
        self.initialize_sensor()

    def initialize_sensor(self):
        # Get I2C bus
        self.bus = smbus2.SMBus(1)
        # Load calibration values.
        if self._read_byte(BMP388_REG_ADD_WIA) == BMP388_REG_VAL_WIA:
            u8RegData = self._read_byte(BMP388_REG_ADD_STATUS)
            if u8RegData & BMP388_REG_VAL_CMD_RDY:
                self._write_byte(BMP388_REG_ADD_CMD, BMP388_REG_VAL_SOFT_RESET)
                time.sleep(0.01)
        else:
            raise DeviceNotFound("No BMP388 found.")
        self._write_byte(
            BMP388_REG_ADD_PWR_CTRL,
            BMP388_REG_VAL_PRESS_EN
            | BMP388_REG_VAL_TEMP_EN
            | BMP388_REG_VAL_NORMAL_MODE,
        )
        # set 32x pressure oversampling, 2x temperature oversampling
        self._write_byte(0x1C, 0x0D)
        # set output data rate to 12.5Hz
        self._write_byte(0x1D, 0x04)
        # set IIR filter to filter coefficient 3.
        self._write_byte(0x1F, 0x04)
        self._load_calibration()
        time.sleep(0.5)

    def _read_byte(self, cmd):
        return self.bus.read_byte_data(self.i2c_address, cmd)

    def _read_s8(self, cmd):
        result = self._read_byte(cmd)
        if result > 128:
            result -= 256
        return result

    def _read_u16(self, cmd):
        lsb = self.bus.read_byte_data(self.i2c_address, cmd)
        msb = self.bus.read_byte_data(self.i2c_address, cmd + 0x01)
        return (msb << 0x08) + lsb

    def _read_s16(self, cmd):
        result = self._read_u16(cmd)
        if result > 32767:
            result -= 65536
        return result

    def _write_byte(self, cmd, val):
        self.bus.write_byte_data(self.i2c_address, cmd, val)

    def _load_calibration(self):
        self.T1 = self._read_u16(BMP388_REG_ADD_T1_LSB)
        self.T2 = self._read_u16(BMP388_REG_ADD_T2_LSB)
        self.T3 = self._read_s8(BMP388_REG_ADD_T3)
        self.P1 = self._read_s16(BMP388_REG_ADD_P1_LSB)
        self.P2 = self._read_s16(BMP388_REG_ADD_P2_LSB)
        self.P3 = self._read_s8(BMP388_REG_ADD_P3)
        self.P4 = self._read_s8(BMP388_REG_ADD_P4)
        self.P5 = self._read_u16(BMP388_REG_ADD_P5_LSB)
        self.P6 = self._read_u16(BMP388_REG_ADD_P6_LSB)
        self.P7 = self._read_s8(BMP388_REG_ADD_P7)
        self.P8 = self._read_s8(BMP388_REG_ADD_P8)
        self.P9 = self._read_s16(BMP388_REG_ADD_P9_LSB)
        self.P10 = self._read_s8(BMP388_REG_ADD_P10)
        self.P11 = self._read_s8(BMP388_REG_ADD_P11)

    def compensate_temperature(self, adc_t):
        partial_data1 = adc_t - 256 * self.T1
        partial_data2 = self.T2 * partial_data1
        partial_data3 = partial_data1 * partial_data1
        partial_data4 = partial_data3 * self.T3
        partial_data5 = partial_data2 * 262144 + partial_data4
        partial_data6 = partial_data5 / 4294967296
        self.t_fine = partial_data6
        comp_temp = partial_data6 * 25 / 16384
        return comp_temp

    def compensate_pressure(self, adc_p):
        partial_data1 = self.t_fine * self.t_fine
        partial_data2 = partial_data1 / 0x40
        partial_data3 = partial_data2 * self.t_fine / 256
        partial_data4 = self.P8 * partial_data3 / 0x20
        partial_data5 = self.P7 * partial_data1 * 0x10
        partial_data6 = self.P6 * self.t_fine * 4194304
        offset = (
            self.P5 * 140737488355328
            + partial_data4
            + partial_data5
            + partial_data6
        )

        partial_data2 = self.P4 * partial_data3 / 0x20
        partial_data4 = self.P3 * partial_data1 * 0x04
        partial_data5 = (self.P2 - 16384) * self.t_fine * 2097152
        sensitivity = (
            (self.P1 - 16384) * 70368744177664
            + partial_data2
            + partial_data4
            + partial_data5
        )

        partial_data1 = sensitivity / 16777216 * adc_p
        partial_data2 = self.P10 * self.t_fine
        partial_data3 = partial_data2 + 65536 * self.P9
        partial_data4 = partial_data3 * adc_p / 8192
        partial_data5 = partial_data4 * adc_p / 512
        partial_data6 = adc_p * adc_p
        partial_data2 = self.P11 * partial_data6 / 65536
        partial_data3 = partial_data2 * adc_p / 128
        partial_data4 = (
            offset / 0x04 + partial_data1 + partial_data5 + partial_data3
        )
        comp_press = partial_data4 * 25 / 1099511627776
        return comp_press

    def get_sensor_data(self):
        timestamp = time.time()
        # Read data from 0x04, 6 bytes
        # pressure xLSB, pressure LSB, pressure MSB,
        # temperature xLSB, temperature LSB, temperature MSB
        data = self.bus.read_i2c_block_data(self.i2c_address, 0x04, 6)
        adc_t = (data[5] << 0x10) + (data[4] << 0x08) + data[3]
        adc_p = (data[2] << 0x10) + (data[1] << 0x08) + data[0]
        # Temperature and pressure offset calculations
        temperature = self.compensate_temperature(adc_t) / 100
        pressure = self.compensate_pressure(adc_p) / 100
        return {
            "temperature": round(temperature, 3),
            "pressure": round(pressure, 2),
            "p_utc": round(timestamp, 3),
            "p_hostname": self.hostname,
            "p_sensor": "BMP388",
        }
