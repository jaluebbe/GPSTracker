import os
import json
import asyncio
import logging
from typing import List
import numpy as np
from redis import asyncio as aioredis
from fastapi import APIRouter, HTTPException, Request, Response, WebSocket, status
from ellipsoid_fit import ellipsoid_fit, data_regularize
import gyr_calibration

router = APIRouter()

if "REDIS_HOST" in os.environ:
    redis_host = os.environ["REDIS_HOST"]
else:
    redis_host = "127.0.0.1"


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


@router.get("/api/current_pressure")
async def get_current_pressure():
    channel = "barometer"
    try:
        pressure_data = await asyncio.wait_for(_get_channel_data(channel), 0.2)
    except asyncio.TimeoutError:
        logging.exception("/api/current_pressure")
        raise HTTPException(status_code=404, detail="no data available")
    return pressure_data


@router.get("/api/calibrate_gyro")
def calibrate_gyro():
    return gyr_calibration.calibrate()


@router.get("/api/current_orientation")
async def get_current_orientation():
    channel = "imu"
    try:
        imu_data = await asyncio.wait_for(_get_channel_data(channel), 0.2)
    except asyncio.TimeoutError:
        logging.exception("/api/current_orientation")
        raise HTTPException(status_code=404, detail="no data available")
    return imu_data


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
    consumer_task = asyncio.create_task(
        consumer_handler(redis_connection, websocket, target_channel)
    )
    producer_task = asyncio.create_task(
        producer_handler(pubsub, websocket, source_channel)
    )
    done, pending = await asyncio.wait(
        [consumer_task, producer_task], return_when=asyncio.FIRST_COMPLETED
    )
    logging.debug(f"Done task: {done}")
    for task in pending:
        logging.debug(f"Cancelling task: {task}")
        task.cancel()
    await redis_connection.close()


@router.websocket("/ws/{channel}")
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


@router.post("/api/calibrate_magnetometer")
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
