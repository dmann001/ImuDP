"""
World Magnetic Model (WMM2025) Implementation using wmm-calculator library
========================================================================

This module provides a simple interface to the World Magnetic Model 2025
using the wmm-calculator Python library for reliable magnetic field calculations.

Author: BRAMPS Navigation System
Date: 2024
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional
import os

try:
    from wmm import wmm_calc
    WMM_AVAILABLE = True
except ImportError:
    WMM_AVAILABLE = False
    print("Warning: wmm-calculator library not available. Install with: pip install wmm-calculator")


class WMM2025Simple:
    """
    Simplified World Magnetic Model 2025 implementation using wmm-calculator library.
    
    This provides a reliable interface to WMM2025 calculations with validation
    against NASA test values.
    """
    
    def __init__(self):
        """Initialize WMM2025 model."""
        if not WMM_AVAILABLE:
            raise ImportError("wmm-calculator library is required. Install with: pip install wmm-calculator")
        
        self.model = wmm_calc()
        print("WMM2025 Simple model initialized using wmm-calculator library")
        
    def calculate_magnetic_field(self, 
                               latitude: float, 
                               longitude: float, 
                               altitude: float, 
                               date: Optional[datetime] = None) -> Dict[str, float]:
        """
        Calculate magnetic field components at given location and time.
        
        Args:
            latitude: Geodetic latitude in degrees (-90 to +90)
            longitude: Longitude in degrees (-180 to +180)
            altitude: Height above WGS84 ellipsoid in meters
            date: Date for calculation (default: current date)
            
        Returns:
            Dictionary with magnetic field components:
            - X: North component (nT)
            - Y: East component (nT) 
            - Z: Down component (nT)
            - H: Horizontal intensity (nT)
            - F: Total intensity (nT)
            - D: Declination (degrees)
            - I: Inclination (degrees)
        """
        if date is None:
            date = datetime.now()
            
        # Convert altitude from meters to kilometers
        altitude_km = altitude / 1000.0
        
        try:
            # Setup time for calculation (year, month, day)
            self.model.setup_time(date.year, date.month, date.day)
            
            # Setup environment for calculation (altitude in km with unit specified)
            self.model.setup_env(latitude, longitude, altitude_km, unit='km')
            
            # Calculate magnetic field components
            self.model.forward_base()
            
            # Get all magnetic field components
            result = self.model.get_all()
            
            return {
                'X': float(result['x'][0]),  # North component (nT)
                'Y': float(result['y'][0]),  # East component (nT)
                'Z': float(result['z'][0]),  # Down component (nT)
                'H': float(result['h'][0]),  # Horizontal intensity (nT)
                'F': float(result['f'][0]),  # Total intensity (nT)
                'D': float(result['dec'][0]),  # Declination (degrees)
                'I': float(result['inc'][0])   # Inclination (degrees)
            }
        except Exception as e:
            raise RuntimeError(f"WMM calculation failed: {e}")
            
    def validate_against_test_values(self, test_file: str = "WMM2025COF/WMM2025_TestValues.txt") -> bool:
        """
        Validate implementation against NASA test values.
        
        Args:
            test_file: Path to test values file
            
        Returns:
            True if validation passes, False otherwise
        """
        if not os.path.exists(test_file):
            print(f"Test file not found: {test_file}")
            return False
            
        print(f"Validating against test values in {test_file}")
        
        with open(test_file, 'r') as f:
            lines = f.readlines()
            
        passed = 0
        failed = 0
        tolerance_field = 1.0  # nT for field components
        tolerance_angle = 0.1  # degrees for angles
        
        for line in lines:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
                
            parts = line.split()
            if len(parts) < 18:
                continue
                
            try:
                # Parse test values
                decimal_year = float(parts[0])
                altitude_km = float(parts[1])
                latitude = float(parts[2])
                longitude = float(parts[3])
                expected_D = float(parts[4])
                expected_I = float(parts[5])
                expected_H = float(parts[6])
                expected_X = float(parts[7])
                expected_Y = float(parts[8])
                expected_Z = float(parts[9])
                expected_F = float(parts[10])
                
                # Convert to our format
                altitude_m = altitude_km * 1000
                
                # Create date from decimal year
                year = int(decimal_year)
                day_fraction = decimal_year - year
                days_in_year = 366 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 365
                day_of_year = int(day_fraction * days_in_year) + 1
                
                # Handle edge case where day_of_year might exceed days in year
                if day_of_year > days_in_year:
                    day_of_year = days_in_year
                    
                # Create date using timedelta to avoid day-of-year issues
                test_date = datetime(year, 1, 1) + timedelta(days=day_of_year - 1)
                
                # Calculate our values
                result = self.calculate_magnetic_field(latitude, longitude, altitude_m, test_date)
                
                # Compare results
                errors = {
                    'X': abs(result['X'] - expected_X),
                    'Y': abs(result['Y'] - expected_Y),
                    'Z': abs(result['Z'] - expected_Z),
                    'H': abs(result['H'] - expected_H),
                    'F': abs(result['F'] - expected_F),
                    'D': abs(result['D'] - expected_D),
                    'I': abs(result['I'] - expected_I)
                }
                
                # Check tolerances
                max_field_error = max(errors['X'], errors['Y'], errors['Z'], errors['H'], errors['F'])
                max_angle_error = max(errors['D'], errors['I'])
                
                if max_field_error < tolerance_field and max_angle_error < tolerance_angle:
                    passed += 1
                    print(f"✓ Test passed: lat={latitude:6.1f}, lon={longitude:7.1f}, alt={altitude_km:3.0f}km")
                else:
                    failed += 1
                    print(f"✗ Test failed: lat={latitude:6.1f}, lon={longitude:7.1f}, alt={altitude_km:3.0f}km")
                    print(f"  Max field error: {max_field_error:.2f} nT, Max angle error: {max_angle_error:.3f}°")
                    if failed <= 3:  # Show details for first few failures
                        print(f"  Expected: X={expected_X:.1f}, Y={expected_Y:.1f}, Z={expected_Z:.1f}")
                        print(f"  Got:      X={result['X']:.1f}, Y={result['Y']:.1f}, Z={result['Z']:.1f}")
                    
            except (ValueError, IndexError) as e:
                print(f"Error parsing test line: {line[:50]}... - {e}")
                continue
            except Exception as e:
                print(f"Calculation error for line: {line[:50]}... - {e}")
                failed += 1
                continue
                
        print(f"\nValidation Results: {passed} passed, {failed} failed")
        success_rate = passed / (passed + failed) * 100 if (passed + failed) > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        return success_rate >= 95.0  # Accept 95% success rate


def main():
    """Test the WMM2025 simple implementation."""
    print("WMM2025 Simple Magnetic Model Test")
    print("=" * 40)
    
    try:
        # Initialize model
        wmm = WMM2025Simple()
        
        # Test calculation for a known location
        print("\nTest calculation for Toronto, Canada:")
        result = wmm.calculate_magnetic_field(43.6532, -79.3832, 100.0)  # Toronto
        
        print(f"Latitude: 43.6532°N, Longitude: 79.3832°W, Altitude: 100m")
        print(f"X (North): {result['X']:.1f} nT")
        print(f"Y (East):  {result['Y']:.1f} nT") 
        print(f"Z (Down):  {result['Z']:.1f} nT")
        print(f"H (Horizontal): {result['H']:.1f} nT")
        print(f"F (Total): {result['F']:.1f} nT")
        print(f"D (Declination): {result['D']:.2f}°")
        print(f"I (Inclination): {result['I']:.2f}°")
        
        # Validate against test values
        print("\n" + "=" * 40)
        print("Validating against NASA test values...")
        validation_passed = wmm.validate_against_test_values()
        
        if validation_passed:
            print("\n✅ WMM2025 simple implementation validation PASSED!")
        else:
            print("\n⚠️  WMM2025 simple implementation validation had some failures but may still be usable")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
