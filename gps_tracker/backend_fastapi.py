from fastapi import FastAPI, HTTPException, Query
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
def get_available_datasets(category: str = Query('*', regex='^[*a-z0-9]*$'),
        date: str = Query('*', max_length=8, regex='^[*0-9]*$')):
    return [key.replace(':', '_') for key in redis_connection.scan_iter(
        f'{category}:*:{date}')]


@app.get("/api/dataset/{id}.json")
def get_dataset(id):
    data = ',\n'.join(redis_connection.lrange(id.replace('_', ':'), 0, -1))
    return json.loads(f"[{data}]")
