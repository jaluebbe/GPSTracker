#!/usr/bin/env python3
import time
import subprocess
from syslog import syslog
import gpiod

JUMPER_GPIO = 21
CHIP = "gpiochip0"

chip = gpiod.Chip(CHIP)
line = chip.get_line(JUMPER_GPIO)
line.request(
    consumer="jumper_wifi_off",
    type=gpiod.LINE_REQ_DIR_IN,
    flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP,
)


def wifi_off():
    subprocess.run(["sudo", "nmcli", "radio", "wifi", "off"])
    syslog("Disabled Wi-Fi")


def wifi_on():
    subprocess.run(["sudo", "nmcli", "radio", "wifi", "on"])
    syslog("Enabled Wi-Fi")


if __name__ == "__main__":
    try:
        wifi_disabled = False
        while True:
            jumper_closed = line.get_value() == 0
            if jumper_closed and not wifi_disabled:
                wifi_off()
                wifi_disabled = True
            elif not jumper_closed and wifi_disabled:
                wifi_on()
                wifi_disabled = False
            time.sleep(1.0)
    finally:
        line.release()
