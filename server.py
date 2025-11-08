"""
BRAMPS - IMU & Magnetometer Data Collection Server
Flask server to receive sensor data from mobile devices
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import logging
from datetime import datetime
import os
import socket
import threading
from threading import Lock

# Import BRAMPS modules
try:
    from fingerprint_storage import FingerprintStorage, MagneticFingerprint
    from magnetic_field_model import MagneticFieldModel
    from imu_dead_reckoning import IMUDeadReckoning
    from map_manager import MapManager
    BRAMPS_MODULES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"BRAMPS modules not available: {e}")
    BRAMPS_MODULES_AVAILABLE = False

# Configure logging with UTF-8 encoding for file, ASCII-safe for console
import sys

# File handler with UTF-8 encoding (supports emojis)
file_handler = logging.FileHandler('bramps_server.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Console handler (ASCII-safe, no emojis)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Configure root logger
logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Statistics tracking
stats = {
    'total_packets': 0,
    'last_packet_time': None,
    'first_packet_time': None,
    'packets_per_second': 0,
    'last_data': None,
    'udp_packets': 0,  # Track UDP packets separately
    'http_packets': 0,  # Track HTTP packets separately
    'last_udp_time': None,  # Last UDP packet time
    'last_http_time': None,  # Last HTTP packet time
    'mapping_packets': 0,  # Track mapping packets
    'fingerprints_created': 0  # Track fingerprints created
}

# Initialize BRAMPS modules if available
fingerprint_storage = None
magnetic_model = None
dead_reckoning = None
map_manager = None
if BRAMPS_MODULES_AVAILABLE:
    try:
        fingerprint_storage = FingerprintStorage("mapping_data")
        magnetic_model = MagneticFieldModel()
        dead_reckoning = IMUDeadReckoning()
        map_manager = MapManager("maps")
        logger.info("BRAMPS modules initialized: fingerprint storage, magnetic model, dead-reckoning, map manager")
    except Exception as e:
        logger.error(f"Failed to initialize BRAMPS modules: {e}")
        BRAMPS_MODULES_AVAILABLE = False

# Mapping session tracking
mapping_sessions = {}
mapping_lock = Lock()

# Navigation session tracking
navigation_sessions = {}
navigation_lock = Lock()

# Store recent data for debugging (last 100 packets)
recent_data = []
recent_data_lock = Lock()  # Thread safety for recent_data

def log_imu_data(packet_num, source, sensor_data, accel_mag, gyro_mag, mag_mag):
    """Log IMU data with emoji-safe console output"""
    # Log to file with emojis (UTF-8 encoding)
    file_handler.stream.write(f"📱 IMU Packet #{packet_num} [{source}]\n")
    file_handler.stream.write(f"   📊 Accelerometer: X={sensor_data['accel_x']:+7.3f}, Y={sensor_data['accel_y']:+7.3f}, Z={sensor_data['accel_z']:+7.3f} (|a|={accel_mag:.3f} m/s²)\n")
    file_handler.stream.write(f"   🔄 Gyroscope:     X={sensor_data['gyro_x']:+7.3f}, Y={sensor_data['gyro_y']:+7.3f}, Z={sensor_data['gyro_z']:+7.3f} (|ω|={gyro_mag:.3f} rad/s)\n")
    file_handler.stream.write(f"   🧲 Magnetometer:  X={sensor_data['mag_x']:+7.3f}, Y={sensor_data['mag_y']:+7.3f}, Z={sensor_data['mag_z']:+7.3f} (|B|={mag_mag:.3f} μT)\n")
    if 'latency_ms' in sensor_data:
        file_handler.stream.write(f"   ⏱️  Latency: {sensor_data['latency_ms']} ms\n")
    file_handler.stream.write(f"   📈 Rate: {stats['packets_per_second']:.1f} packets/sec | Total: {stats['total_packets']} packets\n")
    file_handler.stream.write("-" * 80 + "\n")
    file_handler.stream.flush()
    
    # Log to console without emojis (ASCII-safe)
    logger.info(f"IMU Packet #{packet_num} [{source}]")
    logger.info(f"   Accelerometer: X={sensor_data['accel_x']:+7.3f}, Y={sensor_data['accel_y']:+7.3f}, Z={sensor_data['accel_z']:+7.3f} (|a|={accel_mag:.3f} m/s²)")
    logger.info(f"   Gyroscope:     X={sensor_data['gyro_x']:+7.3f}, Y={sensor_data['gyro_y']:+7.3f}, Z={sensor_data['gyro_z']:+7.3f} (|w|={gyro_mag:.3f} rad/s)")
    logger.info(f"   Magnetometer:  X={sensor_data['mag_x']:+7.3f}, Y={sensor_data['mag_y']:+7.3f}, Z={sensor_data['mag_z']:+7.3f} (|B|={mag_mag:.3f} uT)")
    if 'latency_ms' in sensor_data:
        logger.info(f"   Latency: {sensor_data['latency_ms']} ms")
    logger.info(f"   Rate: {stats['packets_per_second']:.1f} packets/sec | Total: {stats['total_packets']} packets")
    logger.info("-" * 60)

def process_sensor_data(data, source='HTTP'):
    """
    Process sensor data and update statistics
    Shared function for both HTTP POST and UDP
    
    Args:
        data: Dictionary containing sensor data
        source: Source of the data ('HTTP' or 'UDP')
    """
    try:
        # Log raw data for debugging (first packet only, or if all zeros)
        if stats['total_packets'] == 0 or (stats['total_packets'] % 50 == 0):
            logger.info(f"Raw data received [{source}]: {json.dumps(data, indent=2)[:500]}")
        
        # Flexible field name mapping - handle different naming conventions
        # Try multiple possible field names for each sensor
        def get_value(data, *possible_keys):
            """Try multiple possible key names, return first found or 0.0"""
            for key in possible_keys:
                if key in data and data[key] is not None:
                    value = data[key]
                    # Convert to float if it's a number
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return 0.0
            return 0.0
        
        # Extract sensor data with flexible field name matching
        sensor_data = {
            'accel_x': get_value(data, 'accel_x', 'accelX', 'accelerationX', 'acceleration_x', 'ax', 'a_x'),
            'accel_y': get_value(data, 'accel_y', 'accelY', 'accelerationY', 'acceleration_y', 'ay', 'a_y'),
            'accel_z': get_value(data, 'accel_z', 'accelZ', 'accelerationZ', 'acceleration_z', 'az', 'a_z'),
            'gyro_x': get_value(data, 'gyro_x', 'gyroX', 'rotationRateX', 'rotation_rate_x', 'gx', 'g_x', 'omega_x'),
            'gyro_y': get_value(data, 'gyro_y', 'gyroY', 'rotationRateY', 'rotation_rate_y', 'gy', 'g_y', 'omega_y'),
            'gyro_z': get_value(data, 'gyro_z', 'gyroZ', 'rotationRateZ', 'rotation_rate_z', 'gz', 'g_z', 'omega_z'),
            'mag_x': get_value(data, 'mag_x', 'magX', 'magneticFieldX', 'magnetic_field_x', 'mx', 'm_x', 'magnetometerX'),
            'mag_y': get_value(data, 'mag_y', 'magY', 'magneticFieldY', 'magnetic_field_y', 'my', 'm_y', 'magnetometerY'),
            'mag_z': get_value(data, 'mag_z', 'magZ', 'magneticFieldZ', 'magnetic_field_z', 'mz', 'm_z', 'magnetometerZ'),
            'timestamp': data.get('timestamp', data.get('time', int(datetime.now().timestamp() * 1000))),
            'server_received_at': datetime.now().isoformat(),
            'source': source  # Track data source
        }
        
        # Log if we got zeros (might indicate format mismatch)
        if (sensor_data['accel_x'] == 0.0 and sensor_data['accel_y'] == 0.0 and sensor_data['accel_z'] == 0.0 and
            sensor_data['gyro_x'] == 0.0 and sensor_data['gyro_y'] == 0.0 and sensor_data['gyro_z'] == 0.0 and
            sensor_data['mag_x'] == 0.0 and sensor_data['mag_y'] == 0.0 and sensor_data['mag_z'] == 0.0):
            logger.warning(f"All sensor values are zero! Raw data keys: {list(data.keys())}")
            logger.warning(f"Sample values: {json.dumps({k: v for k, v in list(data.items())[:10]})}")
        
        # Calculate latency (if client timestamp provided)
        if 'timestamp' in data:
            client_time = data['timestamp']
            server_time = int(datetime.now().timestamp() * 1000)
            latency = server_time - client_time
            sensor_data['latency_ms'] = latency
        
        # Update statistics
        stats['total_packets'] += 1
        current_time = datetime.now()
        
        if stats['first_packet_time'] is None:
            stats['first_packet_time'] = current_time
        
        stats['last_packet_time'] = current_time
        stats['last_data'] = sensor_data
        
        # Track source-specific stats
        if source == 'UDP':
            stats['udp_packets'] += 1
            stats['last_udp_time'] = current_time
        elif source == 'HTTP':
            stats['http_packets'] += 1
            stats['last_http_time'] = current_time
        
        # Calculate packets per second (simple moving average)
        if stats['first_packet_time']:
            elapsed = (current_time - stats['first_packet_time']).total_seconds()
            if elapsed > 0:
                stats['packets_per_second'] = stats['total_packets'] / elapsed
        
        # Store recent data (keep last 100 packets) - Thread safe
        with recent_data_lock:
            recent_data.append(sensor_data)
            if len(recent_data) > 100:
                recent_data.pop(0)
            current_length = len(recent_data)
        
        # Debug logging for data storage
        if stats['total_packets'] % 10 == 0:
            logger.info(f"Data stored - recent_data length: {current_length}, total_packets: {stats['total_packets']}")
        
        # Enhanced IMU logging - every 5th packet for better monitoring
        if stats['total_packets'] % 5 == 0:
            # Calculate magnitudes for better understanding
            accel_magnitude = (sensor_data['accel_x']**2 + sensor_data['accel_y']**2 + sensor_data['accel_z']**2)**0.5
            gyro_magnitude = (sensor_data['gyro_x']**2 + sensor_data['gyro_y']**2 + sensor_data['gyro_z']**2)**0.5
            mag_magnitude = (sensor_data['mag_x']**2 + sensor_data['mag_y']**2 + sensor_data['mag_z']**2)**0.5
            
            # Use safe logging function
            log_imu_data(stats['total_packets'], source, sensor_data, accel_magnitude, gyro_magnitude, mag_magnitude)
        
        # Update dead-reckoning if available and navigation is active
        if dead_reckoning and BRAMPS_MODULES_AVAILABLE:
            with navigation_lock:
                # Check if any navigation session is active
                has_active_session = any(s['active'] for s in navigation_sessions.values())
            
            if has_active_session:
                try:
                    # Update dead-reckoning with IMU data
                    dead_reckoning.update(
                        accel_x=sensor_data['accel_x'],
                        accel_y=sensor_data['accel_y'],
                        accel_z=sensor_data['accel_z'],
                        gyro_x=sensor_data['gyro_x'],
                        gyro_y=sensor_data['gyro_y'],
                        gyro_z=sensor_data['gyro_z'],
                        timestamp_ms=sensor_data['timestamp']
                    )
                except Exception as e:
                    logger.error(f"Error updating dead-reckoning: {e}")
        
        return sensor_data
    except Exception as e:
        logger.error(f"Error processing sensor data: {e}", exc_info=True)
        return None

def udp_listener(udp_port=65000):
    """
    UDP listener thread to receive sensor data from mobile apps
    """
    try:
        # Create UDP socket
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_socket.bind(('0.0.0.0', udp_port))
        
        logger.info(f"UDP listener started on port {udp_port}")
        logger.info(f"Ready to receive UDP packets at {udp_port}")
        
        while True:
            try:
                # Receive UDP packet (max 4096 bytes)
                data, addr = udp_socket.recvfrom(4096)
                
                # Decode and parse JSON
                try:
                    data_str = data.decode('utf-8')
                    sensor_json = json.loads(data_str)
                    
                    # Log first UDP packet to see format
                    if stats['udp_packets'] == 0:
                        logger.info(f"First UDP packet received from {addr}")
                        logger.info(f"Raw JSON keys: {list(sensor_json.keys())}")
                        logger.info(f"Sample values: {json.dumps({k: v for k, v in list(sensor_json.items())[:15]}, indent=2)}")
                    
                    # Process the sensor data
                    process_sensor_data(sensor_json, source='UDP')
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON from {addr}: {e}")
                    logger.warning(f"Received data (first 200 chars): {data_str[:200]}")
                except UnicodeDecodeError as e:
                    logger.warning(f"Invalid encoding from {addr}: {e}")
                except Exception as e:
                    logger.error(f"Error processing UDP packet from {addr}: {e}")
                    
            except socket.error as e:
                logger.error(f"UDP socket error: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error in UDP listener: {e}", exc_info=True)
                
    except Exception as e:
        logger.error(f"Failed to start UDP listener: {e}", exc_info=True)
    finally:
        if 'udp_socket' in locals():
            udp_socket.close()
        logger.info("UDP listener stopped")

@app.route('/')
def index():
    """Root endpoint - serve HTML page or return server status"""
    # Try to serve the iPhone monitor page first, then fall back to index.html
    try:
        return send_from_directory('.', 'iphone_monitor.html')
    except:
        try:
            return send_from_directory('.', 'index.html')
        except Exception as e:
            # If HTML file not found, return JSON status
            logger.warning(f"Could not serve HTML files: {e}")
            return jsonify({
                'status': 'running',
                'service': 'BRAMPS IMU Data Collection Server',
                'endpoints': {
                    '/': 'GET - iPhone IMU Monitor (HTML interface)',
                    '/navigation.html': 'GET - Indoor navigation interface with map display',
                    '/mapping.html': 'GET - GPS-enabled mapping interface',
                    '/visualization.html': 'GET - Real-time magnetic fingerprint visualization',
                    '/index.html': 'GET - Basic IMU monitor interface',
                    '/imu': 'POST - Receive IMU sensor data',
                    '/maps/upload': 'POST - Upload floor plan map',
                    '/maps': 'GET - List all maps',
                    '/maps/<id>': 'GET/DELETE - Get or delete specific map',
                    '/maps/<id>/activate': 'POST - Set active map',
                    '/maps/<id>/calibrate': 'POST - Update map calibration',
                    '/maps/<id>/image': 'GET - Get map image file',
                    '/navigation/start': 'POST - Start navigation session',
                    '/navigation/stop': 'POST - Stop navigation session',
                    '/navigation/position': 'GET - Get current position',
                    '/navigation/history': 'GET - Get position history trail',
                    '/navigation/reset': 'POST - Reset navigation position',
                    '/mapping/start': 'POST - Start mapping session',
                    '/mapping/stop': 'POST - Stop mapping session',
                    '/mapping/data': 'POST - Send mapping data',
                    '/mapping/sessions': 'GET - List mapping sessions',
                    '/mapping/fingerprints': 'GET - Get fingerprints',
                    '/stats': 'GET - Get server statistics',
                    '/health': 'GET - Health check',
                    '/debug': 'GET - Debug information'
                },
                'note': 'If you see this JSON, no HTML files found in server directory'
            })

# HTML file routes for network access
@app.route('/mapping.html')
def mapping_page():
    """Serve the GPS-enabled mapping interface"""
    try:
        return send_from_directory('.', 'mapping.html')
    except Exception as e:
        logger.error(f"Could not serve mapping.html: {e}")
        return jsonify({'error': 'mapping.html not found'}), 404

@app.route('/visualization.html')
def visualization_page():
    """Serve the real-time magnetic fingerprint visualization"""
    try:
        return send_from_directory('.', 'visualization.html')
    except Exception as e:
        logger.error(f"Could not serve visualization.html: {e}")
        return jsonify({'error': 'visualization.html not found'}), 404

@app.route('/index.html')
def imu_monitor_page():
    """Serve the basic IMU monitor interface"""
    try:
        return send_from_directory('.', 'index.html')
    except Exception as e:
        logger.error(f"Could not serve index.html: {e}")
        return jsonify({'error': 'index.html not found'}), 404

@app.route('/iphone_monitor.html')
def iphone_monitor_page():
    """Serve the iPhone monitor interface"""
    try:
        return send_from_directory('.', 'iphone_monitor.html')
    except Exception as e:
        logger.error(f"Could not serve iphone_monitor.html: {e}")
        return jsonify({'error': 'iphone_monitor.html not found'}), 404

@app.route('/navigation.html')
def navigation_page():
    """Serve the navigation interface"""
    try:
        return send_from_directory('.', 'navigation.html')
    except Exception as e:
        logger.error(f"Could not serve navigation.html: {e}")
        return jsonify({'error': 'navigation.html not found'}), 404

@app.route('/trail_tracker.html')
def trail_tracker_page():
    """Serve the trail tracker interface"""
    try:
        return send_from_directory('.', 'trail_tracker.html')
    except Exception as e:
        logger.error(f"Could not serve trail_tracker.html: {e}")
        return jsonify({'error': 'trail_tracker.html not found'}), 404

# Static file serving for CSS, JS, and other assets
@app.route('/<path:filename>')
def serve_static_files(filename):
    """Serve static files (CSS, JS, images, etc.)"""
    try:
        return send_from_directory('.', filename)
    except Exception as e:
        logger.error(f"Could not serve static file {filename}: {e}")
        return jsonify({'error': f'File {filename} not found'}), 404

# Mapping endpoints for GPS-enabled fingerprint collection
@app.route('/mapping/start', methods=['POST'])
def start_mapping_session():
    """Start a new mapping session."""
    if not BRAMPS_MODULES_AVAILABLE:
        return jsonify({'error': 'BRAMPS modules not available'}), 500
        
    try:
        data = request.get_json()
        session_id = data.get('session_id', f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        device_id = data.get('device_id', 'unknown')
        description = data.get('description', 'Mapping session')
        
        with mapping_lock:
            mapping_sessions[session_id] = {
                'device_id': device_id,
                'description': description,
                'start_time': datetime.now(),
                'fingerprint_count': 0,
                'active': True
            }
            
        logger.info(f"Started mapping session: {session_id} for device: {device_id}")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': f'Mapping session {session_id} started'
        })
        
    except Exception as e:
        logger.error(f"Error starting mapping session: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/mapping/stop', methods=['POST'])
def stop_mapping_session():
    """Stop an active mapping session."""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'session_id required'}), 400
            
        with mapping_lock:
            if session_id in mapping_sessions:
                mapping_sessions[session_id]['active'] = False
                mapping_sessions[session_id]['end_time'] = datetime.now()
                fingerprint_count = mapping_sessions[session_id]['fingerprint_count']
            else:
                return jsonify({'error': 'Session not found'}), 404
                
        # Save fingerprints to disk
        if fingerprint_storage:
            fingerprint_storage.save_to_disk()
            
        logger.info(f"Stopped mapping session: {session_id} with {fingerprint_count} fingerprints")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'fingerprint_count': fingerprint_count,
            'message': f'Mapping session {session_id} stopped'
        })
        
    except Exception as e:
        logger.error(f"Error stopping mapping session: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/mapping/data', methods=['POST'])
def receive_mapping_data():
    """Receive IMU + GPS data for magnetic fingerprinting."""
    if not BRAMPS_MODULES_AVAILABLE:
        return jsonify({'error': 'BRAMPS modules not available'}), 500
        
    try:
        data = request.get_json()
        
        # Extract required fields
        session_id = data.get('session_id')
        if not session_id or session_id not in mapping_sessions:
            return jsonify({'error': 'Invalid or missing session_id'}), 400
            
        if not mapping_sessions[session_id]['active']:
            return jsonify({'error': 'Mapping session is not active'}), 400
            
        # Extract sensor data
        timestamp = datetime.now()
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        altitude = data.get('altitude', 0.0)
        mag_x = data.get('mag_x')
        mag_y = data.get('mag_y')
        mag_z = data.get('mag_z')
        
        # Validate required fields
        if any(x is None for x in [latitude, longitude, mag_x, mag_y, mag_z]):
            return jsonify({'error': 'Missing required fields: latitude, longitude, mag_x, mag_y, mag_z'}), 400
            
        # Create magnetic fingerprint
        fingerprint = MagneticFingerprint(
            timestamp=timestamp,
            latitude=float(latitude),
            longitude=float(longitude),
            altitude=float(altitude),
            mag_x=float(mag_x),
            mag_y=float(mag_y),
            mag_z=float(mag_z),
            device_id=mapping_sessions[session_id]['device_id'],
            session_id=session_id
        )
        
        # Add to storage
        if fingerprint_storage.add_fingerprint(fingerprint):
            with mapping_lock:
                mapping_sessions[session_id]['fingerprint_count'] += 1
                stats['fingerprints_created'] += 1
                
            # Update statistics
            stats['mapping_packets'] += 1
            
            logger.debug(f"Added fingerprint: session={session_id}, lat={latitude:.6f}, lon={longitude:.6f}")
            
            return jsonify({
                'success': True,
                'fingerprint_id': len(fingerprint_storage.fingerprints),
                'quality_score': fingerprint.quality_score,
                'session_fingerprints': mapping_sessions[session_id]['fingerprint_count']
            })
        else:
            return jsonify({'error': 'Fingerprint rejected due to quality'}), 400
            
    except Exception as e:
        logger.error(f"Error processing mapping data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/mapping/sessions', methods=['GET'])
def get_mapping_sessions():
    """Get list of mapping sessions."""
    try:
        with mapping_lock:
            sessions = {}
            for session_id, session_data in mapping_sessions.items():
                sessions[session_id] = {
                    'device_id': session_data['device_id'],
                    'description': session_data['description'],
                    'start_time': session_data['start_time'].isoformat(),
                    'fingerprint_count': session_data['fingerprint_count'],
                    'active': session_data['active']
                }
                if 'end_time' in session_data:
                    sessions[session_id]['end_time'] = session_data['end_time'].isoformat()
                    
        return jsonify({
            'success': True,
            'sessions': sessions,
            'total_sessions': len(sessions)
        })
        
    except Exception as e:
        logger.error(f"Error getting mapping sessions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/mapping/fingerprints', methods=['GET'])
def get_fingerprints():
    """Get magnetic fingerprints with optional filtering."""
    if not BRAMPS_MODULES_AVAILABLE:
        return jsonify({'error': 'BRAMPS modules not available'}), 500
        
    try:
        # Get query parameters
        session_id = request.args.get('session_id')
        lat = request.args.get('latitude', type=float)
        lon = request.args.get('longitude', type=float)
        max_distance = request.args.get('max_distance', 1000.0, type=float)
        limit = request.args.get('limit', 100, type=int)
        
        fingerprints_data = []
        
        if lat is not None and lon is not None:
            # Find fingerprints near a location
            nearest = fingerprint_storage.find_nearest_fingerprints(
                lat, lon, max_distance=max_distance, max_count=limit
            )
            for fp, distance in nearest:
                fp_data = fp.to_dict()
                fp_data['distance'] = distance
                fingerprints_data.append(fp_data)
        else:
            # Get all fingerprints (or filtered by session)
            for fp in fingerprint_storage.fingerprints:
                if session_id is None or fp.session_id == session_id:
                    fingerprints_data.append(fp.to_dict())
                    if len(fingerprints_data) >= limit:
                        break
                        
        return jsonify({
            'success': True,
            'fingerprints': fingerprints_data,
            'count': len(fingerprints_data),
            'total_stored': len(fingerprint_storage.fingerprints)
        })
        
    except Exception as e:
        logger.error(f"Error getting fingerprints: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/imu', methods=['POST', 'OPTIONS'])
def receive_imu_data():
    """
    Receive IMU and magnetometer data from client
    
    Expected JSON format:
    {
        "accel_x": float,
        "accel_y": float,
        "accel_z": float,
        "gyro_x": float,
        "gyro_y": float,
        "gyro_z": float,
        "mag_x": float,
        "mag_y": float,
        "mag_z": float,
        "timestamp": int (milliseconds since epoch)
    }
    """
    if request.method == 'OPTIONS':
        # Handle preflight request
        return '', 200
    
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if not data:
            logger.warning("Received empty request body")
            return jsonify({'error': 'No data received'}), 400
        
        # Validate required fields
        required_fields = ['timestamp']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            logger.warning(f"Missing required fields: {missing_fields}")
            return jsonify({
                'error': f'Missing required fields: {missing_fields}',
                'received_fields': list(data.keys())
            }), 400
        
        # Process sensor data using shared function
        sensor_data = process_sensor_data(data)
        
        if sensor_data is None:
            return jsonify({'error': 'Failed to process sensor data'}), 500
        
        # Return success response
        return jsonify({
            'status': 'success',
            'packet_number': stats['total_packets'],
            'received_at': sensor_data['server_received_at']
        }), 200
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return jsonify({'error': 'Invalid JSON format', 'details': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get server statistics"""
    current_time = datetime.now()
    
    # Check if UDP data was received recently (within last 5 seconds)
    udp_recent = False
    if stats['last_udp_time']:
        time_since_udp = (current_time - stats['last_udp_time']).total_seconds()
        udp_recent = time_since_udp < 5.0
    
    # Get mapping statistics
    mapping_stats = {}
    if BRAMPS_MODULES_AVAILABLE and fingerprint_storage:
        mapping_stats = {
            'total_fingerprints': len(fingerprint_storage.fingerprints),
            'active_sessions': sum(1 for s in mapping_sessions.values() if s['active']),
            'total_sessions': len(mapping_sessions)
        }
    
    return jsonify({
        'total_packets': stats['total_packets'],
        'packets_per_second': round(stats['packets_per_second'], 2),
        'first_packet_time': stats['first_packet_time'].isoformat() if stats['first_packet_time'] else None,
        'last_packet_time': stats['last_packet_time'].isoformat() if stats['last_packet_time'] else None,
        'last_data': stats['last_data'],
        'recent_packets_count': len(recent_data),
        'udp_packets': stats['udp_packets'],
        'http_packets': stats['http_packets'],
        'mapping_packets': stats['mapping_packets'],
        'fingerprints_created': stats['fingerprints_created'],
        'last_udp_time': stats['last_udp_time'].isoformat() if stats['last_udp_time'] else None,
        'last_http_time': stats['last_http_time'].isoformat() if stats['last_http_time'] else None,
        'udp_recent': udp_recent,  # True if UDP data received in last 5 seconds
        'time_since_last_udp': (current_time - stats['last_udp_time']).total_seconds() if stats['last_udp_time'] else None,
        'mapping': mapping_stats,
        'bramps_available': BRAMPS_MODULES_AVAILABLE
    })

