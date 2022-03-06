#!/usr/bin/env python3
import time
import json
import redis
from lsm303d import Lsm303d
from lsm9ds0 import Lsm9ds0
from lsm6dsl_lis3mdl import Lsm6dsl_Lis3mdl

redis_connection = redis.Redis()


if __name__ == "__main__":

    try:
        sensor = Lsm303d()
    except:
        print("no LSM303d found")
    try:
        sensor = Lsm9ds0()
    except:
        print("no LSM9DS0 found")
    try:
        sensor = Lsm6dsl_Lis3mdl()
    except:
        print("no LSM6DSL+LIS3MDL found")
    while True:
        sensor_data = sensor.get_sensor_data()
        redis_connection.publish("imu", json.dumps(sensor_data))
        time.sleep(0.08)
