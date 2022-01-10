#!/usr/bin/env python3
import time
import json
import redis
from lsm303d import Lsm303d

redis_connection = redis.Redis()


if __name__ == "__main__":

    sensor = Lsm303d()
    while True:
        sensor_data = sensor.get_sensor_data()
        redis_connection.publish("imu", json.dumps(sensor_data))
        time.sleep(0.08)
