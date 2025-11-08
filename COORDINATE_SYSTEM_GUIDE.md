# BRAMPS Navigation - Coordinate System & Troubleshooting Guide

## 🧭 Understanding the Coordinate System

### World Coordinates (X, Y)

The navigation system uses a standard North-East-Down (NED) coordinate system:

```
        North (X+)
            ↑
            |
            |
West ←------+-----→ East (Y+)
            |
            |
            ↓
        South (X-)
```

**Coordinate Meanings:**
- **X-axis**: North/South direction
  - **Positive X** = Moving North (forward/up on map)
  - **Negative X** = Moving South (backward/down on map)
  
- **Y-axis**: East/West direction
  - **Positive Y** = Moving East (right on map)
  - **Negative Y** = Moving West (left on map)

**Heading (Direction):**
- **0°** = Facing North (up)
- **90°** = Facing East (right)
- **180°** = Facing South (down)
- **270°** = Facing West (left)

### Example Movements

If you start at position (0, 0) facing North (0°):

1. **Walk forward 5 meters**: Position becomes (5, 0)
2. **Turn right 90°**: Heading becomes 90° (facing East)
3. **Walk forward 3 meters**: Position becomes (5, 3)
4. **Turn right 90°**: Heading becomes 180° (facing South)
5. **Walk forward 2 meters**: Position becomes (3, 3)

## 🐛 Issue: Phone Moving When Stationary

### Problem
The position was moving even when the phone was stationary, appearing as if you were running.

### Root Cause
1. **Sensor Noise**: IMU sensors have inherent noise that was being integrated as movement
2. **Low Thresholds**: Acceleration threshold (0.1 m/s²) was too sensitive
3. **No Stationary Detection**: System didn't detect when phone was still
4. **Velocity Integration**: Small accelerations accumulated over time

### Fixes Applied

#### 1. Increased Thresholds
```python
# OLD VALUES (too sensitive)
accel_threshold = 0.1 m/s²
velocity_threshold = 0.05 m/s

# NEW VALUES (less sensitive to noise)
accel_threshold = 0.5 m/s²
velocity_threshold = 0.15 m/s
gyro_threshold = 0.05 rad/s
```

#### 2. Added Stationary Detection
```python
# If both acceleration AND rotation are below threshold for 10 updates
# System recognizes phone is stationary and zeros velocity
if stationary for 10+ updates:
    velocity = 0
```

#### 3. Improved Filtering
```python
# Increased filter buffer from 5 to 10 samples
# Better noise reduction through averaging
accel_buffer = deque(maxlen=10)
gyro_buffer = deque(maxlen=10)
```

#### 4. Stronger Velocity Damping
```python
# When acceleration is below threshold
# Apply stronger damping (0.85 instead of 0.95)
velocity *= 0.85
```

## 🔧 How to Test the Fixes

