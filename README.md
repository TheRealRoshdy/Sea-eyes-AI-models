# SeaEyes: Smart Anti-Collision System for Vessels

**SeaEyes** is a low-cost, AI-powered collision avoidance system developed for small maritime vessels operating in constrained environments like the Nile River. It combines ultrasonic, sonar, GPS, laser distance sensors, and computer vision to provide real-time situational awareness and environmental monitoring.

## ⚓ System Overview

SeaEyes is designed to enhance safety and awareness for local boat operators using:

- **Embedded Sensors** (Ultrasonic, Sonar, GPS, TfMini+ LiDAR emulator)
- **YOLOv11 + MiDaS** for object detection and monocular depth estimation
- **Raspberry Pi 4B** as the main processing unit
- **Firebase** for real-time cloud synchronization
- **Web-Based Control Room** for monitoring vessel conditions remotely

## 🔧 Hardware Components

- **Raspberry Pi 4 Model B**
- **4× HC-SR04 Ultrasonic Sensors**
- **JSN-SR04T Waterproof Sonar Sensor**
- **TfMini-Plus Laser Distance Sensor (LiDAR Emulator)**
- **Raspberry Pi Camera v1.3**
- **GPS Module (u-blox NEO-6M)**
- **Servo Motor for Scanning LiDAR**

## 🧠 AI Integration

- **YOLOv11**: Real-time object detection (e.g., boats, buoys, obstacles)
- **MiDaS**: Depth estimation to calculate distance using pixel-to-real conversion
- **Fusion**: Bounding box height + focal length + object class height → Distance

## 🌐 Firebase-Based Cloud Dashboard

The cloud layer includes:

- Real-time data upload of all sensor readings (ultrasonic, sonar, GPS, laser)
- JSON-structured data logging
- Web-based control room (HTML + JS + Leaflet.js) showing:
  - Live vessel locations and movement
  - Static data (name, cargo, source/destination)
  - Danger alerts via ultrasonic readings
  - Siren warning system and visual feedback

## 📁 Repository Structure



## 📡 Data Flow

1. Sensor data collected by Raspberry Pi
2. YOLO detects objects; MiDaS estimates depth
3. Distances calculated and formatted in JSON
4. Data pushed to Firebase in real-time
5. Web dashboard visualizes vessel status, location, and risk level

## 🧪 Testing & Validation

- Object detection confirmed for multiple vessel types (kayak, sailboat, etc.)
- Distance accuracy: ±10 cm within 10 meters
- Cloud dashboard latency: <200ms average
- Field-tested on prototype vessel in riverine conditions

## 📌 Future Enhancements

- Offline data caching & upload
- LoRa-based V2V communication in cloud-limited zones
- AI-driven alert prioritization on control dashboard

---

### 🔗 Repository maintained by: [Mohamed Roshdy](https://www.linkedin.com/in/mohamed-roshdy2001)

