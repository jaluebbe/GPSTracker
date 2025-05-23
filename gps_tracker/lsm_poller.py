#!venv/bin/python3
import time
import json
import redis
from lsm303d import Lsm303d
from lsm9ds0 import Lsm9ds0
from lsm6dsl_lis3mdl import Lsm6dsl_Lis3mdl


def get_lsm_sensor():
    """Attempt to initialize each IMU sensor in turn."""
    try:
        return Lsm303d()
    except:
        print("no LSM303d found")
    try:
        return Lsm9ds0()
    except:
        print("no LSM9DS0 found")
    try:
        return Lsm6dsl_Lis3mdl()
    except:
        print("no LSM6DSL+LIS3MDL found")


def main():
    redis_connection = redis.Redis()
    interval = 0.05
    sensor = get_lsm_sensor()
    if sensor is None:
        print("No IMU sensor found. Exiting.")
        return
    while True:
        t_start = time.time()
        sensor_data = sensor.get_sensor_data(sensor_fusion=False)
        redis_connection.publish("imu", json.dumps(sensor_data))
        dt = time.time() - t_start
        time.sleep(max(0, interval - dt))


if __name__ == "__main__":
    main()
