# BRAMPS Indoor Navigation System

## 🎯 Overview

A complete indoor navigation system that tracks your position in real-time using IMU sensors from an iPhone, displayed on an uploaded floor plan. No GPS required!

## ✨ Features

### Core Functionality
- **Real-time Position Tracking**: Track movement using iPhone IMU sensors
- **Floor Plan Upload**: Upload and calibrate building floor plans
- **Visual Navigation**: See your position and movement trail on the map
- **Dead-Reckoning**: Calculate position from accelerometer and gyroscope data
- **Interactive Map**: Pan, zoom, and interact with the map display

### Technical Features
- **IMU Integration**: Accelerometer + gyroscope sensor fusion
- **Coordinate Transformation**: World ↔ Pixel coordinate conversion
- **Position History**: Track and visualize movement trails
- **Session Management**: Start/stop/reset navigation sessions
- **Multi-Map Support**: Upload and switch between multiple floor plans
- **Real-time Updates**: 10 Hz position updates for smooth tracking

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
cd BramUI

# Install dependencies
pip install -r requirements.txt
```

### 2. Start the Server

```bash
python server.py
```

Server will start on:
- **HTTP**: http://localhost:5000
- **UDP**: Port 65000 (for iPhone IMU data)

### 3. Open Navigation Interface

Navigate to: **http://localhost:5000/navigation.html**

### 4. Upload a Floor Plan

1. Click "📁 Upload Floor Plan"
2. Select your floor plan image (PNG/JPG)
3. Enter map name and scale (meters per pixel)
4. Click "Upload Map"
5. Select the map from the dropdown

### 5. Start Navigation

1. Set initial position (X, Y in meters)
2. Set initial heading (0° = North)
3. Click "▶️ Start Navigation"
4. Connect iPhone IMU app to server
5. Watch your position update in real-time!

## 📱 iPhone IMU App Setup

1. Install an IMU sensor app that supports UDP streaming
2. Configure server address: Your computer's IP
3. Configure port: 65000
4. Enable accelerometer, gyroscope, and magnetometer
5. Start streaming

## 🗺️ Map Calibration

### Determining Scale

1. Find a known distance on your floor plan (e.g., room width)
2. Measure the pixel distance in an image editor
3. Calculate: `scale = real_distance_meters / pixel_distance`

**Example:**
- Room is 5 meters wide
- Measures 50 pixels in image
- Scale = 5m / 50px = 0.1 m/px

### Coordinate System

- **Origin**: Bottom-left corner of map
- **X-axis**: Positive = East (right)
- **Y-axis**: Positive = North (up)
- **Heading**: 0° = North, 90° = East, 180° = South, 270° = West

## 🎮 Using the Interface

### Sidebar Controls

**Map Management:**
- Upload new floor plans
- Select active map
- Configure map scale and calibration

**Navigation Control:**
- Set initial position and heading
- Start/stop navigation sessions
- Reset position to known location

**Statistics:**
- Current position (X, Y)
- Current heading (degrees)
- Current velocity (m/s)
- Total distance traveled

**Sensor Data:**
- Real-time accelerometer readings
- Real-time gyroscope readings
- Real-time magnetometer readings

### Map View Controls

**Zoom:**
- Mouse wheel to zoom in/out
- 🔍 Zoom In/Out buttons

**Pan:**
- Click and drag to pan around map
- 🎯 Center button to center on current position

**Trail:**
- 📍 Toggle Trail button to show/hide movement path
- Blue trail shows historical positions
- Opacity fades for older positions

### Visual Elements

- **Blue Dot**: Current position
- **Red Arrow**: Current heading direction
- **Blue Trail**: Movement history
- **Grid**: Background grid when no map loaded

## 📊 API Reference

### Map Management

```bash
# Upload map
POST /maps/upload
Content-Type: multipart/form-data
Fields: file, name, scale_meters_per_pixel, origin_x, origin_y, rotation_degrees

# List all maps
GET /maps
Response: {success, maps[], active_map_id, active_map, count}

# Get specific map
GET /maps/<map_id>
Response: {success, map{}}

# Delete map
DELETE /maps/<map_id>
Response: {success, message}

# Activate map
POST /maps/<map_id>/activate
Response: {success, active_map_id, message}

# Update calibration
POST /maps/<map_id>/calibrate
Body: {scale_meters_per_pixel, origin_x, origin_y, rotation_degrees}
Response: {success, map{}, message}

# Get map image
GET /maps/<map_id>/image
Response: Image file (PNG/JPG)
```

### Navigation

```bash
# Start navigation session
POST /navigation/start
Body: {initial_x, initial_y, initial_heading}
Response: {success, session_id, initial_position{}, initial_heading, message}

# Stop navigation session
POST /navigation/stop
Body: {session_id}
Response: {success, session_id, message}

# Get current position
GET /navigation/position
Response: {
  success,
  position: {
    position: {x, y},
    velocity: {vx, vy, magnitude},
    heading, heading_degrees,
    angular_velocity,
    timestamp,
    update_count,
    total_distance,
    pixel_position: {x, y}  // If map active
  }
}

