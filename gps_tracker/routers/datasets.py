import json
import os
from pathlib import Path
from typing import Union
from redis import asyncio as aioredis
from fastapi import APIRouter, Query, HTTPException
from geojson import FeatureCollection, Feature, LineString
from algorithms import calculate_pressure_altitude
from gebco import Gebco

if "REDIS_HOST" in os.environ:
    redis_host = os.environ["REDIS_HOST"]
else:
    redis_host = "127.0.0.1"
router = APIRouter()
log_directory = Path("../logs_json")


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


@router.get("/api/available_datasets")
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


@router.get("/api/archived_datasets")
async def get_archived_datasets(
    category: str = Query("*", regex="^[*a-z0-9]*$"),
    date: str = Query("*", max_length=8, regex="^[*0-9]*$"),
):
    datasets = [
        _file.name.rstrip(".json")
        for _file in log_directory.glob(f"{category}_*_{date}.json")
    ]
    return datasets


@router.get("/api/dataset/{_id}.json")
async def get_dataset(
    _id: str,
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
        tracking_data = json.loads(f"[{data}]\n")
    return [
        _row
        for _row in tracking_data
        if not (utc_min is not None and _row["utc"] < utc_min)
        and not (utc_max is not None and _row["utc"] > utc_max)
    ]


@router.get("/api/move_to_archive/{_id}")
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


@router.get("/api/dataset/{_id}.geojson")
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
