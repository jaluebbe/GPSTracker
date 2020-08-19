from fastapi import FastAPI, HTTPException
import redis
import json

redis_connection = redis.Redis(decode_responses=True)
app = FastAPI()


@app.get("/api/current_pressure")
def get_current_pressure():
    pressure_data = redis_connection.get('current_pressure')
    if pressure_data is None:
        raise HTTPException(status_code=404, detail="no data available")
    return json.loads(pressure_data)


@app.get("/api/available_datasets")
def get_available_datasets():
    return [key.replace(':', '_') for key in redis_connection.scan_iter('*')]


@app.get("/api/dataset/{id}.json")
def get_dataset(id):
    data = ',\n'.join(redis_connection.lrange(id.replace('_', ':'), 0, -1))
    return json.loads(f"[{data}]")
