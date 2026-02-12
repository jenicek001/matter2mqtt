# Matter on Raspberry Pi - Comprehensive Analysis & Implementation Plan
**Date:** February 2026  
**Objective:** Set up Matter controller on Raspberry Pi with SkyConnect (OpenThread firmware) to control IKEA Alpstuga and Timmerflotte devices using open-source tools, independent of Home Assistant/OpenHAB

---

## Executive Summary

Based on current research as of February 2026, implementing Matter on Raspberry Pi with your requirements is feasible using the following stack:

1. **OpenThread Border Router (OTBR)** running on Raspberry Pi
2. **SkyConnect dongle** with OpenThread RCP firmware (already done ✓)
3. **Matter Controller**: Either `chip-tool` (CLI) or `python-matter-server` (WebSocket API)
4. **IKEA Devices**: Alpstuga (air quality) and Timmerflotte (temp/humidity) - Matter-over-Thread sensors

**Complexity Level:** Intermediate to Advanced  
**Estimated Setup Time:** 4-8 hours  
**Current Maturity:** Matter 1.4/1.4.1 specification (May 2025 update)

---

## 1. Technology Stack Analysis

### 1.1 Protocol Layer Architecture

```
┌─────────────────────────────────────────────────────┐
│  Application Layer: Matter Controller               │
│  (chip-tool, python-matter-server, or custom app)  │
└─────────────────────────────────────────────────────┘
                      ↓ WebSocket/CLI
┌─────────────────────────────────────────────────────┐
│  Matter Protocol Layer (CSA Specification)          │
│  - Device commissioning                             │
│  - Command/control (OnOff, Temperature, etc.)       │
│  - Multi-admin support                              │
│  - Security (CASE, PASE)                            │
└─────────────────────────────────────────────────────┘
                      ↓ IP Transport
┌─────────────────────────────────────────────────────┐
│  Network Transport Layer                            │
│  Thread (802.15.4) ←→ Border Router ←→ Wi-Fi/Eth    │
│  IPv6 Mesh                   |                      │
└─────────────────────────────────────────────────────┘
                      ↓ Physical
┌─────────────────────────────────────────────────────┐
│  Hardware Layer                                      │
│  - SkyConnect (OpenThread RCP)                      │
│  - Raspberry Pi (Host)                              │
│  - IKEA Sensors (End devices)                       │
└─────────────────────────────────────────────────────┘
```

### 1.2 Component Descriptions

#### OpenThread Border Router (OTBR)
- **Purpose**: Bridges Thread mesh network to IP network (Ethernet/Wi-Fi)
- **Functions**:
  - IPv6 routing via 6LoWPAN
  - mDNS service discovery
  - Thread network management
  - NAT64 for IPv4 fallback
- **Installation**: Available as Docker container or native snap package
- **Status**: Mature, well-documented

#### Matter Controller Options

**Option A: chip-tool (Recommended for DIY)**
- **Type**: Command-line interface (CLI)
- **Pros**:
  - Official CSA implementation
  - Full Matter feature support
  - Easy installation via snap: `sudo snap install chip-tool`
  - Low resource usage
  - Direct cluster access
- **Cons**:
  - Command-line only (no GUI/API)
  - Manual commissioning steps
  - Not ideal for automation (unless scripted)

**Option B: python-matter-server**
- **Type**: WebSocket API server
- **Pros**:
  - WebSocket API for integration
  - Used by Home Assistant (but can run standalone)
  - Python SDK available
  - Web dashboard included
- **Cons**:
  - Higher resource usage
  - More complex setup
  - **NOTE**: Being rewritten in matter.js (in maintenance mode as of Q1 2026)
  - Docker-based installation recommended

**Option C: matter.js (Future)**
- **Type**: TypeScript/JavaScript implementation
- **Status**: Still in development (replace python-matter-server)
- **Availability**: Alpha expected Q2 2026

