"""
BRAMPS - IMU Dead-Reckoning Module
Calculates position and orientation from IMU sensor data
"""

import numpy as np
from datetime import datetime
from collections import deque
import logging

logger = logging.getLogger(__name__)


# Add quaternion utilities
def quaternion_multiply(q1, q2):
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
    x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
    y = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
    z = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
    return np.array([w, x, y, z])

def quaternion_conjugate(q):
    w, x, y, z = q
    return np.array([w, -x, -y, -z])

def quaternion_to_euler(q):
    w, x, y, z = q
    # Roll (x-axis rotation)
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = np.arctan2(sinr_cosp, cosr_cosp)

    # Pitch (y-axis rotation)
    sinp = 2 * (w * y - z * x)
    if abs(sinp) >= 1:
        pitch = np.copysign(np.pi / 2, sinp)
    else:
        pitch = np.arcsin(sinp)

    # Yaw (z-axis rotation)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = np.arctan2(siny_cosp, cosy_cosp)

    return roll, pitch, yaw

def vector_rotate(v, q):
    qv = np.array([0, v[0], v[1], v[2]])
    q_conj = quaternion_conjugate(q)
    return quaternion_multiply(quaternion_multiply(q, qv), q_conj)[1:]


class IMUDeadReckoning:
    """
    IMU Dead-Reckoning implementation for position tracking.
    
    Integrates accelerometer and gyroscope data to estimate position and orientation.
    Includes basic filtering and drift correction.
    """
    
    def __init__(self, initial_position=(0.0, 0.0), initial_heading=0.0):
        """
        Initialize dead-reckoning system.
        
        Args:
            initial_position: Tuple (x, y) in meters
            initial_heading: Initial heading in radians (0 = North, clockwise positive)
        """
        # Position state (x, y in meters)
        self.position = np.array(initial_position, dtype=float)
        
        # Velocity state (vx, vy in m/s)
        self.velocity = np.array([0.0, 0.0], dtype=float)
        
        # Orientation state (heading in radians)
        self.heading = float(initial_heading)
        
        # Angular velocity (rad/s)
        self.angular_velocity = 0.0
        
        # Last update timestamp
        self.last_timestamp = None
        
        # Position history for visualization
        self.position_history = deque(maxlen=1000)
        
        # Sensor data buffers for filtering
        self.accel_buffer = deque(maxlen=10)  # Increased for better filtering
        self.gyro_buffer = deque(maxlen=10)
        
        # Calibration offsets
        self.accel_bias = np.array([0.0, 0.0, 0.0])
        self.gyro_bias = np.array([0.0, 0.0, 0.0])
        
        # Gravity vector (m/s²)
        self.gravity = np.array([0.0, 0.0, 9.81])
        
        # Statistics
        self.update_count = 0
        self.total_distance = 0.0
        
        # Stationary detection
        self.stationary_count = 0
        self.stationary_threshold = 20  # Number of updates to consider stationary
        
        # Balanced thresholds - not too sensitive, not too strict
        self.accel_threshold = 0.2  # m/s² - balanced value
        self.velocity_threshold = 0.08  # m/s - balanced value
        self.gyro_threshold = 0.03  # rad/s - for rotation detection
        
        # Orientation quaternion (w, x, y, z) - identity = level, facing north
        self.orientation = np.array([1.0, 0.0, 0.0, 0.0])  # w, x, y, z
        
        # For complementary filter
        self.alpha = 0.98  # Gyro trust factor
        
        # Add mag buffer if needed
        self.mag_buffer = deque(maxlen=10)

        logger.info(f"IMU Dead-Reckoning initialized with quaternion support")
    
    def reset(self, position=(0.0, 0.0), heading=0.0):
        """Reset position and heading to specified values."""
        self.position = np.array(position, dtype=float)
        self.velocity = np.array([0.0, 0.0], dtype=float)
        self.heading = float(heading)
        self.angular_velocity = 0.0
        self.last_timestamp = None
        self.position_history.clear()
        self.total_distance = 0.0
        self.stationary_count = 0
        self.orientation = np.array([1.0, 0.0, 0.0, 0.0])
        logger.info(f"Dead-reckoning reset to position {position}, heading {np.degrees(heading):.1f}°")
        logger.info(f"Reset orientation quaternion to identity")
    
    def calibrate(self, accel_samples, gyro_samples):
        """
        Calibrate sensor biases from stationary samples.
        
        Args:
            accel_samples: List of (ax, ay, az) tuples
            gyro_samples: List of (gx, gy, gz) tuples
        """
        if len(accel_samples) > 0:
            accel_array = np.array(accel_samples)
            self.accel_bias = np.mean(accel_array, axis=0)
            # Subtract gravity from z-axis bias
            self.accel_bias[2] -= 9.81
            logger.info(f"Accelerometer bias calibrated: {self.accel_bias}")
        
        if len(gyro_samples) > 0:
            gyro_array = np.array(gyro_samples)
            self.gyro_bias = np.mean(gyro_array, axis=0)
            logger.info(f"Gyroscope bias calibrated: {self.gyro_bias}")
    
    def _low_pass_filter(self, buffer, new_value, alpha=0.3):
        """
        Apply low-pass filter to reduce noise.
        
        Args:
            buffer: Deque of previous values
            new_value: New sensor reading
            alpha: Filter coefficient (0-1, lower = more smoothing)
        
        Returns:
            Filtered value
        """
        if len(buffer) == 0:
            return new_value
        
        filtered = alpha * new_value + (1 - alpha) * buffer[-1]
        return filtered
    
    def _remove_gravity(self, accel, heading):
        """
        Remove gravity component from accelerometer reading.
        
        Args:
            accel: Raw accelerometer reading (ax, ay, az)
            heading: Current heading in radians
        
        Returns:
            Linear acceleration without gravity
        """
        # Simple gravity removal assuming device is mostly upright
        # In a full implementation, use orientation quaternion
        accel_corrected = accel.copy()
        accel_corrected[2] -= 9.81  # Remove gravity from z-axis
        
        return accel_corrected
    
    def _transform_to_world_frame(self, accel_device, heading):
        """
        Transform acceleration from device frame to world frame.
        
        Args:
            accel_device: Acceleration in device frame (forward, right, down)
            heading: Current heading in radians
        
        Returns:
            Acceleration in world frame (north, east)
        """
        # Simple 2D rotation (assuming device is held upright)
        # In full implementation, use full 3D rotation matrix or quaternion
        
        # Extract horizontal acceleration (assuming device coordinate system)
        ax = accel_device[0]  # Forward
        ay = accel_device[1]  # Right
        
        # Rotate by heading to get world frame
        cos_h = np.cos(heading)
        sin_h = np.sin(heading)
        
        # World frame: x = North, y = East
        world_x = ax * cos_h - ay * sin_h
        world_y = ax * sin_h + ay * cos_h
        
        return np.array([world_x, world_y])
    
    def update(self, accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, timestamp_ms, mag_x=None, mag_y=None, mag_z=None):
        """
        Update position estimate with new IMU data.
        
        Args:
            accel_x, accel_y, accel_z: Accelerometer readings (m/s²)
            gyro_x, gyro_y, gyro_z: Gyroscope readings (rad/s)
            timestamp_ms: Timestamp in milliseconds
        
        Returns:
            Dictionary with current state (position, velocity, heading)
        """
        # Convert timestamp to seconds
        timestamp = timestamp_ms / 1000.0
        
        # Calculate time delta
        if self.last_timestamp is None:
            self.last_timestamp = timestamp
            return self.get_state()
        
        dt = timestamp - self.last_timestamp
        
        # Sanity check on dt (reject if too large or negative)
        if dt <= 0 or dt > 1.0:
            logger.warning(f"Invalid time delta: {dt:.3f}s, skipping update")
            self.last_timestamp = timestamp
            return self.get_state()
        
        # Create numpy arrays
        accel = np.array([accel_x, accel_y, accel_z]) - self.accel_bias
        gyro = np.array([gyro_x, gyro_y, gyro_z]) - self.gyro_bias
        
        # Apply low-pass filter
        accel_filtered = self._low_pass_filter(self.accel_buffer, accel)
        gyro_filtered = self._low_pass_filter(self.gyro_buffer, gyro)
        
        self.accel_buffer.append(accel_filtered)
        self.gyro_buffer.append(gyro_filtered)
        
        # Update heading from gyroscope (z-axis rotation)
        # Positive rotation is clockwise when looking down
        angular_velocity = gyro_filtered[2]
        self.heading += angular_velocity * dt
        
        # Normalize heading to [0, 2π)
        self.heading = self.heading % (2 * np.pi)
        self.angular_velocity = angular_velocity
        
        # Update orientation from gyro
        gyro_vec = gyro_filtered * dt / 2.0
        gyro_quat = np.array([0.0, gyro_vec[0], gyro_vec[1], gyro_vec[2]])
        gyro_quat[0] = np.sqrt(1.0 - np.dot(gyro_quat[1:], gyro_quat[1:]))
        self.orientation = quaternion_multiply(self.orientation, gyro_quat)
        self.orientation /= np.linalg.norm(self.orientation)  # Normalize

        # Complementary filter with accel for pitch/roll correction
        roll, pitch, _ = quaternion_to_euler(self.orientation)
        
        # Accel-based pitch/roll
        accel_pitch = np.arctan2(accel_filtered[0], np.sqrt(accel_filtered[1]**2 + accel_filtered[2]**2))
        accel_roll = np.arctan2(-accel_filtered[1], accel_filtered[2])
        
        # Fuse with gyro estimates
        pitch = self.alpha * (pitch + gyro_filtered[1] * dt) + (1 - self.alpha) * accel_pitch
        roll = self.alpha * (roll + gyro_filtered[0] * dt) + (1 - self.alpha) * accel_roll

        # Update quaternion with fused pitch/roll/yaw
        cy = np.cos(self.heading * 0.5)
        sy = np.sin(self.heading * 0.5)
        cp = np.cos(pitch * 0.5)
        sp = np.sin(pitch * 0.5)
        cr = np.cos(roll * 0.5)
        sr = np.sin(roll * 0.5)

        w = cy * cp * cr + sy * sp * sr
        x = cy * cp * sr - sy * sp * cr
        y = sy * cp * sr + cy * sp * cr
        z = sy * cp * cr - cy * sp * sr

        self.orientation = np.array([w, x, y, z])

        # Magnetometer heading correction if provided
        if mag_x is not None and mag_y is not None and mag_z is not None:
            mag = np.array([mag_x, mag_y, mag_z])
            mag_filtered = self._low_pass_filter(self.mag_buffer, mag)
            self.mag_buffer.append(mag_filtered)
            
            # Rotate mag to horizontal plane
            mag_world = vector_rotate(mag_filtered, self.orientation)
            mag_heading = np.arctan2(mag_world[1], mag_world[0])  # Y/X for heading
            
            # Fuse with gyro heading (simple complementary)
            self.heading = self.alpha * self.heading + (1 - self.alpha) * mag_heading

        # Remove gravity using current orientation
        gravity_world = vector_rotate(self.gravity, self.orientation)
        accel_linear = accel_filtered - gravity_world

        # Project to horizontal plane (ignore Z component for 2D trail)
        accel_horizontal = accel_linear[:2]  # X and Y only
        
        # Rotate by heading (yaw) for world frame
        cos_h = np.cos(self.heading)
        sin_h = np.sin(self.heading)
        ax = accel_horizontal[0]
        ay = accel_horizontal[1]
        world_ax = ax * cos_h - ay * sin_h
        world_ay = ax * sin_h + ay * cos_h
        accel_world = np.array([world_ax, world_ay])
        
        # Calculate magnitudes for thresholding
        accel_magnitude = np.linalg.norm(accel_world)
        gyro_magnitude = np.linalg.norm(gyro_filtered)
        
        # Stationary detection - if both accel and gyro are below threshold
        if accel_magnitude < self.accel_threshold and gyro_magnitude < self.gyro_threshold:
            self.stationary_count += 1
        else:
            self.stationary_count = 0
        
        # If stationary for multiple updates, zero out velocity
        if self.stationary_count >= self.stationary_threshold:
            self.velocity *= 0.0  # Force stop when stationary
        else:
            # Only integrate acceleration if it's above noise level
            if accel_magnitude >= self.accel_threshold:
                # Integrate acceleration to get velocity
                self.velocity += accel_world * dt
            else:
                # Apply strong velocity damping when no significant acceleration
                self.velocity *= 0.85  # Increased damping from 0.95
        
        # Apply velocity threshold - stop if moving very slowly
        velocity_magnitude = np.linalg.norm(self.velocity)
        if velocity_magnitude < self.velocity_threshold:
            self.velocity *= 0.0  # Stop if moving very slowly
        
        # Store old position for distance calculation
        old_position = self.position.copy()
        
        # Integrate velocity to get position
        self.position += self.velocity * dt
        
        # Calculate distance traveled
        distance = np.linalg.norm(self.position - old_position)
        self.total_distance += distance
        
        # Store position history
        self.position_history.append({
            'x': float(self.position[0]),
            'y': float(self.position[1]),
            'heading': float(self.heading),
            'timestamp': timestamp,
            'velocity': float(velocity_magnitude)
        })
        
        # Update timestamp and counter
        self.last_timestamp = timestamp
        self.update_count += 1
        
        # Log every 50 updates
        if self.update_count % 50 == 0:
            logger.info(f"Dead-reckoning update #{self.update_count}: pos=({self.position[0]:.2f}, {self.position[1]:.2f}), "
                       f"heading={np.degrees(self.heading):.1f}°, vel={velocity_magnitude:.2f} m/s, dist={self.total_distance:.2f}m")
        
        return self.get_state()
    
    def get_state(self):
        """
        Get current state of the dead-reckoning system.
        
        Returns:
            Dictionary with position, velocity, heading, and statistics
        """
        velocity_magnitude = np.linalg.norm(self.velocity)
        
        return {
            'position': {
                'x': float(self.position[0]),
                'y': float(self.position[1])
            },
            'velocity': {
                'vx': float(self.velocity[0]),
                'vy': float(self.velocity[1]),
                'magnitude': float(velocity_magnitude)
            },
            'heading': float(self.heading),
            'heading_degrees': float(np.degrees(self.heading)),
            'angular_velocity': float(self.angular_velocity),
            'timestamp': float(self.last_timestamp) if self.last_timestamp else None,
            'update_count': self.update_count,
            'total_distance': float(self.total_distance)
        }
    
    def get_position_history(self, limit=None):
        """
        Get position history for visualization.
        
        Args:
            limit: Maximum number of points to return (None = all)
        
        Returns:
            List of position dictionaries
        """
        history = list(self.position_history)
        if limit and len(history) > limit:
            # Sample evenly from history
            step = len(history) // limit
            history = history[::step]
        return history

