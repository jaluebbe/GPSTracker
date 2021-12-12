#!/usr/bin/env python3
import time
import math
import json
import socket
import redis
import RTIMU
import os.path
import logging

redis_connection = redis.Redis()
hostname = socket.gethostname()
SETTINGS_FILE = "/home/pi/GPSTracker/gps_tracker/RTIMULib"

logging.info("Using settings file " + SETTINGS_FILE + ".ini")
if not os.path.exists(SETTINGS_FILE + ".ini"):
    logging.warning("Settings file does not exist, will be created")

s = RTIMU.Settings(SETTINGS_FILE)
imu = RTIMU.RTIMU(s)

logging.info("IMU Name: " + imu.IMUName())

if not imu.IMUInit():
    logging.error("IMU Init Failed")
    exit(1)
else:
    logging.info("IMU Init Succeeded")

# this is a good time to set any fusion parameters

imu.setSlerpPower(0.02)
imu.setGyroEnable(True)
imu.setAccelEnable(True)
imu.setCompassEnable(False)

poll_interval = imu.IMUGetPollInterval()
logging.info("Recommended Poll Interval: %dmS\n" % poll_interval)


def poll_imu(counter=0):
    if imu.IMURead():
        timestamp = time.time()
        fusion_data = imu.getFusionData()
        sensor_data = {
            "hostname": hostname,
            "i_utc": round(timestamp, 3),
            "roll": round(math.degrees(fusion_data[0]), 1),
            "pitch": round(math.degrees(fusion_data[1]), 1),
        }
        if counter % 20 == 0:
            redis_connection.publish("imu", json.dumps(sensor_data))
        return counter + 1
    return counter


if __name__ == "__main__":

    counter = 0
    while True:
        counter = poll_imu(counter)
        time.sleep(poll_interval / 1e3)
