#!venv/bin/python3
import json
import socket
import time

import redis

CHANNEL = "smart_meter"
INTERVAL = 15
FIELDS = (
    "power",
    "powerProduction",
    "powerL1",
    "powerL2",
    "powerL3",
    "currentL1",
    "currentL2",
    "currentL3",
    "voltagePhase1",
    "voltagePhase2",
    "voltagePhase3",
)


MAX_FIELDS = ("powerL1", "powerL2", "powerL3")


class SmartMeterLogger:
    def __init__(self):
        self.redis_connection = redis.Redis(decode_responses=True)
        self.hostname = socket.gethostname()
        self.window_end = None
        self.samples = []
        self._pubsub = self.redis_connection.pubsub(
            ignore_subscribe_messages=True
        )
        self._pubsub.subscribe(CHANNEL)

    def _flush(self):
        if not self.samples:
            return
        record = {"utc": int(self.window_end), "hostname": self.hostname}
        for field in FIELDS:
            values = [s[field] for s in self.samples if field in s]
            if values:
                record[field] = round(sum(values) / len(values), 2)
                if field in MAX_FIELDS:
                    record[f"{field}Max"] = round(max(values), 2)
        day = time.strftime("%Y%m%d", time.localtime(self.window_end - 1))
        key = f"smartmeter:{self.hostname}:{day}"
        self.redis_connection.lpush(key, json.dumps(record))
        self.samples = []

    def process_message(self, item):
        data = json.loads(item["data"])
        utc = data["utc"]
        window_end = utc - utc % INTERVAL + INTERVAL
        if self.window_end is None:
            self.window_end = window_end
        elif window_end > self.window_end:
            self._flush()
            self.window_end = window_end
        self.samples.append(data)

    def run(self):
        while True:
            item = self._pubsub.get_message(timeout=1)
            if item is not None and item["type"] == "message":
                try:
                    self.process_message(item)
                except (KeyError, ValueError, TypeError):
                    continue


if __name__ == "__main__":
    SmartMeterLogger().run()
