#!venv/bin/python3
import time
import json
import redis
from lsm_poller import get_lsm_sensor
from barometer_poller import get_barometer_sensor


def main():
    redis_connection = redis.Redis()
    interval = 0.05
    imu_sensor = get_lsm_sensor()
    if imu_sensor is None:
        print("No IMU sensor found. Exiting.")
        return
    baro_sensor = get_barometer_sensor()
    if baro_sensor is None:
        print("No barometer found. Exiting.")
        return
    while True:
        t_start = time.time()
        baro_data = baro_sensor.get_sensor_data()
        sensor_data = sensor.get_sensor_data(sensor_fusion=False)
        imu_data["imu_barometer_available"] = True
        baro_data["imu_barometer_available"] = True
        redis_connection.publish("imu", json.dumps(imu_data))
        redis_connection.publish("barometer", json.dumps(baro_data))
        imu_data.update(baro_data)
        del imu_data["imu_barometer_available"]
        redis_connection.publish("imu_barometer", json.dumps(imu_data))
        dt = time.time() - t_start
        time.sleep(max(0, interval - dt))


if __name__ == "__main__":
    main()
