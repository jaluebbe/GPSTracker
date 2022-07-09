# calculate barometric altitude based on the following formula:
# https://www.weather.gov/media/epz/wxcalc/pressureAltitude.pdf
def calculate_pressure_altitude(pressure, p0=101_325):
    altitude = 0.3048 * 145_366.45 * (1 - pow(pressure / p0, 0.190_284))
    return altitude
