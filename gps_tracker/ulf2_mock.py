import time
import json

base_rpm = 800
base_temperatures = {
    "oil": 52.0,
    "carb": 12.4,
    "tank": 22.7,
    "ign": 32.7,
    "ds03": 20.0,
    "ds04": 20.0,
    "la": 89.7,
    "li": 91.3,
    "ri": 95.8,
    "ra": 97.2,
    "egt_l": 123.4,
    "egt_r": 126.7,
    "br1": 53.1,
    "br2": 54.1,
    "bl1": 17.5
}


def get_rpm():
    _timestamp = time.time() % 140
    return {
        'rpm': int(base_rpm + 10*_timestamp),
        'source': 'ulf2_rpm',
        'time': time.strftime('%H:%M:%S', time.gmtime(_timestamp)),
        }


def get_temperatures():
    _timestamp = time.time() % 90
    temperature_offset = 0.1 * _timestamp
    temperatures = {
        key: round(base_temperatures[key] + temperature_offset, 1) for key in
        base_temperatures
        }
    temperatures['source'] = 'ulf2_temperatures'
    temperatures['time'] = time.strftime('%H:%M:%S', time.gmtime(_timestamp))
    return temperatures

if __name__ == '__main__':

    while True:
        print(json.dumps(get_rpm()))
        print(json.dumps(get_temperatures()))
        time.sleep(1)
