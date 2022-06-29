import os
import json
import redis

redis_connection = redis.Redis(decode_responses=True)

for file_name in os.listdir("logs_json"):
    key = os.path.basename(file_name).rstrip(".json").replace("_", ":")
    print(key)
    with open(file_name) as f:
        data = json.load(f)
    json_data = [json.dumps(_row) for _row in data]
    redis_connection.lpush(key, *json_data)
