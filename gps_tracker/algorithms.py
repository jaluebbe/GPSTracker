import numpy as np
import scipy.linalg as la

# calculate barometric altitude based on the following formula:
# https://www.weather.gov/media/epz/wxcalc/pressureAltitude.pdf
def calculate_pressure_altitude(pressure, p0=101_325):
    altitude = 0.3048 * 145_366.45 * (1 - pow(pressure / p0, 0.190_284))
    return altitude


def calculate_altitude_pressure(altitude, p0=101_325):
    pressure = p0 * pow(1 - altitude / (0.3048 * 145_366.45), 1 / 0.190_284)
    return pressure


class KalmanImuAltitude:
    def __init__(self, process_noise_gain=0.05):
        self.x = np.zeros((3, 1))
        self.P = np.diag([1e4**2, 1e1**2, 1e2**2])
        self.process_noise_gain = process_noise_gain
        self.old_utc = None

    def kalman_step(self, utc, h, h_err, a=None, a_err=None):
        if self.old_utc is None:
            self.old_utc = utc
            return
        t = utc - self.old_utc
        # process noise matrix
        Q = (
            np.max([0, np.abs(a) - a_err]) * self.process_noise_gain
        ) ** 2 * np.array(
            [
                [t**4 / 4, t**3 / 2, t**2 / 2],
                [t**3 / 2, t**2, t],
                [t**2 / 2, t, 1],
            ]
        )
        # transition matrix
        F = np.array([[1, t, 0.5 * t**2], [0, 1, t], [0, 0, 1]])
        # prediction
        x_pred = np.dot(F, self.x)
        P_pred = np.dot(F, np.dot(self.P, F.T)) + Q
        # update
        z = np.array([[h]])
        H = np.array([[1, 0, 0]])
        R = np.diag([h_err**2])
        y = z - np.dot(H, x_pred)
        S = np.dot(H, np.dot(P_pred, H.T)) + R
        K = np.dot(P_pred, np.dot(H.T, la.inv(S, check_finite=False)))
        self.x = x_pred + np.dot(K, y)
        self.P = P_pred - np.dot(K, np.dot(S, K.T))
        self.old_utc = utc
        return {
            "altitude": self.x[0, 0],
            "vertical_speed": self.x[1, 0],
            "acc": self.x[2, 0],
        }
