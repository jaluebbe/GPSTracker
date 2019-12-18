from libc.math cimport sin, cos, acos, M_PI

# calculate the distance between two gps coordinates:
def get_distance(location1, location2):
    cdef double lat1 = location1[0]
    cdef double lon1 = location1[1]
    cdef double lat2 = location2[0]
    cdef double lon2 = location2[1]
    cdef double degRad = 2 * M_PI / 360
    cdef double distance = 6.370e6 * acos(sin(lat1 * degRad) * sin(lat2 * degRad
    ) + cos(lat1 * degRad) * cos(lat2 * degRad) * cos((lon2 - lon1) * degRad))
    return distance
