# BRAMPS Setup Guide - Complete Explanation

## 🏗️ Architecture Overview

### Three Main Components:

1. **Flask Server (`server.py`)** - The Central Hub
   - **Purpose**: Receives and stores sensor data from multiple sources
   - **Location**: Runs on your computer
   - **Ports**: 
     - HTTP: Port 5000 (for web browser data)
     - UDP: Port 65000 (for iPhone IMU app data)
   - **What it does**:
     - Receives sensor data via HTTP POST or UDP
     - Stores recent data (last 100 packets)
     - Provides statistics and data via API endpoints
     - Logs all received data

2. **iPhone IMU Utility App** - Mobile Sensor Source
   - **Purpose**: Sends sensor data FROM your iPhone TO the server
   - **Location**: Runs on your iPhone
   - **What it does**:
     - Reads accelerometer, gyroscope, magnetometer from iPhone
     - Sends data to server via UDP (port 65000)
   - **Data Flow**: iPhone → Server (UDP)

3. **index.html (Web Interface)** - Browser Interface
   - **Purpose**: 
     - **Option A**: Sends sensor data FROM browser TO server (if browser has sensors)
     - **Option B**: Displays data received by server FROM iPhone IMU app
   - **Location**: Served by Flask server or opened directly in browser
   - **What it does**:
     - Can send browser sensor data to server (HTTP POST)
     - Can display data received from iPhone IMU app (by polling server)
   - **Data Flow**: Browser → Server (HTTP) OR Server → Browser (for display)

---

## 📱 iPhone IMU Utility App Setup

### Configuration in Your iPhone App:

1. **Host/IP address**: `10.75.173.146`
   - This is your computer's IP address on the local network
   - The app will send data TO this address

2. **UDP Port**: `65000`
   - This is the UDP port the server listens on
   - Make sure this matches in your app

3. **Data format**: `JSON`
   - The server expects JSON format

4. **Data Forwarding Rate**: `10.0 Hz` (or your preferred rate)
   - How often the app sends data (10 times per second)

5. **Display Update Rate**: `15 Hz` (optional, for app's own display)

6. **Chart Update Rate**: `15 Hz` (optional, for app's own display)

### Steps:
1. Open your iPhone IMU Utility App
2. Go to Setup screen
3. Enter the settings above
4. Click "Connect" button
5. Click "Start" button
6. Your iPhone will now send sensor data to the server!

---

## 🌐 index.html Setup

### Current Purpose:
The `index.html` file can do TWO things:

#### Option 1: Send Browser Sensor Data (Current Functionality)
- If you open it on a device with sensors (mobile browser)
- It reads accelerometer/gyroscope/magnetometer from the browser
- Sends that data to the server
- **Server Configuration**: `http://10.75.173.146:5000`

#### Option 2: Display iPhone IMU App Data (We'll add this!)
- Shows data that was sent by your iPhone IMU app
- Polls the server to get the latest received data
- Displays it in real-time on the web page

### Setup for Option 1 (Sending Browser Data):

1. **Open the page**:
   - Option A: Go to `http://10.75.173.146:5000` in your browser
   - Option B: Open `index.html` file directly

2. **Configure Server**:
   - In "Server Configuration" field, enter: `http://10.75.173.146:5000`
   - This tells the browser where to send its sensor data

3. **Start Streaming**:
   - Click "Start Streaming" button
   - Grant permissions if prompted (iOS 13+)
   - Browser will send its sensor data to the server

### Setup for Option 2 (Displaying iPhone Data):

1. **Open the page**: `http://10.75.173.146:5000`

2. **View iPhone Data Section**:
   - A new section will show data received from your iPhone
   - Updates automatically every second
   - Shows the latest sensor values from your iPhone

---

## 🔄 Complete Data Flow

### Scenario 1: iPhone App → Server → Browser Display

```
iPhone IMU App (sends data)
    ↓ (UDP port 65000)
Flask Server (receives & stores)
    ↓ (HTTP GET /recent)
Browser (index.html displays it)
```

### Scenario 2: Browser → Server

```
Browser (index.html reads sensors)
    ↓ (HTTP POST /imu)
Flask Server (receives & stores)
```

### Scenario 3: Both Sources → Server

```
iPhone IMU App ──┐
                  ├──→ Flask Server (receives from both)
Browser (index.html) ┘
```

---

## ✅ Quick Setup Checklist

### Server Setup:
- [ ] Install Python dependencies: `pip install -r requirements.txt`
- [ ] Start server: `python server.py`
- [ ] Verify server is running on `http://10.75.173.146:5000`
- [ ] Check UDP listener started on port 65000

### iPhone IMU App Setup:
- [ ] Host/IP: `10.75.173.146`
- [ ] UDP Port: `65000`
- [ ] Data format: `JSON`
- [ ] Click "Connect"
- [ ] Click "Start"

### Browser (index.html) Setup:
- [ ] Open `http://10.75.173.146:5000`
- [ ] Server Configuration: `http://10.75.173.146:5000`
- [ ] (Optional) Click "Start Streaming" to send browser sensor data
- [ ] View "Data from iPhone IMU App" section to see iPhone data

---

## 🎯 What You'll See

### In Server Logs:
```
Received packet #10 [UDP] - Accel: (0.12, -0.45, 9.81), ...
Received packet #20 [HTTP] - Accel: (0.15, -0.42, 9.80), ...
```

### In Browser (index.html):
- Real-time sensor values from iPhone
- Statistics (packet count, rate)
- Last update timestamp

### In iPhone App:
- Your app's own sensor display
- Connection status

---

## 🔍 Troubleshooting

**iPhone app not connecting?**
- Check iPhone and computer are on same Wi-Fi
- Verify server IP is correct: `10.75.173.146`
- Check Windows Firewall allows UDP port 65000

**Browser not showing iPhone data?**
- Make sure iPhone app is sending data (check server logs)
- Refresh the browser page
- Check browser console for errors

**Server not receiving data?**
- Verify server is running
- Check firewall settings
- Look at server logs for errors

