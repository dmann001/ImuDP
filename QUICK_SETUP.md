# 🚀 Quick Setup Guide - BRAMPS

## 📋 What Each Component Does

### 1. **Flask Server (`server.py`)**
- **Purpose**: Central hub that receives sensor data
- **What it does**: 
  - Listens for data on HTTP port 5000
  - Listens for data on UDP port 65000
  - Stores all received data
  - Provides API endpoints to view data

### 2. **iPhone IMU Utility App**
- **Purpose**: Sends sensor data FROM your iPhone TO the server
- **What it does**:
  - Reads iPhone's accelerometer, gyroscope, magnetometer
  - Sends data to server via UDP

### 3. **index.html (Web Page)**
- **Purpose**: TWO functions:
  1. **Sends** browser sensor data TO server (if browser has sensors)
  2. **Displays** data received FROM iPhone IMU app (NEW!)

---

## ⚙️ Complete Setup Instructions

### Step 1: Start the Server

```bash
# Install dependencies (first time only)
pip install -r requirements.txt

# Start the server
python server.py
```

**You should see:**
```
HTTP server: http://0.0.0.0:5000/imu
UDP listener: udp://0.0.0.0:65000
UDP listener thread started
```

**Note your IP address** (e.g., `10.75.173.146`)

---

### Step 2: Configure iPhone IMU Utility App

1. **Open your iPhone IMU Utility App**
2. **Go to Setup screen**
3. **Enter these settings:**

   | Setting | Value |
   |---------|-------|
   | **Host/IP address** | `10.75.173.146` |
   | **UDP Port** | `65000` |
   | **Data format** | `JSON` |
   | **Data Forwarding Rate** | `10.0 Hz` (or your preference) |

4. **Click "Connect"** button
5. **Click "Start"** button

✅ Your iPhone is now sending data to the server!

---

### Step 3: Open index.html in Browser

1. **Open browser** (on computer or phone)
2. **Go to**: `http://10.75.173.146:5000`
   - (Replace with your actual server IP)

3. **You'll see TWO sections:**

   **Section 1: Browser Sensor Data (Top)**
   - Shows data FROM the browser's sensors
   - To use: Enter server URL and click "Start Streaming"
   - **Server Configuration**: `http://10.75.173.146:5000`

   **Section 2: iPhone IMU App Data (Bottom)** ⭐ NEW!
   - Shows data FROM your iPhone IMU app
   - Updates automatically every second
   - No configuration needed - just works!

---

## 📊 What You'll See

### In Browser (index.html):

**Top Section - Browser Data:**
- Accelerometer, Gyroscope, Magnetometer (from browser)
- Statistics (packets sent from browser)

**Bottom Section - iPhone Data:** ⭐
- Accelerometer, Gyroscope, Magnetometer (from iPhone)
- Server Statistics (total packets from all sources)
- Connection Status (✓ Connected / Waiting...)

### In Server Logs:

```
Received packet #10 [UDP] - Accel: (0.12, -0.45, 9.81), ...
Received packet #20 [HTTP] - Accel: (0.15, -0.42, 9.80), ...
```

---

## ✅ Quick Checklist

- [ ] Server running (`python server.py`)
- [ ] Server shows UDP listener started
- [ ] iPhone app configured:
  - [ ] Host: `10.75.173.146` (your IP)
  - [ ] UDP Port: `65000`
  - [ ] Data format: `JSON`
  - [ ] Clicked "Connect"
  - [ ] Clicked "Start"
- [ ] Browser opened: `http://10.75.173.146:5000`
- [ ] See "Data from iPhone IMU App" section
- [ ] See sensor values updating from iPhone

---

## 🔧 Troubleshooting

**iPhone data not showing?**
- Check iPhone app is "Connected" and "Start" is active
- Check server logs for `[UDP]` messages
- Verify iPhone and computer on same Wi-Fi
- Check Windows Firewall allows UDP port 65000

**Browser not loading?**
- Verify server IP is correct
- Check server is running
- Try `http://localhost:5000` if on same computer

**No data in iPhone section?**
- Wait a few seconds (updates every 1 second)
- Check server is receiving data (look at logs)
- Refresh browser page

---

## 🎯 Summary

1. **Server** = Receives data from both sources
2. **iPhone App** = Sends data TO server (UDP)
3. **index.html** = 
   - Can send browser data TO server (HTTP)
   - **Displays iPhone data FROM server** (NEW!)

**Data Flow:**
```
iPhone App → (UDP) → Server → (HTTP GET) → Browser Display
Browser → (HTTP POST) → Server
```

Both work simultaneously! 🎉

