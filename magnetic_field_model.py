"""
Magnetic Field Model for BRAMPS Navigation System
===============================================

This module provides magnetic field calculations using the World Magnetic Model (WMM2025)
for the BRAMPS navigation system. It serves as the foundation for magnetic fingerprinting
and heading correction in the dead-reckoning algorithm.

Author: BRAMPS Navigation System
Date: 2024
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import os
import logging

try:
    from wmm import wmm_calc
    WMM_AVAILABLE = True
except ImportError:
    WMM_AVAILABLE = False
    logging.warning("wmm-calculator library not available. Install with: pip install wmm-calculator")


class MagneticFieldModel:
    """
    Magnetic field model for BRAMPS navigation system.
    
    Provides:
    - WMM2025 baseline magnetic field calculations
    - Magnetic field component extraction (X, Y, Z, H, F, D, I)
    - Integration with sensor fusion algorithms
    - Validation against NASA test values
    """
    
    def __init__(self):
        """Initialize magnetic field model."""
        if not WMM_AVAILABLE:
            raise ImportError("wmm-calculator library is required. Install with: pip install wmm-calculator")
        
        self.model = wmm_calc()
        self.logger = logging.getLogger(__name__)
        
        # Cache for performance
        self._cache = {}
        self._cache_max_size = 100
        
        self.logger.info("Magnetic Field Model initialized with WMM2025")
        
    def get_magnetic_field(self, 
                          latitude: float, 
                          longitude: float, 
                          altitude: float = 0.0, 
                          date: Optional[datetime] = None) -> Dict[str, float]:
        """
        Get magnetic field components at specified location and time.
        
        Args:
            latitude: Geodetic latitude in degrees (-90 to +90)
            longitude: Longitude in degrees (-180 to +180)
            altitude: Height above WGS84 ellipsoid in meters (default: 0)
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
            
        Raises:
            ValueError: If coordinates are out of valid range
            RuntimeError: If WMM calculation fails
        """
        # Validate inputs
        if not (-90 <= latitude <= 90):
            raise ValueError(f"Latitude must be between -90 and 90 degrees, got {latitude}")
        if not (-180 <= longitude <= 180):
            raise ValueError(f"Longitude must be between -180 and 180 degrees, got {longitude}")
        if altitude < -1000 or altitude > 1000000:  # -1km to 1000km
            raise ValueError(f"Altitude must be between -1000 and 1000000 meters, got {altitude}")
            
        if date is None:
            date = datetime.now()
            
        # Check cache
        cache_key = (round(latitude, 4), round(longitude, 4), round(altitude, 0), 
                    date.year, date.month, date.day)
        if cache_key in self._cache:
            return self._cache[cache_key].copy()
            
        # Convert altitude from meters to kilometers
        altitude_km = altitude / 1000.0
        
        try:
            # Setup time and environment for calculation
            self.model.setup_time(date.year, date.month, date.day)
            self.model.setup_env(latitude, longitude, altitude_km, unit='km')
            
            # Calculate magnetic field components
            self.model.forward_base()
            
            # Get all magnetic field components
            result = self.model.get_all()
            
            # Extract and format results
            magnetic_field = {
                'X': float(result['x'][0]),      # North component (nT)
                'Y': float(result['y'][0]),      # East component (nT)
                'Z': float(result['z'][0]),      # Down component (nT)
                'H': float(result['h'][0]),      # Horizontal intensity (nT)
                'F': float(result['f'][0]),      # Total intensity (nT)
                'D': float(result['dec'][0]),    # Declination (degrees)
                'I': float(result['inc'][0])     # Inclination (degrees)
            }
            
            # Cache result
            if len(self._cache) >= self._cache_max_size:
                # Remove oldest entry
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[cache_key] = magnetic_field.copy()
            
            return magnetic_field
            
        except Exception as e:
            self.logger.error(f"WMM calculation failed for lat={latitude}, lon={longitude}, alt={altitude}: {e}")
            raise RuntimeError(f"Magnetic field calculation failed: {e}")
            
    def get_magnetic_vector(self, 
                           latitude: float, 
                           longitude: float, 
                           altitude: float = 0.0, 
                           date: Optional[datetime] = None) -> Tuple[float, float, float]:
        """
        Get magnetic field vector components (X, Y, Z) for sensor fusion.
        
        Args:
            latitude: Geodetic latitude in degrees
            longitude: Longitude in degrees
            altitude: Height above WGS84 ellipsoid in meters
            date: Date for calculation
            
        Returns:
            Tuple of (X, Y, Z) magnetic field components in nanoTesla
        """
        field = self.get_magnetic_field(latitude, longitude, altitude, date)
        return (field['X'], field['Y'], field['Z'])
        
    def get_magnetic_heading(self, 
                           latitude: float, 
                           longitude: float, 
                           altitude: float = 0.0, 
                           date: Optional[datetime] = None) -> float:
        """
        Get magnetic declination for heading correction.
        
        Args:
            latitude: Geodetic latitude in degrees
            longitude: Longitude in degrees
            altitude: Height above WGS84 ellipsoid in meters
            date: Date for calculation
            
        Returns:
            Magnetic declination in degrees (positive = east of true north)
        """
        field = self.get_magnetic_field(latitude, longitude, altitude, date)
        return field['D']
        
    def calculate_field_difference(self, 
                                 measured_field: Tuple[float, float, float],
                                 latitude: float, 
                                 longitude: float, 
                                 altitude: float = 0.0, 
                                 date: Optional[datetime] = None) -> Tuple[float, float, float]:
        """
        Calculate difference between measured and expected magnetic field.
        
        This is useful for magnetic anomaly detection and position correction.
        
        Args:
            measured_field: Measured magnetic field (X, Y, Z) in nT
            latitude: Expected latitude in degrees
            longitude: Expected longitude in degrees
            altitude: Expected altitude in meters
            date: Date for calculation
            
        Returns:
            Tuple of (dX, dY, dZ) field differences in nanoTesla
        """
        expected_field = self.get_magnetic_vector(latitude, longitude, altitude, date)
        
        return (
            measured_field[0] - expected_field[0],  # dX
            measured_field[1] - expected_field[1],  # dY
            measured_field[2] - expected_field[2]   # dZ
        )
        
    def validate_model(self, test_file: str = "WMM2025COF/WMM2025_TestValues.txt") -> bool:
        """
        Validate magnetic field model against NASA test values.
        
        Args:
            test_file: Path to NASA test values file
            
        Returns:
            True if validation passes (>95% success rate)
        """
        if not os.path.exists(test_file):
            self.logger.warning(f"Test file not found: {test_file}")
            return False
            
        self.logger.info(f"Validating magnetic field model against {test_file}")
        
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
                
                if day_of_year > days_in_year:
                    day_of_year = days_in_year
                    
                test_date = datetime(year, 1, 1) + timedelta(days=day_of_year - 1)
                
                # Calculate our values
                result = self.get_magnetic_field(latitude, longitude, altitude_m, test_date)
                
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
                else:
                    failed += 1
                    if failed <= 3:  # Log details for first few failures
                        self.logger.warning(f"Validation failed: lat={latitude:.1f}, lon={longitude:.1f}, "
                                          f"field_error={max_field_error:.2f}nT, angle_error={max_angle_error:.3f}°")
                    
            except Exception as e:
                self.logger.error(f"Error in validation: {e}")
                failed += 1
                continue
                
        success_rate = passed / (passed + failed) * 100 if (passed + failed) > 0 else 0
        self.logger.info(f"Validation results: {passed} passed, {failed} failed ({success_rate:.1f}% success)")
        
        return success_rate >= 95.0
        
    def clear_cache(self):
        """Clear the magnetic field calculation cache."""
        self._cache.clear()
        self.logger.info("Magnetic field cache cleared")


# Global instance for easy access
_magnetic_model = None

def get_magnetic_model() -> MagneticFieldModel:
    """Get global magnetic field model instance."""
    global _magnetic_model
    if _magnetic_model is None:
        _magnetic_model = MagneticFieldModel()
    return _magnetic_model


def calculate_magnetic_field(latitude: float, 
                           longitude: float, 
                           altitude: float = 0.0, 
                           date: Optional[datetime] = None) -> Dict[str, float]:
    """
    Convenience function to calculate magnetic field at given location.
    
    Args:
        latitude: Geodetic latitude in degrees
        longitude: Longitude in degrees
        altitude: Height above WGS84 ellipsoid in meters
        date: Date for calculation
        
    Returns:
        Dictionary with magnetic field components
    """
    model = get_magnetic_model()
    return model.get_magnetic_field(latitude, longitude, altitude, date)


def main():
    """Test the magnetic field model."""
    print("BRAMPS Magnetic Field Model Test")
    print("=" * 40)
    
    try:
        # Initialize model
        model = MagneticFieldModel()
        
        # Test calculation for Toronto, Canada
        print("\nTest calculation for Toronto, Canada:")
        result = model.get_magnetic_field(43.6532, -79.3832, 100.0)
        
        print(f"Latitude: 43.6532°N, Longitude: 79.3832°W, Altitude: 100m")
        print(f"X (North): {result['X']:.1f} nT")
        print(f"Y (East):  {result['Y']:.1f} nT") 
        print(f"Z (Down):  {result['Z']:.1f} nT")
        print(f"H (Horizontal): {result['H']:.1f} nT")
        print(f"F (Total): {result['F']:.1f} nT")
        print(f"D (Declination): {result['D']:.2f}°")
        print(f"I (Inclination): {result['I']:.2f}°")
        
        # Test convenience functions
        print("\nTesting convenience functions:")
        vector = model.get_magnetic_vector(43.6532, -79.3832, 100.0)
        declination = model.get_magnetic_heading(43.6532, -79.3832, 100.0)
        print(f"Magnetic vector: ({vector[0]:.1f}, {vector[1]:.1f}, {vector[2]:.1f}) nT")
        print(f"Magnetic declination: {declination:.2f}°")
        
        # Validate model
        print("\n" + "=" * 40)
        print("Validating model against NASA test values...")
        validation_passed = model.validate_model()
        
        if validation_passed:
            print("✅ Magnetic field model validation PASSED!")
        else:
            print("❌ Magnetic field model validation FAILED!")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