#### SkyConnect with OpenThread RCP
- **Model**: Home Assistant Connect ZBT-1
- **Firmware**: OpenThread RCP (already flashed ✓)
- **Chipset**: Silicon Labs EFR32MG21
- **Function**: Acts as Thread radio co-processor for OTBR
- **Status**: Ready to use

#### IKEA Matter Devices

**Timmerflotte (Temperature & Humidity Sensor)**
- **Model Number**: 506.189.57
- **Type**: Matter-over-Thread
- **Clusters**: Temperature Measurement, Relative Humidity Measurement
- **Battery**: Yes (low power)
- **Release**: Q4 2025 / Q1 2026
- **Price**: ~£5 / €5

**Alpstuga (Air Quality Sensor)**
- **Model Number**: 706.093.96
- **Type**: Matter-over-Thread
- **Clusters**: Air Quality, possibly PM2.5, CO2
- **Power**: Mains powered (£25 suggests always-on)
- **Release**: Q4 2025 / Q1 2026
- **Price**: ~£25 / €25

**Known Issues** (as of Feb 2026):
- Some users report pairing difficulties with various border routers
- Works best when placed physically close to border router during commissioning
- IKEA Dirigera hub firmware updates may be needed
- Multi-fabric support can be inconsistent

---

## 2. Software Stack Components

### 2.1 Required Software Packages

#### System Prerequisites (Raspberry Pi OS)
```bash
# System updates
sudo apt update && sudo apt upgrade -y

# Build tools (if building from source)
sudo apt install -y git cmake build-essential autoconf automake \
                    libtool pkg-config python3-pip libssl-dev \
                    libdbus-1-dev libglib2.0-dev ninja-build

# Network tools
sudo apt install -y avahi-daemon avahi-utils mdns-scan

# Python tools
pip3 install pyserial intelhex
```

#### OpenThread Border Router (OTBR)

**Installation Method 1: Snap Package (Easiest)**
```bash
sudo snap install openthread-border-router
```

**Installation Method 2: Docker (Recommended for isolation)**
```bash
# Pull official OTBR docker image
docker pull openthread/otbr:latest

# Run with SkyConnect device
docker run -d \
  --name otbr \
  --restart unless-stopped \
  --network host \
  --privileged \
  -v /dev:/dev \
  openthread/otbr:latest \
  --radio-url spinel+hdlc+uart:///dev/ttyUSB0?uart-baudrate=460800
```

**Installation Method 3: Build from Source**
- Repository: https://github.com/openthread/ot-br-posix
- More control, latest features
- Longer setup time

#### Matter Controller: chip-tool

**Installation via Snap (Recommended)**
```bash
sudo snap install chip-tool
```

**Verification**
```bash
chip-tool
# Should display help/version info
```

#### Matter Controller: python-matter-server (Alternative)

**Docker Installation**
```yaml
# docker-compose.yml
version: '3'
services:
  matter-server:
    container_name: matter-server
    image: ghcr.io/home-assistant-libs/python-matter-server:stable
    restart: unless-stopped
    network_mode: host
    security_opt:
      - apparmor=unconfined
    volumes:
      - ./matter-data:/data
      - /run/dbus:/run/dbus:ro
```

```bash
docker-compose up -d
```

**Access**: WebSocket server on `ws://localhost:5580`  
**Web Dashboard**: `http://localhost:5580` (if enabled)

### 2.2 Firmware Verification

Ensure SkyConnect has correct firmware:
```bash
# Check device connection
ls -la /dev/ttyUSB*  # or /dev/ttyACM*

# Verify with universal-silabs-flasher
pip3 install universal-silabs-flasher
python3 -m universal_silabs_flasher.flash --device /dev/ttyUSB0 probe
```

Expected output: OpenThread RCP firmware version (e.g., "SL-OPENTHREAD/2.4.4.0")

---

## 3. Network Architecture

### 3.1 Thread Network Structure

