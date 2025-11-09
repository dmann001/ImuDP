import numpy as np
from collections import deque
import logging
import math
import time

logger = logging.getLogger(__name__)
# Only configure logging if not already configured (to avoid conflicts when imported)
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class IMUDeadReckoningFixed:
    """
    IMU dead-reckoning with robust stationary detection (ZUPT), bias estimation,
    high-pass filtering, and magnetometer-assisted heading stabilization.

    Inputs per update:
      accel_x, accel_y, accel_z: linear accelerometer (m/s^2) including gravity
      gyro_x, gyro_y, gyro_z: angular rate (rad/s)
      timestamp_s: seconds (float)
      mag_x, mag_y, mag_z: optional magnetometer (uT)

    If your source timestamp is in ms, convert to seconds before calling update.
    """

    def __init__(self,
                 initial_position=(0.0, 0.0),
                 initial_heading_rad=0.0,
                 sample_rate_hz=50.0):
        # State
        self.position = np.array(initial_position, dtype=float)
        self.velocity = np.array([0.0, 0.0], dtype=float)  # m/s in world frame
        self.heading = float(initial_heading_rad)          # radians (yaw)
        self.last_timestamp = None

        # Keep origin for optional snap-to-origin when back at start
        self.origin = np.array(initial_position, dtype=float)
        self.snap_to_origin_radius = 0.5  # meters (set None to disable snapping)

        # Buffers for stationary detection (use seconds->samples)
        self.sample_hz = float(sample_rate_hz)
        win_seconds = 0.5
        self.win_len = max(4, int(round(self.sample_hz * win_seconds)))
        self.accel_mag_buf = deque(maxlen=self.win_len)
        self.gyro_mag_buf = deque(maxlen=self.win_len)

        # Bias estimates (updated during stationary)
        self.accel_bias = np.zeros(3)
        self.gyro_bias = np.zeros(3)

        # Gravity estimate (low-pass on accelerometer when near gravity)
        self.gravity = np.array([0.0, 0.0, 9.81])
        self.gravity_alpha = 0.995  # slow adapt

        # High-pass filter memory for accel to remove residual low-freq components
        self.hp_state = np.zeros(3)
        self.hp_alpha = 0.92  # closer to 1 -> less high-pass (tunable: 0.85-0.98)

        # Magnetometer fusion
        self.mag_alpha = 0.25  # slightly higher trust in mag when moving

        # Stationary detection thresholds (tuned a bit looser)
        # For phone-in-pocket: these are reasonable starting points
        self.accel_std_threshold = 0.15   # was 0.1
        self.gyro_std_threshold = 1.2 * (math.pi/180.0)  # ~1.2 deg/s (was 0.8 deg/s)
        self.stationary_required_windows = 2  # number of consecutive windows to declare stationary

        # ReckonMe-style zero velocity detection thresholds (slightly relaxed)
        self.threshold_peaks_gravity = 0.35        # was 0.25
        self.threshold_peaks_user_acc = 0.35       # was 0.25
        self.user_acc_threshold = 0.15             # was 0.1
        self.user_gravity_threshold_x = 0.7        # was 0.5
        self.user_gravity_threshold_y = 0.7        # was 0.5

        # Buffers for peak detection (store recent values to detect peaks)
        self.gravity_buf = deque(maxlen=self.win_len)      # Store gravity magnitude
        self.user_acc_buf = deque(maxlen=self.win_len)     # Store user acceleration magnitude
        self.gravity_x_buf = deque(maxlen=self.win_len)    # Store gravity X component
        self.gravity_y_buf = deque(maxlen=self.win_len)    # Store gravity Y component

        # Counters
        self.stationary_windows = 0
        self.is_stationary = False
        self.last_motion_time = None
        self.no_motion_timeout = 3.0  # seconds of no motion => force freeze

        # Integration safety and damping
        self.velocity_damping = 0.7
        self.velocity_threshold = 0.03  # m/s (tunable: 0.02-0.05) - avoid tiny drifts
        self.max_speed = 4.0  # m/s

        # Diagnostics / history
        self.history = []

        logger.info("IMUDeadReckoningFixed initialized")
        logger.info(f"  sample_hz={self.sample_hz}, window_len={self.win_len}")
        logger.info(f"  accel_std_th={self.accel_std_threshold}, gyro_std_th={self.gyro_std_threshold:.4f} rad/s")
        logger.info(f"  mag_alpha={self.mag_alpha}, hp_alpha={self.hp_alpha}")
        logger.info(f"  ReckonMe thresholds: gravity_peak={self.threshold_peaks_gravity}, "
                    f"user_acc_peak={self.threshold_peaks_user_acc}, step_th={self.user_acc_threshold}")

    # ----------------------------
    # Utility helpers
    # ----------------------------
    @staticmethod
    def _vec_norm(v):
        return float(np.linalg.norm(v))

    @staticmethod
    def _clamp_speed(v, max_speed):
        speed = np.linalg.norm(v)
        if speed > max_speed:
            return v * (max_speed / speed)
        return v

    @staticmethod
    def _wrap_angle(angle):
        # normalize to [-pi, pi)
        return math.atan2(math.sin(angle), math.cos(angle))

    # ----------------------------
    # Core update function
    # ----------------------------
    def update(self, accel_x, accel_y, accel_z,
               gyro_x, gyro_y, gyro_z,
               timestamp_s,
               mag_x=None, mag_y=None, mag_z=None):
        """
        Call at high rate (e.g., 50 Hz). timestamp_s is seconds (float).
        Returns state dict.
        """
        # initialize timestamp
        if self.last_timestamp is None:
            self.last_timestamp = float(timestamp_s)
            self.last_motion_time = float(timestamp_s)
            # initialize gravity with first accel reading (best-effort)
            self.gravity = np.array([accel_x, accel_y, accel_z])
            return self.get_state()

        dt = float(timestamp_s) - self.last_timestamp
        if dt <= 0 or dt > 1.0:
            # skip bad dt but update last_timestamp so we don't get stuck
            self.last_timestamp = float(timestamp_s)
            return self.get_state()

        # Raw vectors
        raw_acc = np.array([accel_x, accel_y, accel_z], dtype=float)
        raw_gyro = np.array([gyro_x, gyro_y, gyro_z], dtype=float)

        # Remove biases
        acc_unbiased = raw_acc - self.accel_bias
        gyro_unbiased = raw_gyro - self.gyro_bias

        # Magnitudes for stationarity metrics (use accel magnitude including gravity)
        acc_mag = np.linalg.norm(acc_unbiased)
        gyro_mag = np.linalg.norm(gyro_unbiased)

        # Compute user acceleration (linear acceleration after removing gravity)
        linear_acc = acc_unbiased - self.gravity
        user_acc_mag = np.linalg.norm(linear_acc)

        # Gravity magnitude and components
        gravity_mag = np.linalg.norm(self.gravity)
        gravity_x = self.gravity[0]
        gravity_y = self.gravity[1]

        # Push to rolling buffers (we use magnitude std to detect motion)
        self.accel_mag_buf.append(acc_mag)
        self.gyro_mag_buf.append(gyro_mag)

        # Push to ReckonMe-style buffers
        self.gravity_buf.append(gravity_mag)
        self.user_acc_buf.append(user_acc_mag)
        self.gravity_x_buf.append(abs(gravity_x))
        self.gravity_y_buf.append(abs(gravity_y))

        # Compute windowed std
        if len(self.accel_mag_buf) >= max(3, int(self.win_len / 2)):
            a_std = float(np.std(np.array(self.accel_mag_buf)))
            g_std = float(np.std(np.array(self.gyro_mag_buf)))
        else:
            a_std = 0.0
            g_std = 0.0

        # ReckonMe-style peak detection for gravity and user acceleration
        gravity_has_peak = False
        user_acc_has_peak = False

        if len(self.gravity_buf) >= 3:
            gravity_arr = np.array(self.gravity_buf)
            # Detect if there's a significant peak (max - min > threshold)
            gravity_range = float(np.max(gravity_arr) - np.min(gravity_arr))
            gravity_has_peak = gravity_range > self.threshold_peaks_gravity

        if len(self.user_acc_buf) >= 3:
            user_acc_arr = np.array(self.user_acc_buf)
            # Detect if there's a significant peak (max - min > threshold)
            user_acc_range = float(np.max(user_acc_arr) - np.min(user_acc_arr))
            user_acc_has_peak = user_acc_range > self.threshold_peaks_user_acc

        # Check if user acceleration exceeds step threshold
        user_acc_exceeds_step = user_acc_mag > self.user_acc_threshold

        # Check gravity component thresholds
        gravity_x_exceeds = abs(gravity_x) > self.user_gravity_threshold_x
        gravity_y_exceeds = abs(gravity_y) > self.user_gravity_threshold_y

        # Enhanced stationary detection logic (combine original + ReckonMe thresholds)
        is_stationary_candidate = (
            (a_std < self.accel_std_threshold) and
            (g_std < self.gyro_std_threshold) and
            not gravity_has_peak and
            not user_acc_has_peak and
            not user_acc_exceeds_step and
            not gravity_x_exceeds and
            not gravity_y_exceeds
        )

        if is_stationary_candidate:
            self.stationary_windows += 1
        else:
            self.stationary_windows = 0

        prev_stationary = self.is_stationary
        self.is_stationary = (self.stationary_windows >= self.stationary_required_windows)

        # If stationary, perform ZUPT and bias updates
        if self.is_stationary:
            # Simple gyro bias update via exponential smoothing
            if len(self.gyro_mag_buf) > 0:
                smooth_alpha = 0.99
                self.gyro_bias = smooth_alpha * self.gyro_bias + (1.0 - smooth_alpha) * raw_gyro

            # Zero velocity update
            self.velocity[:] = 0.0

            # Slowly adapt gravity estimate toward current accel (helps if phone small tilt)
            self.gravity = self.gravity_alpha * self.gravity + (1.0 - self.gravity_alpha) * acc_unbiased

            # record last motion time as now (we're stationary now)
            self.last_motion_time = float(timestamp_s)
        else:
            # Not stationary -> integrate and update motion timestamps
            self.last_motion_time = float(timestamp_s)

            # Update gravity only if accel close to gravity magnitude and gyro small (to avoid corrupting gravity)
            if abs(acc_mag - 9.81) < 1.5 and gyro_mag < (5.0 * self.gyro_std_threshold):
                self.gravity = self.gravity_alpha * self.gravity + (1.0 - self.gravity_alpha) * acc_unbiased

            # Compute linear acceleration by removing gravity (in device frame approximation)
            linear_acc = acc_unbiased - self.gravity

            # High-pass filter to remove low-frequency residuals (helps drift)
            self.hp_state = self.hp_alpha * self.hp_state + (1.0 - self.hp_alpha) * linear_acc
            accel_hp = linear_acc - self.hp_state

            # Rotate device-frame accel_hp into world XY using yaw-only rotation
            # Assuming device X forward, Y right.
            ax_body = accel_hp[0]
            ay_body = accel_hp[1]
            cos_h = math.cos(self.heading)
            sin_h = math.sin(self.heading)
            ax_world = ax_body * cos_h - ay_body * sin_h
            ay_world = ax_body * sin_h + ay_body * cos_h
            accel_world_2d = np.array([ax_world, ay_world])

            # Deadzone small components
            accel_world_2d[np.abs(accel_world_2d) < 0.01] = 0.0

            # Integrate velocity
            self.velocity += accel_world_2d * dt

            # Damping if small motion (scaled with dt)
            self.velocity *= (1.0 - (1.0 - self.velocity_damping) * dt * 10.0)

            # clamp speed
            self.velocity = self._clamp_speed(self.velocity, self.max_speed)

        # Heading update: integrate gyro z (yaw)
        self.heading += (gyro_unbiased[2] * dt)  # gyro in rad/s
        self.heading = self._wrap_angle(self.heading)

        # Magnetometer fusion
        if mag_x is not None and mag_y is not None and mag_z is not None:
            mag_vec = np.array([mag_x, mag_y, mag_z], dtype=float)
            # Simple heading from device X/Y (assuming mostly upright)
            mag_heading = math.atan2(mag_vec[1], mag_vec[0])

            if self.is_stationary:
                # When stationary, hard-reset heading to magnetometer to kill accumulated yaw drift
                self.heading = self._wrap_angle(mag_heading)
            else:
                # When moving, complementary fusion
                self.heading = self._wrap_angle(
                    (1.0 - self.mag_alpha) * self.heading + self.mag_alpha * mag_heading
                )

        # If stationary for too long, force hard stop
        if (float(timestamp_s) - self.last_motion_time) > self.no_motion_timeout:
            self.velocity[:] = 0.0

        # Apply velocity cutoff
        speed = np.linalg.norm(self.velocity)
        if speed < self.velocity_threshold:
            self.velocity[:] = 0.0

        # Integrate position
        old_pos = self.position.copy()
        self.position += self.velocity * dt
        dist_step = np.linalg.norm(self.position - old_pos)

        # Optional: snap to origin when stationary and close to it
        if self.is_stationary and self.snap_to_origin_radius is not None:
            dist_to_origin = np.linalg.norm(self.position - self.origin)
            if dist_to_origin < self.snap_to_origin_radius:
                self.position[:] = self.origin

        # Keep history for debugging
        self.history.append({
            't': float(timestamp_s),
            'pos_x': float(self.position[0]),
            'pos_y': float(self.position[1]),
            'vel_x': float(self.velocity[0]),
            'vel_y': float(self.velocity[1]),
            'speed': float(np.linalg.norm(self.velocity)),
            'acc_mag': float(acc_mag),
            'gyro_mag': float(gyro_mag),
            'is_stationary': bool(self.is_stationary),
            'heading_deg': float(math.degrees(self.heading) % 360.0)
        })

        # update time
        self.last_timestamp = float(timestamp_s)
        return self.get_state()

    # ----------------------------
    # Accessors
    # ----------------------------
    def get_state(self):
        speed = float(np.linalg.norm(self.velocity))
        return {
            'position': {'x': float(self.position[0]), 'y': float(self.position[1])},
            'velocity': {'vx': float(self.velocity[0]), 'vy': float(self.velocity[1]), 'speed': speed},
            'heading_rad': float(self.heading),
            'heading_deg': float(math.degrees(self.heading) % 360.0),
            'is_stationary': bool(self.is_stationary),
            'last_timestamp': float(self.last_timestamp) if self.last_timestamp else None
        }

    def reset(self, pos=(0.0, 0.0), heading_rad=0.0):
        self.__init__(initial_position=pos, initial_heading_rad=heading_rad, sample_rate_hz=self.sample_hz)


