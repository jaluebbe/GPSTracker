#!/usr/bin/env python3
import time
import subprocess
from syslog import syslog
from gpiozero import Button
from gpiozero.pins.lgpio import LGPIOFactory
from gpiozero import Device

Device.pin_factory = LGPIOFactory()

BUTTON_GPIO = 17
button = Button(BUTTON_GPIO, bounce_time=0.2)


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
            button.wait_for_press()
            press_start = time.monotonic()
            button.wait_for_release()
            hold_time = time.monotonic() - press_start

            if hold_time > 5:
                shutdown()
            elif hold_time >= 2:
                restart()
            elif hold_time >= 0.5:
                wifi_off()
            else:
                wifi_on()
    finally:
        button.close()
