# 📱 iPhone IMU App Visualization Guide

This guide shows you how to use your existing iPhone IMU app with the BRAMPS magnetic fingerprinting visualization system.

## 🎯 What You'll See

The visualization will show:
- **Real-time magnetic fingerprint mapping** as you move around
- **Movement trail** showing your path
- **Quality-colored dots** (blue=high quality, yellow=medium, red=low)
- **Live statistics** (fingerprint count, data rate, coverage area)
- **Current position** with pulsing green indicator

## 🚀 Quick Start (3 Steps)

### Step 1: Start the BRAMPS Server
```bash
# In your project directory
python server.py
```
The server will start on `http://localhost:5000`

### Step 2: Start Your iPhone IMU App
- Configure your iPhone IMU app to send data to: `http://YOUR_COMPUTER_IP:5000/imu`
- Start streaming IMU data from your iPhone
- You should see data appearing in the server logs

### Step 3: Open the Visualization
- Open `visualization.html` in your web browser
- Click "Connect to Server" 
- Click "Start Mapping"
- Move around with your iPhone to see real-time mapping!

## 🔧 Advanced Setup (With GPS Bridge)

For more realistic magnetic fingerprinting with simulated GPS movement:

### Step 1: Start Server & iPhone App (same as above)

### Step 2: Run the IMU Bridge
```bash
# This adds GPS coordinates to your IMU data
python imu_bridge.py
```

### Step 3: Open Visualization
- Open `visualization.html` in your browser
- You'll see automatic mapping with simulated GPS movement

## 📊 What Each Interface Shows

### Visualization Interface (`visualization.html`)
- **Real-time map** with magnetic fingerprints
- **Movement trail** showing your path
- **Quality indicators** (color-coded dots)
- **Live statistics** and data rates
- **Control panel** for connection and mapping

### Mapping Interface (`mapping.html`) 
- **Manual GPS entry** for precise location mapping
- **Session management** with device tracking
- **Real-time sensor data** display
- **Quality scoring** and fingerprint statistics

### IMU Monitor (`index.html`)
- **Raw sensor data** from your iPhone
- **Connection status** and data rates
- **Basic IMU visualization**

## 🎛️ Visualization Controls

### Connection Panel
- **Server URL**: Usually `http://localhost:5000`
- **Connect Button**: Establishes connection to BRAMPS server
- **Status Indicator**: Green=connected, Red=disconnected

### Mapping Panel  
- **Device ID**: Identifier for your iPhone (auto-generated)
- **Start/Stop Mapping**: Controls fingerprint collection
- **Session Status**: Shows active mapping session

### Display Options
- **Show Movement Trail**: Toggle path visualization
- **Color by Quality**: Color-code dots by magnetic field quality
- **Show Magnetic Anomalies**: Highlight unusual magnetic readings
- **Clear Display**: Reset the visualization

### Statistics Panel
- **Fingerprints**: Total magnetic fingerprints collected
- **Rate/sec**: Data collection rate
- **Avg Quality**: Average quality score (0-1)
- **Coverage**: Estimated area covered (m²)

## 🗺️ Understanding the Map

### Color Coding
- 🔵 **Blue dots**: High quality fingerprints (>0.8)
- 🟡 **Yellow dots**: Medium quality fingerprints (0.5-0.8)  
- 🔴 **Red dots**: Low quality fingerprints (<0.5)
- 🟢 **Green pulsing**: Your current position
- 🔵 **Blue line**: Movement trail

### Map Features
- **Auto-centering**: Map automatically centers on your data
- **Auto-scaling**: Zoom adjusts to fit all fingerprints
- **Grid overlay**: 10-meter grid for scale reference
- **Coordinates display**: Shows current lat/lon/altitude/magnetic field

## 🔍 Troubleshooting

### "Connection Failed"
- Make sure the server is running: `python server.py`
- Check the server URL (usually `http://localhost:5000`)
- Verify your firewall isn't blocking the connection

### "No Data Appearing"
- Ensure your iPhone IMU app is sending data to the correct URL
- Check server logs for incoming data
- Verify the iPhone and computer are on the same network

### "GPS Not Working"
- The bridge script simulates GPS movement for demonstration
- For real GPS, you'd need to modify the bridge to use actual coordinates
- The mapping interface can accept manual GPS coordinates

### "Poor Quality Scores"
- Quality is based on comparison with the World Magnetic Model
- Indoor environments may have magnetic interference
- Try moving to different locations to see quality variations

## 📱 iPhone IMU App Configuration

Your iPhone IMU app should send JSON data like this to `/imu`:
```json
{
  "accel_x": 0.1,
  "accel_y": 0.2, 
  "accel_z": 9.8,
  "gyro_x": 0.01,
  "gyro_y": 0.02,
  "gyro_z": 0.03,
  "timestamp": 1699123456789
}
```

## 🎯 Use Cases

### Indoor Mapping
- Walk around a building to create magnetic fingerprint map
- Identify areas with magnetic anomalies (metal structures, electronics)
- Build reference database for indoor navigation

### Outdoor Surveying  
- Map magnetic field variations in an area
- Compare measured field with World Magnetic Model predictions
- Identify geological or man-made magnetic anomalies

### Navigation Testing
- Test dead-reckoning algorithms with real sensor data
- Validate magnetic heading correction methods
- Evaluate sensor fusion performance

## 🔧 Customization

### Modify GPS Simulation
Edit `imu_bridge.py` to change the movement pattern:
```python
# In simulate_gps_movement() function
radius = 0.0001  # Change movement radius
angle = elapsed * 0.1  # Change movement speed
```

### Adjust Visualization
Edit `visualization.html` to customize:
- Colors and styling
- Update rates and polling intervals  
- Grid spacing and scale
- Statistics calculations

### Add Real GPS
Replace the GPS simulation in `imu_bridge.py` with actual GPS coordinates from your device.

## 📈 Next Steps

Once you have magnetic fingerprints collected:
1. **Analyze the data** using the fingerprint storage system
2. **Implement dead-reckoning** with magnetic heading correction
3. **Test navigation algorithms** using your collected fingerprint database
4. **Expand to sensor fusion** with Kalman filtering

The visualization provides a foundation for understanding how magnetic fingerprinting works in real-time with your actual device sensors!
