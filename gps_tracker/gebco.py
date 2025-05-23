import h5py
import os
import json
from pathlib import Path
import numpy as np

NCOLS = 86400
NROWS = 43200
CELLSIZE = 1.0 / 240
XLLCENTER = -180.0
YLLCENTER = -90.0

GEBCO_PATH = Path("../../GEBCO_2024.nc")


def get_index_from_latitude(lat):
    return max(min(int(round((lat - YLLCENTER) / CELLSIZE)), (NROWS - 1)), 0)


def get_index_from_longitude(lon):
    return int(round((lon - XLLCENTER) / CELLSIZE)) % NCOLS


def get_lat_from_index(i):
    return round(i * CELLSIZE + YLLCENTER, 6)


def get_lon_from_index(j):
    return round(j * CELLSIZE + XLLCENTER, 6)


class Gebco:
    attribution_url = (
        "https://www.gebco.net/data-products-gridded-bathymetry-data/"
        "gebco2024-grid"
    )
    attribution_name = "GEBCO_2024 Grid"
    attribution = '&copy <a href="{}">{}</a>'.format(
        attribution_url, attribution_name
    )
    seabed_included = True
    NODATA = -32768
    old_i = None
    old_j = None
    old_val = None
    h5_file = None

    def __init__(self, file_path: Path = GEBCO_PATH):
        if not file_path.is_file():
            raise FileNotFoundError(file_path)
        self.h5_file = h5py.File(file_path, "r")

    def get_height(self, lat, lon):
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("invalid coordinates ({}, {})".format(lat, lon))
        val = self.NODATA
        i = get_index_from_latitude(lat)
        j = get_index_from_longitude(lon)
        lat_found = get_lat_from_index(i)
        lon_found = get_lon_from_index(j)
        if self.h5_file is None:
            pass
        elif self.old_i == i and self.old_j == j:
            # same grid position, file access not necessary
            val = self.old_val
        else:
            val = round(float(self.h5_file["elevation"][i][j]), 2)
            self.old_i = i
            self.old_j = j
            self.old_val = val
        return {
            "lat": lat,
            "lon": lon,
            "lat_found": round(lat_found, 6),
            "lon_found": round(lon_found, 6),
            "altitude_m": val,
            "lat_index": i,
            "lon_index": j,
            "source": self.attribution_name,
            "attributions": [self.attribution],
        }
