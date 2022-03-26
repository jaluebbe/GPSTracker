#!/usr/bin/env python3
import asyncio
import socket
import json
from datetime import datetime as dt
import gps.aiogps
import aioredis


async def consume_gpsd():
    hostname = socket.gethostname()
    redis_connection = aioredis.Redis()
    async with gps.aiogps.aiogps() as gpsd:
        sky_info = {}
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
                data["utc"] = dt.fromisoformat(
                    data["time"].rstrip("Z")
                ).timestamp()
                for _key in ("magtrack", "magvar"):
                    data.pop(_key, None)
                if data["mode"] > 1:
                    await redis_connection.publish("gps", json.dumps(data))
                print(data)


if __name__ == "__main__":
    asyncio.run(consume_gpsd())
