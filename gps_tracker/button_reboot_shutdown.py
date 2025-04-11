#!/usr/bin/env python3
import time
import os
from syslog import syslog
import RPi.GPIO as GPIO

BUTTON_GPIO = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_GPIO, GPIO.IN)


def restart():
    syslog("initiating system restart")
    os.system("sudo shutdown -r now")
    exit(0)


def shutdown():
    syslog("initiating system shutdown")
    os.system("sudo shutdown -h now")
    exit(0)


if __name__ == "__main__":
    while True:
        # reduce CPU usage by sleep time
        time.sleep(0.5)
        channel = GPIO.wait_for_edge(BUTTON_GPIO, GPIO.FALLING, bouncetime=200)
        if channel is None:
            continue
        counter = 0

        while GPIO.input(BUTTON_GPIO) == False:
            counter += 1
            time.sleep(0.5)
            if counter > 5:
                shutdown()
        if counter > 1:
            restart()
