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
from typing import List, Union
from geojson import FeatureCollection, Feature, LineString
import aioredis
import json
import os
import asyncio
import logging
import sqlite3
import numpy as np
from pathlib import Path
from ellipsoid_fit import ellipsoid_fit, data_regularize
from algorithms import calculate_pressure_altitude
from gebco import Gebco
import gyr_calibration


if "REDIS_HOST" in os.environ:
    redis_host = os.environ["REDIS_HOST"]
else:
    redis_host = "127.0.0.1"

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
    redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)
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
async def root(request: Request):
    if request.url.hostname.startswith("vigor22"):
        return RedirectResponse("/static/vigor22.html")
    elif request.url.hostname.startswith("rotation"):
        return RedirectResponse("/static/rotation_monitor.html")
    else:
        return RedirectResponse("/static/index.html")


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
    redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)
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


@app.get("/api/dataset/{_id}.json")
async def get_dataset(
    _id: str,
    utc_min: Union[int, None] = None,
    utc_max: Union[int, None] = None,
):
    redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)
    reversed_data = await redis_connection.lrange(_id.replace("_", ":"), 0, -1)
    data = ",\n".join(reversed_data[::-1])
    return [
        _row
        for _row in json.loads(f"[{data}]\n")
        if not (utc_min is not None and _row["utc"] < utc_min)
        and not (utc_max is not None and _row["utc"] > utc_max)
    ]


@app.get("/api/move_to_archive/{_id}")
async def move_to_archive(_id):
    redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)
    key = _id.replace("_", ":")
    file_name = log_directory.joinpath(f"{_id}.json")
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


@app.get("/api/dataset/{_id}.geojson")
async def get_geojson_dataset(
    _id: str,
    show_pressure_altitude: bool = Query(True),
    show_gps_altitude: bool = Query(False),
    show_gebco_altitude: bool = Query(False),
    ref_pressure_mbar: float = Query(1013.25),
    utc_min: Union[int, None] = None,
    utc_max: Union[int, None] = None,
    from_archive: bool = Query(False),
):
    if from_archive:
        with log_directory.joinpath(f"{_id}.json").open() as f:
            tracking_data = json.load(f)
    else:
        redis_connection = aioredis.Redis(
            host=redis_host, decode_responses=True
        )
        reversed_data = await redis_connection.lrange(
            _id.replace("_", ":"), 0, -1
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
                and not (utc_min is not None and row["utc"] < utc_min)
                and not (utc_max is not None and row["utc"] > utc_max)
            ]
            if len(_coords) == 0:
                continue
            _feature = Feature(geometry=LineString(_coords))
            _features.append(_feature)
        if len(_features) > 0:
            _feature_collection = FeatureCollection(
                _features, properties={"summary": "GPS altitude"}
            )
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
                and not (utc_min is not None and row["utc"] < utc_min)
                and not (utc_max is not None and row["utc"] > utc_max)
            ]
            if len(_coords) == 0:
                continue
            _feature = Feature(geometry=LineString(_coords))
            _features.append(_feature)
        if len(_features) > 0:
            _feature_collection = FeatureCollection(
                _features, properties={"summary": "barometric altitude"}
            )
            height_data.append(_feature_collection)
    if show_gebco_altitude:
        _gebco = Gebco()
        _features = []
        for _segment in track_segments:
            _coords = [
                [
                    row["lon"],
                    row["lat"],
                    _gebco.get_height(row["lat"], row["lon"])["altitude_m"],
                ]
                for row in _segment
                if row.get("alt") is not None
                and not (row.get("hdop") is not None and row["hdop"] > 20)
                and not (utc_min is not None and row["utc"] < utc_min)
                and not (utc_max is not None and row["utc"] > utc_max)
            ]
            if len(_coords) == 0:
                continue
            _feature = Feature(geometry=LineString(_coords))
            _features.append(_feature)
        if len(_features) > 0:
            _feature_collection = FeatureCollection(
                _features, properties={"summary": "GEBCO altitude"}
            )
            height_data.append(_feature_collection)
    return height_data


async def redis_connector(
    websocket: WebSocket, source_channel: str, target_channel: str
):
    async def consumer_handler(
        redis_connection: aioredis.client.Redis,
        websocket: WebSocket,
        target_channel: str,
    ):
        async for message in websocket.iter_text():
            await redis_connection.publish(target_channel, message)

    async def producer_handler(
        pubsub: aioredis.client.PubSub,
        websocket: WebSocket,
        source_channel: str,
    ):
        await pubsub.subscribe(source_channel)
        async for message in pubsub.listen():
            await websocket.send_text(message["data"])

    redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)
    pubsub = redis_connection.pubsub(ignore_subscribe_messages=True)
    consumer_task = consumer_handler(
        redis_connection, websocket, target_channel
    )
    producer_task = producer_handler(pubsub, websocket, source_channel)
    done, pending = await asyncio.wait(
        [consumer_task, producer_task], return_when=asyncio.FIRST_COMPLETED
    )
    logging.debug(f"Done task: {done}")
    for task in pending:
        logging.debug(f"Cancelling task: {task}")
        task.cancel()
    await redis_connection.close()


@app.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str):
    supported_channels = [
        "imu",
        "gps",
        "barometer",
        "transfer_data",
        "imu_barometer",
        "rotation",
    ]
    await websocket.accept()
    if channel not in supported_channels:
        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
        return
    await redis_connector(
        websocket, source_channel=channel, target_channel="client_feedback"
    )


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
        port_suffix = ""
    else:
        port_suffix = f":{request.url.port}"
    metadata = {
        "tilejson": "2.0.0",
        "scheme": "xyz",
        "tiles": [
            f"{request.url.scheme}://{request.url.hostname}{port_suffix}"
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
