import numpy as np
from collections import deque
import logging
import math

logger = logging.getLogger(__name__)


class IMUDeadReckoning:
    """
    IMU Dead-Reckoning tuned for hand-held phone walking on a flat floor,
    BALANCED: Detects walking movement but stops drift when stationary.
    """

    def __init__(self, initial_position=(0.0, 0.0), initial_heading=0.0):
        # Position and velocity
        self.position = np.array(initial_position, dtype=float)
        self.velocity = np.array([0.0, 0.0], dtype=float)
        self.heading = float(initial_heading)
        self.angular_velocity = 0.0

        # Timing
        self.last_timestamp = None
        self.last_motion_timestamp = None  # last time we detected real motion

        # History
        self.position_history = deque(maxlen=1000)

        # Sensor buffers
        self.accel_buffer = deque(maxlen=10)
        self.gyro_buffer = deque(maxlen=10)
        self.mag_buffer = deque(maxlen=10)

        # Calibration
        self.accel_bias = np.array([0.0, 0.0, 0.0])
        self.gyro_bias = np.array([0.0, 0.0, 0.0])

        # Gravity estimate
        self.gravity_estimate = np.array([0.0, 0.0, 9.81])
        self.gravity_alpha = 0.98  # slow adaptation

        # Stats
        self.update_count = 0
        self.total_distance = 0.0

        # ===== BALANCED PARAMETERS - DETECTS MOVEMENT BUT STOPS DRIFT =====
        # Stationary detection
        self.stationary_count = 0
        self.stationary_threshold = 3          # samples (fast ZUPT)

        # Acceleration thresholds
        # CRITICAL FIX: Walking acceleration is typically 0.8-1.5 m/s²
        # Your old code had 2.0 m/s² which is TOO HIGH - missed all walking!
        self.accel_stationary_threshold = 2.0  # m/s²: tolerance around 1g for "near gravity"
        self.accel_move_threshold = 0.4        # m/s²: FIXED! Walking is ~0.8-1.5 m/s² (was 2.0!)

        # Horizontal accel deadzone (world frame)
        self.accel_deadzone = 0.12             # m/s² per component (LOWERED from 0.30)

        # Gyro thresholds  
        self.gyro_stationary_threshold = 0.04  # rad/s: tighter "still" condition (LOWERED from 0.1)

        # Velocity damping & cutoff
        self.velocity_damping = 0.25           # keep 25% per frame when not integrating
        self.velocity_threshold = 0.03         # m/s: below this -> zero (LOWERED from 0.05)

        # Max plausible speed (safety clamp)
        self.max_speed = 3.0                   # m/s (~10.8 km/h)

        # Tilt gating
        self.max_tilt_deg = 60.0               # More reasonable limit

        # If no motion detected for this many seconds, slam everything to zero
        self.no_motion_timeout = 0.5  # s

        logger.info("IMU Dead-Reckoning initialized (BALANCED mode)")
        logger.info(f"  ✅ FIX: accel_move_threshold = {self.accel_move_threshold} m/s² (was 2.0)")
        logger.info(f"  This will now detect walking movements!")
        logger.info(f"  Stationary samples: {self.stationary_threshold}")
        logger.info(f"  Velocity damping: {self.velocity_damping}")
        logger.info(f"  Velocity cutoff: {self.velocity_threshold} m/s")

    def reset(self, position=(0.0, 0.0), heading=0.0):
        self.position = np.array(position, dtype=float)
        self.velocity = np.array([0.0, 0.0], dtype=float)
        self.heading = float(heading)
        self.angular_velocity = 0.0
        self.last_timestamp = None
        self.last_motion_timestamp = None
        self.position_history.clear()
        self.total_distance = 0.0
        self.stationary_count = 0
        self.orientation = np.array([1.0, 0.0, 0.0, 0.0])
        self.gravity_estimate = np.array([0.0, 0.0, 9.81])
        self.pitch = 0.0
        self.roll = 0.0
        logger.info(f"Reset to position {position}, heading {np.degrees(heading):.1f}°")

    def calibrate(self, accel_samples, gyro_samples):
        if len(accel_samples) > 0:
            accel_array = np.array(accel_samples)
            self.accel_bias = np.mean(accel_array, axis=0)
            self.accel_bias[2] -= 9.81
            logger.info(f"Accel bias: {self.accel_bias}")

        if len(gyro_samples) > 0:
            gyro_array = np.array(gyro_samples)
            self.gyro_bias = np.mean(gyro_array, axis=0)
            logger.info(f"Gyro bias: {self.gyro_bias}")

    def _low_pass_filter(self, buffer, new_value, alpha=0.3):
        if len(buffer) == 0:
            return new_value
        return alpha * new_value + (1 - alpha) * buffer[-1]

    def _quaternion_multiply(self, q1, q2):
        w1, x1, y1, z1 = q1
        w2, x2, y2, z2 = q2
        w = w1*w2 - x1*x2 - y1*y2 - z1*z2
        x = w1*x2 + x1*w2 + y1*z2 - z1*y2
        y = w1*y2 - x1*z2 + y1*w2 + z1*x2
        z = w1*z2 + x1*y2 - y1*x2 + z1*w2
        return np.array([w, x, y, z])

    def _quaternion_conjugate(self, q):
        w, x, y, z = q
        return np.array([w, -x, -y, -z])

    def _vector_rotate(self, v, q):
        qv = np.array([0, v[0], v[1], v[2]])
        q_conj = self._quaternion_conjugate(q)
        rotated = self._quaternion_multiply(self._quaternion_multiply(q, qv), q_conj)
        return rotated[1:]

    def _update_tilt_from_gravity(self):
        g = self.gravity_estimate
        norm = np.linalg.norm(g)
        if norm < 1e-3:
            return
        gx, gy, gz = g / norm
        self.pitch = math.atan2(-gx, math.sqrt(gy*gy + gz*gz))
        self.roll = math.atan2(gy, gz)

    def _hard_stop(self):
        """Brutally force everything to 'stopped'."""
        self.velocity[:] = 0.0

    def update(self, accel_x, accel_y, accel_z,
               gyro_x, gyro_y, gyro_z,
               timestamp_ms,
               mag_x=None, mag_y=None, mag_z=None):

        # Timestamp handling: accept ms or seconds
        timestamp = timestamp_ms / 1000.0 if timestamp_ms > 1000 else float(timestamp_ms)

        if self.last_timestamp is None:
            self.last_timestamp = timestamp
            self.last_motion_timestamp = timestamp
            return self.get_state()

        dt = timestamp - self.last_timestamp
        if dt <= 0 or dt > 1.0:
            logger.warning(f"Invalid dt: {dt:.3f}s, skipping")
            self.last_timestamp = timestamp
            return self.get_state()

        # ----- STEP 1: Bias removal & filtering -----
        accel = np.array([accel_x, accel_y, accel_z]) - self.accel_bias
        gyro = np.array([gyro_x, gyro_y, gyro_z]) - self.gyro_bias

        accel_filtered = self._low_pass_filter(self.accel_buffer, accel)
        gyro_filtered = self._low_pass_filter(self.gyro_buffer, gyro)

        self.accel_buffer.append(accel_filtered)
        self.gyro_buffer.append(gyro_filtered)

        # Magnitudes
        raw_acc_mag = np.linalg.norm(accel_filtered)
        gyro_mag = np.linalg.norm(gyro_filtered)

        # Near 1g?
        near_gravity = abs(raw_acc_mag - 9.81) < self.accel_stationary_threshold

        # ----- STEP 2: Gravity estimate (only when clearly near 1g & low gyro) -----
        if near_gravity and gyro_mag < self.gyro_stationary_threshold:
            self.gravity_estimate = (
                self.gravity_alpha * self.gravity_estimate +
                (1.0 - self.gravity_alpha) * accel_filtered
            )

        # Update tilt from gravity
        self._update_tilt_from_gravity()

        # ----- STEP 3: Remove gravity -> linear accel -----
        accel_linear = accel_filtered - self.gravity_estimate

        # ----- STEP 4: Heading from gyro (yaw only) -----
        self.heading += gyro_filtered[2] * dt
        self.heading = math.atan2(math.sin(self.heading), math.cos(self.heading))
        self.angular_velocity = gyro_filtered[2]

        # ----- STEP 5: Quaternion integration (optional) -----
        gyro_vec = gyro_filtered * dt / 2.0
        dq = np.array([1.0, gyro_vec[0], gyro_vec[1], gyro_vec[2]])
        norm_dq = np.linalg.norm(dq)
        if norm_dq > 1e-6:
            dq /= norm_dq
            self.orientation = self._quaternion_multiply(self.orientation, dq)
            self.orientation /= np.linalg.norm(self.orientation)

        # ----- STEP 6: Magnetometer correction (if available) -----
        if mag_x is not None and mag_y is not None and mag_z is not None:
            mag = np.array([mag_x, mag_y, mag_z])
            mag_filtered = self._low_pass_filter(self.mag_buffer, mag)
            self.mag_buffer.append(mag_filtered)
            mag_heading = math.atan2(mag_filtered[1], mag_filtered[0])
            self.heading = self.alpha * self.heading + (1.0 - self.alpha) * mag_heading

        # ----- STEP 7: Transform horizontal accel to world frame -----
        accel_horizontal = accel_linear[:2]
        cos_h = math.cos(self.heading)
        sin_h = math.sin(self.heading)
        world_ax = accel_horizontal[0] * cos_h - accel_horizontal[1] * sin_h
        world_ay = accel_horizontal[0] * sin_h + accel_horizontal[1] * cos_h
        accel_world = np.array([world_ax, world_ay])

        # Deadzone per component
        for i in (0, 1):
            if abs(accel_world[i]) < self.accel_deadzone:
                accel_world[i] = 0.0

        accel_magnitude = np.linalg.norm(accel_world)

        # ----- STEP 8: Stationary detection -----
        horizontal_near_zero = accel_magnitude < 0.15  # almost no horizontal accel

        if ((near_gravity and gyro_mag < self.gyro_stationary_threshold) or
            (horizontal_near_zero and gyro_mag < self.gyro_stationary_threshold)):
            self.stationary_count += 1
        else:
            self.stationary_count = 0

        is_stationary = self.stationary_count >= self.stationary_threshold

        # Immediate hard-stop hint: even one very "still" frame
        if near_gravity and gyro_mag < (0.5 * self.gyro_stationary_threshold):
            self._hard_stop()
            accel_world[:] = 0.0
            accel_magnitude = 0.0

        # ----- STEP 9: Tilt gating -----
        pitch_deg = abs(math.degrees(self.pitch))
        roll_deg = abs(math.degrees(self.roll))
        too_tilted = (pitch_deg > self.max_tilt_deg) or (roll_deg > self.max_tilt_deg)

        # ----- STEP 10: Velocity update -----
        if is_stationary:
            # Hard stop when clearly stationary across multiple frames
            self._hard_stop()
        else:
            # Any strong horizontal accel or rotation counts as "motion"
            if accel_magnitude >= self.accel_move_threshold or gyro_mag >= self.gyro_stationary_threshold:
                self.last_motion_timestamp = timestamp

            if (not too_tilted) and accel_magnitude >= self.accel_move_threshold:
                # REAL MOVEMENT DETECTED - INTEGRATE!
                self.velocity += accel_world * dt
            else:
                # No significant movement - damp velocity
                self.velocity *= self.velocity_damping

        # Speed clamp
        speed = np.linalg.norm(self.velocity)
        if speed > self.max_speed:
            self.velocity *= (self.max_speed / speed)
            speed = self.max_speed

        # Velocity cutoff
        if speed < self.velocity_threshold:
            self._hard_stop()
            speed = 0.0

        # If we've seen no motion for a while, forcefully freeze
        if self.last_motion_timestamp is not None and (timestamp - self.last_motion_timestamp) > self.no_motion_timeout:
            self._hard_stop()
            speed = 0.0

        # ----- STEP 11: Position integration -----
        old_position = self.position.copy()
        self.position += self.velocity * dt
        distance = np.linalg.norm(self.position - old_position)
        self.total_distance += distance

        # ----- STEP 12: History -----
        self.position_history.append({
            'x': float(self.position[0]),
            'y': float(self.position[1]),
            'heading': float(self.heading),
            'timestamp': float(timestamp),
            'velocity': float(speed)
        })

        self.last_timestamp = timestamp
        self.update_count += 1

        if self.update_count % 50 == 0:
            logger.info(
                f"Update #{self.update_count}: "
                f"pos=({self.position[0]:.2f}, {self.position[1]:.2f}), "
                f"vel={speed:.3f} m/s, "
                f"accel_mag={accel_magnitude:.3f}, "
                f"stationary={is_stationary}, "
                f"dist={self.total_distance:.2f}m"
            )

        return self.get_state()

    def get_state(self):
        speed = np.linalg.norm(self.velocity)
        is_stationary = self.stationary_count >= self.stationary_threshold

        return {
            'position': {
                'x': float(self.position[0]),
                'y': float(self.position[1])
            },
            'velocity': {
                'vx': float(self.velocity[0]),
                'vy': float(self.velocity[1]),
                'magnitude': float(speed)
            },
            'heading': float(self.heading),
            'heading_degrees': float(np.degrees(self.heading)),
            'angular_velocity': float(self.angular_velocity),
            'pitch': float(self.pitch),
            'roll': float(self.roll),
            'pitch_degrees': float(np.degrees(self.pitch)),
            'roll_degrees': float(np.degrees(self.roll)),
            'timestamp': float(self.last_timestamp) if self.last_timestamp else None,
            'update_count': self.update_count,
            'total_distance': float(self.total_distance),
            'is_stationary': is_stationary,
            'stationary_count': self.stationary_count
        }

    def get_position_history(self, limit=None):
        history = list(self.position_history)
        if limit and len(history) > limit:
            step = max(1, len(history) // limit)
            history = history[::step]
        return history


class AdvancedTrailTracker(IMUDeadReckoning):
    """
    Wrapper that only needs accel + gyro_z + timestamp and keeps a path history.
    Signature is compatible with server.py calling update(..., timestamp=...).
    """

    def __init__(self):
        super().__init__()
        self.trail_points = [(0.0, 0.0)]

    def reset(self):
        super().reset()
        self.trail_points = [(0.0, 0.0)]

    def update(self, accel_x, accel_y, accel_z,
               gyro_z, timestamp,
               mag_x=None, mag_y=None, mag_z=None):
        """
        Backwards-compatible signature:
        - server.py calls this with keyword 'timestamp'
        """
        state = super().update(
            accel_x, accel_y, accel_z,
            0.0, 0.0, gyro_z,
            timestamp,          # IMUDeadReckoning handles s vs ms
            mag_x, mag_y, mag_z
        )

        self.trail_points.append((
            float(self.position[0]),
            float(self.position[1])
        ))

        return state

    def get_trail_data(self):
        speed = np.linalg.norm(self.velocity)
        return {
            "path": self.trail_points,
            "position": {
                "x": float(self.position[0]),
                "y": float(self.position[1])
            },
            "velocity": float(speed),
            "heading": float(np.degrees(self.heading)) % 360
        }