import math
import json
import gps_tracker.distance_calculation as dc

file_name = "static/real_tracking_data.json"
with open(file_name, "r") as f:
    data = json.load(f)
distance = 0
old_location = None
for segment in data[0]["features"]:
    for location in segment["geometry"]["coordinates"]:
        if old_location:
            dz = dc.get_distance(location[:2][::-1], old_location[:2][::-1])
            if not math.isnan(dz):
                distance += dz
        old_location = location

print("track length: {} km".format(round(distance / 1000, 2)))