```
┌──────────────────┐
│  Raspberry Pi    │
│  ┌────────────┐  │          ┌─────────────────┐
│  │   OTBR     │  │          │ IKEA Timmerflotte│
│  │  (Docker)  │  │          │  (End Device)   │
│  └─────┬──────┘  │          └────────┬────────┘
│        │         │                   │
│  ┌─────▼──────┐  │     Thread        │
│  │ SkyConnect │◄─┼───────Mesh────────┤
│  │(RCP Radio) │  │    (802.15.4)     │
│  └────────────┘  │                   │
│                  │          ┌────────▼────────┐
│  ┌────────────┐  │          │ IKEA Alpstuga   │
│  │ chip-tool  │  │          │  (End Device or │
│  │(Controller)│  │          │   Router)       │
│  └────────────┘  │          └─────────────────┘
└──────────────────┘
        │
        │ Ethernet/Wi-Fi
        ▼
   Router / LAN
```

### 3.2 IP Addressing

- **Thread Network**: IPv6 mesh (fd00::/8 ULA range typical)
- **Border Router**: Dual-stack (Thread + Ethernet/Wi-Fi)
- **Service Discovery**: mDNS on `_matterc._udp` for commissioning
- **Matter Communication**: IPv6 preferred, IPv4 via NAT64 if needed

### 3.3 Firewall Considerations

Raspberry Pi firewall rules (if using `ufw` or `iptables`):
- Allow mDNS: UDP port 5353
- Allow Matter commissioning: UDP port 5540
- Allow Matter operational: Various ephemeral ports
- Typically no inbound internet access needed (local-only)

---

## 4. Implementation Plan

### Phase 1: System Preparation (30 minutes)

**Step 1.1: Raspberry Pi Setup**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install prerequisites
sudo apt install -y avahi-daemon avahi-utils docker.io docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in for group membership
```

**Step 1.2: Verify SkyConnect**
```bash
# Check USB device
lsusb | grep -i silabs

# Check serial device
ls -la /dev/ttyUSB* /dev/ttyACM*

# Set permissions (if needed)
sudo usermod -aG dialout $USER
```

**Step 1.3: Network Configuration**
```bash
# Ensure avahi is running (mDNS)
sudo systemctl enable avahi-daemon
sudo systemctl start avahi-daemon

# Test mDNS
avahi-browse -a
```

---

### Phase 2: OpenThread Border Router Setup (45-60 minutes)

**Step 2.1: Install OTBR via Docker**

Create `docker-compose-otbr.yml`:
```yaml
version: '3'
services:
  otbr:
    container_name: otbr
    image: openthread/otbr:latest
    restart: unless-stopped
    network_mode: host
    privileged: true
    volumes:
      - /dev:/dev
    command: >
      --radio-url spinel+hdlc+uart:///dev/ttyUSB0?uart-baudrate=460800
    environment:
      - INFRA_IF_NAME=eth0  # Change to wlan0 if using Wi-Fi
```

**Step 2.2: Start OTBR**
```bash
docker-compose -f docker-compose-otbr.yml up -d

# Check logs
docker logs -f otbr
```

**Step 2.3: Access OTBR Web Interface**
- URL: `http://<raspberry-pi-ip>:80`
- Or: `http://raspberrypi.local` (via mDNS)

**Step 2.4: Form Thread Network**

**Option A: Via Web UI**
1. Navigate to http://raspberrypi.local
2. Click "Form" to create new network
3. Note the network credentials (or use existing dataset)

**Option B: Via CLI (ot-ctl)**
```bash
# Attach to OTBR container
docker exec -it otbr sh

# Access OpenThread CLI
ot-ctl

# Create new dataset
> dataset init new
> dataset commit active
> ifconfig up
> thread start

# Verify
> state
# Should show "leader" or "router"

# Get dataset for chip-tool commissioning
> dataset active -x
# Copy this hex string - you'll need it

# Exit
> exit
```

**Step 2.5: Verify Thread Network**
```bash
# Check thread mesh status
docker exec otbr ot-ctl state
# Expected: leader (first device)

docker exec otbr ot-ctl panid
# Note the PAN ID

docker exec otbr ot-ctl ipaddr
# Should see multiple IPv6 addresses
```

