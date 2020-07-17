#!/usr/bin/env python3
import redis
import json
import os
import numpy as np
redis_connection = redis.Redis(decode_responses=True)
from collections import deque
from time import localtime, sleep, strftime, time, strptime
pressure_history = deque(maxlen=500)
_pubsub = redis_connection.pubsub()
_pubsub.subscribe(['bmp280', 'transfer_data'])
#ca 17/min with 0.05s
last_record = None
old_pressure = None
last_transfer = None
log_pressure = False

for item in _pubsub.listen():
    if not item[u'type'] == 'message':
        continue
    if item['channel'] == 'transfer_data':
        _transfer_data = json.loads(item['data'])
        last_transfer = _transfer_data['utc']
        old_pressure = _transfer_data['pressure']
        continue
    data = json.loads(item['data'])
    pressure_history.append(data['pressure'])
    now = time()
    if log_pressure and (last_record is None or last_record < now - 5):
        pressure_data = {
            'pressure': int(round(np.mean(pressure_history))),
            'temperature': round(data['temperature'], 1),
            'utc': int(round(now))}
        key = 'pressure_log:{}:{}'.format(data['hostname'], strftime("%Y%m"))
        redis_connection.lpush(key, json.dumps(pressure_data))
        last_record = now
    if old_pressure is None or np.abs(np.diff([data['pressure'], old_pressure])
            ) > 5:
        key = 'altitude:{}:{}'.format(data['hostname'], strftime("%Y%m%d"))
        redis_connection.lpush(key, json.dumps(data))
        old_pressure = data['pressure']
    sleep(0.1)
    continue
