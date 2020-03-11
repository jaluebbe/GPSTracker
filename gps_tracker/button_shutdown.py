#!/usr/bin/env python3
import time
import os
from syslog import syslog

# GPIO access for shutdown control
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)  # Set pin numbering to board numbering
GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Setup pin 21 as an input

if __name__ == '__main__':
    shutdown_triggered = False
    try:
        while True:
            if GPIO.input(21) == 0:
                shutdown_triggered = True
                break
            # reduce CPU usage by sleep time
            time.sleep(1.0)
    except (KeyboardInterrupt, SystemExit):  # when you press ctrl+c
        print("Exception in main")
    finally:
        print("\nKilling Thread...")
        syslog("Killing Thread...")
        if shutdown_triggered:
            syslog('initiating system shutdown')
            os.system("sudo shutdown -h now")  # Send shutdown command to os
        else:
            print ("Exit without triggering shutdown.")
