# GPSTracker
Use a Raspberry Pi with a GPS receiver and a pressure sensor. 
Tracking data from this setup and other sources can be visualised using 
Leaflet.js and several plugins. 
Optional, orientation data from an IMU may be recorded (work in progress).

## GPS tracking
It is assumed that you are using Raspberry Pi OS (Lite version) on your 
Raspberry Pi.
### Setup and requirements
```
sudo apt-get install python3-rpi.gpio python3-redis redis-server gpsd
python3-pip git python3-numpy python3-smbus  # optional: chrony gpsd-clients
sudo pip3 install git+https://github.com/inmcm/micropyGPS.git
sudo pip3 install PyGeodesy fastapi uvicorn aiofiles geojson ahrs \
aioredis==2.0.0
```

```
sudo cp etc/systemd/system/button_shutdown.service /etc/systemd/system/
chmod +x /home/pi/GPSTracker/gps_tracker/button_shutdown.py
sudo systemctl enable button_shutdown.service
```

```
sudo cp etc/systemd/system/gpspoller.service /etc/systemd/system/
chmod +x /home/pi/GPSTracker/gps_tracker/gps3_poller.py
sudo systemctl enable gpspoller.service
```

```
sudo cp etc/systemd/system/gps_baro_merge.service /etc/systemd/system/
chmod +x /home/pi/GPSTracker/gps_tracker/gps_baro_merge.py
sudo systemctl enable gps_baro_merge.service
```

```
sudo cp etc/systemd/system/pressurelogger.service /etc/systemd/system/
chmod +x /home/pi/GPSTracker/gps_tracker/pressure_logger.py
sudo systemctl enable pressurelogger.service
```
Download egm2008-1 as ZIP file from one of the locations listed at 
https://geographiclib.sourceforge.io/1.18/geoid.html and put egm2008-1.pgm 
in /home/pi/egm2008/ .

To use a BMP280 pressure sensor:
```
sudo cp etc/systemd/system/bmp280poller.service /etc/systemd/system/
chmod +x /home/pi/GPSTracker/gps_tracker/bmp280_poller.py
sudo systemctl enable bmp280poller.service
```

To use a BMP388 pressure sensor:
```
sudo cp etc/systemd/system/bmp388poller.service /etc/systemd/system/
chmod +x /home/pi/GPSTracker/gps_tracker/bmp388_poller.py
sudo systemctl enable bmp388poller.service
```

Optional, if using an LSM sensor:
```
sudo cp etc/systemd/system/lsm_poller.service /etc/systemd/system/
chmod +x /home/pi/GPSTracker/gps_tracker/lsm_poller.py
sudo systemctl enable lsm_poller.service
```

#### Data transfer to web page (optional)
```
sudo cp etc/systemd/system/transfer_gps_data.service /etc/systemd/system/
chmod +x /home/pi/GPSTracker/gps_tracker/transfer_data.py
sudo systemctl enable transfer_gps_data.service
```

#### Local web API (optional)
```
sudo cp etc/systemd/system/gps_tracker_api.service /etc/systemd/system/
sudo systemctl enable gps_tracker_api.service
```
You may access the API via [ip or hostname]:8080/docs .

## GPS track visualisation
Different data sources are visualised on 
https://jaluebbe.github.io/GPSTracker/ .
The artificial data was created using geojson.io. 
The real data is taken from a Raspberry Pi equipped with GPS and barometer. 
The Airbus tree is taken from the sample data supplied with 
https://github.com/xoolive/traffic .
Elevation data was determined using the method published in 
https://github.com/jaluebbe/HeightMap .