---

### Phase 3: Matter Controller Setup (30 minutes)

**Step 3.1: Install chip-tool**
```bash
sudo snap install chip-tool
```

**Step 3.2: Verify Installation**
```bash
chip-tool
# Should display usage information
```

**Step 3.3: Test Discovery**
```bash
# Discover Matter commissioners (should find OTBR)
chip-tool discover commissioners
```

**Alternative: python-matter-server** (if preferred)

Create `docker-compose-matter.yml`:
```yaml
version: '3'
services:
  matter-server:
    container_name: matter-server
    image: ghcr.io/home-assistant-libs/python-matter-server:stable
    restart: unless-stopped
    network_mode: host
    security_opt:
      - apparmor=unconfined
    volumes:
      - ./matter-server-data:/data
      - /run/dbus:/run/dbus:ro
```

```bash
docker-compose -f docker-compose-matter.yml up -d
```

---

### Phase 4: Device Commissioning (60-90 minutes)

**Step 4.1: Prepare IKEA Devices**

1. **Unbox and power on devices**
   - Timmerflotte: Insert batteries
   - Alpstuga: Plug into power

2. **Reset to factory settings** (if previously paired)
   - Timmerflotte: Press button 4 times quickly
   - Alpstuga: Press button 4 times quickly
   - Wait for LED to flash indicating reset

3. **Enter pairing mode**
   - Devices should automatically enter pairing mode after reset
   - Look for QR code on device or packaging
   - Note the manual pairing code (11-digit number)

**Step 4.2: Commission Timmerflotte (Temperature Sensor)**

```bash
# Method 1: Using QR Code
chip-tool pairing code 1 MT:XXXXXXXXXXXXX

# Method 2: Using manual pairing code
chip-tool pairing onnetwork-long 1 20202021 3840

# Parameters:
# - 1: Node ID (you assign this)
# - 20202021: Default setup PIN (check device label)
# - 3840: Default discriminator (check device label)
```

**Note**: Keep device very close to SkyConnect during commissioning!

Expected output:
```
[timestamp] CHIP:CTL: Commissioning discovery over DNS-SD started
[timestamp] CHIP:CTL: Discovered device at [ipv6-address]
[timestamp] CHIP:CTL: Establishing PASE connection
[timestamp] CHIP:CTL: Successfully commissioned device
```

**Step 4.3: Verify Timmerflotte**

```bash
# Read current temperature
chip-tool temperaturemeasurement read measured-value 1 1

# Read humidity
chip-tool relativehumiditymeasurement read measured-value 1 1

# Subscribe to temperature updates
chip-tool temperaturemeasurement subscribe measured-value 0 60 1 1
# Will show temperature every time it changes
```

**Step 4.4: Commission Alpstuga (Air Quality Sensor)**

```bash
# Assign node ID 2
chip-tool pairing code 2 MT:YYYYYYYYYYYYYY

# Or with manual code
chip-tool pairing onnetwork-long 2 20202021 3840
```

**Step 4.5: Verify Alpstuga**

```bash
# Read air quality level
chip-tool airquality read air-quality 2 1

# If device supports PM2.5
chip-tool pm25concentrationmeasurement read measured-value 2 1

# Subscribe to air quality updates
chip-tool airquality subscribe air-quality 0 60 2 1
```

**Troubleshooting Commissioning Issues**:

1. **Device not discovered**
   - Move device closer to SkyConnect
   - Ensure OTBR is running: `docker ps | grep otbr`
   - Check Thread network: `docker exec otbr ot-ctl state`
   - Scan for mDNS: `avahi-browse -a | grep matter`

2. **Commissioning fails**
   - Reset device again
   - Check PIN code and discriminator on device label
   - Try `--bypass-attestation-verifier true` flag
   - Verify system time is correct (Matter uses time-based crypto)

3. **Device paired but not responding**
   - Check Thread mesh: `docker exec otbr ot-ctl child table`
   - Verify routes: `docker exec otbr ot-ctl routes`
   - Restart OTBR: `docker restart otbr`

