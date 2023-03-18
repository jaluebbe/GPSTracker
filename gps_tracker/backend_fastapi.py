from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    WebSocket,
    status,
    Request,
    Response,
)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from typing import List
from geojson import FeatureCollection, Feature, LineString
import aioredis
import websockets.exceptions
import json
import os
import asyncio
import logging
import sqlite3
import numpy as np
from pathlib import Path
from ellipsoid_fit import ellipsoid_fit, data_regularize
from algorithms import calculate_pressure_altitude
import gyr_calibration


if "REDIS_HOST" in os.environ:
    redis_host = os.environ["REDIS_HOST"]
else:
    redis_host = "127.0.0.1"
redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)

app = FastAPI()
app.mount("/static", StaticFiles(directory="../static"), name="static")
if Path("../fonts").is_dir():
    app.mount("/fonts", StaticFiles(directory="../fonts"), name="fonts")
log_directory = Path("../logs_json")
if not log_directory.is_dir():
    log_directory.mkdir()
app.mount("/archive", StaticFiles(directory=log_directory), name="archive")


def split_track_segments(tracking_data, delta_t=600):
    """
    split tracking data into segments where the time gap is larger than delta_t.
    """
    index_list = (
        [None]
        + [
            i
            for i in range(1, len(tracking_data))
            if tracking_data[i]["utc"] - tracking_data[i - 1]["utc"] > delta_t
        ]
        + [None]
    )
    return [
        tracking_data[index_list[j - 1] : index_list[j]]
        for j in range(1, len(index_list))
    ]


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
        pressure_data = await asyncio.wait_for(_get_channel_data(channel), 0.2)
    except asyncio.TimeoutError:
        logging.exception("/api/current_pressure")
        raise HTTPException(status_code=404, detail="no data available")
    return pressure_data


@app.get("/api/calibrate_gyro")
def calibrate_gyro():
    return gyr_calibration.calibrate()


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


@app.get("/api/archived_datasets")
async def get_archived_datasets(
    category: str = Query("*", regex="^[*a-z0-9]*$"),
    date: str = Query("*", max_length=8, regex="^[*0-9]*$"),
):
    datasets = [
        _file.name.rstrip(".json")
        for _file in log_directory.glob(f"{category}_*_{date}.json")
    ]
    return datasets


@app.get("/api/dataset/{id}.json")
async def get_dataset(id):
    reversed_data = await redis_connection.lrange(id.replace("_", ":"), 0, -1)
    data = ",\n".join(reversed_data[::-1])
    return json.loads(f"[{data}]\n")


@app.get("/api/move_to_archive/{id}")
async def move_to_archive(id):
    key = id.replace("_", ":")
    file_name = log_directory.joinpath(f"{id}.json")
    reversed_data = await redis_connection.lrange(key, 0, -1)
    data = ",\n".join(reversed_data[::-1])
    if len(data) == 0:
        raise HTTPException(status_code=404, detail="dataset unknown.")
    json_string = f"[{data}]\n"
    if not file_name.exists():
        file_name.write_text(json_string)
    # compare to written or existing data.
    existing_data = file_name.read_text()
    if existing_data == json_string:
        # delete dataset from Redis only if a copy exists.
        await redis_connection.delete(key)
    else:
        raise HTTPException(
            status_code=409, detail="data doesn't match to existing file."
        )
    return json.loads(json_string)


@app.get("/api/dataset/{id}.geojson")
async def get_geojson_dataset(
    id: str = Query(..., regex="^tracking_[a-z0-9]*_[0-9]{8}$"),
    show_pressure_altitude: bool = Query(True),
    show_gps_altitude: bool = Query(False),
    ref_pressure_mbar: float = Query(1013.25),
    from_archive: bool = Query(False),
):
    if from_archive:
        with log_directory.joinpath(f"{id}.json").open() as f:
            tracking_data = json.load(f)
    else:
        reversed_data = await redis_connection.lrange(
            id.replace("_", ":"), 0, -1
        )
        data = ",\n".join(reversed_data[::-1])
        tracking_data = json.loads(f"[{data}]")
    track_segments = split_track_segments(tracking_data)
    height_data = []
    if show_gps_altitude:
        _features = []
        for _segment in track_segments:
            _coords = [
                [row["lon"], row["lat"], row["alt"]]
                for row in _segment
                if row.get("alt") is not None
                and not (row.get("hdop") is not None and row["hdop"] > 20)
            ]
            _feature = Feature(geometry=LineString(_coords))
            _features.append(_feature)
        _feature_collection = FeatureCollection(
            _features, properties={"summary": "GPS altitude"}
        )
        if len(_coords) > 0:
            height_data.append(_feature_collection)
    if show_pressure_altitude:
        _features = []
        for _segment in track_segments:
            _coords = [
                [
                    row["lon"],
                    row["lat"],
                    round(
                        calculate_pressure_altitude(
                            pressure=row["pressure"], p0=ref_pressure_mbar * 100
                        ),
                        2,
                    ),
                ]
                for row in _segment
                if row.get("pressure") is not None
                and row.get("alt") is not None
                and not (row.get("hdop") is not None and row["hdop"] > 20)
            ]
            _feature = Feature(geometry=LineString(_coords))
            _features.append(_feature)
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
        "imu_barometer",
        "rotation",
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


