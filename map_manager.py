"""
BRAMPS - Map Management Module
Handles floor plan upload, storage, and coordinate transformation
"""

import os
import json
import uuid
from datetime import datetime
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class MapManager:
    """
    Manages floor plan maps with coordinate calibration.
    
    Handles map upload, storage, metadata, and coordinate transformations
    between real-world coordinates and pixel coordinates.
    """
    
    def __init__(self, maps_directory="maps"):
        """
        Initialize map manager.
        
        Args:
            maps_directory: Directory to store map images and metadata
        """
        self.maps_directory = maps_directory
        self.metadata_file = os.path.join(maps_directory, "maps_metadata.json")
        
        # Create maps directory if it doesn't exist
        os.makedirs(maps_directory, exist_ok=True)
        
        # Load existing maps metadata
        self.maps = self._load_metadata()
        
        # Active map
        self.active_map_id = None
        
        logger.info(f"Map Manager initialized with {len(self.maps)} maps")
    
    def _load_metadata(self):
        """Load maps metadata from JSON file."""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading maps metadata: {e}")
                return {}
        return {}
    
    def _save_metadata(self):
        """Save maps metadata to JSON file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.maps, f, indent=2)
            logger.info(f"Maps metadata saved ({len(self.maps)} maps)")
        except Exception as e:
            logger.error(f"Error saving maps metadata: {e}")
    
    def upload_map(self, image_file, name, description="", scale_meters_per_pixel=0.1,
                   origin_x=0.0, origin_y=0.0, rotation_degrees=0.0):
        """
        Upload a new floor plan map.
        
        Args:
            image_file: File object or path to image file
            name: Name of the map
            description: Optional description
            scale_meters_per_pixel: Scale factor (meters per pixel)
            origin_x: Real-world x-coordinate of image origin (meters)
            origin_y: Real-world y-coordinate of image origin (meters)
            rotation_degrees: Rotation of map relative to north (degrees, clockwise)
        
        Returns:
            Map ID if successful, None otherwise
        """
        try:
            # Generate unique map ID
            map_id = str(uuid.uuid4())
            
            # Open and process image
            if isinstance(image_file, str):
                img = Image.open(image_file)
            else:
                img = Image.open(image_file)
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Get image dimensions
            width, height = img.size
            
            # Save image
            image_filename = f"{map_id}.png"
            image_path = os.path.join(self.maps_directory, image_filename)
            img.save(image_path, 'PNG')
            
            # Create metadata
            metadata = {
                'id': map_id,
                'name': name,
                'description': description,
                'image_filename': image_filename,
                'width': width,
                'height': height,
                'scale_meters_per_pixel': scale_meters_per_pixel,
                'origin_x': origin_x,
                'origin_y': origin_y,
                'rotation_degrees': rotation_degrees,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Store metadata
            self.maps[map_id] = metadata
            self._save_metadata()
            
            logger.info(f"Map uploaded: {name} ({map_id}), size: {width}x{height}, scale: {scale_meters_per_pixel}m/px")
            
            return map_id
            
        except Exception as e:
            logger.error(f"Error uploading map: {e}")
            return None
    
    def delete_map(self, map_id):
        """
        Delete a map.
        
        Args:
            map_id: ID of map to delete
        
        Returns:
            True if successful, False otherwise
        """
        if map_id not in self.maps:
            logger.warning(f"Map not found: {map_id}")
            return False
        
        try:
            # Delete image file
            image_filename = self.maps[map_id]['image_filename']
            image_path = os.path.join(self.maps_directory, image_filename)
            if os.path.exists(image_path):
                os.remove(image_path)
            
            # Remove from metadata
            del self.maps[map_id]
            self._save_metadata()
            
            # Clear active map if it was deleted
            if self.active_map_id == map_id:
                self.active_map_id = None
            
            logger.info(f"Map deleted: {map_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting map: {e}")
            return False
    
    def get_map(self, map_id):
        """
        Get map metadata.
        
        Args:
            map_id: ID of map
        
        Returns:
            Map metadata dictionary or None
        """
        return self.maps.get(map_id)
    
    def list_maps(self):
        """
        Get list of all maps.
        
        Returns:
            List of map metadata dictionaries
        """
        return list(self.maps.values())
    
    def set_active_map(self, map_id):
        """
        Set the active map for navigation.
        
        Args:
            map_id: ID of map to activate
        
        Returns:
            True if successful, False otherwise
        """
        if map_id not in self.maps:
            logger.warning(f"Cannot set active map: {map_id} not found")
            return False
        
        self.active_map_id = map_id
        logger.info(f"Active map set to: {self.maps[map_id]['name']} ({map_id})")
        return True
    
    def get_active_map(self):
        """
        Get active map metadata.
        
        Returns:
            Active map metadata or None
        """
        if self.active_map_id:
            return self.maps.get(self.active_map_id)
        return None
    
    def update_map_calibration(self, map_id, scale_meters_per_pixel=None,
                               origin_x=None, origin_y=None, rotation_degrees=None):
        """
        Update map calibration parameters.
        
        Args:
            map_id: ID of map to update
            scale_meters_per_pixel: New scale factor
            origin_x: New origin x-coordinate
            origin_y: New origin y-coordinate
            rotation_degrees: New rotation angle
        
        Returns:
            True if successful, False otherwise
        """
        if map_id not in self.maps:
            logger.warning(f"Map not found: {map_id}")
            return False
        
        try:
            if scale_meters_per_pixel is not None:
                self.maps[map_id]['scale_meters_per_pixel'] = scale_meters_per_pixel
            if origin_x is not None:
                self.maps[map_id]['origin_x'] = origin_x
            if origin_y is not None:
                self.maps[map_id]['origin_y'] = origin_y
            if rotation_degrees is not None:
                self.maps[map_id]['rotation_degrees'] = rotation_degrees
            
            self.maps[map_id]['updated_at'] = datetime.now().isoformat()
            self._save_metadata()
            
            logger.info(f"Map calibration updated: {map_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating map calibration: {e}")
            return False
    
    def world_to_pixel(self, world_x, world_y, map_id=None):
        """
        Convert world coordinates to pixel coordinates.
        
        Args:
            world_x: X coordinate in meters
            world_y: Y coordinate in meters
            map_id: Map ID (uses active map if None)
        
        Returns:
            Tuple (pixel_x, pixel_y) or None if map not found
        """
        if map_id is None:
            map_id = self.active_map_id
        
        if map_id not in self.maps:
            return None
        
        map_data = self.maps[map_id]
        
        # Get calibration parameters
        scale = map_data['scale_meters_per_pixel']
        origin_x = map_data['origin_x']
        origin_y = map_data['origin_y']
        rotation = map_data['rotation_degrees']
        
        # Translate to map origin
        dx = world_x - origin_x
        dy = world_y - origin_y
        
        # Apply rotation (if any)
        if rotation != 0:
            import math
            rad = math.radians(-rotation)  # Negative for clockwise
            cos_r = math.cos(rad)
            sin_r = math.sin(rad)
            dx_rot = dx * cos_r - dy * sin_r
            dy_rot = dx * sin_r + dy * cos_r
            dx, dy = dx_rot, dy_rot
        
        # Convert to pixels
        # Note: Image coordinates have Y increasing downward
        pixel_x = dx / scale
        pixel_y = -dy / scale  # Flip Y axis
        
        return (pixel_x, pixel_y)
    
    def pixel_to_world(self, pixel_x, pixel_y, map_id=None):
        """
        Convert pixel coordinates to world coordinates.
        
        Args:
            pixel_x: X coordinate in pixels
            pixel_y: Y coordinate in pixels
            map_id: Map ID (uses active map if None)
        
        Returns:
            Tuple (world_x, world_y) or None if map not found
        """
        if map_id is None:
            map_id = self.active_map_id
        
        if map_id not in self.maps:
            return None
        
        map_data = self.maps[map_id]
        
        # Get calibration parameters
        scale = map_data['scale_meters_per_pixel']
        origin_x = map_data['origin_x']
        origin_y = map_data['origin_y']
        rotation = map_data['rotation_degrees']
        
        # Convert from pixels to meters
        dx = pixel_x * scale
        dy = -pixel_y * scale  # Flip Y axis
        
        # Apply rotation (if any)
        if rotation != 0:
            import math
            rad = math.radians(rotation)  # Positive for clockwise
            cos_r = math.cos(rad)
            sin_r = math.sin(rad)
            dx_rot = dx * cos_r - dy * sin_r
            dy_rot = dx * sin_r + dy * cos_r
            dx, dy = dx_rot, dy_rot
        
        # Translate to world coordinates
        world_x = origin_x + dx
        world_y = origin_y + dy
        
        return (world_x, world_y)
    
    def get_map_bounds(self, map_id=None):
        """
        Get world coordinate bounds of map.
        
        Args:
            map_id: Map ID (uses active map if None)
        
        Returns:
            Dictionary with min_x, max_x, min_y, max_y or None
        """
        if map_id is None:
            map_id = self.active_map_id
        
        if map_id not in self.maps:
            return None
        
        map_data = self.maps[map_id]
        width = map_data['width']
        height = map_data['height']
        
        # Get corners in world coordinates
        corners = [
            self.pixel_to_world(0, 0, map_id),
            self.pixel_to_world(width, 0, map_id),
            self.pixel_to_world(0, height, map_id),
            self.pixel_to_world(width, height, map_id)
        ]
        
        # Find bounds
        x_coords = [c[0] for c in corners]
        y_coords = [c[1] for c in corners]
        
        return {
            'min_x': min(x_coords),
            'max_x': max(x_coords),
            'min_y': min(y_coords),
            'max_y': max(y_coords),
            'width_meters': max(x_coords) - min(x_coords),
            'height_meters': max(y_coords) - min(y_coords)
        }

