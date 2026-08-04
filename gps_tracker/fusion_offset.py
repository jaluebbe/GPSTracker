"""
Correction algorithm for run-time calibration of the gyroscope offset.

Ported from Fusion library by Seb Madgwick.
"""

import numpy as np


class FusionOffset:
    """
    Gyroscope offset correction algorithm.

    Automatically calibrates gyroscope offset during stationary periods.
    The algorithm waits for the gyroscope to be stationary (below threshold)
    for a timeout period, then gradually adjusts the offset using a low-pass filter.
    """

    # Default constants from original C implementation
    CUTOFF_FREQUENCY = 0.02  # Hz
    TIMEOUT = 5  # seconds
    THRESHOLD = 3.0  # degrees per second

    def __init__(
        self, sample_rate, threshold=None, timeout=None, cutoff_frequency=None
    ):
        """
        Initialize the gyroscope offset algorithm.

        Parameters
        ----------
        sample_rate : float
            Sample rate in Hz (e.g., 25 for 0.04s intervals)
        threshold : float, optional
            Threshold in degrees per second for stationary detection.
            Default is 3.0 deg/s. Lower values = more sensitive to movement.
        timeout : float, optional
            Timeout in seconds before offset adjustment begins.
            Default is 5 seconds.
        cutoff_frequency : float, optional
            Low-pass filter cutoff frequency in Hz.
            Default is 0.02 Hz.
        """
        self.sample_rate = sample_rate
        self.threshold = threshold if threshold is not None else self.THRESHOLD
        self.timeout_seconds = timeout if timeout is not None else self.TIMEOUT
        cutoff = (
            cutoff_frequency
            if cutoff_frequency is not None
            else self.CUTOFF_FREQUENCY
        )

        # Calculate filter coefficient
        self.filter_coefficient = 2.0 * np.pi * cutoff / sample_rate

        # Calculate timeout in samples
        self.timeout = int(self.timeout_seconds * sample_rate)

        # State variables
        self.timer = 0
        self.gyroscope_offset = np.array([0.0, 0.0, 0.0], dtype=np.float32)

    def update(self, gyroscope):
        """
        Update the gyroscope offset algorithm and return the corrected measurement.

        Parameters
        ----------
        gyroscope : array_like
            Gyroscope measurement in degrees per second [x, y, z]

        Returns
        -------
        np.ndarray
            Corrected gyroscope measurement in degrees per second
        """
        gyroscope = np.asarray(gyroscope, dtype=np.float32)

        # Subtract current offset from gyroscope measurement
        corrected = gyroscope - self.gyroscope_offset

        # Check if gyroscope is stationary (all axes below threshold)
        if np.any(np.abs(corrected) > self.threshold):
            # Reset timer if gyroscope not stationary
            self.timer = 0
            return corrected

        # Increment timer while gyroscope stationary
        if self.timer < self.timeout:
            self.timer += 1
            return corrected

        # Adjust offset if timer has elapsed (gyroscope has been stationary long enough)
        self.gyroscope_offset += corrected * self.filter_coefficient

        return corrected

    def reset(self):
        """Reset the offset algorithm to initial state."""
        self.timer = 0
        self.gyroscope_offset = np.array([0.0, 0.0, 0.0], dtype=np.float32)

    def get_offset(self):
        """
        Get the current gyroscope offset.

        Returns
        -------
        np.ndarray
            Current offset in degrees per second [x, y, z]
        """
        return self.gyroscope_offset.copy()

    def set_offset(self, offset):
        """
        Manually set the gyroscope offset.

        Parameters
        ----------
        offset : array_like
            Offset in degrees per second [x, y, z]
        """
        self.gyroscope_offset = np.asarray(offset, dtype=np.float32)
        self.timer = 0
