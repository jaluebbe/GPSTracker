from fastapi import FastAPI, HTTPException, Query, WebSocket, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from geojson import FeatureCollection, Feature, LineString
import aioredis
import websockets.exceptions
import json
import os
import asyncio
import logging

if "REDIS_HOST" in os.environ:
    redis_host = os.environ["REDIS_HOST"]
else:
    redis_host = "127.0.0.1"
redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)

app = FastAPI()
app.mount("/static", StaticFiles(directory="../static"), name="static")


# calculate barometric altitude based on the following formula:
# https://www.weather.gov/media/epz/wxcalc/pressureAltitude.pdf
def _calculate_pressure_altitude(pressure, p0=101_325):
    altitude = 0.3048 * 145_366.45 * (1 - pow(pressure / p0, 0.190_284))
    return altitude


async def _get_channel_data(channel):
    pubsub = redis_connection.pubsub(ignore_subscribe_messages=True)
    await pubsub.subscribe(channel)
    while True:
        message = await pubsub.get_message()
        if message is not None:
            _channel = message["channel"]
            _data = json.loads(message["data"])
            _data["channel"] = _channel
            return _data
        await asyncio.sleep(0.01)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/static/index.html")


@app.get("/api/websocket_connections")
async def get_websocket_connections():
    websocket_connections = await redis_connection.get("ws_connections")
    return websocket_connections


@app.get("/api/current_pressure")
async def get_current_pressure():
    channel = "barometer"
    try:
        pressure_data = await asyncio.wait_for(_get_channel_data(channels), 0.2)
    except asyncio.TimeoutError:
        logging.exception("/api/current_pressure")
        raise HTTPException(status_code=404, detail="no data available")
    return pressure_data


@app.get("/api/current_orientation")
async def get_current_orientation():
    channel = "imu"
    try:
        imu_data = await asyncio.wait_for(_get_channel_data(channel), 0.2)
    except asyncio.TimeoutError:
        logging.exception("/api/current_orientation")
        raise HTTPException(status_code=404, detail="no data available")
    return imu_data


@app.get("/api/available_datasets")
async def get_available_datasets(
    category: str = Query("*", regex="^[*a-z0-9]*$"),
    date: str = Query("*", max_length=8, regex="^[*0-9]*$"),
):
    datasets = [
        key.replace(":", "_")
        async for key in redis_connection.scan_iter(f"{category}:*:{date}")
    ]
    return datasets


@app.get("/api/dataset/{id}.json")
async def get_dataset(id):
    reversed_data = await redis_connection.lrange(id.replace("_", ":"), 0, -1)
    data = ",\n".join(reversed_data[::-1])
    return json.loads(f"[{data}]")


@app.get("/api/dataset/{id}.geojson")
async def get_geojson_dataset(
    id: str = Query(..., regex="^tracking_[a-z0-9]*_[0-9]{8}$"),
    show_pressure_altitude: bool = True,
    show_gps_altitude: bool = False,
    ref_pressure_mbar: float = 1013.25,
):
    reversed_data = await redis_connection.lrange(id.replace("_", ":"), 0, -1)
    data = ",\n".join(reversed_data[::-1])
    height_data = []
    tracking_data = json.loads(f"[{data}]")
    if show_gps_altitude:
        _coords = [
            [row["lon"], row["lat"], row["alt"]]
            for row in tracking_data
            if row.get("alt") is not None
            and not (row.get("hdop") is not None and row["hdop"] > 20)
        ]
        _feature = Feature(geometry=LineString(_coords))
        _features = [_feature]
        _feature_collection = FeatureCollection(
            _features, properties={"summary": "GPS altitude"}
        )
        if len(_coords) > 0:
            height_data.append(_feature_collection)
    if show_pressure_altitude:
        _coords = [
            [
                row["lon"],
                row["lat"],
                round(
                    _calculate_pressure_altitude(
                        pressure=row["pressure"], p0=ref_pressure_mbar * 100
                    ),
                    2,
                ),
            ]
            for row in tracking_data
            if row.get("pressure") is not None
            and row.get("alt") is not None
            and not (row.get("hdop") is not None and row["hdop"] > 20)
        ]
        _feature = Feature(geometry=LineString(_coords))
        _features = [_feature]
        _feature_collection = FeatureCollection(
            _features, properties={"summary": "barometric altitude"}
        )
        if len(_coords) > 0:
            height_data.append(_feature_collection)
    return height_data


@app.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str):
    supported_channels = [
        "imu",
        "gps",
        "barometer",
        "transfer_data",
        "ws_connections",
        "imu_pressure",
    ]
    await websocket.accept()
    if channel not in supported_channels:
        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
        return
    pubsub = redis_connection.pubsub(ignore_subscribe_messages=True)
    await pubsub.subscribe(channel)
    ws_connections = await redis_connection.incr("ws_connections")
    await redis_connection.publish("ws_connections", ws_connections)
    while True:
        try:
            message = await pubsub.get_message()
            if message is not None:
                await websocket.send_text(message["data"])
            await asyncio.sleep(0.01)
        except asyncio.TimeoutError:
            pass
        except websockets.exceptions.ConnectionClosedError:
            ws_connections = await redis_connection.decr("ws_connections")
            await redis_connection.publish("ws_connections", ws_connections)
            logging.exception("abnormal closure of websocket connection.")
            break
        except websockets.exceptions.ConnectionClosedOK:
            ws_connections = await redis_connection.decr("ws_connections")
            await redis_connection.publish("ws_connections", ws_connections)
            # normal closure with close code 1000
            break