@app.post("/api/calibrate_magnetometer")
async def calibrate_magnetometer(data: List):
    # based on https://github.com/aleksandrbazhin/ellipsoid_fit_python
    center, evecs, radii, v = ellipsoid_fit(
        data_regularize(np.array(data), divs=8)
    )
    a, b, c = radii
    r = (a * b * c) ** (1.0 / 3.0)
    D = np.array([[r / a, 0.0, 0.0], [0.0, r / b, 0.0], [0.0, 0.0, r / c]])
    # http://www.cs.brandeis.edu/~cs155/Lecture_07_6.pdf
    # affine transformation from ellipsoid to sphere (translation excluded)
    TR = evecs.dot(D).dot(evecs.T)
    calibration = {"m_matrix": TR.tolist(), "m_offset": center.tolist()}
    for _key, _value in calibration.items():
        await redis_connection.set(_key, json.dumps(_value))
    return calibration


@app.get("/api/vector/metadata/{region}.json")
def get_vector_metadata(region: str, request: Request):
    db_file_name = f"{region}.mbtiles"
    if not os.path.isfile(db_file_name):
        raise HTTPException(
            status_code=404, detail=f"Region '{region}' not found."
        )
    db_connection = sqlite3.connect(f"file:{db_file_name}?mode=ro", uri=True)
    cursor = db_connection.execute("SELECT * FROM metadata")
    result = cursor.fetchall()
    cursor.close()
    db_connection.close()
    if result is None:
        raise HTTPException(status_code=404, detail="Metadata not found.")
    if request.url.port is None:
        # workaround for operation behind reverse proxy
        port_suffix = ""
        scheme = "https"
    else:
        port_suffix = f":{request.url.port}"
        scheme = request.url.scheme
    metadata = {
        "tilejson": "2.0.0",
        "scheme": "xyz",
        "tiles": [
            f"{scheme}://{request.url.hostname}{port_suffix}"
            f"/api/vector/tiles/{region}/{{z}}/{{x}}/{{y}}.pbf"
        ],
    }
    for key, value in result:
        if key == "json":
            metadata.update(json.loads(value))
        elif key in ("minzoom", "maxzoom"):
            metadata[key] = int(value)
        elif key == "center":
            continue
        elif key == "bounds":
            metadata[key] = [float(_value) for _value in value.split(",")]
        else:
            metadata[key] = value
    return metadata


@app.get("/api/vector/tiles/{region}/{zoom_level}/{x}/{y}.pbf")
def get_vector_tiles(region: str, zoom_level: int, x: int, y: int):
    tile_column = x
    tile_row = 2**zoom_level - 1 - y
    db_file_name = f"{region}.mbtiles"
    if not os.path.isfile(db_file_name):
        raise HTTPException(
            status_code=404, detail=f"Region '{region}' not found."
        )
    db_connection = sqlite3.connect(f"file:{db_file_name}?mode=ro", uri=True)
    cursor = db_connection.execute(
        "SELECT tile_data FROM tiles "
        "WHERE zoom_level = ? and tile_column = ? and tile_row = ?",
        (zoom_level, tile_column, tile_row),
    )
    result = cursor.fetchone()
    cursor.close()
    db_connection.close()
    if result is None:
        raise HTTPException(status_code=404, detail="Tile not found.")
    return Response(
        content=result[0],
        media_type="application/octet-stream",
        headers={"Content-Encoding": "gzip"},
    )