@app.route('/recent', methods=['GET'])
def get_recent_data():
    """Get recent sensor data packets (last 100)"""
    limit = request.args.get('limit', 100, type=int)
    
    # Thread-safe access to recent_data
    with recent_data_lock:
        data_length = len(recent_data)
        data_to_return = recent_data[-limit:] if recent_data else []
    
    # Debug logging with more details
    logger.info(f"Recent data request - limit: {limit}, available packets: {data_length}")
    logger.info(f"Total packets received: {stats['total_packets']}, UDP packets: {stats['udp_packets']}")
    
    if data_length > 0:
        logger.info(f"Latest packet sample: {json.dumps(data_to_return[-1], indent=2)[:300]}")
    else:
        logger.warning("No recent data available despite receiving packets!")
        logger.info(f"Stats: {json.dumps(stats, default=str, indent=2)}")
    
    return jsonify({
        'count': min(data_length, limit),
        'data': data_to_return
    })

@app.route('/debug', methods=['GET'])
def debug_info():
    """Debug endpoint to check server state"""
    return jsonify({
        'stats': stats,
        'recent_data_count': len(recent_data),
        'sample_recent_data': recent_data[-1] if recent_data else None,
        'all_recent_data': recent_data[-5:] if len(recent_data) >= 5 else recent_data
    })

