#!/usr/bin/env python3
from time import strftime
import requests

HOSTNAME = "localhost"
PORT = 8080

this_month = strftime("%Y%m")
response = requests.get(f"http://{HOSTNAME}:{PORT}/api/available_datasets")
for _name in response.json():
    if _name.split("_")[-1].startswith(this_month):
        continue
    requests.get(f"http://{HOSTNAME}:{PORT}/api/move_to_archive/{_name}")
