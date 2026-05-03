#!/usr/bin/env python3
import time
import subprocess
from syslog import syslog
import gpiod

BUTTON_GPIO = 17
CHIP = "gpiochip0"

chip = gpiod.Chip(CHIP)
line = chip.get_line(BUTTON_GPIO)
line.request(
    consumer="button_reboot_shutdown",
    type=gpiod.LINE_REQ_EV_FALLING_EDGE,
    flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP,
)


def restart():
    syslog("Initiating system restart")
    subprocess.run(["sudo", "shutdown", "-r", "now"])


def shutdown():
    syslog("Initiating system shutdown")
    subprocess.run(["sudo", "shutdown", "-h", "now"])


def wifi_off():
    syslog("Disabling Wi-Fi")
    subprocess.run(["sudo", "nmcli", "radio", "wifi", "off"])


def wifi_on():
    syslog("Enabling Wi-Fi")
    subprocess.run(["sudo", "nmcli", "radio", "wifi", "on"])


if __name__ == "__main__":
    try:
        while True:
            event = line.event_wait(sec=10)
            if not event:
                continue
            line.event_read()
            press_start = time.monotonic()
            while line.get_value() == 0:
                time.sleep(0.05)
                if time.monotonic() - press_start > 5:
                    shutdown()
                    break
            else:
                hold_time = time.monotonic() - press_start
                if hold_time >= 2:
                    restart()
                elif hold_time >= 0.5:
                    wifi_off()
                else:
                    wifi_on()
    finally:
        line.release()
