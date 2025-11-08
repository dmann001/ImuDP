"""
IMU Bridge for iPhone App Integration with BRAMPS Mapping
========================================================

This script bridges your iPhone IMU app data with GPS coordinates
to create magnetic fingerprints for the BRAMPS navigation system.

Usage:
1. Start your iPhone IMU app sending data to the server
2. Run this script to add GPS coordinates and create fingerprints
3. Use visualization.html to see real-time mapping

Author: BRAMPS Navigation System
Date: 2024
"""

import requests
import json
import time
import logging
from datetime import datetime
from typing import Dict, Optional
import threading
from queue import Queue

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class IMUBridge:
    """
    Bridge between iPhone IMU app and BRAMPS mapping system.
    
    Monitors IMU data from the server, adds GPS coordinates,
    and creates magnetic fingerprints for visualization.
    """
    
    def __init__(self, server_url: str = "http://localhost:5000"):
        """
        Initialize IMU bridge.
        
        Args:
            server_url: URL of the BRAMPS server
        """
        self.server_url = server_url.rstrip('/')
        self.session_id = None
        self.device_id = "iPhone_Bridge"
        self.running = False
        
        # GPS simulation (you can replace this with actual GPS)
        self.gps_enabled = True
        self.current_gps = {
            'latitude': 43.6532,  # Toronto coordinates as starting point
            'longitude': -79.3832,
            'altitude': 100.0
        }
        
        # Data queues
        self.imu_data_queue = Queue()
        
        # Statistics
        self.stats = {
            'imu_packets_received': 0,
            'fingerprints_created': 0,
            'last_imu_time': None,
            'start_time': datetime.now()
        }
        
    def start_mapping_session(self, description: str = "iPhone IMU Bridge Session") -> bool:
        """
        Start a new mapping session.
        
        Args:
            description: Description for the mapping session
            
        Returns:
            True if session started successfully
        """
        try:
            response = requests.post(
                f"{self.server_url}/mapping/start",
                json={
                    'device_id': self.device_id,
                    'description': description
                },
                timeout=10
            )
            
            result = response.json()
            
            if result.get('success'):
                self.session_id = result['session_id']
                logger.info(f"Started mapping session: {self.session_id}")
                return True
            else:
                logger.error(f"Failed to start session: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting mapping session: {e}")
            return False
            
    def stop_mapping_session(self) -> bool:
        """
        Stop the current mapping session.
        
        Returns:
            True if session stopped successfully
        """
        if not self.session_id:
            return True
            
        try:
            response = requests.post(
                f"{self.server_url}/mapping/stop",
                json={'session_id': self.session_id},
                timeout=10
            )
            
            result = response.json()
            
            if result.get('success'):
                fingerprint_count = result.get('fingerprint_count', 0)
                logger.info(f"Stopped mapping session. Created {fingerprint_count} fingerprints")
                self.session_id = None
                return True
            else:
                logger.error(f"Failed to stop session: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error stopping mapping session: {e}")
            return False
            
    def get_latest_imu_data(self) -> Optional[Dict]:
        """
        Get the latest IMU data from the server.
        
        Returns:
            Latest IMU data packet or None if no data available
        """
        try:
            response = requests.get(
                f"{self.server_url}/recent?limit=1",
                timeout=5
            )
            
            result = response.json()
            
            if result.get('success') and result.get('data'):
                return result['data'][0]  # Get the most recent packet
            else:
                return None
                
        except Exception as e:
            logger.debug(f"Error getting IMU data: {e}")
            return None
            
    def simulate_gps_movement(self):
        """
        Simulate GPS movement for testing.
        In a real scenario, you'd get actual GPS coordinates.
        """
        # Simple circular movement pattern for demonstration
        import math
        
        elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
        radius = 0.0001  # About 10 meters
        center_lat = 43.6532
        center_lon = -79.3832
        
        # Circular movement
        angle = elapsed * 0.1  # Slow movement
        self.current_gps['latitude'] = center_lat + radius * math.cos(angle)
        self.current_gps['longitude'] = center_lon + radius * math.sin(angle)
        self.current_gps['altitude'] = 100.0 + 5 * math.sin(angle * 2)  # Slight altitude variation
        
    def estimate_magnetometer_from_orientation(self, imu_data: Dict) -> Dict:
        """
        Estimate magnetometer data from device orientation.
        This is a rough approximation since iPhone apps may not provide raw magnetometer.
        
        Args:
            imu_data: IMU data packet
            
        Returns:
            Estimated magnetometer data
        """
        # Get orientation data (if available)
        gyro_x = imu_data.get('gyro_x', 0)
        gyro_y = imu_data.get('gyro_y', 0) 
        gyro_z = imu_data.get('gyro_z', 0)
        
        # Simple estimation based on device orientation
        # In reality, you'd use actual magnetometer readings
        import math
        
        # Estimate heading from gyroscope integration (very rough)
        heading = math.atan2(gyro_y, gyro_x)
        
        # Typical Earth magnetic field strength in Toronto area
        field_strength = 52000  # nT
        inclination = math.radians(70)  # Typical inclination for Toronto
        
        # Estimate magnetic field components
        mag_x = field_strength * math.cos(inclination) * math.cos(heading)
        mag_y = field_strength * math.cos(inclination) * math.sin(heading)
        mag_z = field_strength * math.sin(inclination)
        
        # Add some noise to make it more realistic
        import random
        noise_level = 500  # nT
        mag_x += random.uniform(-noise_level, noise_level)
        mag_y += random.uniform(-noise_level, noise_level)
        mag_z += random.uniform(-noise_level, noise_level)
        
        return {
            'mag_x': mag_x,
            'mag_y': mag_y,
            'mag_z': mag_z
        }
        
    def create_fingerprint_from_imu(self, imu_data: Dict) -> bool:
        """
        Create a magnetic fingerprint from IMU data.
        
        Args:
            imu_data: IMU data packet from iPhone app
            
        Returns:
            True if fingerprint created successfully
        """
        if not self.session_id:
            return False
            
        try:
            # Update GPS position (simulate movement)
            if self.gps_enabled:
                self.simulate_gps_movement()
                
            # Estimate magnetometer data
            mag_data = self.estimate_magnetometer_from_orientation(imu_data)
            
            # Create fingerprint data
            fingerprint_data = {
                'session_id': self.session_id,
                'latitude': self.current_gps['latitude'],
                'longitude': self.current_gps['longitude'],
                'altitude': self.current_gps['altitude'],
                'mag_x': mag_data['mag_x'],
                'mag_y': mag_data['mag_y'],
                'mag_z': mag_data['mag_z'],
                'timestamp': imu_data.get('timestamp', datetime.now().isoformat())
            }
            
            # Send to mapping endpoint
            response = requests.post(
                f"{self.server_url}/mapping/data",
                json=fingerprint_data,
                timeout=5
            )
            
            result = response.json()
            
            if result.get('success'):
                self.stats['fingerprints_created'] += 1
                quality = result.get('quality_score', 0)
                logger.debug(f"Created fingerprint #{self.stats['fingerprints_created']} "
                           f"at ({self.current_gps['latitude']:.6f}, {self.current_gps['longitude']:.6f}) "
                           f"quality: {quality:.2f}")
                return True
            else:
                logger.warning(f"Failed to create fingerprint: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating fingerprint: {e}")
            return False
            
    def monitor_imu_data(self):
        """
        Monitor IMU data from the server and create fingerprints.
        """
        logger.info("Starting IMU data monitoring...")
        last_timestamp = None
        
        while self.running:
            try:
                # Get latest IMU data
                imu_data = self.get_latest_imu_data()
                
                if imu_data:
                    # Check if this is new data
                    current_timestamp = imu_data.get('timestamp')
                    if current_timestamp != last_timestamp:
                        self.stats['imu_packets_received'] += 1
                        self.stats['last_imu_time'] = datetime.now()
                        
                        # Create fingerprint from IMU data
                        if self.session_id:
                            self.create_fingerprint_from_imu(imu_data)
                            
                        last_timestamp = current_timestamp
                        
                # Print statistics periodically
                if self.stats['imu_packets_received'] % 10 == 0 and self.stats['imu_packets_received'] > 0:
                    self.print_statistics()
                    
            except Exception as e:
                logger.error(f"Error in IMU monitoring: {e}")
                
            time.sleep(0.5)  # Check for new data every 500ms
            
    def print_statistics(self):
        """Print current statistics."""
        elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
        imu_rate = self.stats['imu_packets_received'] / elapsed if elapsed > 0 else 0
        fingerprint_rate = self.stats['fingerprints_created'] / elapsed if elapsed > 0 else 0
        
        logger.info(f"Statistics: IMU packets: {self.stats['imu_packets_received']} "
                   f"({imu_rate:.1f}/s), Fingerprints: {self.stats['fingerprints_created']} "
                   f"({fingerprint_rate:.1f}/s)")
                   
    def run(self):
        """
        Run the IMU bridge.
        """
        logger.info("Starting BRAMPS IMU Bridge")
        logger.info("Make sure your iPhone IMU app is sending data to the server")
        logger.info("Open visualization.html in your browser to see real-time mapping")
        
        # Start mapping session
        if not self.start_mapping_session():
            logger.error("Failed to start mapping session")
            return
            
        # Start monitoring
        self.running = True
        
        try:
            self.monitor_imu_data()
        except KeyboardInterrupt:
            logger.info("Stopping IMU bridge...")
        finally:
            self.running = False
            self.stop_mapping_session()
            self.print_statistics()
            
        logger.info("IMU bridge stopped")


def main():
    """Main function."""
    print("BRAMPS IMU Bridge - iPhone App Integration")
    print("=" * 50)
    print()
    print("This script bridges your iPhone IMU app with BRAMPS mapping.")
    print("Instructions:")
    print("1. Start the BRAMPS server: python server.py")
    print("2. Start your iPhone IMU app sending data to the server")
    print("3. Run this script: python imu_bridge.py")
    print("4. Open visualization.html in your browser")
    print()
    print("Press Ctrl+C to stop")
    print()
    
    # Create and run bridge
    bridge = IMUBridge()
    bridge.run()


if __name__ == "__main__":
    main()
