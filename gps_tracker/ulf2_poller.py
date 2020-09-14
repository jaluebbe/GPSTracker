#!/usr/bin/env python3
import time
import requests
import json
import redis

temperatures_url = 'http://localhost:8080/mock/ulf2/temperatures'
rpm_url = 'http://127.0.0.1:8080/mock/ulf2/rpm'

redis_connection = redis.Redis()


def poll_ulf2():
    utc = time.time()
    ulf2_data = {}
    try:
        temperatures = requests.get(temperatures_url, timeout=0.1).json()
    except requests.exceptions.ConnectTimeout:
        print(f'connection to {temperatures_url} timed out.')
    except requests.exceptions.ConnectionError:
        print(f'connection to {temperatures_url} failed.')
    else:
        if temperatures.get('source') == 'ulf2_temperatures':
            del temperatures['source']
            del temperatures['time']
            ulf2_data.update(temperatures)
    try:
        rpm = requests.get(rpm_url, timeout=0.1).json()
    except requests.exceptions.ConnectTimeout:
        print(f'connection to {rpm_url} timed out.')
    except requests.exceptions.ConnectionError:
        print(f'connection to {rpm_url} failed.')
    else:
        if rpm.get('source') == 'ulf2_rpm':
            del rpm['source']
            del rpm['time']
            ulf2_data.update(rpm)
    if len(ulf2_data) > 0:
        ulf2_data['utc'] = round(utc, 1)
        redis_connection.set('ulf2', json.dumps(ulf2_data))
        redis_connection.expire('ulf2', 2)
    time.sleep(1 - time.time() + utc)


if __name__ == '__main__':

    while True:
        poll_ulf2()
