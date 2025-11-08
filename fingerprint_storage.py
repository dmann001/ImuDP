"""
Magnetic Fingerprint Storage System for BRAMPS Navigation
========================================================

This module provides persistent storage and retrieval of magnetic fingerprints
for the BRAMPS navigation system. It handles spatial indexing, quality scoring,
and efficient lookup of magnetic field measurements.

Author: BRAMPS Navigation System
Date: 2024
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Union
import os
import logging
from pathlib import Path
import json
import math
from scipy.spatial import cKDTree
from magnetic_field_model import MagneticFieldModel


class MagneticFingerprint:
    """
    Represents a single magnetic fingerprint measurement.
    """
    
    def __init__(self, 
                 timestamp: datetime,
                 latitude: float,
                 longitude: float,
                 altitude: float,
                 mag_x: float,
                 mag_y: float,
                 mag_z: float,
                 quality_score: float = 1.0,
                 device_id: str = "unknown",
                 session_id: str = "default"):
        """
        Initialize a magnetic fingerprint.
        
        Args:
            timestamp: When the measurement was taken
            latitude: GPS latitude in degrees
            longitude: GPS longitude in degrees  
            altitude: Altitude in meters above WGS84
            mag_x: Magnetic field X component (North) in nT
            mag_y: Magnetic field Y component (East) in nT
            mag_z: Magnetic field Z component (Down) in nT
            quality_score: Quality score 0-1 (1 = best quality)
            device_id: Identifier for the measuring device
            session_id: Identifier for the mapping session
        """
        self.timestamp = timestamp
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude
        self.mag_x = mag_x
        self.mag_y = mag_y
        self.mag_z = mag_z
        self.quality_score = quality_score
        self.device_id = device_id
        self.session_id = session_id
        
        # Derived properties
        self.mag_total = math.sqrt(mag_x**2 + mag_y**2 + mag_z**2)
        
    def to_dict(self) -> Dict:
        """Convert fingerprint to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude': self.altitude,
            'mag_x': self.mag_x,
            'mag_y': self.mag_y,
            'mag_z': self.mag_z,
            'mag_total': self.mag_total,
            'quality_score': self.quality_score,
            'device_id': self.device_id,
            'session_id': self.session_id
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'MagneticFingerprint':
        """Create fingerprint from dictionary."""
        timestamp = datetime.fromisoformat(data['timestamp'])
        return cls(
            timestamp=timestamp,
            latitude=data['latitude'],
            longitude=data['longitude'],
            altitude=data['altitude'],
            mag_x=data['mag_x'],
            mag_y=data['mag_y'],
            mag_z=data['mag_z'],
            quality_score=data.get('quality_score', 1.0),
            device_id=data.get('device_id', 'unknown'),
            session_id=data.get('session_id', 'default')
        )


