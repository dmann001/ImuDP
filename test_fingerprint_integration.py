"""
Integration Test for Magnetic Fingerprint Storage with BRAMPS Server
===================================================================

This test demonstrates how the fingerprint storage system integrates
with the existing IMU server and magnetic field model.

Author: BRAMPS Navigation System
Date: 2024
"""

import json
from datetime import datetime
from fingerprint_storage import FingerprintStorage, MagneticFingerprint
from magnetic_field_model import MagneticFieldModel
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)


def simulate_imu_data_with_gps():
    """
    Simulate IMU data collection with GPS coordinates for fingerprint creation.
    This simulates what would happen during a mapping walk (M2.1).
    """
    print("Simulating IMU data collection with GPS for fingerprinting...")
    
    # Initialize storage and magnetic model
    storage = FingerprintStorage("demo_fingerprints")
    wmm_model = MagneticFieldModel()
    
    # Simulate a walking path (e.g., around a building)
    # Toronto coordinates with small variations
    base_lat, base_lon = 43.6532, -79.3832
    
    fingerprints = []
    
    # Simulate 20 measurement points along a path
    for i in range(20):
        # Create a rectangular path
        if i < 5:  # North side
            lat = base_lat + 0.001
            lon = base_lon + (i * 0.0005)
        elif i < 10:  # East side  
            lat = base_lat + 0.001 - ((i-5) * 0.0004)
            lon = base_lon + 0.002
        elif i < 15:  # South side
            lat = base_lat - 0.001
            lon = base_lon + 0.002 - ((i-10) * 0.0005)
        else:  # West side
            lat = base_lat - 0.001 + ((i-15) * 0.0004)
            lon = base_lon
            
        # Get WMM baseline field
        wmm_field = wmm_model.get_magnetic_field(lat, lon, 100.0)
        
        # Add some local magnetic anomaly (simulate building/infrastructure effects)
        anomaly_x = 200 * (i % 3 - 1)  # ±200 nT variation
        anomaly_y = 150 * ((i+1) % 3 - 1)  # ±150 nT variation  
        anomaly_z = 300 * ((i+2) % 3 - 1)  # ±300 nT variation
        
        # Create measured field with anomaly
        measured_x = wmm_field['X'] + anomaly_x
        measured_y = wmm_field['Y'] + anomaly_y
        measured_z = wmm_field['Z'] + anomaly_z
        
        # Create fingerprint
        fingerprint = MagneticFingerprint(
            timestamp=datetime.now(),
            latitude=lat,
            longitude=lon,
            altitude=100.0,
            mag_x=measured_x,
            mag_y=measured_y,
            mag_z=measured_z,
            device_id="iphone_test",
            session_id="building_survey_001"
        )
        
        fingerprints.append(fingerprint)
        
        print(f"Point {i+1:2d}: lat={lat:.6f}, lon={lon:.6f}, "
              f"field=({measured_x:.0f}, {measured_y:.0f}, {measured_z:.0f}) nT")
              
    # Add fingerprints to storage
    added_count = storage.add_fingerprints_batch(fingerprints)
    print(f"\nAdded {added_count} fingerprints to storage")
    
    return storage


