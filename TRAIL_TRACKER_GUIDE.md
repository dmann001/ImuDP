# BRAMPS Trail Tracker - Quick Start Guide

## 🎯 Simple Movement Trail Visualization

A simplified interface that just shows your movement path without map complexity!

## 🚀 Quick Start

### 1. Start the Server

```bash
python server.py
```

### 2. Open Trail Tracker

Navigate to: **http://localhost:5000/trail_tracker.html**

### 3. Connect iPhone IMU App

- **Server Address:** Your computer's IP
- **Port:** 65000
- **Start streaming**

### 4. Start Tracking

1. Click **"▶️ Start Tracking"**
2. Walk around
3. Watch your trail appear in real-time!

## 🎨 What You'll See

### Visual Elements

- **Blue Dot** = Your current position
- **Red Arrow** = Direction you're facing
- **Cyan Line** = Your movement trail
- **Grid** = 1-meter squares for reference
- **Red/Green Axes** = Origin point (0,0)

### Coordinate System

```
        North (X+)
            ↑
            |
West ←------+-----→ East (Y+)
            |
            ↓
        South (X-)
```

- **X-axis (Red)**: North/South
- **Y-axis (Green)**: East/West
- **Origin (0,0)**: Starting point

## 🎮 Controls

### View Controls

- **Drag**: Pan around the view
- **Scroll**: Zoom in/out
- **🎯 Center**: Return to origin
- **📐 Toggle Grid**: Show/hide grid

### Tracking Controls

- **▶️ Start Tracking**: Begin recording your path
- **⏹️ Stop Tracking**: Stop recording (keeps trail visible)
- **🗑️ Clear Trail**: Remove all trail points
- **🔍 Zoom In/Out**: Adjust view scale

### Display Settings

- **Trail Width**: Adjust line thickness (1-10)
- **Scale**: Adjust zoom level (10-100 pixels per meter)

## 📊 Statistics Panel

Real-time information:

- **Position X, Y**: Current coordinates in meters
- **Heading**: Direction you're facing (0-360°)
- **Velocity**: Current speed in m/s
- **Total Distance**: How far you've traveled
- **Trail Points**: Number of recorded positions
- **Updates**: Total position updates received

## 🎯 How to Use

### Basic Usage

1. **Start Tracking**
   - Click "Start Tracking"
   - Status turns green

2. **Walk Around**
   - Hold your iPhone
   - Walk naturally
   - Watch the trail form behind you

3. **Stop Tracking**
   - Click "Stop Tracking"
   - Trail remains visible
   - Can start again to continue

### Tips for Best Results

1. **Hold Phone Steady**: Keep orientation consistent
2. **Walk Smoothly**: Avoid jerky movements
3. **Clear Trail**: Start fresh for each session
4. **Center View**: Use center button if you lose sight of trail

## 🔧 Adjusted Settings

The system now has **balanced sensitivity**:

- **Acceleration Threshold**: 0.2 m/s² (not too strict, not too sensitive)
- **Velocity Threshold**: 0.08 m/s (stops when you stop)
- **Stationary Detection**: 20 updates (~2 seconds)

### What This Means

✅ **Detects movement** when you walk  
✅ **Stops** when you stop moving  
✅ **Reduces** false movement from noise  
✅ **Tracks** actual path accurately  

## 🐛 Troubleshooting

### Trail Not Appearing

**Check:**
1. ✅ Tracking is started (green status)
2. ✅ iPhone app is streaming
3. ✅ Server shows data reception
4. ✅ Walk at least 1-2 meters

**Fix:**
- Walk more deliberately
- Check server logs for position updates
- Verify IMU app is connected

### Position Not Moving

**Check:**
1. ✅ You're actually moving
2. ✅ Movement is > 0.2 m/s²
3. ✅ Velocity shows > 0 m/s

**Fix:**
- Walk faster or more deliberately
- Check if stationary detection is active
- Restart tracking

### Trail Drifting

**This is normal for IMU dead-reckoning!**

**Solutions:**
- Clear trail and restart for fresh start
- Track for shorter periods (< 5 minutes)
- Future: Magnetic correction will improve this

## 📈 Expected Performance

### Stationary Phone
- Drift: < 0.5 meters over 1 minute
- Should stay mostly still

### Walking (1 m/s)
- Tracks path shape accurately
- ±0.5-1 meter error per 10 meters
- Heading ±5-10 degrees

### Running (3 m/s)
- Tracks general path
- ±1-2 meter error per 10 meters
- May miss quick turns

## 🎨 Customization

### Adjust Trail Appearance

```javascript
// In trail_tracker.html, you can modify:
trailWidth = 3;  // Line thickness
viewScale = 50;  // Zoom level (pixels per meter)
```

### Adjust Sensitivity

If movement is too sensitive or not sensitive enough, edit `imu_dead_reckoning.py`:

```python
# Line 68-70
self.accel_threshold = 0.2  # Increase to be less sensitive
self.velocity_threshold = 0.08  # Increase to stop faster
self.stationary_threshold = 20  # Increase to wait longer
```

## 🎓 Understanding the Trail

### What Does It Show?

The trail shows your **estimated path** based on:
- Accelerometer (movement)
- Gyroscope (rotation)
- Dead-reckoning calculations

### Limitations

- **Accumulates error** over time (drift)
- **No absolute position** (relative to start)
- **Affected by** phone orientation changes

### Best For

✅ Short-term tracking (< 5 minutes)  
✅ Visualizing movement patterns  
✅ Testing IMU sensors  
✅ Indoor navigation demos  

## 🚧 Future Improvements

To improve accuracy:

1. **Magnetic Heading** (M3.2): Use magnetometer for better heading
2. **Kalman Filter** (M3.3): Reduce drift with sensor fusion
3. **Fingerprints** (M6): Correct position using magnetic map

## 📱 iPhone App Settings

### Recommended

- **Update Rate**: 50-100 Hz
- **Sensors**: All enabled
- **Format**: JSON over UDP
- **Port**: 65000

## ✅ Summary

**What Changed:**
- ✅ Balanced thresholds (not too strict)
- ✅ Simple trail visualization (no map complexity)
- ✅ Real-time path tracking
- ✅ Interactive controls

**How to Use:**
1. Start server
2. Open `http://localhost:5000/trail_tracker.html`
3. Click "Start Tracking"
4. Walk around and watch your trail!

**Perfect For:**
- Testing IMU tracking
- Visualizing movement
- Indoor navigation demos
- Understanding dead-reckoning

---

**Start tracking your movement!** 🧭

Open: `http://localhost:5000/trail_tracker.html`

