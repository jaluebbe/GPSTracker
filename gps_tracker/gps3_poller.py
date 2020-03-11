#!/usr/bin/env python3

import logging
from time import sleep
from gps3 import gps3
import json
import redis
import socket
from micropyGPS import MicropyGPS
my_gps = MicropyGPS(location_formatting='dd')
redis_connection = redis.Redis()
hostname = socket.gethostname()
knt_to_mps = 463. / 900


def convert_lat_lon(json_msg, _my_gps):
    if my_gps.latitude[1] == 'N':
        json_msg['lat'] = round(my_gps.latitude[0], 6)
    else:
        json_msg['lat'] = - round(my_gps.latitude[0], 6)
    if my_gps.longitude[1] == 'E':
        json_msg['lon'] = round(my_gps.longitude[0], 6)
    else:
        json_msg['lon'] = - round(my_gps.longitude[0])


def poll_gpsd():
    gpsd_socket = gps3.GPSDSocket()
    gpsd_socket.connect()
    gpsd_socket.watch(gpsd_protocol='nmea')
    time_now = None
    json_msg = {'hostname': hostname, 'mode': 0}
    error_count = 0
    while True:
        if error_count > 100:
            logging.warning('too many errors, reconnecting to gpsd...')
            break
        new_data = gpsd_socket.next(timeout=1.0)
        if new_data is None or new_data == '':
            error_count += 1
            sleep(.05)
            continue
        for x in new_data:
            result = my_gps.update(x)
            if result is None or result == '':
                continue
            elif not my_gps.valid:
                continue
            if int(my_gps.fix_time) != time_now:
                if len(json_msg) > 0:
                    if json_msg['mode'] < 3:
                        json_msg['alt'] = None
                        json_msg['vdop'] = None
                        json_msg['pdop'] = None
                    redis_connection.publish('gps', json.dumps(json_msg))
                json_msg = {'hostname': hostname, 'mode': 0}
                time_now = int(my_gps.fix_time)
            if result == 'GPGGA':
                """Parse Global Positioning System Fix Data (GGA) Sentence.
                Updates UTC timestamp, latitude, longitude, fix status,
                satellites in use, Horizontal Dilution of Precision (HDOP),
                altitude, geoid height and fix status"""
                json_msg.update({
                    'alt': my_gps.altitude, 'geo_sep': my_gps.geoid_height,
                    'utc': round(my_gps.fix_time, 2),
                    'hdop': my_gps.hdop, 'num_sats': my_gps.satellites_in_use,
                    'gps_status': my_gps.fix_stat})
                convert_lat_lon(json_msg, my_gps)
                error_count = 0
            elif result == 'GPGSA':
                """Parse GNSS DOP and Active Satellites (GSA) sentence. Updates
                GPS fix type, list of satellites used in fix calculation,
                Position Dilution of Precision (PDOP), Horizontal Dilution of
                Precision (HDOP), Vertical Dilution of Precision, and fix status
                """
                json_msg.update({
                    'hdop': my_gps.hdop, 'vdop': my_gps.vdop,
                    'pdop': my_gps.pdop, 'mode': my_gps.fix_type,
                    'gps_status': my_gps.fix_stat})
                error_count = 0
            elif result == 'GPRMC':
                """Parse Recommended Minimum Specific GPS/Transit data
                (RMC)Sentence. Updates UTC timestamp, latitude, longitude,
                Course, Speed, Date, and fix status """
                json_msg.update({
                    'utc': round(my_gps.fix_time, 2),
                    'track': my_gps.course, 'gps_status': my_gps.fix_stat,
                    'speed': round(my_gps.speed[0] * knt_to_mps, 2)})
                convert_lat_lon(json_msg, my_gps)
                error_count = 0


if __name__ == '__main__':

    while True:
        poll_gpsd()
