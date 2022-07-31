#!/usr/bin/env python3
import asyncio
import socket
import json
import datetime as dt
import gps.aiogps
import aioredis
import subprocess


async def consume_gpsd():
    hostname = socket.gethostname()
    redis_connection = aioredis.Redis()
    async with gps.aiogps.aiogps() as gpsd:
        sky_info = {}
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
                    await redis_connection.publish("gps", json.dumps(data))
                if devices is not None and old_utc is not None:
                    _driver = devices[0]["driver"]
                    if _driver == "u-blox" and data["utc"] - old_utc > 0.16:
                        # set the data rate of the GPS to 10Hz
                        subprocess.check_output(
                            ["gpsctl", "-c", "0.1", "-s", "115200"], timeout=8
                        )
                    elif _driver == "MTK-3301" and data["utc"] - old_utc > 0.7:
                        # set the data rate of the GPS to 2Hz
                        subprocess.check_output(
                            ["gpsctl", "-c", "0.5"], timeout=8
                        )
                old_utc = data["utc"]
            elif msg["class"] == "DEVICES":
                devices = msg["devices"]
                await redis_connection.set(
                    "gps_devices", json.dumps(msg["devices"])
                )


if __name__ == "__main__":
    asyncio.run(consume_gpsd())