# ----------------------------
# AdvancedTrailTracker - Wrapper for server.py compatibility
# ----------------------------
class AdvancedTrailTracker:
    """
    Wrapper around IMUDeadReckoningFixed that provides the interface expected by server.py.
    This class adapts the full 6-DOF IMU interface to a simplified interface for trail tracking.
    """

    def __init__(self, expected_hz=100.0):
        """
        Initialize the trail tracker.

        Args:
            expected_hz: Expected data rate in Hz (50-100 Hz recommended)
        """
        self.expected_hz = float(expected_hz)
        self.imu = IMUDeadReckoningFixed(sample_rate_hz=self.expected_hz)

        # Map old parameter names to new ones for compatibility
        self.accel_move_threshold = 0.1  # Not used in new implementation, kept for compatibility
        self.accel_deadzone = 0.01       # Not used in new implementation, kept for compatibility
        self.velocity_threshold = self.imu.velocity_threshold
        self.stationary_threshold = self.imu.accel_std_threshold  # Map to accel_std_threshold
        self.velocity_damping = self.imu.velocity_damping

        logger.info(f"AdvancedTrailTracker initialized for {self.expected_hz} Hz data")

    def update(self, accel_x, accel_y, accel_z, gyro_z, timestamp,
               mag_x=None, mag_y=None, mag_z=None):
        """
        Update the trail tracker with new sensor data.

        Note: This interface only requires gyro_z (yaw rate) for simplicity.
        The underlying IMUDeadReckoningFixed uses full 6-DOF, so we pass gyro_x=0, gyro_y=0.

        Args:
            accel_x, accel_y, accel_z: Accelerometer data (m/s^2)
            gyro_z: Yaw rate (rad/s) - only z-axis gyro needed for 2D tracking
            timestamp: Timestamp in seconds (float)
            mag_x, mag_y, mag_z: Optional magnetometer data (uT)
        """
        state = self.imu.update(
            accel_x, accel_y, accel_z,
            0.0, 0.0, gyro_z,
            timestamp,
            mag_x=mag_x, mag_y=mag_y, mag_z=mag_z
        )

        return state

    @property
    def position(self):
        """Get current position."""
        return self.imu.position

    @position.setter
    def position(self, value):
        """Set position (updates underlying IMU state)."""
        self.imu.position = np.array(value, dtype=float)

    @property
    def heading(self):
        """Get current heading in radians."""
        return self.imu.heading

    @heading.setter
    def heading(self, value):
        """Set heading in radians (updates underlying IMU state)."""
        self.imu.heading = float(value)

    def get_state(self):
        """Get current state of the tracker."""
        return self.imu.get_state()

    def get_trail_data(self):
        """
        Get trail data for visualization.
        Returns a dict with 'path' containing list of position points.
        """
        path = []
        if self.imu.history:
            for entry in self.imu.history:
                path.append({
                    'x': entry['pos_x'],
                    'y': entry['pos_y'],
                    't': entry['t'],
                    'speed': entry['speed'],
                    'heading': entry['heading_deg']
                })

        return {
            'path': path,
            'current_state': self.get_state(),
            'total_points': len(path)
        }

    def reset(self):
        """Reset the trail tracker to initial state."""
        self.imu.reset()
        self.position = self.imu.position
        self.heading = self.imu.heading


# (Rest of your file — process_real_imu_data, MadgwickDeadReckoning, UDP listener, main()
#  — can stay as you had it, since they don’t need changes for this specific fix.)
