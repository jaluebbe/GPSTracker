#!/bin/sh
python3 setup.py build_ext --inplace
cp *.so ../gps_tracker/