# ============================================================================
# MAP MANAGEMENT ENDPOINTS
# ============================================================================

@app.route('/maps/upload', methods=['POST'])
def upload_map():
    """Upload a new floor plan map."""
    if not BRAMPS_MODULES_AVAILABLE or not map_manager:
        return jsonify({'error': 'Map manager not available'}), 500
    
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get metadata from form data
        name = request.form.get('name', 'Unnamed Map')
        description = request.form.get('description', '')
        scale = float(request.form.get('scale_meters_per_pixel', 0.1))
        origin_x = float(request.form.get('origin_x', 0.0))
        origin_y = float(request.form.get('origin_y', 0.0))
        rotation = float(request.form.get('rotation_degrees', 0.0))
        
        # Upload map
        map_id = map_manager.upload_map(
            file,
            name=name,
            description=description,
            scale_meters_per_pixel=scale,
            origin_x=origin_x,
            origin_y=origin_y,
            rotation_degrees=rotation
        )
        
        if map_id:
            map_data = map_manager.get_map(map_id)
            return jsonify({
                'success': True,
                'map_id': map_id,
                'map': map_data,
                'message': f'Map "{name}" uploaded successfully'
            })
        else:
            return jsonify({'error': 'Failed to upload map'}), 500
            
    except Exception as e:
        logger.error(f"Error uploading map: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/maps', methods=['GET'])
def list_maps():
    """Get list of all maps."""
    if not BRAMPS_MODULES_AVAILABLE or not map_manager:
        return jsonify({'error': 'Map manager not available'}), 500
    
    try:
        maps = map_manager.list_maps()
        active_map = map_manager.get_active_map()
        
        return jsonify({
            'success': True,
            'maps': maps,
            'active_map_id': map_manager.active_map_id,
            'active_map': active_map,
            'count': len(maps)
        })
    except Exception as e:
        logger.error(f"Error listing maps: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/maps/<map_id>', methods=['GET'])
def get_map(map_id):
    """Get specific map metadata."""
    if not BRAMPS_MODULES_AVAILABLE or not map_manager:
        return jsonify({'error': 'Map manager not available'}), 500
    
    try:
        map_data = map_manager.get_map(map_id)
        if map_data:
            return jsonify({
                'success': True,
                'map': map_data
            })
        else:
            return jsonify({'error': 'Map not found'}), 404
    except Exception as e:
        logger.error(f"Error getting map: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/maps/<map_id>', methods=['DELETE'])
def delete_map(map_id):
    """Delete a map."""
    if not BRAMPS_MODULES_AVAILABLE or not map_manager:
        return jsonify({'error': 'Map manager not available'}), 500
    
    try:
        if map_manager.delete_map(map_id):
            return jsonify({
                'success': True,
                'message': f'Map {map_id} deleted'
            })
        else:
            return jsonify({'error': 'Failed to delete map'}), 500
    except Exception as e:
        logger.error(f"Error deleting map: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/maps/<map_id>/activate', methods=['POST'])
def activate_map(map_id):
    """Set active map for navigation."""
    if not BRAMPS_MODULES_AVAILABLE or not map_manager:
        return jsonify({'error': 'Map manager not available'}), 500
    
    try:
        if map_manager.set_active_map(map_id):
            return jsonify({
                'success': True,
                'active_map_id': map_id,
                'message': f'Map {map_id} activated'
            })
        else:
            return jsonify({'error': 'Map not found'}), 404
    except Exception as e:
        logger.error(f"Error activating map: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/maps/<map_id>/calibrate', methods=['POST'])
def calibrate_map(map_id):
    """Update map calibration parameters."""
    if not BRAMPS_MODULES_AVAILABLE or not map_manager:
        return jsonify({'error': 'Map manager not available'}), 500
    
    try:
        data = request.get_json()
        
        success = map_manager.update_map_calibration(
            map_id,
            scale_meters_per_pixel=data.get('scale_meters_per_pixel'),
            origin_x=data.get('origin_x'),
            origin_y=data.get('origin_y'),
            rotation_degrees=data.get('rotation_degrees')
        )
        
        if success:
            map_data = map_manager.get_map(map_id)
            return jsonify({
                'success': True,
                'map': map_data,
                'message': 'Map calibration updated'
            })
        else:
            return jsonify({'error': 'Failed to update calibration'}), 500
            
    except Exception as e:
        logger.error(f"Error calibrating map: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/maps/<map_id>/image', methods=['GET'])
def get_map_image(map_id):
    """Get map image file."""
    if not BRAMPS_MODULES_AVAILABLE or not map_manager:
        return jsonify({'error': 'Map manager not available'}), 500
    
    try:
        map_data = map_manager.get_map(map_id)
        if not map_data:
            return jsonify({'error': 'Map not found'}), 404
        
        image_filename = map_data['image_filename']
        return send_from_directory(map_manager.maps_directory, image_filename)
        
    except Exception as e:
        logger.error(f"Error getting map image: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# NAVIGATION ENDPOINTS
# ============================================================================

@app.route('/navigation/start', methods=['POST'])
def start_navigation():
    """Start a navigation session."""
    if not BRAMPS_MODULES_AVAILABLE or not dead_reckoning:
        return jsonify({'error': 'Navigation system not available'}), 500
    
    try:
        data = request.get_json()
        
        # Get initial position and heading
        initial_x = float(data.get('initial_x', 0.0))
        initial_y = float(data.get('initial_y', 0.0))
        initial_heading = float(data.get('initial_heading', 0.0))
        
        # Reset dead-reckoning
        dead_reckoning.reset(position=(initial_x, initial_y), heading=initial_heading)
        
        # Create navigation session
        session_id = f"nav_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with navigation_lock:
            navigation_sessions[session_id] = {
                'session_id': session_id,
                'start_time': datetime.now(),
                'initial_position': (initial_x, initial_y),
                'initial_heading': initial_heading,
                'active': True,
                'map_id': map_manager.active_map_id if map_manager else None
            }
        
        logger.info(f"Navigation session started: {session_id}")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'initial_position': {'x': initial_x, 'y': initial_y},
            'initial_heading': initial_heading,
            'message': 'Navigation session started'
        })
        
    except Exception as e:
        logger.error(f"Error starting navigation: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/navigation/stop', methods=['POST'])
def stop_navigation():
    """Stop navigation session."""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'session_id required'}), 400
        
        with navigation_lock:
            if session_id in navigation_sessions:
                navigation_sessions[session_id]['active'] = False
                navigation_sessions[session_id]['end_time'] = datetime.now()
            else:
                return jsonify({'error': 'Session not found'}), 404
        
        logger.info(f"Navigation session stopped: {session_id}")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'Navigation session stopped'
        })
        
    except Exception as e:
        logger.error(f"Error stopping navigation: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/navigation/position', methods=['GET'])
def get_current_position():
    """Get current position from dead-reckoning."""
    if not BRAMPS_MODULES_AVAILABLE or not dead_reckoning:
        return jsonify({'error': 'Navigation system not available'}), 500
    
    try:
        state = dead_reckoning.get_state()
        
        # Add pixel coordinates if map is active
        if map_manager and map_manager.active_map_id:
            pixel_coords = map_manager.world_to_pixel(
                state['position']['x'],
                state['position']['y']
            )
            if pixel_coords:
                state['pixel_position'] = {
                    'x': pixel_coords[0],
                    'y': pixel_coords[1]
                }
        
        return jsonify({
            'success': True,
            'position': state
        })
        
    except Exception as e:
        logger.error(f"Error getting position: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/navigation/history', methods=['GET'])
def get_position_history():
    """Get position history trail."""
    if not BRAMPS_MODULES_AVAILABLE or not dead_reckoning:
        return jsonify({'error': 'Navigation system not available'}), 500
    
    try:
        limit = request.args.get('limit', type=int)
        history = dead_reckoning.get_position_history(limit=limit)
        
        # Add pixel coordinates if map is active
        if map_manager and map_manager.active_map_id:
            for point in history:
                pixel_coords = map_manager.world_to_pixel(point['x'], point['y'])
                if pixel_coords:
                    point['pixel_x'] = pixel_coords[0]
                    point['pixel_y'] = pixel_coords[1]
        
        return jsonify({
            'success': True,
            'history': history,
            'count': len(history)
        })
        
    except Exception as e:
        logger.error(f"Error getting position history: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/navigation/reset', methods=['POST'])
def reset_navigation():
    """Reset navigation position."""
    if not BRAMPS_MODULES_AVAILABLE or not dead_reckoning:
        return jsonify({'error': 'Navigation system not available'}), 500
    
    try:
        data = request.get_json()
        
        x = float(data.get('x', 0.0))
        y = float(data.get('y', 0.0))
        heading = float(data.get('heading', 0.0))
        
        dead_reckoning.reset(position=(x, y), heading=heading)
        
        logger.info(f"Navigation reset to position ({x}, {y}), heading {heading}")
        
        return jsonify({
            'success': True,
            'position': {'x': x, 'y': y},
            'heading': heading,
            'message': 'Navigation position reset'
        })
        
    except Exception as e:
        logger.error(f"Error resetting navigation: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Get ports from environment variables or use defaults
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')  # Listen on all interfaces
    udp_port = int(os.environ.get('UDP_PORT', 65000))  # UDP port for mobile apps
    
    logger.info(f"Starting BRAMPS IMU Data Collection Server")
    logger.info(f"HTTP server: http://{host}:{port}/imu")
    logger.info(f"UDP listener: udp://{host}:{udp_port}")
    
    # Start UDP listener in a separate thread
    udp_thread = threading.Thread(target=udp_listener, args=(udp_port,), daemon=True)
    udp_thread.start()
    logger.info("UDP listener thread started")
    
    # Run Flask app (this blocks)
    # Note: debug=False to avoid conflicts with UDP listener thread
    app.run(host=host, port=port, debug=False)

