#!/usr/bin/env python3
import time
import json
import redis
from lsm_poller import get_lsm_sensor
from barometer_poller import get_barometer_sensor
from algorithms import (
    calculate_pressure_altitude,
    KalmanImuAltitude,
    calculate_altitude_pressure,
)


if __name__ == "__main__":

    redis_connection = redis.Redis()
    interval = 0.08
    imu_sensor = get_lsm_sensor()
    if imu_sensor is None:
        exit()
    baro_sensor = get_barometer_sensor()
    if baro_sensor is None:
        exit()
    kia = KalmanImuAltitude()
    g = 9.80665
    while True:
        t_start = time.time()
        baro_data = baro_sensor.get_sensor_data()
        imu_data = imu_sensor.get_sensor_data()
        kalman_data = kia.kalman_step(
            utc=imu_data["i_utc"],
            h=calculate_pressure_altitude(baro_data["pressure"]),
            h_err=0.09,
            a=imu_data["vertical_acceleration"] - g,
            a_err=0.07,
        )
        if kalman_data is not None:
            baro_data["imu_baro_altitude"] = round(kalman_data["altitude"], 3)
            baro_data["imu_baro_vertical_speed"] = round(
                kalman_data["vertical_speed"], 3
            )
            baro_data["imu_baro_pressure"] = round(
                calculate_altitude_pressure(kalman_data["altitude"]), 2
            )
        imu_data["imu_barometer_available"] = True
        baro_data["imu_barometer_available"] = True
        redis_connection.publish("imu", json.dumps(imu_data))
        redis_connection.publish("barometer", json.dumps(baro_data))
        imu_data.update(baro_data)
        del imu_data["imu_barometer_available"]
        redis_connection.publish("imu_barometer", json.dumps(imu_data))
        dt = time.time() - t_start
        time.sleep(max(0, interval - dt))
