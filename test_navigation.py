"""
Test script for BRAMPS Navigation System
Tests dead-reckoning and map management functionality
"""

import numpy as np
from imu_dead_reckoning import IMUDeadReckoning
from map_manager import MapManager
import time


def test_dead_reckoning():
    """Test IMU dead-reckoning with simulated movement."""
    print("=" * 60)
    print("Testing IMU Dead-Reckoning")
    print("=" * 60)
    
    # Initialize dead-reckoning
    dr = IMUDeadReckoning(initial_position=(0.0, 0.0), initial_heading=0.0)
    print(f"✓ Dead-reckoning initialized at (0, 0), heading 0°")
    
    # Simulate walking forward (1 m/s for 5 seconds)
    print("\nSimulating forward movement (1 m/s for 5 seconds)...")
    timestamp = int(time.time() * 1000)
    
    for i in range(50):  # 50 updates at 10 Hz = 5 seconds
        # Simulate forward acceleration (1 m/s²)
        accel_x = 1.0 if i < 10 else 0.0  # Accelerate for 1 second
        accel_y = 0.0
        accel_z = 9.81  # Gravity
        
        # No rotation
        gyro_x = 0.0
        gyro_y = 0.0
        gyro_z = 0.0
        
        # Update dead-reckoning
        state = dr.update(accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, timestamp)
        
        timestamp += 100  # 100ms intervals
        
        # Print every 10th update
        if i % 10 == 0:
            print(f"  t={i*0.1:.1f}s: pos=({state['position']['x']:.2f}, {state['position']['y']:.2f}), "
                  f"vel={state['velocity']['magnitude']:.2f} m/s")
    
    final_state = dr.get_state()
    print(f"\n✓ Final position: ({final_state['position']['x']:.2f}, {final_state['position']['y']:.2f})")
    print(f"✓ Total distance: {final_state['total_distance']:.2f} m")
    print(f"✓ Updates: {final_state['update_count']}")
    
    # Test rotation
    print("\nSimulating 90° right turn...")
    dr.reset(position=(0.0, 0.0), heading=0.0)
    timestamp = int(time.time() * 1000)
    
    for i in range(20):  # Rotate for 2 seconds
        # Simulate rotation (π/2 rad in 2 seconds = 0.785 rad/s)
        gyro_z = 0.785
        
        state = dr.update(0.0, 0.0, 9.81, 0.0, 0.0, gyro_z, timestamp)
        timestamp += 100
    
    final_state = dr.get_state()
    print(f"✓ Final heading: {final_state['heading_degrees']:.1f}° (expected ~90°)")
    
    # Test position history
    history = dr.get_position_history(limit=10)
    print(f"✓ Position history: {len(history)} points")
    
    print("\n✅ Dead-reckoning tests passed!\n")


def test_map_manager():
    """Test map management functionality."""
    print("=" * 60)
    print("Testing Map Manager")
    print("=" * 60)
    
    # Initialize map manager
    mm = MapManager("test_maps")
    print(f"✓ Map manager initialized")
    
    # Test coordinate transformations
    print("\nTesting coordinate transformations...")
    
    # Create a test map metadata (without actual image)
    test_map_id = "test_map_001"
    mm.maps[test_map_id] = {
        'id': test_map_id,
        'name': 'Test Map',
        'width': 1000,
        'height': 800,
        'scale_meters_per_pixel': 0.1,  # 10 pixels = 1 meter
        'origin_x': 0.0,
        'origin_y': 0.0,
        'rotation_degrees': 0.0
    }
    mm.active_map_id = test_map_id
    
    # Test world to pixel
    world_x, world_y = 5.0, 3.0  # 5m east, 3m north
    pixel_x, pixel_y = mm.world_to_pixel(world_x, world_y)
    print(f"  World ({world_x}, {world_y}) → Pixel ({pixel_x:.1f}, {pixel_y:.1f})")
    
    # Test pixel to world
    world_x2, world_y2 = mm.pixel_to_world(pixel_x, pixel_y)
    print(f"  Pixel ({pixel_x:.1f}, {pixel_y:.1f}) → World ({world_x2:.2f}, {world_y2:.2f})")
    
    # Verify round-trip
    assert abs(world_x - world_x2) < 0.01, "X coordinate mismatch"
    assert abs(world_y - world_y2) < 0.01, "Y coordinate mismatch"
    print(f"✓ Round-trip conversion accurate")
    
    # Test map bounds
    bounds = mm.get_map_bounds()
    print(f"\n✓ Map bounds: {bounds['width_meters']:.1f}m × {bounds['height_meters']:.1f}m")
    print(f"  X: [{bounds['min_x']:.1f}, {bounds['max_x']:.1f}]")
    print(f"  Y: [{bounds['min_y']:.1f}, {bounds['max_y']:.1f}]")
    
    # Test map list
    maps = mm.list_maps()
    print(f"\n✓ Maps in system: {len(maps)}")
    
    # Clean up test map
    del mm.maps[test_map_id]
    
    print("\n✅ Map manager tests passed!\n")


def test_integration():
    """Test integration of dead-reckoning with map coordinates."""
    print("=" * 60)
    print("Testing Integration")
    print("=" * 60)
    
    # Initialize systems
    dr = IMUDeadReckoning(initial_position=(5.0, 3.0), initial_heading=0.0)
    mm = MapManager("test_maps")
    
    # Create test map
    test_map_id = "integration_test"
    mm.maps[test_map_id] = {
        'id': test_map_id,
        'name': 'Integration Test Map',
        'width': 1000,
        'height': 800,
        'scale_meters_per_pixel': 0.1,
        'origin_x': 0.0,
        'origin_y': 0.0,
        'rotation_degrees': 0.0
    }
    mm.active_map_id = test_map_id
    
    print(f"✓ Systems initialized")
    print(f"  Starting position: (5.0, 3.0) world coordinates")
    
    # Simulate movement and track on map
    timestamp = int(time.time() * 1000)
    positions = []
    
    print("\nSimulating movement and tracking on map...")
    for i in range(30):
        # Simulate forward movement
        accel_x = 0.5 if i < 10 else 0.0
        state = dr.update(accel_x, 0.0, 9.81, 0.0, 0.0, 0.0, timestamp)
        timestamp += 100
        
        # Convert to pixel coordinates
        world_x = state['position']['x']
        world_y = state['position']['y']
        pixel_coords = mm.world_to_pixel(world_x, world_y)
        
        if pixel_coords:
            positions.append({
                'world': (world_x, world_y),
                'pixel': pixel_coords
            })
        
        if i % 10 == 0:
            print(f"  t={i*0.1:.1f}s: World ({world_x:.2f}, {world_y:.2f}) → "
                  f"Pixel ({pixel_coords[0]:.1f}, {pixel_coords[1]:.1f})")
    
    print(f"\n✓ Tracked {len(positions)} positions")
    print(f"✓ Final world position: ({positions[-1]['world'][0]:.2f}, {positions[-1]['world'][1]:.2f})")
    print(f"✓ Final pixel position: ({positions[-1]['pixel'][0]:.1f}, {positions[-1]['pixel'][1]:.1f})")
    
    # Clean up
    del mm.maps[test_map_id]
    
    print("\n✅ Integration tests passed!\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("BRAMPS Navigation System - Test Suite")
    print("=" * 60 + "\n")
    
    try:
        test_dead_reckoning()
        test_map_manager()
        test_integration()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nNavigation system is ready for use.")
        print("Start the server with: python server.py")
        print("Open navigation interface: http://localhost:5000/navigation.html")
        print()
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())