class FingerprintStorage:
    """
    Manages storage and retrieval of magnetic fingerprints.
    
    Features:
    - CSV-based persistent storage
    - Spatial indexing for fast lookup
    - Quality scoring and filtering
    - Data validation and cleaning
    - Session management
    """
    
    def __init__(self, storage_dir: str = "fingerprint_data"):
        """
        Initialize fingerprint storage system.
        
        Args:
            storage_dir: Directory to store fingerprint data files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        self.csv_file = self.storage_dir / "magnetic_fingerprints.csv"
        self.metadata_file = self.storage_dir / "metadata.json"
        
        self.logger = logging.getLogger(__name__)
        
        # In-memory data for fast access
        self.fingerprints: List[MagneticFingerprint] = []
        self.spatial_index: Optional[cKDTree] = None
        self.coordinates: Optional[np.ndarray] = None
        
        # Magnetic field model for validation
        self.wmm_model = MagneticFieldModel()
        
        # Load existing data
        self._load_data()
        
        self.logger.info(f"Fingerprint storage initialized with {len(self.fingerprints)} fingerprints")
        
    def add_fingerprint(self, fingerprint: MagneticFingerprint) -> bool:
        """
        Add a new magnetic fingerprint to storage.
        
        Args:
            fingerprint: The fingerprint to add
            
        Returns:
            True if fingerprint was added, False if rejected due to quality
        """
        # Validate fingerprint
        if not self._validate_fingerprint(fingerprint):
            self.logger.warning(f"Fingerprint validation failed: {fingerprint.to_dict()}")
            return False
            
        # Calculate quality score
        fingerprint.quality_score = self._calculate_quality_score(fingerprint)
        
        # Add to memory
        self.fingerprints.append(fingerprint)
        
        # Rebuild spatial index
        self._rebuild_spatial_index()
        
        # Save to disk periodically (every 10 fingerprints)
        if len(self.fingerprints) % 10 == 0:
            self.save_to_disk()
            
        self.logger.debug(f"Added fingerprint: lat={fingerprint.latitude:.4f}, "
                         f"lon={fingerprint.longitude:.4f}, quality={fingerprint.quality_score:.2f}")
        
        return True
        
    def add_fingerprints_batch(self, fingerprints: List[MagneticFingerprint]) -> int:
        """
        Add multiple fingerprints in batch for efficiency.
        
        Args:
            fingerprints: List of fingerprints to add
            
        Returns:
            Number of fingerprints successfully added
        """
        added_count = 0
        
        for fingerprint in fingerprints:
            if self.add_fingerprint(fingerprint):
                added_count += 1
                
        # Save after batch operation
        self.save_to_disk()
        
        self.logger.info(f"Batch added {added_count}/{len(fingerprints)} fingerprints")
        return added_count
        
    def find_nearest_fingerprints(self, 
                                 latitude: float, 
                                 longitude: float, 
                                 max_distance: float = 100.0,
                                 max_count: int = 10) -> List[Tuple[MagneticFingerprint, float]]:
        """
        Find nearest magnetic fingerprints to a given location.
        
        Args:
            latitude: Target latitude in degrees
            longitude: Target longitude in degrees
            max_distance: Maximum distance in meters
            max_count: Maximum number of fingerprints to return
            
        Returns:
            List of (fingerprint, distance) tuples sorted by distance
        """
        if self.spatial_index is None or len(self.fingerprints) == 0:
            return []
            
        # Convert to approximate meters (rough approximation)
        target_point = np.array([latitude, longitude])
        
        # Find nearest neighbors
        distances, indices = self.spatial_index.query(
            target_point, 
            k=min(max_count, len(self.fingerprints))
        )
        
        # Convert distances to meters (rough approximation)
        # 1 degree ≈ 111,000 meters
        if np.isscalar(distances):
            distances = [distances]
            indices = [indices]
            
        results = []
        for dist, idx in zip(distances, indices):
            if idx < len(self.fingerprints):
                fingerprint = self.fingerprints[idx]
                distance_meters = dist * 111000  # Rough conversion
                
                if distance_meters <= max_distance:
                    results.append((fingerprint, distance_meters))
                    
        return results
        
    def get_interpolated_field(self, 
                              latitude: float, 
                              longitude: float, 
                              altitude: float = 0.0) -> Optional[Tuple[float, float, float]]:
        """
        Get interpolated magnetic field at a location using nearby fingerprints.
        
        Args:
            latitude: Target latitude in degrees
            longitude: Target longitude in degrees
            altitude: Target altitude in meters
            
        Returns:
            Tuple of (mag_x, mag_y, mag_z) or None if no nearby fingerprints
        """
        nearby = self.find_nearest_fingerprints(latitude, longitude, max_distance=200.0, max_count=5)
        
        if len(nearby) == 0:
            return None
            
        # Inverse distance weighting
        total_weight = 0.0
        weighted_x = 0.0
        weighted_y = 0.0
        weighted_z = 0.0
        
        for fingerprint, distance in nearby:
            # Avoid division by zero
            weight = 1.0 / max(distance, 1.0)  # Minimum 1 meter
            weight *= fingerprint.quality_score  # Factor in quality
            
            weighted_x += fingerprint.mag_x * weight
            weighted_y += fingerprint.mag_y * weight
            weighted_z += fingerprint.mag_z * weight
            total_weight += weight
            
        if total_weight > 0:
            return (
                weighted_x / total_weight,
                weighted_y / total_weight,
                weighted_z / total_weight
            )
            
        return None
        
    def get_field_anomaly(self, 
                         latitude: float, 
                         longitude: float, 
                         altitude: float = 0.0,
                         date: Optional[datetime] = None) -> Optional[Tuple[float, float, float]]:
        """
        Calculate magnetic field anomaly at a location.
        
        Anomaly = Measured field (from fingerprints) - WMM expected field
        
        Args:
            latitude: Target latitude in degrees
            longitude: Target longitude in degrees
            altitude: Target altitude in meters
            date: Date for WMM calculation
            
        Returns:
            Tuple of (anomaly_x, anomaly_y, anomaly_z) or None if no data
        """
        # Get interpolated measured field
        measured_field = self.get_interpolated_field(latitude, longitude, altitude)
        if measured_field is None:
            return None
            
        # Get WMM expected field
        wmm_field = self.wmm_model.get_magnetic_vector(latitude, longitude, altitude, date)
        
        # Calculate anomaly
        return (
            measured_field[0] - wmm_field[0],  # X anomaly
            measured_field[1] - wmm_field[1],  # Y anomaly
            measured_field[2] - wmm_field[2]   # Z anomaly
        )
        
    def save_to_disk(self):
        """Save all fingerprints to CSV file."""
        if len(self.fingerprints) == 0:
            return
            
        # Convert to DataFrame
        data = [fp.to_dict() for fp in self.fingerprints]
        df = pd.DataFrame(data)
        
        # Save to CSV
        df.to_csv(self.csv_file, index=False)
        
        # Save metadata
        metadata = {
            'total_fingerprints': len(self.fingerprints),
            'last_updated': datetime.now().isoformat(),
            'sessions': list(set(fp.session_id for fp in self.fingerprints)),
            'devices': list(set(fp.device_id for fp in self.fingerprints))
        }
        
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
            
        self.logger.info(f"Saved {len(self.fingerprints)} fingerprints to {self.csv_file}")
        
    def _load_data(self):
        """Load fingerprints from CSV file."""
        if not self.csv_file.exists():
            self.logger.info("No existing fingerprint data found")
            return
            
        try:
            df = pd.read_csv(self.csv_file)
            self.fingerprints = []
            
            for _, row in df.iterrows():
                fingerprint = MagneticFingerprint.from_dict(row.to_dict())
                self.fingerprints.append(fingerprint)
                
            self._rebuild_spatial_index()
            self.logger.info(f"Loaded {len(self.fingerprints)} fingerprints from {self.csv_file}")
            
        except Exception as e:
            self.logger.error(f"Error loading fingerprint data: {e}")
            self.fingerprints = []
            
    def _rebuild_spatial_index(self):
        """Rebuild spatial index for fast nearest neighbor queries."""
        if len(self.fingerprints) == 0:
            self.spatial_index = None
            self.coordinates = None
            return
            
        # Extract coordinates
        self.coordinates = np.array([
            [fp.latitude, fp.longitude] for fp in self.fingerprints
        ])
        
        # Build spatial index
        self.spatial_index = cKDTree(self.coordinates)
        
    def _validate_fingerprint(self, fingerprint: MagneticFingerprint) -> bool:
        """
        Validate a fingerprint for basic sanity checks.
        
        Args:
            fingerprint: Fingerprint to validate
            
        Returns:
            True if fingerprint is valid
        """
        # Check coordinate ranges
        if not (-90 <= fingerprint.latitude <= 90):
            return False
        if not (-180 <= fingerprint.longitude <= 180):
            return False
        if not (-1000 <= fingerprint.altitude <= 100000):  # -1km to 100km
            return False
            
        # Check magnetic field magnitude (Earth's field is ~25,000-65,000 nT)
        if not (10000 <= fingerprint.mag_total <= 100000):
            return False
            
        return True
        
    def _calculate_quality_score(self, fingerprint: MagneticFingerprint) -> float:
        """
        Calculate quality score for a fingerprint based on various factors.
        
        Args:
            fingerprint: Fingerprint to score
            
        Returns:
            Quality score between 0 and 1 (1 = best quality)
        """
        score = 1.0
        
        try:
            # Compare with WMM expected field
            wmm_field = self.wmm_model.get_magnetic_vector(
                fingerprint.latitude, 
                fingerprint.longitude, 
                fingerprint.altitude,
                fingerprint.timestamp
            )
            
            # Calculate difference from expected field
            diff_x = abs(fingerprint.mag_x - wmm_field[0])
            diff_y = abs(fingerprint.mag_y - wmm_field[1])
            diff_z = abs(fingerprint.mag_z - wmm_field[2])
            max_diff = max(diff_x, diff_y, diff_z)
            
            # Penalize large deviations from WMM (but allow for local anomalies)
            if max_diff > 10000:  # Very large deviation (>10,000 nT)
                score *= 0.1
            elif max_diff > 5000:  # Large deviation (>5,000 nT)
                score *= 0.5
            elif max_diff > 2000:  # Moderate deviation (>2,000 nT)
                score *= 0.8
                
        except Exception as e:
            self.logger.warning(f"Error calculating quality score: {e}")
            score *= 0.5  # Penalize if we can't validate
            
        return max(0.0, min(1.0, score))
        
    def get_statistics(self) -> Dict:
        """Get storage statistics."""
        if len(self.fingerprints) == 0:
            return {'total_fingerprints': 0}
            
        quality_scores = [fp.quality_score for fp in self.fingerprints]
        
        return {
            'total_fingerprints': len(self.fingerprints),
            'sessions': len(set(fp.session_id for fp in self.fingerprints)),
            'devices': len(set(fp.device_id for fp in self.fingerprints)),
            'quality_stats': {
                'mean': np.mean(quality_scores),
                'min': np.min(quality_scores),
                'max': np.max(quality_scores),
                'std': np.std(quality_scores)
            },
            'date_range': {
                'earliest': min(fp.timestamp for fp in self.fingerprints).isoformat(),
                'latest': max(fp.timestamp for fp in self.fingerprints).isoformat()
            }
        }
        
    def clear_data(self, confirm: bool = False):
        """Clear all fingerprint data (use with caution)."""
        if not confirm:
            raise ValueError("Must set confirm=True to clear data")
            
        self.fingerprints.clear()
        self.spatial_index = None
        self.coordinates = None
        
        # Remove files
        if self.csv_file.exists():
            self.csv_file.unlink()
        if self.metadata_file.exists():
            self.metadata_file.unlink()
            
        self.logger.warning("All fingerprint data cleared")


def main():
    """Test the fingerprint storage system."""
    print("BRAMPS Magnetic Fingerprint Storage Test")
    print("=" * 45)
    
    # Initialize storage
    storage = FingerprintStorage("test_fingerprints")
    
    # Create test fingerprints
    print("\nCreating test fingerprints...")
    test_fingerprints = []
    
    # Toronto area test points
    base_lat, base_lon = 43.6532, -79.3832
    
    for i in range(10):
        # Vary position slightly
        lat = base_lat + (i - 5) * 0.001  # ±0.005 degrees
        lon = base_lon + (i - 5) * 0.001
        
        # Create fingerprint with some test data
        fp = MagneticFingerprint(
            timestamp=datetime.now(),
            latitude=lat,
            longitude=lon,
            altitude=100.0,
            mag_x=18000 + i * 100,  # Vary magnetic field
            mag_y=-3000 - i * 50,
            mag_z=49000 + i * 200,
            session_id=f"test_session_{i//5}",
            device_id="test_device"
        )
        test_fingerprints.append(fp)
        
    # Add fingerprints
    added = storage.add_fingerprints_batch(test_fingerprints)
    print(f"Added {added} test fingerprints")
    
    # Test nearest neighbor search
    print(f"\nTesting nearest neighbor search...")
    nearest = storage.find_nearest_fingerprints(base_lat, base_lon, max_distance=500.0)
    print(f"Found {len(nearest)} nearby fingerprints:")
    for fp, distance in nearest[:3]:
        print(f"  Distance: {distance:.1f}m, Quality: {fp.quality_score:.2f}")
        
    # Test interpolation
    print(f"\nTesting field interpolation...")
    interpolated = storage.get_interpolated_field(base_lat, base_lon, 100.0)
    if interpolated:
        print(f"Interpolated field: X={interpolated[0]:.1f}, Y={interpolated[1]:.1f}, Z={interpolated[2]:.1f} nT")
    else:
        print("No interpolated field available")
        
    # Test anomaly calculation
    print(f"\nTesting anomaly calculation...")
    anomaly = storage.get_field_anomaly(base_lat, base_lon, 100.0)
    if anomaly:
        print(f"Magnetic anomaly: X={anomaly[0]:.1f}, Y={anomaly[1]:.1f}, Z={anomaly[2]:.1f} nT")
    else:
        print("No anomaly data available")
        
    # Show statistics
    print(f"\nStorage statistics:")
    stats = storage.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
        
    print("\n✅ Fingerprint storage test completed!")


if __name__ == "__main__":
    main()
