#!/usr/bin/env python3
import time
import json
import redis
from bme280_poller import Bme280
from bmp280_poller import Bmp280
from bmp388_poller import Bmp388


def get_barometer_sensor():
    try:
        return Bme280()
    except:
        print("no BME280 found")
    try:
        return Bmp280()
    except:
        print("no BMP280 found")
    try:
        return Bmp388()
    except:
        print("no BMP388 found")


if __name__ == "__main__":

    redis_connection = redis.Redis()
    interval = 0.08
    sensor = get_barometer_sensor()
    if sensor is None:
        exit()
    while True:
        t_start = time.time()
        sensor_data = sensor.get_sensor_data()
        redis_connection.publish("barometer", json.dumps(sensor_data))
        dt = time.time() - t_start
        time.sleep(max(0, interval - dt))
