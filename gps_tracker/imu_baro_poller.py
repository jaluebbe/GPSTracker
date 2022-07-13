#!/usr/bin/env python3
import time
import json
import redis
import numpy as np
import numpy.linalg as la
from lsm_poller import get_lsm_sensor
from barometer_poller import get_barometer_sensor
from algorithms import (
    calculate_pressure_altitude,
    KalmanImuAltitude,
    calculate_altitude_pressure,
)


if __name__ == "__main__":

    redis_connection = redis.Redis()
    interval = 0.04
    imu_sensor = get_lsm_sensor()
    if imu_sensor is None:
        exit()
    baro_sensor = get_barometer_sensor()
    if baro_sensor is None:
        exit()
    kia = KalmanImuAltitude(sigma_a=0.5)
    g = 9.80665
    old_i_utc = None
    while True:
        t_start = time.time()
        baro_data = baro_sensor.get_sensor_data()
        imu_data = imu_sensor.get_sensor_data()
        kalman_data = kia.kalman_step(
            utc=imu_data["i_utc"],
            h=calculate_pressure_altitude(baro_data["pressure"]),
            h_err=0.06,
            a=imu_data["vertical_acceleration"] - g,
            a_err=0.05,
        )
        if baro_data is not None:
            baro_data["imu_baro_altitude"] = kalman_data["altitude"]
            baro_data["imu_baro_vertical_speed"] = kalman_data["vertical_speed"]
            baro_data["imu_baro_pressure"] = calculate_altitude_pressure(
                kalman_data["altitude"]
            )
        redis_connection.publish("imu", json.dumps(imu_data))
        redis_connection.publish("barometer", json.dumps(baro_data))
        dt = time.time() - t_start
        time.sleep(max(0, interval - dt))