# Get position history
GET /navigation/history?limit=100
Response: {success, history[], count}

# Reset position
POST /navigation/reset
Body: {x, y, heading}
Response: {success, position{}, heading, message}
```

### IMU Data

```bash
# Receive IMU data (from iPhone app)
POST /imu
Body: {
  accel_x, accel_y, accel_z,
  gyro_x, gyro_y, gyro_z,
  mag_x, mag_y, mag_z,
  timestamp
}
Response: {status, packet_number, received_at}

# Get statistics
GET /stats
Response: {total_packets, packets_per_second, ...}
```

## 🏗️ Architecture

### Components

1. **IMU Dead-Reckoning** (`imu_dead_reckoning.py`)
   - Integrates accelerometer for position
   - Integrates gyroscope for heading
   - Applies filtering and drift correction

2. **Map Manager** (`map_manager.py`)
   - Handles floor plan upload and storage
   - Manages coordinate transformations
   - Supports multiple maps

3. **Flask Server** (`server.py`)
   - REST API for maps and navigation
   - IMU data processing
   - Real-time position streaming

4. **Navigation Interface** (`navigation.html`)
   - HTML5 Canvas map renderer
   - Real-time position visualization
   - Interactive controls and statistics

### Data Flow

```
iPhone IMU App
    ↓ (UDP/HTTP)
Flask Server (/imu endpoint)
    ↓
IMU Dead-Reckoning
    ↓
Position Calculation
    ↓
Map Coordinate Transformation
    ↓
Navigation Interface (/navigation/position)
    ↓
Canvas Rendering
```

## 🧪 Testing

Run the test suite:

```bash
python test_navigation.py
```

Tests include:
- Dead-reckoning with simulated movement
- Map coordinate transformations
- Integration of dead-reckoning with maps

## 📈 Performance

- **Position Update Rate**: 10 Hz (100ms intervals)
- **IMU Processing Rate**: 50-100 Hz (sensor dependent)
- **Canvas Rendering**: 60 FPS
- **Position History**: 1000 points (configurable)
- **Trail Display**: 500 points (configurable)

## 🔧 Configuration

### Server Configuration

Edit `server.py`:
```python
port = 5000          # HTTP server port
udp_port = 65000     # UDP listener port
host = '0.0.0.0'     # Listen on all interfaces
```

### Dead-Reckoning Parameters

Edit `imu_dead_reckoning.py`:
```python
# Low-pass filter coefficient
alpha = 0.3  # Lower = more smoothing

# Velocity threshold (m/s)
velocity_threshold = 0.05

# Acceleration threshold (m/s²)
accel_threshold = 0.1
```

### Map Display

Edit `navigation.html`:
```javascript
// Position update interval (ms)
const updateInterval = 100;  // 10 Hz

// Trail length
const maxTrailLength = 500;

// Zoom limits
const minScale = 0.1;
const maxScale = 5.0;
```

## 🐛 Troubleshooting

### Position Not Updating

**Check:**
1. Navigation session is started (green indicator)
2. iPhone app is connected and streaming
3. Server is receiving data (`/stats` endpoint)
4. No firewall blocking UDP port 65000

### Position Drift

**Causes:**
- IMU sensor noise
- Integration error accumulation
- Incorrect initial position/heading

**Solutions:**
- Reset position periodically
- Implement magnetic heading correction
- Use Kalman filter (future enhancement)

### Map Not Loading

**Check:**
1. Map uploaded successfully
2. Map activated in dropdown
3. Image file in `maps/` directory
4. Browser console for errors

## 🚧 Future Enhancements

- [ ] **M3.2**: Magnetic heading correction
- [ ] **M3.3**: Kalman filter for sensor fusion
- [ ] **M6**: Magnetic fingerprint integration
- [ ] Click-to-set initial position on map
- [ ] Session replay functionality
- [ ] Multi-floor support
- [ ] Position export (CSV/JSON)
- [ ] Offline mode support

## 📁 Project Structure

```
BramUI/
├── imu_dead_reckoning.py      # Dead-reckoning implementation
├── map_manager.py              # Map management system
├── server.py                   # Flask server with API
├── navigation.html             # Navigation interface
├── test_navigation.py          # Test suite
├── requirements.txt            # Python dependencies
├── NAVIGATION_GUIDE.md         # User guide
├── README_NAVIGATION.md        # This file
└── maps/                       # Uploaded floor plans
    ├── maps_metadata.json      # Map metadata
    └── <map_id>.png            # Map images
```

## 🤝 Contributing

This is part of the BRAMPS (Bram's Universal Navigation System) project. See `.cursor/scratchpad.md` for development roadmap and progress.

## 📝 License

Part of the BRAMPS project.

## 🎓 Credits

Developed as part of the BRAMPS Universal Navigation System, combining:
- IMU dead-reckoning
- Magnetic field fingerprinting
- Pulsar timing corrections

---

**Ready to navigate!** 🧭

Start the server: `python server.py`  
Open interface: http://localhost:5000/navigation.html

