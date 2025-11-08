#!/usr/bin/env python3
"""
Test script for BRAMPS Flask server
Simulates sensor data to verify server functionality
"""

import requests
import time
import json
import random
from datetime import datetime

SERVER_URL = "http://localhost:5000"

def generate_test_sensor_data():
    """Generate simulated sensor data"""
    return {
        "accel_x": random.uniform(-10, 10),
        "accel_y": random.uniform(-10, 10),
        "accel_z": random.uniform(-10, 10),
        "gyro_x": random.uniform(-5, 5),
        "gyro_y": random.uniform(-5, 5),
        "gyro_z": random.uniform(-5, 5),
        "mag_x": random.uniform(-100, 100),
        "mag_y": random.uniform(-100, 100),
        "mag_z": random.uniform(-100, 100),
        "timestamp": int(time.time() * 1000)
    }

def test_health_endpoint():
    """Test health check endpoint"""
    print("Testing /health endpoint...")
    try:
        response = requests.get(f"{SERVER_URL}/health")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"  Error: {e}")
        return False

def test_imu_endpoint():
    """Test IMU data endpoint"""
    print("\nTesting /imu endpoint...")
    test_data = generate_test_sensor_data()
    
    try:
        response = requests.post(
            f"{SERVER_URL}/imu",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"  Error: {e}")
        return False

def test_stats_endpoint():
    """Test statistics endpoint"""
    print("\nTesting /stats endpoint...")
    try:
        response = requests.get(f"{SERVER_URL}/stats")
        print(f"  Status: {response.status_code}")
        stats = response.json()
        print(f"  Total Packets: {stats.get('total_packets', 0)}")
        print(f"  Packets/Second: {stats.get('packets_per_second', 0):.2f}")
        return response.status_code == 200
    except Exception as e:
        print(f"  Error: {e}")
        return False

def test_streaming(num_packets=10, interval=0.1):
    """Test continuous streaming"""
    print(f"\nTesting continuous streaming ({num_packets} packets at {1/interval:.1f} Hz)...")
    
    success_count = 0
    for i in range(num_packets):
        test_data = generate_test_sensor_data()
        try:
            response = requests.post(
                f"{SERVER_URL}/imu",
                json=test_data,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                success_count += 1
                print(f"  Packet {i+1}/{num_packets}: ✓")
            else:
                print(f"  Packet {i+1}/{num_packets}: ✗ (Status: {response.status_code})")
        except Exception as e:
            print(f"  Packet {i+1}/{num_packets}: ✗ (Error: {e})")
        
        time.sleep(interval)
    
    print(f"\n  Success Rate: {success_count}/{num_packets} ({100*success_count/num_packets:.1f}%)")
    return success_count == num_packets

def main():
    print("=" * 60)
    print("BRAMPS Server Test Suite")
    print("=" * 60)
    print(f"Testing server at: {SERVER_URL}")
    print(f"Make sure the server is running before running this test!")
    print("=" * 60)
    
    # Wait a moment for user to read
    time.sleep(2)
    
    results = []
    
    # Test health endpoint
    results.append(("Health Check", test_health_endpoint()))
    
    # Test IMU endpoint
    results.append(("IMU Endpoint", test_imu_endpoint()))
    
    # Test stats endpoint
    results.append(("Stats Endpoint", test_stats_endpoint()))
    
    # Test continuous streaming
    results.append(("Streaming Test", test_streaming(num_packets=10, interval=0.1)))
    
    # Final stats
    print("\n" + "=" * 60)
    print("Final Statistics:")
    try:
        response = requests.get(f"{SERVER_URL}/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"  Total Packets Received: {stats.get('total_packets', 0)}")
            print(f"  Average Rate: {stats.get('packets_per_second', 0):.2f} packets/sec")
    except:
        pass
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    print("=" * 60)
    if all_passed:
        print("All tests passed! ✓")
    else:
        print("Some tests failed. Check server logs for details.")
    print("=" * 60)

if __name__ == "__main__":
    main()