---

### Phase 5: Testing & Validation (30 minutes)

**Step 5.1: Test Basic Functionality**

```bash
# List all commissioned devices
chip-tool pairing list

# Test temperature sensor
echo "Reading Temperature:"
chip-tool temperaturemeasurement read measured-value 1 1

echo "Reading Humidity:"
chip-tool relativehumiditymeasurement read measured-value 1 1

# Test air quality sensor
echo "Reading Air Quality:"
chip-tool airquality read air-quality 2 1
```

**Step 5.2: Thread Network Health**

```bash
# Check connected Thread devices
docker exec otbr ot-ctl child table

# Check network status
docker exec otbr ot-ctl state
docker exec otbr ot-ctl rloc16
docker exec otbr ot-ctl panid
```

**Step 5.3: Subscribe to Updates**

Create a monitoring script `monitor_sensors.sh`:
```bash
#!/bin/bash

# Monitor both sensors simultaneously
echo "Starting sensor monitoring..."

# Temperature & Humidity in background
chip-tool temperaturemeasurement subscribe measured-value 10 120 1 1 &
chip-tool relativehumiditymeasurement subscribe measured-value 10 120 1 1 &

# Air quality
chip-tool airquality subscribe air-quality 10 120 2 1 &

# Wait
wait
```

```bash
chmod +x monitor_sensors.sh
./monitor_sensors.sh
```

---

## 5. Automation & Integration Options

### 5.1 Command-Line Scripts

**Example: Temperature Alert Script**
```bash
#!/bin/bash
# temperature_alert.sh

TEMP=$(chip-tool temperaturemeasurement read measured-value 1 1 2>&1 | \
       grep -oP 'Int16s.*:\s*\K\d+')

# Matter reports in hundredths of degree Celsius
TEMP_C=$((TEMP / 100))

if [ $TEMP_C -gt 25 ]; then
    echo "Temperature high: ${TEMP_C}°C"
    # Send notification, trigger fan, etc.
fi
```

Add to crontab:
```bash
crontab -e
# Add: */5 * * * * /home/pi/temperature_alert.sh
```

### 5.2 Python Integration (python-matter-server)

If using python-matter-server, create Python scripts:

```python
#!/usr/bin/env python3
import asyncio
import websockets
import json

async def read_temperature():
    uri = "ws://localhost:5580/ws"
    async with websockets.connect(uri) as websocket:
        # Subscribe to temperature
        command = {
            "message_id": "1",
            "command": "device.subscribe_attributes",
            "args": {
                "node_id": 1,
                "attributes": [
                    {
                        "cluster_id": 0x0402,  # TemperatureMeasurement
                        "attribute_id": 0x0000  # MeasuredValue
                    }
                ]
            }
        }
        await websocket.send(json.dumps(command))
        
        # Listen for updates
        while True:
            response = await websocket.recv()
            data = json.loads(response)
            print(f"Temperature update: {data}")

asyncio.run(read_temperature())
```

### 5.3 MQTT Bridge (Advanced)

Create a bridge to publish sensor data to MQTT:

```python
#!/usr/bin/env python3
import asyncio
import paho.mqtt.client as mqtt
from matter_server.client import MatterClient

# Connect to MQTT broker
mqtt_client = mqtt.Client()
mqtt_client.connect("localhost", 1883, 60)

# Subscribe to Matter updates and publish to MQTT
async def bridge():
    async with MatterClient("ws://localhost:5580/ws") as client:
        def on_attribute_update(node_id, attribute_path, value):
            topic = f"matter/{node_id}/{attribute_path}"
            mqtt_client.publish(topic, value)
        
        client.subscribe_attributes(on_attribute_update)
        await asyncio.Future()  # Run forever

asyncio.run(bridge())
```

### 5.4 Web Dashboard

**Option 1**: Use python-matter-server built-in dashboard  
**Option 2**: Build custom dashboard with Node-RED, Grafana, or custom web app

---

## 6. Maintenance & Operations

