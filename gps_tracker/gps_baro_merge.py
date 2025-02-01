#!venv/bin/python3
import redis
import json
import os
import pygeodesy
from collections import deque
from time import localtime, strftime, gmtime
from math import sin, cos, acos, radians

# Initialize Redis connection and pubsub
redis_connection = redis.Redis(decode_responses=True)
_pubsub = redis_connection.pubsub()
_pubsub.subscribe("gps", "barometer", "imu", "imu_barometer")
# Initialize deques for history
pressure_history = deque(maxlen=50)
imu_history = deque(maxlen=50)
imu_barometer_history = deque(maxlen=50)
# Constants
MAX_PAUSE = 30
MAX_DIST = 8
STATUS_THRESHOLD = 1
H_UERE_NO_DGPS = 15.0
DUMP_IGNORE_KEYS = [
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
    "raw_gyro",
    "raw_acceleration",
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
    "velN",
    "velE",
    "velD",
    "imu_baro_vertical_speed",
    "imu_baro_altitude",
]
# Global variables for tracking state
old_location = None
old_utc = None
old_pressure = None


def get_cpu_temperature():
    res = os.popen("vcgencmd measure_temp").readline()
    return float(res.replace("temp=", "").replace("'C\n", ""))


def get_distance(location1, location2):
    """Calculate the distance between two GPS coordinates."""
    lat1, lon1 = map(radians, location1)
    lat2, lon2 = map(radians, location2)
    distance = 6.370e6 * acos(
        sin(lat1) * sin(lat2) + cos(lat1) * cos(lat2) * cos(lon2 - lon1)
    )
    return distance


def update_data_with_history(data, history, key_prefix):
    """Update data with the most recent entry from history."""
    while history:
        history_data = history.popleft()
        if history_data[f"{key_prefix}_utc"] > data["utc"] - 0.08:
            data.update(history_data)
            break


def process_gps_data(data):
    """Process GPS data and update Redis."""
    global old_location, old_utc, old_pressure

    utc = data.get("utc")
    if utc is None:
        print("utc is None")
        return

    location = (data["lat"], data["lon"])
    update_data_with_history(data, pressure_history, "p")
    update_data_with_history(data, imu_history, "i")
    update_data_with_history(data, imu_barometer_history, "p")

    hdop = data.get("hdop")
    error = hdop * H_UERE_NO_DGPS if hdop is not None else None

    if old_location is None:
        status = 3
    elif get_distance(old_location, location) > MAX_DIST:
        status = 2
    elif utc - MAX_PAUSE > old_utc:
        status = 1
    elif (
        data.get("pressure") is not None
        and abs(data["pressure"] - old_pressure) > 10
    ):
        status = 4
    else:
        status = 0

    if status >= STATUS_THRESHOLD:
        old_utc = utc
        old_location = location
        old_pressure = data.get("pressure")

        if location is not None:
            utm = pygeodesy.toUtm(*location)
            data["utm"] = utm.toStr()
            data["mgrs"] = utm.toMgrs().toStr()

        data["rpi_temperature"] = get_cpu_temperature()
        data["my_status"] = status
        data["localtime"] = strftime("%Y-%m-%d %H:%M:%S", localtime())
        data["pos_error"] = (
            round(error, 2) if error is not None else float("nan")
        )

        redis_connection.publish("transfer_data", json.dumps(data))

        for key in DUMP_IGNORE_KEYS:
            data.pop(key, None)

        key = f"tracking:{data['hostname']}:{strftime('%Y%m%d', gmtime())}"
        redis_connection.lpush(key, json.dumps(data))


for item in _pubsub.listen():
    if item["type"] != "message":
        continue
    channel = item["channel"]
    data = json.loads(item["data"])
    if channel == "barometer" and not data.get("imu_barometer_available"):
        pressure_history.append(data)
    elif channel == "imu" and not data.get("imu_barometer_available"):
        imu_history.append(data)
    elif channel == "imu_barometer":
        imu_barometer_history.append(data)
    elif channel == "gps" and data.get("sensor") == "gps":
        process_gps_data(data)
