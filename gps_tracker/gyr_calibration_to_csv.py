#!venv/bin/python3
import csv
import json
import redis


def export_gyr_calibration_history_to_csv(
    redis_key="gyr_calibration_history",
    output_file="gyr_calibration_history.csv",
):
    redis_connection = redis.Redis(decode_responses=True)
    history = redis_connection.lrange(redis_key, 0, -1)
    with open(output_file, mode="w", newline="") as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["timestamp", "temperature", "x", "y", "z"])
        for entry in history:
            calibration = json.loads(entry)
            timestamp = calibration["timestamp"]
            g_temp = calibration["g_temp"]
            g_offset = calibration["g_offset"]
            x, y, z = g_offset
            csv_writer.writerow([timestamp, g_temp, x, y, z])


if __name__ == "__main__":
    export_gyr_calibration_history_to_csv()
