#!/usr/bin/env python3
import subprocess
from syslog import syslog
import gpiod

BUTTON_GPIO = 21
CHIP = "gpiochip0"

chip = gpiod.Chip(CHIP)
line = chip.get_line(BUTTON_GPIO)
line.request(
    consumer="button_shutdown",
    type=gpiod.LINE_REQ_EV_FALLING_EDGE,
    flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP,
)


def shutdown():
    syslog("Initiating system shutdown")
    subprocess.run(["sudo", "shutdown", "-h", "now"])


if __name__ == "__main__":
    try:
        while True:
            event = line.event_wait(sec=10)
            if not event:
                continue
            line.event_read()
            shutdown()
    finally:
        line.release()
