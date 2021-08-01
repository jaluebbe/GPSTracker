#!/usr/bin/env python3
import time
import os
from syslog import syslog

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)  # Set pin numbering to board numbering
GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Setup pin 21 as an input

if __name__ == "__main__":
    wifi_disabled = False
    while True:
        if GPIO.input(21) == 0 and not wifi_disabled:
            os.system("sudo iwconfig wlan0 txpower off")
            wifi_disabled = True
            syslog("disabled wifi")
        elif GPIO.input(21) == 1 and wifi_disabled:
            os.system("sudo iwconfig wlan0 txpower auto")
            wifi_disabled = False
            syslog("enabled wifi")
        # reduce CPU usage by sleep time
        time.sleep(10.0)