### 6.1 Regular Maintenance Tasks

**Weekly**:
- Check OTBR status: `docker ps`
- Check Thread network: `docker exec otbr ot-ctl state`
- Verify device connectivity

**Monthly**:
- Update OTBR: `docker pull openthread/otbr:latest && docker-compose restart`
- Update chip-tool: `sudo snap refresh chip-tool`
- Check device battery levels (Timmerflotte)
- Review logs: `docker logs otbr --tail 100`

**Quarterly**:
- Review Matter specification updates
- Test device firmware updates (if available from IKEA)
- Backup Thread credentials

### 6.2 Backup Procedures

**Thread Network Credentials**:
```bash
# Export Thread dataset
docker exec otbr ot-ctl dataset active -x > thread_dataset_backup.txt

# Save to secure location
cp thread_dataset_backup.txt /backup/location/
```

**Matter Controller Data**:
```bash
# chip-tool stores data in:
# /root/snap/chip-tool/common/ (when using snap)

# Backup chip-tool data
sudo cp -r /root/snap/chip-tool/common /backup/location/chip-tool-backup
```

**python-matter-server data**:
```bash
# Data is in Docker volume
docker cp matter-server:/data ./matter-server-backup
```

### 6.3 Monitoring & Logging

**OTBR Logs**:
```bash
# Real-time logs
docker logs -f otbr

# Last 100 lines
docker logs otbr --tail 100

# Save to file
docker logs otbr > otbr_logs_$(date +%Y%m%d).log
```

**chip-tool Logging**:
```bash
# Enable verbose logging
chip-tool --log-level 4 temperaturemeasurement read measured-value 1 1
```

---

## 7. Troubleshooting Guide

### 7.1 Common Issues

#### Issue: OTBR container won't start
```bash
# Check logs
docker logs otbr

# Common causes:
# 1. Wrong serial device
# 2. Permission issues
# 3. Device already in use

# Solutions:
# Verify device: ls -la /dev/ttyUSB*
# Check permissions: sudo chmod 666 /dev/ttyUSB0
# Check for conflicts: lsof | grep ttyUSB0
```

#### Issue: Devices won't commission
```bash
# 1. Verify OTBR is leader
docker exec otbr ot-ctl state
# Should show "leader"

# 2. Scan for Matter devices
chip-tool discover commissioners

# 3. Check mDNS
avahi-browse -rt _matterc._udp

# 4. Reset device and try again
# 5. Move device very close to SkyConnect
```

#### Issue: Device commissioned but not responding
```bash
# Check Thread child table
docker exec otbr ot-ctl child table

# Check device is reachable
chip-tool descriptor read device-type-list 1 0

# If fails, try:
# 1. Restart OTBR: docker restart otbr
# 2. Re-pair device
# 3. Check for Thread network interference
```

### 7.2 Network Debugging

```bash
# Check IPv6 routing
ip -6 route

# Check Thread addresses
docker exec otbr ot-ctl ipaddr

# Test mDNS resolution
avahi-resolve-host-name raspberrypi.local

# Packet capture (advanced)
# sudo tcpdump -i any -w matter_debug.pcap port 5540 or port 5353
```

### 7.3 Performance Issues

**High CPU usage**:
- Check for excessive polling
- Reduce subscription update frequency
- Review chip-tool commands in cron

**Thread network instability**:
- Add more Thread routers (mains-powered devices)
- Check for 2.4GHz interference
- Verify border router placement

---

## 8. Security Considerations

### 8.1 Matter Security Model

- **PASE (Password Authenticated Session Establishment)**: Initial pairing
- **CASE (Certificate Authenticated Session Establishment)**: Operational communication
- **Access Control Lists (ACLs)**: Per-device permissions
- **Fabric**: Isolated administration domain

### 8.2 Best Practices

1. **Physical Security**
   - Keep QR codes/PIN codes secure
   - Don't share commissioning credentials

2. **Network Security**
   - Thread network is isolated from Wi-Fi/Ethernet by default
   - OTBR bridges securely
   - No port forwarding needed (local-only)

