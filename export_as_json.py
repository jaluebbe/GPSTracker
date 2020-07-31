import os
import json
import redis

redis_connection = redis.Redis(decode_responses=True)

if not os.path.isdir('logs_json'):
    os.mkdir('logs_json')

for key in redis_connection.scan_iter('*'):
    file_name = 'logs_json/' + '_'.join(key.split(':')) + '.json'
    print(key)
    data = redis_connection.lrange(key, 0, -1)
    with open(file_name, "w+") as f:
        f.write('[')
        f.write(',\n'.join(data))
        f.write(']\n')
