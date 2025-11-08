# BRAMPS - Universal Navigation System

## Module M1: Phone IMU & Magnetometer Streaming

This module implements real-time streaming of IMU (accelerometer, gyroscope) and magnetometer data from a mobile device to a Flask server.

### Setup Instructions

#### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

#### 2. Start the Flask Server

```bash
python server.py
```

The server will start on `http://localhost:5000` by default.

To listen on all network interfaces (for mobile device access):
```bash
HOST=0.0.0.0 python server.py
```

To use a different port:
```bash
PORT=8080 python server.py
```

#### 3. Open the Web Interface

1. Open `index.html` in a web browser
2. For mobile devices, you'll need to access the HTML file via a web server or host it
3. Enter the server IP address (e.g., `http://192.168.1.100:5000` for network access)
4. Click "Start Streaming" to begin sending sensor data

### Features

- **Real-time Sensor Access**: Accesses device accelerometer, gyroscope, and magnetometer
- **JSON POST to Server**: Sends sensor data to Flask server at `/imu` endpoint
- **Start/Stop Controls**: Demo control buttons for streaming
- **Live Visualization**: Real-time display of sensor values
- **Statistics**: Packet count, stream rate, and latency tracking
- **Error Handling**: Graceful handling of unsupported browsers and connection errors

### API Endpoints

**HTTP Endpoints:**
- `POST /imu` - Receive IMU and magnetometer data (HTTP POST)
- `GET /stats` - Get server statistics
- `GET /health` - Health check
- `GET /recent?limit=100` - Get recent sensor data packets

**UDP Endpoint:**
- `UDP Port 65000` - Receive IMU and magnetometer data via UDP (for mobile apps)
  - Default port: 65000 (configurable via `UDP_PORT` environment variable)
  - Expects JSON format data
  - Same data format as HTTP POST endpoint

### Browser Compatibility

- **iOS 13+**: Requires permission prompt for device motion
- **Android**: Works with Chrome and other modern browsers
- **Desktop**: Limited sensor support (for testing server only)

### Testing

#### Automated Server Testing

Test the server functionality with the provided test script:

```bash
# Make sure server is running first
python server.py

# In another terminal, run the test script
python test_server.py
```

The test script will:
- Test health check endpoint
- Test IMU data endpoint
- Test statistics endpoint
- Test continuous streaming (10 packets)

#### Manual Mobile Device Testing

1. **Start the Flask server (already running):**
   ```bash
   # The server is already configured to listen on all interfaces (0.0.0.0)
   python server.py
   ```
   Your server will show the IP addresses it's running on, for example:
   ```
   * Running on http://127.0.0.1:5000      (localhost only)
   * Running on http://10.75.173.146:5000   (network access - USE THIS!)
   UDP listener: udp://0.0.0.0:65000       (UDP for mobile apps)
   ```
   
   **Note:** The server now supports both HTTP POST and UDP protocols simultaneously!

2. **Find your server IP address:**
   - The server output shows it: `Running on http://10.75.173.146:5000`
   - Or manually check:
     - **Windows**: Open Command Prompt, type `ipconfig`, look for "IPv4 Address"
     - **Linux/Mac**: Type `ifconfig` or `ip addr`, look for your Wi-Fi adapter's IP

3. **Access from your phone:**
   - Make sure your phone is on the **same Wi-Fi network** as your computer
   - Open your phone's browser (Chrome, Safari, etc.)
   - Type the network IP address in the address bar:
     ```
     http://10.75.173.146:5000
     ```
   - The BRAMPS interface should load automatically!

4. **If it doesn't work - Windows Firewall:**
   - Windows may block the connection. To allow it:
     - Press `Win + R`, type `wf.msc`, press Enter
     - Click "Inbound Rules" → "New Rule"
     - Select "Port" → Next
     - Select "TCP", enter port `5000` → Next
     - Select "Allow the connection" → Next
     - Check all profiles → Next
     - Name it "Flask Server" → Finish
   - Or temporarily disable Windows Firewall for testing (not recommended for production)

5. **Configure and test:**
   
   **For Web Browser (index.html):**
   - Enter server URL (e.g., `http://10.75.173.146:5000`)
   - Click "Start Streaming"
   - Grant permissions if prompted (iOS 13+)
   
   **For iPhone IMU App (UDP):**
   - Host/IP address: `10.75.173.146:5000/imu` (or just `10.75.173.146`)
   - UDP Port: `65000`
   - Data format: `JSON`
   - Data Forwarding Rate: `10.0 Hz` (or your preferred rate)
   - Click "Connect" then "Start"
   
   **Observe:**
   - Sensor values updating in real-time
   - Server logs showing received packets (`bramps_server.log`)
   - Statistics updating (packet count, stream rate)
   - Logs will show `[HTTP]` or `[UDP]` to indicate the source

6. **Verify data integrity:**
   - Check server logs for received packets
   - Verify all sensor fields are present (accel_x/y/z, gyro_x/y/z, mag_x/y/z)
   - Check statistics endpoint: `http://YOUR_IP:5000/stats`
   - Verify latency is reasonable (< 100ms typically)

### Troubleshooting

- **Sensors not working**: Ensure you're using a mobile device with a modern browser
- **Connection errors**: Check that the server IP address is correct and the server is running
- **UDP not receiving data**: 
  - Verify Windows Firewall allows UDP port 65000
  - Check that phone and computer are on the same Wi-Fi network
  - Verify the UDP port in your app matches the server (default: 65000)
- **Permission denied (iOS)**: Allow device motion access when prompted
- **CORS errors**: The server includes CORS headers, but ensure the URL is correct
- **Port conflicts**: Change UDP port with `UDP_PORT=12345 python server.py` if needed

### Next Steps

After M1 is complete, proceed to:
- **M2**: Magnetic Fingerprint & NASA Model Integration
- **M3**: Dead-Reckoning & Sensor Fusion

