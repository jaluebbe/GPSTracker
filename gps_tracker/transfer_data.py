#!/usr/bin/env python3
import redis
import json
import requests
from collections import deque
from time import sleep, time
redis_connection = redis.Redis(decode_responses=True)
_pubsub = redis_connection.pubsub()
_pubsub.subscribe(['transfer_data'])

with open('/home/pi/gps_config.json') as json_data_file:
    config = json.load(json_data_file)

transfer_deque = deque()
max_pause = config['transfer']['max_pause']
min_pause = config['transfer']['min_pause']
post_url = config['transfer']['post_url']
password = config['transfer']['password']

last_transfer = None
ts = transfer_deque
message_buffer = deque()

for item in _pubsub.listen():
    if not item[u'type'] == 'message':
        continue
    ts.append(json.loads(item['data']))
    if len(ts) > 30 or last_transfer is None or (last_transfer < time() -
            max_pause and len(ts) > 0):
        text_data = {'password': password}
        line_count = 0
        while len(ts) > 0 and len(message_buffer) < 30:
            data = dict(ts.popleft())
            line_key = 'line_%d' % line_count
            text_data[line_key] = json.dumps(data, separators=(',', ':'))
            message_buffer.append(data)
            line_count += 1
        text_data['num_lines'] = len(message_buffer)
        t = time()
        r = requests.post(post_url, data=text_data, timeout=10)
        if r.status_code == 200 and r.text.startswith('success'):
            last_transfer = time()
            data['transferred'] = last_transfer
            redis_connection.publish('last_transfer', json.dumps(data))
            message_buffer.clear()
        dt = time() - t
        while len(message_buffer) > 0:
            ts.appendleft(dict(message_buffer.pop()))
    sleep(min_pause)