def test_position_estimation():
    """
    Test position estimation using magnetic fingerprints.
    This simulates what would happen during navigation (M3.2).
    """
    print("\n" + "="*60)
    print("Testing Position Estimation with Magnetic Fingerprints")
    print("="*60)
    
    # Create fingerprint database
    storage = simulate_imu_data_with_gps()
    
    # Test position estimation at various points
    test_points = [
        (43.6532, -79.3832, "Center of mapped area"),
        (43.6542, -79.3827, "North of mapped area"),
        (43.6522, -79.3837, "South of mapped area"),
        (43.6532, -79.3822, "East of mapped area"),
    ]
    
    print(f"\nTesting position estimation at {len(test_points)} locations:")
    
    for lat, lon, description in test_points:
        print(f"\n📍 {description}")
        print(f"   Target: lat={lat:.6f}, lon={lon:.6f}")
        
        # Find nearest fingerprints
        nearest = storage.find_nearest_fingerprints(lat, lon, max_distance=300.0, max_count=5)
        print(f"   Found {len(nearest)} nearby fingerprints within 300m")
        
        if nearest:
            closest_fp, distance = nearest[0]
            print(f"   Closest: {distance:.1f}m away, quality={closest_fp.quality_score:.2f}")
            
        # Get interpolated magnetic field
        interpolated = storage.get_interpolated_field(lat, lon, 100.0)
        if interpolated:
            print(f"   Interpolated field: ({interpolated[0]:.0f}, {interpolated[1]:.0f}, {interpolated[2]:.0f}) nT")
            
        # Calculate magnetic anomaly
        anomaly = storage.get_field_anomaly(lat, lon, 100.0)
        if anomaly:
            anomaly_magnitude = (anomaly[0]**2 + anomaly[1]**2 + anomaly[2]**2)**0.5
            print(f"   Magnetic anomaly: {anomaly_magnitude:.0f} nT magnitude")
            
    # Show storage statistics
    print(f"\n📊 Storage Statistics:")
    stats = storage.get_statistics()
    print(f"   Total fingerprints: {stats['total_fingerprints']}")
    print(f"   Sessions: {stats['sessions']}")
    print(f"   Devices: {stats['devices']}")
    print(f"   Quality range: {stats['quality_stats']['min']:.2f} - {stats['quality_stats']['max']:.2f}")


def test_heading_correction():
    """
    Test magnetic heading correction using fingerprints.
    This demonstrates integration with dead-reckoning (M3.2).
    """
    print(f"\n" + "="*60)
    print("Testing Magnetic Heading Correction")
    print("="*60)
    
    storage = FingerprintStorage("demo_fingerprints")
    wmm_model = MagneticFieldModel()
    
    # Test location
    test_lat, test_lon = 43.6532, -79.3832
    
    print(f"\nTesting heading correction at lat={test_lat:.6f}, lon={test_lon:.6f}")
    
    # Get WMM baseline declination
    wmm_field = wmm_model.get_magnetic_field(test_lat, test_lon, 100.0)
    wmm_declination = wmm_field['D']
    print(f"WMM declination: {wmm_declination:.2f}°")
    
    # Get local magnetic field from fingerprints
    local_field = storage.get_interpolated_field(test_lat, test_lon, 100.0)
    if local_field:
        # Calculate local declination
        import math
        local_declination = math.degrees(math.atan2(local_field[1], local_field[0]))
        print(f"Local declination (from fingerprints): {local_declination:.2f}°")
        
        # Calculate correction needed
        declination_correction = local_declination - wmm_declination
        print(f"Declination correction: {declination_correction:.2f}°")
        
        # Simulate heading correction
        raw_heading = 45.0  # Example: 45° from gyroscope
        corrected_heading = raw_heading - local_declination
        print(f"\nHeading correction example:")
        print(f"  Raw gyroscope heading: {raw_heading:.1f}°")
        print(f"  Corrected true heading: {corrected_heading:.1f}°")
        
    else:
        print("No local magnetic field data available for heading correction")


def main():
    """Run all integration tests."""
    print("BRAMPS Fingerprint Storage Integration Test")
    print("=" * 50)
    
    try:
        # Test 1: Position estimation
        test_position_estimation()
        
        # Test 2: Heading correction
        test_heading_correction()
        
        print(f"\n✅ All integration tests completed successfully!")
        print(f"\nNext steps:")
        print(f"  - M2.1: Implement GPS-enabled mapping walk UI")
        print(f"  - M3.2: Integrate with dead-reckoning algorithm")
        print(f"  - M2.4: Add advanced interpolation methods")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
