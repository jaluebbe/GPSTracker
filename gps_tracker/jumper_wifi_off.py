#!/usr/bin/env python3
import time
import os
import re
import subprocess
from syslog import syslog

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)  # Set pin numbering to board numbering
GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Setup pin 21 as an input

if __name__ == "__main__":
    wifi_re = re.compile(
        "(?P<soft_block>(?:un){0,1}blocked) (?P<hard_block>(?:un){0,1}blocked)"
    )
    wifi_state = wifi_re.search(subprocess.check_output("rfkill").decode())
    wifi_disabled = wifi_state["soft_block"] == "blocked"
    while True:
        if GPIO.input(21) == 0 and not wifi_disabled:
            os.system("sudo rfkill block wlan")
            wifi_disabled = True
            syslog("disabled wifi")
        elif GPIO.input(21) == 1 and wifi_disabled:
            os.system("sudo rfkill unblock wlan")
            if os.path.isfile("/usr/bin/autohotspot"):
                time.sleep(5)
                os.system("sudo /usr/bin/autohotspot")
            wifi_disabled = False
            syslog("enabled wifi")
        # reduce CPU usage by sleep time
        time.sleep(1.0)
