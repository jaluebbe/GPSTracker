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
python3-scipy python3-smbus python3-h5py hostapd dnsmasq anacron
sudo systemctl unmask hostapd
sudo systemctl disable hostapd
sudo systemctl disable dnsmasq
sudo useradd -m gpstracker
sudo usermod -a -G i2c,video,gpio gpstracker
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
pip install fastapi geojson websockets pygeodesy redis uvicorn
git clone https://github.com/Mayitzin/ahrs.git
cd ahrs
python setup.py install --user
cd
git clone https://github.com/jaluebbe/GPSTracker.git
cd GPSTracker
git clone https://github.com/klokantech/klokantech-gl-fonts fonts
ln -s ../../GEBCO_2022.nc gps_tracker/GEBCO_2022.nc
```

### Test Python scripts
Enter the subfolder containing all the Python scripts:
```
cd gps_tracker
```
Open a second terminal window where you call
```
redis-cli
```
and enter:
```
subscribe gps barometer imu
```
Go back to your first window and start consuming GPS data by calling:
```
./gps_poller.py
```
The script should start without errors and if the GPS has a fix, messages may appear
on the "gps" channel on the Redis server (see the other window).
Prepare to start this script on boot and restart if crashed:
```
sudo cp /home/gpstracker/GPSTracker/etc/systemd/system/gpspoller.service /etc/systemd/system/
sudo systemctl enable gpspoller.service
```
Instead of "enable" you may also call "disable", "start", "stop" or "restart".
Attention, do not try these steps as "gpstracker" user as it is missing sudo privileges.
Use your personal user e.g. "pi" instead.

For the following scripts, you should carefully decide which to install to cover your requirements.

To test consumption of barometer data is is the same procedure with (supports BME280, BMP280 or BMP388)):
```
./barometer_poller.py
```
Permanent install:
```
sudo cp /home/gpstracker/GPSTracker/etc/systemd/system/barometer_poller.service /etc/systemd/system/
sudo systemctl enable barometer_poller.service
```

Data from an LSM IMU is consumed using:
```
./lsm_poller.py
```
Permanent install:
```
sudo cp /home/gpstracker/GPSTracker/etc/systemd/system/lsm_poller.service /etc/systemd/system/
sudo systemctl enable lsm_poller.service
```

Consuming barometer and IMU data at the same time is done using:
```
./imu_baro_poller.py
```
Permanent install:
```
sudo cp /home/gpstracker/GPSTracker/etc/systemd/system/imu_baro_poller.service /etc/systemd/system/
sudo systemctl enable imu_baro_poller.service
```

The data logging process is included in (even if no barometer is being used):
```
./gps_baro_merge.py
```
Permanent install:
```
sudo cp /home/gpstracker/GPSTracker/etc/systemd/system/gps_baro_merge.service /etc/systemd/system/
sudo systemctl enable gps_baro_merge.service
```

Optional, if a shutdown button is attached between GND and GPIO21:
```
sudo cp /home/gpstracker/GPSTracker/etc/systemd/system/button_shutdown.service /etc/systemd/system/
```
Edit /etc/systemd/system/button_shutdown.service if your username is not "pi".
```
sudo systemctl enable button_shutdown.service
```
Or, instead of the shutdown button, a switch to disable WiFi may be connected
to GND and GPIO21. The setup is similar to the installation of the shutdown
button but the service file is called "jumper_wifi_off.service" instead.


Optional, if data of an attached pressure sensor should be logged
separately even if no GPS data is available:
```
sudo cp /home/gpstracker/GPSTracker/etc/systemd/system/pressurelogger.service /etc/systemd/system/
sudo systemctl enable pressurelogger.service
```

Prepare OpenStreetMap offline data:
```
docker run -e JAVA_TOOL_OPTIONS="-Xmx10g" -v "$(pwd)/data":/data ghcr.io/onthegomap/planetiler:latest --download --area=europe
```
You need Docker. Do not try this on a Raspberry Pi. It may take more than a day to create
the output.mbtiles even on a powerful machine. You may choose another or a
smaller region (e.g. "germany" or "dach" to include Austria, Germany and Switzerland).
For more information see the
[planetiler documentation](https://github.com/onthegomap/planetiler).
Finally, copy the output.mbtiles to the following location on your Raspberry Pi:
```
/home/gpstracker/osm_offline.mbtiles
```

Download the [GEBCO_2022 grid](https://www.gebco.net/data_and_products/gridded_bathymetry_data/)
in netCDF format and copy GEBCO_2022.nc to the user folder of "gpstracker".

### Local web API
```
sudo cp /home/gpstracker/GPSTracker/etc/systemd/system/gps_tracker_api.service /etc/systemd/system/
sudo systemctl enable gps_tracker_api.service
sudo cp /home/gpstracker/GPSTracker/etc/cron.daily/archive_data /etc/cron.daily/
```
You may access the API via [ip or hostname]:8080/docs .

If you would like to create a redirection from port 80 to port 8080,
you should add the following line to /etc/rc.local :
```
/usr/sbin/iptables -A PREROUTING -t nat -i wlan0 -p tcp --dport 80 -j REDIRECT --to-port 8080
```

### WLAN access point setup
Follow this [Tutorial](https://www.raspberryconnect.com/projects/65-raspberrypi-hotspot-accesspoints/158-raspberry-pi-auto-wifi-hotspot-switch-direct-connection)
(some steps are already completed).
```
sudo cp /home/gpstracker/GPSTracker/etc/dnsmasq.conf /etc/dnsmasq.conf
sudo cp /home/gpstracker/GPSTracker/etc/hostapd/hostapd.conf /etc/hostapd/hostapd.conf
```
Edit /etc/hostapd/hostapd.conf and set "my-wifi-network" as well as "my-wifi-password" to your needs.
Attention, these are the login credentials for clients connecting to your
access point on the Raspberry Pi.

Finally, set up the service to perform the choice of the connection during startup:
```
sudo cp /home/gpstracker/GPSTracker/usr/bin/autohotspot /usr/bin/
sudo cp /home/gpstracker/GPSTracker/etc/systemd/system/autohotspot.service /etc/systemd/system/
sudo systemctl enable autohotspot.service
```
If your known WiFi networks are not available, the hotspot will be created instead.
When connected to this hotspot, you may type http://gps which will be forwarded to the main page.
A shortcut to the vigor22 demo is available via http://vigor22 .
Further shortcuts may be created by modification of dnsmasq.conf and backend_fastapi.py .

### Optimisation of power consumption
To reduce the power consumption on a Raspberry Pi Zero you should switch to the legacy graphics driver via
```
sudo raspi-config
```
and select "Advanced" -> "GL driver" -> "Legacy" -> "Ok".
Now you could disable HDMI by calling:
```
/usr/bin/tvservice -o
```
You may setup your /etc/rc.local in a similar way as the file in /home/gpstracker/GPSTracker/etc/rc.local
to switch of HDMI at boot.

## GPS track visualisation
TODO
