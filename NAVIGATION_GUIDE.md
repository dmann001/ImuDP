# BRAMPS Indoor Navigation System - User Guide

## Overview

The BRAMPS Indoor Navigation System provides real-time position tracking using IMU sensors from your iPhone, displayed on an uploaded floor plan. The system uses dead-reckoning to calculate position from accelerometer and gyroscope data.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- Flask (web server)
- NumPy, SciPy, Pandas (data processing)
- Pillow (image processing for maps)
- Flask-CORS (cross-origin requests)

### 2. Start the Server

```bash
python server.py
```

The server will start on:
- HTTP: `http://localhost:5000`
- UDP: Port `65000` (for iPhone IMU app)

### 3. Open Navigation Interface

Navigate to: `http://localhost:5000/navigation.html`

## Using the Navigation System

### Step 1: Upload a Floor Plan

1. **Prepare Your Floor Plan**
   - Supported formats: PNG, JPG, JPEG
   - Recommended: High-resolution image with clear features
   - Ensure the floor plan is oriented correctly (North up)

2. **Upload the Map**
   - Click "📁 Upload Floor Plan" button
   - Select your floor plan image
   - Enter a descriptive name (e.g., "Building A - Floor 1")
   - Set the scale in meters per pixel:
     - Measure a known distance on your floor plan
     - Calculate: `scale = real_distance_meters / pixel_distance`
     - Example: If 50 pixels = 5 meters, scale = 0.1 m/px
   - Click "Upload Map"

3. **Activate the Map**
   - Select your uploaded map from the "Active Map" dropdown
   - The map will load and display in the main view

### Step 2: Configure Initial Position

1. **Set Starting Position**
   - Enter X coordinate (meters) - typically 0 for origin
   - Enter Y coordinate (meters) - typically 0 for origin
   - Enter initial heading (degrees):
     - 0° = North
     - 90° = East
     - 180° = South
     - 270° = West

2. **Position on Map**
   - Click on the map to set your starting position (future feature)
   - Or manually enter coordinates relative to map origin

### Step 3: Start Navigation

1. **Connect iPhone IMU App**
   - Ensure your iPhone is running the IMU sensor app
   - Configure it to send data to your server's IP address
   - Port: 65000 (UDP)

2. **Start Navigation Session**
   - Click "▶️ Start Navigation" button
   - Status indicator will turn green
   - Position tracking begins immediately

3. **Move Around**
   - Carry your iPhone as you walk
   - Watch the blue dot move on the map in real-time
   - The red arrow shows your heading direction
   - The trail shows your path history

### Step 4: Monitor Navigation

**Real-time Statistics:**
- **Position X/Y**: Current position in meters
- **Heading**: Current direction (0-360°)
- **Velocity**: Current speed in m/s
- **Total Distance**: Cumulative distance traveled

**Sensor Data Panel:**
- Shows raw accelerometer, gyroscope, and magnetometer readings
- Updates in real-time as data arrives from iPhone

**Map Controls:**
- **🔍 Zoom In/Out**: Adjust map scale
- **🎯 Center**: Center view on current position
- **📍 Toggle Trail**: Show/hide movement trail

### Step 5: Stop Navigation

1. Click "⏹️ Stop Navigation" button
2. Position tracking stops
3. Trail and statistics are preserved

## Map Controls

### Pan and Zoom

- **Pan**: Click and drag on the map
- **Zoom**: Use mouse wheel or zoom buttons
- **Reset View**: Click "🎯 Center" to center on current position

### Trail Visualization

- **Blue Trail**: Shows your movement path
- **Blue Dot**: Current position
- **Red Arrow**: Current heading direction
- **Opacity**: Trail fades for older positions

## Coordinate Systems

### World Coordinates

- Origin: (0, 0) at map origin point
- X-axis: Positive = East, Negative = West
- Y-axis: Positive = North, Negative = South
- Units: Meters

### Pixel Coordinates

- Origin: Top-left corner of map image
- X-axis: Positive = Right
- Y-axis: Positive = Down
- Units: Pixels

### Coordinate Transformation

