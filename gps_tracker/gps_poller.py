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
                sky_info.clear()
                for _key in ("hdop", "vdop", "pdop", "uSat", "nSat"):
                    sky_info[_key] = msg[_key]
            elif msg["class"] == "TPV":
                data = dict(msg)
                if data.get("time") is None:
                    continue
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
                if devices is not None and old_utc is not None:
                    _driver = devices[0]["driver"]
                    _path = devices[0]["path"]
                    if config_counter > 5:
                        pass
                    elif _path != "/dev/serial0":
                        pass
                    elif _driver == "u-blox" and data["utc"] - old_utc > 0.7:
                        # set the data rate of the GPS to 2Hz
                        # (up to 10Hz is possible)
                        subprocess.check_output(
                            ["gpsctl", "-c", "0.5", "-s", "115200"], timeout=8
                        )
                        config_counter = config_counter + 1
                    elif _driver == "MTK-3301" and data["utc"] - old_utc > 0.7:
                        # set the data rate of the GPS to 2Hz
                        subprocess.check_output(
                            ["gpsctl", "-c", "0.5"], timeout=8
                        )
                        config_counter = config_counter + 1
                old_utc = data["utc"]
            elif msg["class"] == "DEVICES":
                devices = msg["devices"]
                await redis_connection.set(
                    "gps_devices", orjson.dumps(msg["devices"])
                )


if __name__ == "__main__":
    asyncio.run(consume_gpsd())
