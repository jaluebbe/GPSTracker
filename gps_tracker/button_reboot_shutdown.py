#!/usr/bin/env python3
import time
import os
from syslog import syslog
import RPi.GPIO as GPIO

BUTTON_GPIO = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_GPIO, GPIO.IN)


def restart():
    syslog("Initiating system restart")
    os.system("sudo shutdown -r now")
    exit(0)


def shutdown():
    syslog("Initiating system shutdown")
    os.system("sudo shutdown -h now")
    exit(0)


def wifi_off():
    wifi_status = os.popen("nmcli radio wifi").read().strip()
    if wifi_status == "enabled":
        syslog("Disabling Wi-Fi")
        os.system("sudo nmcli radio wifi off")


def wifi_on():
    wifi_status = os.popen("nmcli radio wifi").read().strip()
    if wifi_status != "enabled":
        syslog("Enabling Wi-Fi")
        os.system("sudo nmcli radio wifi on")


if __name__ == "__main__":
    while True:
        GPIO.wait_for_edge(BUTTON_GPIO, GPIO.FALLING, bouncetime=200)
        hold_time = 0
        while GPIO.input(BUTTON_GPIO) == GPIO.LOW:
            time.sleep(0.1)
            hold_time += 0.1
            if hold_time > 5:
                shutdown()
        if hold_time < 0.5:
            wifi_on()
        elif hold_time < 2:
            wifi_off()
            continue
        elif hold_time >= 2:
            restart()