3. **Update Management**
   - Keep OTBR firmware updated
   - Monitor Matter specification updates
   - Update chip-tool regularly

4. **Access Control**
   - Limit who can access Raspberry Pi
   - Use strong SSH passwords/keys
   - Consider VPN for remote access

### 8.3 Privacy Benefits

- **No cloud dependency**: All communication is local
- **No vendor lock-in**: Open-source stack
- **Data ownership**: All data stays on your network

---

## 9. Cost Analysis

| Component | Cost (approx) |
|-----------|---------------|
| Raspberry Pi 4 (4GB) | £50-60 / $50-70 |
| SkyConnect (already owned) | £0 (£25 typical) |
| IKEA Timmerflotte | £5 / €5 |
| IKEA Alpstuga | £25 / €25 |
| SD Card (32GB+) | £10 / $10 |
| Power supply (if needed) | £10 / $10 |
| **Total** | **~£100-110 / $105-125** |

**vs Commercial Solutions**:
- Home Assistant Yellow: £120-180
- Apple HomePod Mini (Thread BR): £100
- IKEA Dirigera Hub: £60

**Advantages of DIY approach**:
- Full control and customization
- Educational value
- No subscription fees
- Open-source transparency

---

## 10. Future Expansion

### 10.1 Additional Devices

Once working, you can add:
- More IKEA Matter sensors (Bilresa button, Klippbok water sensor)
- Eve devices (Thread-based)
- Nanoleaf lights
- SmartThings sensors
- Any Matter-certified device

### 10.2 Advanced Features

**Multi-Fabric Setup**:
```bash
# Create second fabric with chip-tool
chip-tool pairing code 1 MT:XXXXX --commissioner-name beta

# Now device appears in two ecosystems
```

**OTA Updates** (when available):
- Configure OTA provider in chip-tool
- IKEA may provide firmware updates

**Custom Matter Applications**:
- Build your own Matter devices using ESP32
- Create Matter bridges for non-Matter devices

### 10.3 Integration Projects

- **Node-RED**: Visual flow programming
- **Grafana**: Data visualization
- **InfluxDB**: Time-series database for sensor data
- **Telegram Bot**: Notifications and control
- **Voice Assistant**: Mycroft, Rhasspy (open-source)

---

## 11. Comparison with Alternatives

### vs Home Assistant

| Aspect | Your Setup | Home Assistant |
|--------|------------|----------------|
| Complexity | Medium-High | Low (with HA OS) |
| Control | Full | High (via add-ons) |
| UI | CLI/Custom | Excellent Web UI |
| Automation | Manual/Scripting | Visual automation |
| Updates | Manual | Automatic |
| Learning Curve | Steep | Moderate |
| Independence | Complete | Partial (can be standalone) |

### vs OpenHAB

| Aspect | Your Setup | OpenHAB |
|--------|------------|---------|
| Matter Support | Native | Via add-on |
| Complexity | Medium | High |
| Java Dependency | No | Yes |
| Performance | Better (lighter) | Good |
| Flexibility | High | Very High |

### Recommendation

**Use your DIY approach if**:
- You want to learn Matter/Thread internals
- Maximum control and transparency desired
- Educational/experimental purpose
- Building something custom

**Use Home Assistant if**:
- You want quick setup with great UI
- Need complex automation rules
- Want to integrate many non-Matter devices
- Prefer visual configuration

**Both approaches can coexist**: Run your setup for learning, then add HA later for automation while keeping chip-tool access.

---

## 12. Conclusion & Next Steps

### Summary

You have a viable path to run Matter on Raspberry Pi independently:

✅ **Hardware**: Raspberry Pi + SkyConnect (OpenThread RCP firmware)  
✅ **Border Router**: OTBR (Docker or snap)  
✅ **Controller**: chip-tool (snap) - simple, stable, official  
✅ **Devices**: IKEA Alpstuga & Timmerflotte (Matter-over-Thread)  
✅ **Maturity**: Matter 1.4 spec is stable as of May 2025  
✅ **Independence**: Fully open-source, no vendor lock-in  

