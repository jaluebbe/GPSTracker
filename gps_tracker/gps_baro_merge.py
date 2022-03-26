#!/usr/bin/env python3
import sys
import redis
import json
import os
import numpy as np
import pygeodesy
from collections import deque
from time import localtime, strftime

sys.path.append("/home/pi/GPSTracker")

redis_connection = redis.Redis(decode_responses=True)
pressure_history = deque(maxlen=50)
imu_history = deque(maxlen=50)
_pubsub = redis_connection.pubsub()
_pubsub.subscribe("gps", "barometer", "imu")
old_location = None
old_utc = None
old_pressure = None
max_pause = 30
max_dist = 8
status_threshold = 1
h_uere_no_dgps = 15.0
dump_ignore_keys = [
    "map_height",
    "map_type",
    "mode",
    "utm",
    "ref_pressure",
    "time",
    "pos_error",
    "epc",
    "eps",
    "epd",
    "epx",
    "epy",
    "epv",
    "ept",
    "tag",
    "device",
    "class",
    "mgrs",
    "p_utc",
    "i_utc",
    "raw_magnetometer",
    "p_sensor",
    "i_sensor",
    "roll_acc",
    "yaw_gyr",
    "p_hostname",
    "i_hostname",
    "leapseconds",
    "ecefx",
    "ecefy",
    "ecefz",
    "ecefvx",
    "ecefvy",
    "ecefvz",
    "ecefpAcc",
    "ecefvAcc",
    "eph",
    "sep",
]


def get_cpu_temperature():
    res = os.popen("vcgencmd measure_temp").readline()
    return float(res.replace("temp=", "").replace("'C\n", ""))


# calculate the distance between two gps coordinates:
def get_distance(location1, location2):
    lat1 = location1[0]
    lon1 = location1[1]
    lat2 = location2[0]
    lon2 = location2[1]
    deg_rad = 2 * np.pi / 360
    distance = 6.370e6 * np.arccos(
        np.sin(lat1 * deg_rad) * np.sin(lat2 * deg_rad)
        + np.cos(lat1 * deg_rad)
        * np.cos(lat2 * deg_rad)
        * np.cos((lon2 - lon1) * deg_rad)
    )
    return distance


for item in _pubsub.listen():
    if not item[u"type"] == "message":
        continue
    if item["channel"] == "barometer":
        pressure_history.append(json.loads(item["data"]))
        if len(imu_history) == 0:
            continue
        imu_pressure = {}
        imu_pressure.update(pressure_history[-1])
        imu_pressure.update(imu_history[-1])
        redis_connection.publish("imu_pressure", json.dumps(imu_pressure))
    elif item["channel"] == "imu":
        imu_history.append(json.loads(item["data"]))
    elif item["channel"] == "gps":
        data = json.loads(item["data"])
        utc = data.get("utc")
        if utc is None:
            print("utc is None")
            continue
        location = (data["lat"], data["lon"])
        while len(pressure_history) > 0:
            pressure_data = pressure_history.popleft()
            if pressure_data["p_utc"] > data["utc"] - 0.08:
                data.update(pressure_data)
                break
        while len(imu_history) > 0:
            imu_data = imu_history.popleft()
            if imu_data["i_utc"] > data["utc"] - 0.08:
                data.update(imu_data)
                break
        hdop = data.get("hdop")
        if hdop is not None:
            error = hdop * h_uere_no_dgps
        else:
            error = None
        if old_location is None:
            status = 3
        elif get_distance(old_location, location) > max_dist:
            status = 2
        elif utc - max_pause > old_utc:
            status = 1
        elif (
            data.get("pressure") is not None
            and np.abs(np.diff([data["pressure"], old_pressure])) > 10
        ):
            status = 4
        else:
            status = 0
        if status >= status_threshold:
            old_utc = utc
            old_location = location
            old_pressure = data.get("pressure")
            gps_altitude = data.get("alt")
            if location is not None:
                utm = pygeodesy.toUtm(*location)
                data["utm"] = utm.toStr()
                data["mgrs"] = utm.toMgrs().toStr()
            data["rpi_temperature"] = get_cpu_temperature()
            data["my_status"] = status
            data["localtime"] = str(strftime("%Y-%m-%d %H:%M:%S", localtime()))
            if error is not None:
                data["pos_error"] = round(error, 2)
            else:
                data["pos_error"] = float("nan")
            redis_connection.publish("transfer_data", json.dumps(data))
            if dump_ignore_keys is not None:
                for key in dump_ignore_keys:
                    data.pop(key, None)
            key = "tracking:{}:{}".format(data["hostname"], strftime("%Y%m%d"))
            redis_connection.lpush(key, json.dumps(data))