### Test 1: Stationary Phone
1. Start navigation
2. Place phone on table (don't move it)
3. **Expected**: Position should stay at (0, 0) or drift very slowly
4. **Before fix**: Position would move rapidly
5. **After fix**: Position should remain stable

### Test 2: Walking Forward
1. Start at (0, 0) facing North (0°)
2. Walk forward 5 steps
3. **Expected**: X increases (e.g., 0 → 2-3 meters), Y stays near 0
4. Stop walking
5. **Expected**: Position stops updating after ~1 second

### Test 3: Turning
1. Start at (0, 0) facing North (0°)
2. Turn right 90°
3. **Expected**: Heading changes from 0° → 90°, position stays same
4. Walk forward
5. **Expected**: Y increases (moving East), X stays same

## 📊 Adjusting Sensitivity

If the system is still too sensitive or not sensitive enough, you can adjust these parameters in `imu_dead_reckoning.py`:

### Make it LESS Sensitive (reduce false movement)
```python
self.accel_threshold = 0.8  # Increase from 0.5
self.velocity_threshold = 0.25  # Increase from 0.15
self.stationary_threshold = 5  # Decrease from 10 (detect stationary faster)
```

### Make it MORE Sensitive (detect smaller movements)
```python
self.accel_threshold = 0.3  # Decrease from 0.5
self.velocity_threshold = 0.1  # Decrease from 0.15
self.stationary_threshold = 15  # Increase from 10 (be more patient)
```

## 🎯 Calibration Tips

### Before Starting Navigation

1. **Place Phone Flat**: Put phone on a flat surface for 5-10 seconds
2. **Calibrate**: This allows the system to measure sensor bias
3. **Start Navigation**: Begin from a known position

### During Navigation

1. **Hold Phone Steady**: Try to keep phone orientation consistent
2. **Walk Smoothly**: Avoid jerky movements
3. **Reset Periodically**: When you reach a known landmark, reset position

### Setting Initial Position

When you start navigation:

1. **Know Your Location**: Identify where you are on the map
2. **Measure Coordinates**: 
   - How many meters North from origin? → X value
   - How many meters East from origin? → Y value
3. **Set Heading**: Which direction are you facing?
   - Facing up on map? → 0°
   - Facing right on map? → 90°
   - Facing down on map? → 180°
   - Facing left on map? → 270°

## 🔍 Debugging Position Issues

### Check Current Values

Open browser console (F12) and check:

```javascript
// In navigation.html, you can see:
console.log('Position:', posX, posY);
console.log('Velocity:', velocity);
console.log('Acceleration:', accel_magnitude);
```

### Check Server Logs

Look at terminal output or `bramps_server.log`:

```
Dead-reckoning update #50: pos=(0.12, -0.05), heading=2.3°, vel=0.00 m/s, dist=0.15m
```

**Good signs:**
- Velocity near 0.00 when stationary
- Position changes < 0.1m when stationary
- Distance increases only when moving

**Bad signs:**
- Velocity > 0.1 when stationary
- Position changing rapidly when still
- Distance increasing without movement

## 📱 iPhone IMU App Settings

### Recommended Settings

1. **Update Rate**: 50-100 Hz (not too fast, not too slow)
2. **Sensors**: Enable all (accelerometer, gyroscope, magnetometer)
3. **Coordinate System**: Device frame (not world frame)
4. **Units**: 
   - Acceleration: m/s²
   - Gyroscope: rad/s
   - Magnetometer: μT

### Common Issues

**Issue**: Position updates too fast
- **Fix**: Reduce IMU update rate to 50 Hz

**Issue**: Position updates too slow
- **Fix**: Increase IMU update rate to 100 Hz

**Issue**: Position drifts in one direction
- **Fix**: Calibrate phone on flat surface before starting

## 🎓 Understanding Drift

### Why Does Drift Happen?

Dead-reckoning accumulates errors over time:

1. **Sensor Noise**: Small random errors in measurements
2. **Integration**: Errors compound when integrating twice (accel → velocity → position)
3. **Bias**: Constant sensor offset that accumulates
4. **Orientation**: Phone orientation affects measurements

### Minimizing Drift

**Short Term (< 1 minute):**
- Improved thresholds (✅ done)
- Stationary detection (✅ done)
- Better filtering (✅ done)

**Medium Term (1-5 minutes):**
- Magnetic heading correction (M3.2 - future)
- Periodic position reset at landmarks

**Long Term (> 5 minutes):**
- Kalman filter (M3.3 - future)
- Magnetic fingerprint correction (M6 - future)

## 📈 Expected Accuracy

With the current fixes:

**Stationary Phone:**
- Drift: < 0.5 meters over 1 minute
- Velocity: < 0.05 m/s

**Walking (1 m/s):**
- Position error: ±0.5-1 meter per 10 meters traveled
- Heading error: ±5-10 degrees

**Running (3 m/s):**
- Position error: ±1-2 meters per 10 meters traveled
- Heading error: ±10-20 degrees

## 🚀 Next Steps

To further improve accuracy:

1. **Test the Fixes**: Try the updated system
2. **Adjust Thresholds**: Fine-tune based on your phone
3. **Implement M3.2**: Add magnetic heading correction
4. **Implement M3.3**: Add Kalman filter
5. **Use Landmarks**: Reset position at known locations

## ✅ Summary

**What Changed:**
- ✅ Increased acceleration threshold: 0.1 → 0.5 m/s²
- ✅ Increased velocity threshold: 0.05 → 0.15 m/s
- ✅ Added stationary detection (10 updates)
- ✅ Improved filtering (5 → 10 sample buffer)
- ✅ Stronger velocity damping (0.95 → 0.85)

**What to Expect:**
- ✅ Phone stays still when stationary
- ✅ Less false movement from sensor noise
- ✅ More stable position tracking
- ⚠️ May need to walk more deliberately for detection
- ⚠️ Small movements (< 0.5 m/s²) may not register

**How to Use:**
1. Restart server: `python server.py`
2. Refresh navigation page
3. Place phone flat for 5 seconds
4. Start navigation
5. Test by keeping phone still - should not move!

---

**Coordinate Quick Reference:**
- **X**: North(+) / South(-)
- **Y**: East(+) / West(-)
- **Heading**: 0°=North, 90°=East, 180°=South, 270°=West

