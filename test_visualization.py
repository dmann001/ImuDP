"""
Test script to simulate iPhone IMU data for visualization testing
===============================================================

This script simulates IMU data being sent from an iPhone app
to test the visualization system without needing the actual app.
"""

import requests
import json
import time
import math
from datetime import datetime


def simulate_imu_data():
    """Simulate iPhone IMU data and send to server."""
    server_url = "http://localhost:5000"
    
    print("Simulating iPhone IMU data for visualization testing...")
    print("Open visualization.html in your browser to see the mapping!")
    print("Press Ctrl+C to stop")
    
    # Simulate walking in a square pattern
    start_time = time.time()
    
    try:
        for i in range(100):  # Send 100 data points
            elapsed = time.time() - start_time
            
            # Simulate walking in a square (4 sides, 25 points each)
            side = i // 25
            progress = (i % 25) / 25.0
            
            if side == 0:  # North side
                accel_x = 0.1 + 0.05 * math.sin(elapsed * 2)  # Walking motion
                accel_y = 0.0
                accel_z = 9.8 + 0.1 * math.cos(elapsed * 3)
                gyro_x = 0.01
                gyro_y = 0.0
                gyro_z = 0.0
            elif side == 1:  # East side
                accel_x = 0.0
                accel_y = 0.1 + 0.05 * math.sin(elapsed * 2)
                accel_z = 9.8 + 0.1 * math.cos(elapsed * 3)
                gyro_x = 0.0
                gyro_y = 0.01
                gyro_z = 0.02  # Turning
            elif side == 2:  # South side
                accel_x = -0.1 - 0.05 * math.sin(elapsed * 2)
                accel_y = 0.0
                accel_z = 9.8 + 0.1 * math.cos(elapsed * 3)
                gyro_x = -0.01
                gyro_y = 0.0
                gyro_z = 0.0
            else:  # West side
                accel_x = 0.0
                accel_y = -0.1 - 0.05 * math.sin(elapsed * 2)
                accel_z = 9.8 + 0.1 * math.cos(elapsed * 3)
                gyro_x = 0.0
                gyro_y = -0.01
                gyro_z = -0.02  # Turning
            
            # Create IMU data packet
            imu_data = {
                "accel_x": accel_x,
                "accel_y": accel_y,
                "accel_z": accel_z,
                "gyro_x": gyro_x,
                "gyro_y": gyro_y,
                "gyro_z": gyro_z,
                "timestamp": int(time.time() * 1000),
                "device_id": "iPhone_Simulator"
            }
            
            # Send to server
            try:
                response = requests.post(
                    f"{server_url}/imu",
                    json=imu_data,
                    timeout=5
                )
                
                if response.status_code == 200:
                    print(f"Sent IMU data point {i+1}/100 (side {side+1}/4)")
                else:
                    print(f"Error sending data: {response.status_code}")
                    
            except Exception as e:
                print(f"Connection error: {e}")
                break
                
            time.sleep(0.5)  # Send data every 500ms
            
    except KeyboardInterrupt:
        print("\nStopping simulation...")
        
    print("Simulation complete!")


if __name__ == "__main__":
    simulate_imu_data()
