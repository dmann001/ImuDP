# 🌐 Network Access Guide for BRAMPS HTML Interfaces

## ✅ **Routes Added Successfully!**

You can now access all BRAMPS HTML interfaces directly through your network using these URLs:

## 📱 **Access from Any Device on Your Network**

### **Main Interfaces:**

#### **1. Magnetic Fingerprint Mapping** 
```
http://10.75.173.146:5000/mapping.html
```
- **Purpose**: GPS-enabled magnetic fingerprint collection
- **Best for**: Real mapping sessions with GPS coordinates
- **Use on**: iPhone Safari for real GPS data

#### **2. Real-time Visualization (BRAMPS Viz)**
```
http://10.75.173.146:5000/visualization.html
```
- **Purpose**: Live magnetic fingerprint visualization dashboard  
- **Best for**: Monitoring mapping operations in real-time
- **Use on**: PC browser or tablet for large screen viewing

#### **3. Basic IMU Monitor**
```
http://10.75.173.146:5000/index.html
```
- **Purpose**: Simple IMU data monitoring
- **Best for**: Testing iPhone IMU app connection
- **Use on**: Any browser for basic monitoring

#### **4. Server Root (Auto-redirect)**
```
http://10.75.173.146:5000/
```
- **Purpose**: Automatically serves the best available interface
- **Fallback**: Shows server status and available endpoints

## 🎯 **Recommended Workflow**

### **For Real GPS Mapping:**
1. **iPhone Safari**: Open `http://10.75.173.146:5000/mapping.html`
2. **Grant location permissions** when prompted
3. **Start mapping session** and walk around
4. **PC Browser**: Open `http://10.75.173.146:5000/visualization.html` to watch live

### **For Testing/Demo:**
1. **PC Browser**: Open `http://10.75.173.146:5000/visualization.html`
2. **iPhone IMU App**: Send data to server
3. **Run bridge script**: `python imu_bridge.py` (for simulated GPS)
4. **Watch live visualization** of magnetic fingerprinting

## 🔧 **Server Endpoints Available**

### **HTML Interfaces:**
- `/` - Auto-serve best interface
- `/mapping.html` - GPS mapping interface
- `/visualization.html` - Real-time visualization
- `/index.html` - Basic IMU monitor
- `/iphone_monitor.html` - iPhone-specific monitor

### **API Endpoints:**
- `/imu` - Receive IMU data (POST)
- `/mapping/start` - Start mapping session (POST)
- `/mapping/stop` - Stop mapping session (POST)
- `/mapping/data` - Send mapping data (POST)
- `/mapping/sessions` - List sessions (GET)
- `/mapping/fingerprints` - Get fingerprints (GET)
- `/stats` - Server statistics (GET)
- `/health` - Health check (GET)

## 📱 **Device-Specific Instructions**

### **iPhone (Real GPS):**
1. Open Safari
2. Go to: `http://10.75.173.146:5000/mapping.html`
3. Allow location access
4. Configure your IMU app to send to: `http://10.75.173.146:5000/imu`
5. Start both mapping session and IMU streaming

### **PC/Laptop (Visualization):**
1. Open any browser
2. Go to: `http://10.75.173.146:5000/visualization.html`
3. Connect to server
4. Start mapping session
5. Watch real-time magnetic fingerprint visualization

### **Tablet (Dashboard):**
- Use `visualization.html` for large-screen monitoring
- Perfect for field operations dashboard

## 🔍 **Troubleshooting**

### **"Page not found" errors:**
- Make sure server is running: `python server.py`
- Check IP address is correct: `10.75.173.146`
- Verify you're on the same network

### **"Connection failed" in visualization:**
- Server URL should be: `http://10.75.173.146:5000` (no trailing slash)
- Make sure BRAMPS modules are installed: `pip install -r requirements.txt`

### **No GPS data:**
- Use iPhone Safari for real GPS: `http://10.75.173.146:5000/mapping.html`
- Grant location permissions when prompted
- For testing, use the bridge script: `python imu_bridge.py`

## 🎉 **What's New**

✅ **Direct network access** to all HTML interfaces
✅ **Cross-device compatibility** - access from any device on network
✅ **Real GPS support** via iPhone Safari browser
✅ **Static file serving** for CSS, JS, and other assets
✅ **Error handling** with helpful error messages

## 🚀 **Ready to Use!**

Your BRAMPS system now supports full network access. You can:
- **Map with iPhone GPS** using Safari
- **Visualize in real-time** on PC browser  
- **Monitor from multiple devices** simultaneously
- **Access all interfaces** from anywhere on your network

**Start mapping now**: `http://10.75.173.146:5000/mapping.html` 📍
