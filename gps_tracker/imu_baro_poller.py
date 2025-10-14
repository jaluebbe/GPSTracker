#!venv/bin/python3
import time
import json
import redis
from lsm_poller import get_lsm_sensor
from barometer_poller import get_barometer_sensor


def main():
    redis_connection = redis.Redis()
    interval = 0.04
    imu_sensor = get_lsm_sensor()
    if imu_sensor is None:
        print("No IMU sensor found. Exiting.")
        return
    baro_sensor = get_barometer_sensor()
    if baro_sensor is None:
        print("No barometer found. Exiting.")
        return
    # initial barometer read
    baro_data = baro_sensor.get_sensor_data()
    loop_counter = 0
    next_t = time.monotonic()
    while True:
        # update barometer only every second iteration
        if loop_counter % 2 == 0:
            baro_data = baro_sensor.get_sensor_data()
        imu_data = imu_sensor.get_sensor_data(sensor_fusion=False)
        imu_data.update(baro_data)
        redis_connection.publish(
            "imu_barometer", json.dumps(imu_data, separators=(",", ":"))
        )
        loop_counter += 1
        next_t += interval
        sleep = next_t - time.monotonic()
        if sleep > 0:
            time.sleep(sleep)
        elif sleep < -interval:
            # realign if we've fallen far behind
            next_t = time.monotonic()


if __name__ == "__main__":
    main()
