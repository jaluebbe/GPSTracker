#!venv/bin/python3
import time
import json
import redis
from lsm303d import Lsm303d
from lsm9ds0 import Lsm9ds0
from lsm6dsl_lis3mdl import Lsm6dsl_Lis3mdl


def get_lsm_sensor():
    """Try available IMU sensor drivers in order and return the first that
    initializes."""
    try:
        return Lsm303d()
    except Exception:
        print("no LSM303d found")
    try:
        return Lsm9ds0()
    except Exception:
        print("no LSM9DS0 found")
    try:
        return Lsm6dsl_Lis3mdl()
    except Exception:
        print("no LSM6DSL+LIS3MDL found")
    return None


def main():
    redis_connection = redis.Redis()
    interval = 0.04  # target seconds between publishes
    sensor = get_lsm_sensor()
    if sensor is None:
        print("No IMU sensor found. Exiting.")
        return

    publish = redis_connection.publish
    dumps = json.dumps
    get_data = sensor.get_sensor_data
    next_t = time.monotonic()

    while True:
        sensor_data = get_data(sensor_fusion=False)
        publish("imu", dumps(sensor_data, separators=(",", ":")))

        # Deterministic scheduling to reduce jitter and drift
        next_t += interval
        sleep = next_t - time.monotonic()
        if sleep > 0:
            time.sleep(sleep)
        else:
            # If we lagged by more than one interval, realign to now
            if sleep < -interval:
                next_t = time.monotonic()


if __name__ == "__main__":
    main()
