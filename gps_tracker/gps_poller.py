#!venv/bin/python3
import asyncio
import datetime as dt
import logging
import signal
import socket
import subprocess
import sys
from pathlib import Path

import orjson
from redis import asyncio as aioredis

import gps.aiogps


def fixed_baudrate_set():
    gpsd_config = Path("/etc/default/gpsd")
    if gpsd_config.exists():
        with gpsd_config.open("r") as config_file:
            for line in config_file:
                if line.startswith("GPSD_OPTIONS=") and "-s" in line:
                    return True
    return False


def call_gpsctl(args, timeout=12):
    try:
        cmd = ["gpsctl"] + args.split()
        subprocess.check_output(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        logging.exception(f"The gpsctl command timed out.")


def sigterm_handler(signal, frame):
    # setting the baud rate of the GPS back to standard before rebooting.
    call_gpsctl("-s 9600")
    sys.exit(0)


if not fixed_baudrate_set():
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
                    if key in msg
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
                    _driver = devices[0].get("driver")
                    _path = devices[0].get("path")
                    if (
                        config_counter <= 5
                        and _path == "/dev/ttyS0"
                        and data["utc"] - old_utc > 0.7
                    ):
                        if _driver == "u-blox":
                            # set the data rate of the GPS to 2Hz
                            # (up to 10Hz is possible)
                            call_gpsctl("-c 0.5 -s 115200 -n")
                            config_counter += 1
                        elif _driver == "MTK-3301":
                            # set the data rate of the GPS to 2Hz
                            call_gpsctl("-c 0.5")
                            config_counter += 1
                old_utc = data["utc"]
            elif msg["class"] == "DEVICES":
                devices = msg["devices"]
                await redis_connection.set(
                    "gps_devices", orjson.dumps(msg["devices"])
                )


if __name__ == "__main__":
    asyncio.run(consume_gpsd())