### Recommended Implementation Path

1. **Start Simple**: Use chip-tool with OTBR Docker setup
2. **Validate**: Get both IKEA devices working
3. **Automate**: Add shell scripts for monitoring
4. **Expand** (optional): Add python-matter-server or custom apps
5. **Consider HA later**: If you need advanced automation

### Time Estimate

- **Initial Setup**: 4-6 hours (first time)
- **Device Commissioning**: 1-2 hours (including troubleshooting)
- **Automation**: Ongoing (as needed)
- **Maintenance**: ~30 min/month

### Success Criteria

✓ OTBR running and showing "leader" state  
✓ Both IKEA devices commissioned successfully  
✓ Can read sensor values via chip-tool  
✓ Subscriptions working (real-time updates)  
✓ Thread network stable for 7+ days  

### Resources

- Official Matter SDK: https://github.com/project-chip/connectedhomeip
- OTBR Documentation: https://openthread.io/guides/border-router
- chip-tool Guide: https://github.com/project-chip/connectedhomeip/tree/master/examples/chip-tool
- Matter Specification: https://csa-iot.org/all-solutions/matter/
- Community: 
  - r/MatterProtocol (Reddit)
  - Matter Discord (CSA)
  - OpenThread GitHub Discussions

---

## Appendix A: Quick Reference Commands

### OTBR Management
```bash
# Start OTBR
docker-compose -f docker-compose-otbr.yml up -d

# Stop OTBR
docker-compose -f docker-compose-otbr.yml down

# Restart OTBR
docker restart otbr

# Check status
docker exec otbr ot-ctl state

# Get Thread dataset
docker exec otbr ot-ctl dataset active -x

# View logs
docker logs -f otbr
```

### chip-tool Common Commands
```bash
# Discover devices
chip-tool discover commissioners

# Commission device (QR code)
chip-tool pairing code <node-id> <QR-code>

# Commission device (manual)
chip-tool pairing onnetwork-long <node-id> <pin> <discriminator>

# Read temperature
chip-tool temperaturemeasurement read measured-value <node-id> 1

# Read humidity
chip-tool relativehumiditymeasurement read measured-value <node-id> 1

# Read air quality
chip-tool airquality read air-quality <node-id> 1

# Subscribe to updates
chip-tool <cluster> subscribe <attribute> <min-interval> <max-interval> <node-id> <endpoint>

# List commissioned devices
chip-tool pairing list

# Unpair device
chip-tool pairing unpair <node-id>
```

### Network Diagnostics
```bash
# Check mDNS
avahi-browse -a

# Check Thread children
docker exec otbr ot-ctl child table

# Check routes
docker exec otbr ot-ctl routes

# View IPv6 addresses
docker exec otbr ot-ctl ipaddr
```

---

## Appendix B: Example docker-compose.yml

Complete Docker Compose file for the entire stack:

```yaml
version: '3.8'

services:
  # OpenThread Border Router
  otbr:
    container_name: otbr
    image: openthread/otbr:latest
    restart: unless-stopped
    network_mode: host
    privileged: true
    volumes:
      - /dev:/dev
    command: >
      --radio-url spinel+hdlc+uart:///dev/ttyUSB0?uart-baudrate=460800
    environment:
      - INFRA_IF_NAME=eth0
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  # Matter Server (optional - alternative to chip-tool)
  matter-server:
    container_name: matter-server
    image: ghcr.io/home-assistant-libs/python-matter-server:stable
    restart: unless-stopped
    network_mode: host
    security_opt:
      - apparmor=unconfined
    volumes:
      - ./matter-server-data:/data
      - /run/dbus:/run/dbus:ro
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

Save as `docker-compose.yml` and run:
```bash
docker-compose up -d
```

---

**Document Version**: 1.0  
**Last Updated**: February 5, 2026  
**Author**: AI Assistant  
**Status**: Ready for Implementation
