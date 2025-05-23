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
sudo apt install chrony gpsd git redis-server python3-fastapi python3-uvicorn \
python3-numpy python3-scipy python3-smbus python3-h5py anacron python3-venv
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
DEVICES="/dev/ttyS0"
GPSD_OPTIONS="-n"
USBAUTO="false"
```
Some Raspberry Pi OS installations may require you to use /dev/serial0 as device instead.

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
git clone https://github.com/jaluebbe/GPSTracker.git
cd GPSTracker
git clone https://github.com/klokantech/klokantech-gl-fonts fonts
python -m venv --system-site-packages venv
source venv/bin/activate
pip install -r requirements.txt
```
```
Check your Python version by calling:
```
python --version
```
If your version is below 3.10 call:
```
pip install eval_type_backport
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

Optional, if you are using a qwiic pHat with a button on GPIO17:
```
sudo cp /home/gpstracker/GPSTracker/etc/systemd/system/button_reboot_shutdown.service /etc/systemd/system/
```
Edit /etc/systemd/system/button_reboot_shutdown.service if your username is not "pi" with /home/pi.
```
sudo systemctl enable button_reboot_shutdown.service
```
Pressing the button for more than 5s triggers a shutdown. After 2s a reboot is triggered.
A short press enables Wi-Fi. Anything longer but below 2s diables Wi-Fi.

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

Download the [GEBCO_2024 grid](https://www.gebco.net/data_and_products/gridded_bathymetry_data/)
in netCDF format and copy GEBCO_2024.nc to the user folder of "gpstracker".

### Local web API
```
sudo cp /home/gpstracker/GPSTracker/etc/systemd/system/gps_tracker_api.service /etc/systemd/system/
sudo systemctl enable gps_tracker_api.service
sudo cp /home/gpstracker/GPSTracker/etc/cron.daily/archive_data /etc/cron.daily/
```
You may access the API via [ip or hostname]:8080/docs .

### Setup port forwarding
If you would avoid to add :8080 to the hostname of the device you can create
a port forwarding from port 80 to 8080.
At first try if it works by calling
```
sudo /usr/sbin/iptables -A PREROUTING -t nat -i wlan0 -p tcp --dport 80 -j REDIRECT --to-port 8080
```
and test if you could call the device without the port number.
Then call:
```
sudo apt install iptables-persistent
```
During installation, you will be prompted to save the current iptables rules. Select Yes.
If you change your rules after the installation of iptables-persistent just
call:
```
sudo netfilter-persistent save

### WLAN access point setup
The hotspot setup for systems running bookwork mainly follows this
[Tutorial](https://www.raspberryconnect.com/projects/65-raspberrypi-hotspot-accesspoints/203-automated-switching-accesspoint-wifi-network).
Type the following commands and set name and password for your hotspot
network.
You may also add multiple known networks where the device should join as a
client.
```
curl "https://www.raspberryconnect.com/images/scripts/AccessPopup.tar.gz" -o AccessPopup.tar.gz
tar -xvf ./AccessPopup.tar.gz
cd AccessPopup
sudo ./installconfig.sh
```

## GPS track visualisation
TODO
