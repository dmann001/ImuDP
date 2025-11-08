"""
World Magnetic Model (WMM2025) Implementation
============================================

This module implements the World Magnetic Model 2025 for calculating Earth's magnetic field
at any given location and time. It uses spherical harmonic coefficients from NOAA/NCEI.

Author: BRAMPS Navigation System
Date: 2024
"""

import numpy as np
import math
from datetime import datetime, timedelta
from typing import Tuple, Dict, Optional
import os


class WMM2025:
    """
    World Magnetic Model 2025 implementation.
    
    Calculates magnetic field components (X, Y, Z, H, F, D, I) for given
    coordinates and date using spherical harmonic expansion.
    """
    
    def __init__(self, coeff_file: str = "WMM2025COF/WMM2025.COF"):
        """
        Initialize WMM2025 model with coefficient file.
        
        Args:
            coeff_file: Path to WMM2025.COF coefficient file
        """
        self.coeff_file = coeff_file
        self.epoch = None
        self.model_name = None
        self.release_date = None
        self.coefficients = {}
        self.secular_variation = {}
        self.max_degree = 12  # WMM2025 uses degree 12
        
        # Earth parameters
        self.earth_radius = 6371.2  # km (WGS84 reference)
        self.earth_radius_m = 6371200.0  # meters
        
        # Load coefficients
        self._load_coefficients()
        
    def _load_coefficients(self):
        """Load spherical harmonic coefficients from WMM2025.COF file."""
        if not os.path.exists(self.coeff_file):
            raise FileNotFoundError(f"WMM coefficient file not found: {self.coeff_file}")
            
        print(f"Loading WMM2025 coefficients from {self.coeff_file}")
        
        with open(self.coeff_file, 'r') as f:
            lines = f.readlines()
            
        # Parse header
        header = lines[0].strip().split()
        self.epoch = float(header[0])
        self.model_name = header[1]
        self.release_date = header[2]
        
        print(f"Model: {self.model_name}, Epoch: {self.epoch}, Release: {self.release_date}")
        
        # Parse coefficients
        for line in lines[1:]:
            line = line.strip()
            if not line or line.startswith('999'):  # End marker
                break
                
            parts = line.split()
            if len(parts) >= 6:
                n = int(parts[0])  # degree
                m = int(parts[1])  # order
                gnm = float(parts[2])  # g coefficient
                hnm = float(parts[3])  # h coefficient
                dgnm = float(parts[4])  # secular variation dg/dt
                dhnm = float(parts[5])  # secular variation dh/dt
                
                # Store coefficients
                self.coefficients[(n, m)] = (gnm, hnm)
                self.secular_variation[(n, m)] = (dgnm, dhnm)
                
        print(f"Loaded {len(self.coefficients)} coefficient pairs")
        
    def _legendre_functions(self, theta: float, max_degree: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate Schmidt semi-normalized associated Legendre functions and derivatives.
        
        Args:
            theta: Colatitude in radians
            max_degree: Maximum degree to calculate
            
        Returns:
            Tuple of (P, dP) arrays where P[n][m] are Legendre functions 
            and dP[n][m] are their derivatives with respect to theta
        """
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        
        # Initialize arrays
        P = np.zeros((max_degree + 1, max_degree + 1))
        dP = np.zeros((max_degree + 1, max_degree + 1))
        
        # P_0^0 = 1, dP_0^0 = 0
        P[0][0] = 1.0
        dP[0][0] = 0.0
        
        # Calculate for n=1
        if max_degree >= 1:
            P[1][0] = cos_theta
            P[1][1] = sin_theta
            dP[1][0] = -sin_theta
            dP[1][1] = cos_theta
        
        # Calculate P_n^m and dP_n^m using recurrence relations
        for n in range(2, max_degree + 1):
            # P_n^0 (zonal harmonics)
            P[n][0] = ((2*n - 1) * cos_theta * P[n-1][0] - (n-1) * P[n-2][0]) / n
            dP[n][0] = ((2*n - 1) * (cos_theta * dP[n-1][0] - sin_theta * P[n-1][0]) - (n-1) * dP[n-2][0]) / n
            
            # P_n^n (sectoral harmonics)
            P[n][n] = (2*n - 1) * sin_theta * P[n-1][n-1]
            dP[n][n] = (2*n - 1) * (sin_theta * dP[n-1][n-1] + cos_theta * P[n-1][n-1])
            
            # P_n^m for 0 < m < n (tesseral harmonics)
            for m in range(1, n):
                P[n][m] = ((2*n - 1) * cos_theta * P[n-1][m] - (n + m - 1) * P[n-2][m]) / (n - m)
                dP[n][m] = ((2*n - 1) * (cos_theta * dP[n-1][m] - sin_theta * P[n-1][m]) - (n + m - 1) * dP[n-2][m]) / (n - m)
        
        return P, dP
        
    def _schmidt_normalization(self, n: int, m: int) -> float:
        """
        Calculate Schmidt semi-normalization factor.
        
        Args:
            n: Degree
            m: Order
            
        Returns:
            Schmidt normalization factor
        """
        if m == 0:
            return 1.0
        else:
            # Schmidt semi-normalization: sqrt(2 * (n-m)! / (n+m)!)
            factor = 1.0
            for i in range(n - m + 1, n + m + 1):
                factor *= i
            return math.sqrt(2.0 / factor)
            
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
            
        # Convert date to decimal year
        year = date.year
        day_of_year = date.timetuple().tm_yday
        days_in_year = 366 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 365
        decimal_year = year + (day_of_year - 1) / days_in_year
        
        # Time difference from epoch for secular variation
        dt = decimal_year - self.epoch
        
        # Convert coordinates
        lat_rad = math.radians(latitude)
        lon_rad = math.radians(longitude)
        theta = math.pi/2 - lat_rad  # Colatitude
        phi = lon_rad
        
        # Geocentric radius
        r = self.earth_radius_m + altitude  # meters
        a = self.earth_radius_m  # Earth radius in meters
        
        # Calculate Schmidt semi-normalized Legendre functions and derivatives
        P, dP = self._legendre_functions(theta, self.max_degree)
        
        # Initialize field components
        Br = 0.0  # Radial component
        Bt = 0.0  # Theta component (colatitude)
        Bp = 0.0  # Phi component (longitude)
        
        # Sum over all degrees and orders
        for n in range(1, self.max_degree + 1):
            # Radial distance factor
            r_factor = (a / r) ** (n + 2)
            
            for m in range(0, n + 1):
                if (n, m) not in self.coefficients:
                    continue
                    
                # Get coefficients with secular variation
                gnm, hnm = self.coefficients[(n, m)]
                dgnm, dhnm = self.secular_variation[(n, m)]
                
                # Apply secular variation
                gnm_t = gnm + dgnm * dt
                hnm_t = hnm + dhnm * dt
                
                # Schmidt normalization factor
                schmidt = self._schmidt_normalization(n, m)
                
                # Trigonometric terms
                cos_mphi = math.cos(m * phi)
                sin_mphi = math.sin(m * phi)
                
                # Schmidt normalized Legendre functions
                Pnm = P[n][m] * schmidt
                dPnm = dP[n][m] * schmidt
                
                # Accumulate field components
                # Radial component
                Br += (n + 1) * r_factor * (gnm_t * cos_mphi + hnm_t * sin_mphi) * Pnm
                
                # Theta component (colatitude)
                Bt -= r_factor * (gnm_t * cos_mphi + hnm_t * sin_mphi) * dPnm
                
                # Phi component (longitude)
                if math.sin(theta) != 0:  # Avoid division by zero at poles
                    Bp -= r_factor * m * (-gnm_t * sin_mphi + hnm_t * cos_mphi) * Pnm / math.sin(theta)
        
        # Convert to geodetic coordinates (X=North, Y=East, Z=Down)
        X = -Bt  # North component
        Y = Bp   # East component  
        Z = Br   # Down component (positive downward)
        
        # Calculate derived quantities
        H = math.sqrt(X*X + Y*Y)  # Horizontal intensity
        F = math.sqrt(X*X + Y*Y + Z*Z)  # Total intensity
        
        # Declination (magnetic declination from true north)
        D = math.degrees(math.atan2(Y, X))
        
        # Inclination (dip angle)
        I = math.degrees(math.atan2(Z, H))
        
        return {
            'X': X,  # North component (nT)
            'Y': Y,  # East component (nT)
            'Z': Z,  # Down component (nT)
            'H': H,  # Horizontal intensity (nT)
            'F': F,  # Total intensity (nT)
            'D': D,  # Declination (degrees)
            'I': I   # Inclination (degrees)
        }
        
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
        tolerance = 0.1  # nT for field components, 0.01 degrees for angles
        
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
                max_error = max(errors['X'], errors['Y'], errors['Z'], errors['H'], errors['F'])
                angle_error = max(errors['D'], errors['I'])
                
                if max_error < tolerance and angle_error < 0.01:
                    passed += 1
                    print(f"✓ Test passed: lat={latitude:6.1f}, lon={longitude:7.1f}, alt={altitude_km:3.0f}km")
                else:
                    failed += 1
                    print(f"✗ Test failed: lat={latitude:6.1f}, lon={longitude:7.1f}, alt={altitude_km:3.0f}km")
                    print(f"  Max field error: {max_error:.2f} nT, Angle error: {angle_error:.3f}°")
                    
            except (ValueError, IndexError) as e:
                print(f"Error parsing test line: {line[:50]}... - {e}")
                continue
                
        print(f"\nValidation Results: {passed} passed, {failed} failed")
        return failed == 0


def main():
    """Test the WMM2025 implementation."""
    print("WMM2025 Magnetic Model Test")
    print("=" * 40)
    
    try:
        # Initialize model
        wmm = WMM2025()
        
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
            print("\n✅ WMM2025 implementation validation PASSED!")
        else:
            print("\n❌ WMM2025 implementation validation FAILED!")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