The system automatically converts between world and pixel coordinates using:
- Scale factor (meters per pixel)
- Origin offset (world coordinates of pixel 0,0)
- Rotation angle (if map is not aligned with North)

## Calibration

### Map Scale Calibration

1. **Measure Known Distance**
   - Find a known distance on your floor plan (e.g., room width)
   - Measure the pixel distance in an image editor
   - Calculate: `scale = real_meters / pixel_distance`

2. **Update Calibration**
   - Use the scale input when uploading
   - Or update later via API: `POST /maps/<id>/calibrate`

### IMU Calibration

The dead-reckoning system includes automatic calibration:
- **Accelerometer bias**: Removed during stationary periods
- **Gyroscope bias**: Compensated for drift
- **Gravity removal**: Automatically subtracted from acceleration

For best results:
1. Keep iPhone stationary for 5 seconds before starting
2. Hold iPhone in consistent orientation
3. Avoid rapid rotations

## Troubleshooting

### No Position Updates

**Check:**
1. Navigation session is started (green status indicator)
2. iPhone IMU app is connected and sending data
3. Server is receiving data (check `/stats` endpoint)
4. No firewall blocking UDP port 65000

**Solution:**
- Restart navigation session
- Check server logs for errors
- Verify iPhone app configuration

### Position Drift

**Causes:**
- IMU sensor noise and bias
- Accelerometer integration error accumulation
- Incorrect initial position or heading

**Solutions:**
- Reset position periodically using known landmarks
- Implement magnetic heading correction (M3.2)
- Use Kalman filter for sensor fusion (M3.3)

### Map Not Loading

**Check:**
1. Map is uploaded successfully
2. Map is activated (selected in dropdown)
3. Image file exists in `maps/` directory
4. Browser console for errors

**Solution:**
- Re-upload map
- Refresh maps list
- Check server logs

### Trail Not Showing

**Check:**
1. Trail toggle is enabled (📍 button)
2. Position history has data points
3. Canvas rendering is working

**Solution:**
- Toggle trail off and on
- Restart navigation session
- Refresh page

## API Reference

### Map Management

```bash
# Upload map
POST /maps/upload
Content-Type: multipart/form-data
Body: file, name, scale_meters_per_pixel, origin_x, origin_y

# List maps
GET /maps

# Get map
GET /maps/<map_id>

# Delete map
DELETE /maps/<map_id>

# Activate map
POST /maps/<map_id>/activate

# Get map image
GET /maps/<map_id>/image
```

### Navigation

```bash
# Start navigation
POST /navigation/start
Body: {"initial_x": 0, "initial_y": 0, "initial_heading": 0}

# Stop navigation
POST /navigation/stop
Body: {"session_id": "nav_xxx"}

# Get current position
GET /navigation/position

# Get position history
GET /navigation/history?limit=100

# Reset position
POST /navigation/reset
Body: {"x": 0, "y": 0, "heading": 0}
```

## Advanced Features

### Multiple Maps

- Upload multiple floor plans for different areas
- Switch between maps using the dropdown
- Each map maintains its own calibration

### Position History

- System stores last 1000 position points
- Export history via API for analysis
- Replay navigation sessions (future feature)

### Real-time Updates

- Position updates at 10 Hz (100ms intervals)
- IMU data processed at sensor rate (typically 50-100 Hz)
- Canvas renders at 60 FPS for smooth visualization

## Performance Tips

1. **Map Size**: Use reasonably sized images (< 5MB)
2. **Trail Length**: Limit history to 500 points for smooth rendering
3. **Update Rate**: 10 Hz provides good balance of smoothness and performance
4. **Browser**: Use modern browsers (Chrome, Firefox, Safari) for best performance

## Next Steps

- **M3.2**: Implement magnetic heading correction for improved accuracy
- **M3.3**: Add Kalman filter for sensor fusion
- **M6**: Integrate with magnetic fingerprinting for position correction
- **M7**: Test with rover platform

## Support

For issues or questions:
1. Check server logs: `bramps_server.log`
2. Review scratchpad: `.cursor/scratchpad.md`
3. Test with debug endpoints: `/debug`, `/stats`

## License

Part of the BRAMPS (Bram's Universal Navigation System) project.

