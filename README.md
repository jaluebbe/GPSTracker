# GPSTracker
Use a Raspberry Pi with a GPS receiver and a pressure sensor. 
Tracking data from this setup and other sources can be visualised using 
Leaflet.js and several plugins. 
Optional, orientation data from an IMU may be recorded (work in progress).

## Installation
It is assumed that you are using Raspberry Pi OS (Lite version) on your 
Raspberry Pi. Depending on the type of your Raspberry Pi your may either the 32bit or the 64bit version. You are free to choose your username except for the name "gpstracker" which will be generated later. In the following we assume "pi" as username.
### Installation with sudo privileges
These steps are performed under your username with sudo privileges:
```
sudo apt update
sudo apt upgrade
sudo apt dist-upgrade
sudo apt install chrony gpsd git redis-server python3-gps python3-pip \
python3-scipy python3-smbus hostapd dnsmasq
sudo systemctl unmask hostapd
sudo systemctl disable hostapd
sudo systemctl disable dnsmasq
sudo useradd -m gpstracker
sudo usermod -a -G i2c,video gpstracker
sudo passwd gpstracker
```

### GPS setup and test
If a compatible GPS device is attached via USB set these options in /etc/default/gpsd :
```
DEVICES=""
GPSD_OPTIONS="-n"
USBAUTO="true"
```
Or if the GPS device is attached via serial port, set the following parameters in /etc/default/gpsd :
```
DEVICES="/dev/serial0"
GPSD_OPTIONS="-n"
USBAUTO="false"
```

You have to enable the serial port via
```
sudo raspi-config
```
and select "Interface Options" -> "Serial Port" -> "No" -> "Yes" -> "Ok". The I2C interface should be enabled as well if other sensors like barometer or IMU are connected.

Reboot your device with
```
sudo reboot
```
if not done before.

Put the GPS antenna close to a window or outdoors and call cgps (terminate with Ctrl+C).
You should see messages from your device every second or even the coordinates of your location. 

### Obtain time from GPS
When the GPS is running, it’s time to setup the retrieval of the time via GPS.
Edit /etc/chrony/chrony.conf and set the following parameters:
```
makestep 1 -1
refclock SHM 0 offset 0.2 refid GPS
```

Restart chrony by calling
```
sudo /etc/init.d/chrony restart
```
and call:
```
chronyc sources
```

In the GPS row, the value Reach should be above zero.
It could take some time, you may recheck later.

### Install GPS tracking software
We created a "gpstracker" user with the required privileges.
Now let's switch to this user (to go back to your user, type "exit"):
```
sudo su - gpstracker  # or login as user gpstracker directly
pip install fastapi geojson websockets pygeodesy aioredis redis uvicorn
git clone https://github.com/Mayitzin/ahrs.git
cd ahrs
python setup.py install --user
cd
git clone https://github.com/jaluebbe/GPSTracker.git
cd GPSTracker
git clone https://github.com/klokantech/klokantech-gl-fonts fonts
ln -s ../../osm_offline.mbtiles gps_tracker/osm_offline.mbtiles
```

### Test Python scripts
Enter the subfolder containing all the Python scripts:
```
cd gps_tracker
```
TODO

### Start Python scripts as system services during boot
```
sudo cp /home/gpstracker/etc/systemd/system/gpspoller.service /etc/systemd/system/
sudo systemctl enable gpspoller.service
```

```
sudo cp /home/gpstracker/etc/systemd/system/gps_baro_merge.service /etc/systemd/system/
sudo systemctl enable gps_baro_merge.service
```

Optional, if a shutdown button is attached between GND and GPIO21:
```
sudo cp /home/gpstracker/etc/systemd/system/button_shutdown.service /etc/systemd/system/
sudo systemctl enable button_shutdown.service
```

Optional, if data of an attached pressure sensor should be logged
separately:
```
sudo cp /home/gpstracker/etc/systemd/system/pressurelogger.service /etc/systemd/system/
sudo systemctl enable pressurelogger.service
```

To use a pressure sensor (BME280, BMP280 or BMP388):
```
sudo cp /home/gpstracker/etc/systemd/system/barometer_poller.service /etc/systemd/system/
sudo systemctl enable barometer_poller.service
```

Optional, if using an LSM sensor:
```
sudo cp /home/gpstracker/etc/systemd/system/lsm_poller.service /etc/systemd/system/
sudo systemctl enable lsm_poller.service
```

If you would like to use sensor fusion, skip barometer_poller and
lsm_poller. 
Instead, use the imu_baro_poller:
```
sudo cp /home/gpstracker/etc/systemd/system/imu_baro_poller.service /etc/systemd/system/
sudo systemctl enable imu_baro_poller.service
```

Prepare OpenStreetMap offline data:
```
docker run -e JAVA_TOOL_OPTIONS="-Xmx10g" -v "$(pwd)/data":/data ghcr.io/onthegomap/planetiler:latest --download --area=europe
```
Do not try this on a Raspberry Pi. It may take more than a day to create
the output.mbtiles even on a powerful machine. You may choose another or a
smaller region.
For more information see the
[planetiler documentation](https://github.com/onthegomap/planetiler).
Finally, copy the output.mbtiles to your Raspberry Pi and move the file to the
gpstracker user:
```
sudo mv output.mbtiles /home/gpstracker/osm_offline.mbtiles
```

#### Local web API (optional)
```
sudo cp /home/gpstracker/etc/systemd/system/gps_tracker_api.service /etc/systemd/system/
sudo systemctl enable gps_tracker_api.service
```
You may access the API via [ip or hostname]:8080/docs .

### Optimisation of power consumption
TODO

## GPS track visualisation
