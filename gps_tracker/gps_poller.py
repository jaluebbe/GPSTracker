#!venv/bin/python3
import signal
import sys
import asyncio
import socket
import orjson
import datetime as dt
import gps.aiogps
from redis import asyncio as aioredis
import subprocess


def sigterm_handler(signal, frame):
    # setting the baud rate of the GPS back to standard before rebooting.
    subprocess.check_output(["gpsctl", "-s", "9600"], timeout=8)
    sys.exit(0)


signal.signal(signal.SIGTERM, sigterm_handler)


async def consume_gpsd():
    hostname = socket.gethostname()
    redis_connection = aioredis.Redis()

    async with gps.aiogps.aiogps() as gpsd:
        sky_info = {}
        config_counter = 0
        devices = None
        old_utc = None
        async for msg in gpsd:
            if msg["class"] == "SKY":
                sky_info = {
                    key: msg[key]
                    for key in ("hdop", "vdop", "pdop", "uSat", "nSat")
                }
            elif msg["class"] == "TPV":
                if "time" not in msg:
                    continue
                data = dict(msg)
                data.update(sky_info)
                data["hostname"] = hostname
                data["utc"] = (
                    dt.datetime.fromisoformat(data["time"].rstrip("Z"))
                    .replace(tzinfo=dt.timezone.utc)
                    .timestamp()
                )
                if data["utc"] == old_utc:
                    # observed duplicated entries using the MTK-3301 driver
                    continue
                for _key in ("magtrack", "magvar"):
                    data.pop(_key, None)
                if data["mode"] > 1:
                    data["sensor"] = "gps"
                    await redis_connection.publish("gps", orjson.dumps(data))
                if devices and old_utc:
                    _driver = devices[0]["driver"]
                    _path = devices[0]["path"]
                    if (
                        config_counter <= 5
                        and _path == "/dev/serial0"
                        and data["utc"] - old_utc > 0.7
                    ):
                        if _driver == "u-blox":
                            # set the data rate of the GPS to 2Hz
                            # (up to 10Hz is possible)
                            subprocess.check_output(
                                ["gpsctl", "-c", "0.5", "-s", "115200", "-n"],
                                timeout=8,
                            )
                            config_counter += 1
                        elif _driver == "MTK-3301":
                            # set the data rate of the GPS to 2Hz
                            subprocess.check_output(
                                ["gpsctl", "-c", "0.5"], timeout=8
                            )
                            config_counter += 1
                old_utc = data["utc"]
            elif msg["class"] == "DEVICES":
                devices = msg["devices"]
                await redis_connection.set(
                    "gps_devices", orjson.dumps(msg["devices"])
                )


if __name__ == "__main__":
    asyncio.run(consume_gpsd())
