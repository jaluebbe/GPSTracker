from fastapi import FastAPI, HTTPException, Query
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse
from geojson import FeatureCollection, Feature, LineString
import redis
import json

redis_connection = redis.Redis(decode_responses=True)
app = FastAPI()

app.mount("/static", StaticFiles(directory="../static"), name="static")


@app.get("/", include_in_schema=False)
async def root():
    return FileResponse('../index.html')


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
    data = ',\n'.join(redis_connection.lrange(id.replace('_', ':'), 0, -1)[
        ::-1])
    return json.loads(f"[{data}]")


@app.get("/api/dataset/{id}.geojson")
def get_geojson_dataset(id: str = Query(...,
        regex='^tracking_[a-z0-9]*_[0-9]{8}$')):
    data = ',\n'.join(redis_connection.lrange(id.replace('_', ':'), 0, -1)[
        ::-1])
    tracking_data = json.loads(f"[{data}]")
    _coords = [[row['lon'], row['lat'], row['alt']] for row in tracking_data if
        row.get('alt') is not None]
    _feature = Feature(geometry=LineString(_coords))
    _features = [_feature]
    return [FeatureCollection(_features, properties={'summary': 'GPS altitude'}
        )]
