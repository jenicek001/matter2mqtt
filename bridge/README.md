# Matter Setup - Project Files (Updated v2)

This directory contains everything you need to set up Matter on your Raspberry Pi with SkyConnect and IKEA devices.

## 🆕 What's New in v2

- ✅ **IEEE address-based MQTT topics** (like zigbee2mqtt)
- ✅ **IPv6 kernel configuration** (required for Thread)
- ✅ **Bridge comparison** (Custom vs Canonical)
- ✅ **Friendly device names** support
- ✅ **Device availability** tracking

## 📁 Files Overview

### Documentation
- **`MATTER_SETUP_ANALYSIS.md`** ⭐ - Complete technical analysis and step-by-step implementation guide (12,000+ words)
- **`QUICK_START_GUIDE.md`** ⚡ - Condensed quick-start for fast setup (5-10 minutes read)
- **`MQTT_BRIDGE_COMPARISON.md`** 🆕 - Custom vs Canonical bridge, IEEE addresses, IPv6 setup
- **`HABAPP_MQTT_INTEGRATION.md`** 🔗 - HABApp/OpenHAB integration via MQTT with Python examples
- **`MDNS_DISCOVERY_GUIDE.md`** 📡 - Detailed explanation of mDNS discovery in Matter stack
- **`README.md`** - This file

### Configuration (v2 - IEEE Address Support)
- **`docker-compose-v2.yml`** 🆕 - Docker stack with IPv6 docs and healthchecks
- **`bridge-config-v2.yaml`** 🆕 - IEEE-to-friendly-name mapping (like zigbee2mqtt)
- **`matter_mqtt_bridge_v2.py`** 🆕 - Bridge with IEEE address support
- **`Dockerfile.bridge-v2`** 🆕 - Docker image for v2 bridge
- **`60-otbr-ipv6.conf`** 🆕 - Required IPv6 kernel configuration
- **`setup-ipv6.sh`** 🆕 - Automated IPv6 setup script
- **`.env.example`** - Environment variables template (copy to `.env`)
- **`monitor_sensors.sh`** - Script to monitor your IKEA sensors in real-time

### Configuration (v1 - Legacy)
- `docker-compose.yml` - Node ID-based bridge (legacy)
- `bridge-config.yaml` - Numeric node IDs
- `matter_mqtt_bridge.py` - Original bridge
- `Dockerfile.bridge` - Original Docker image

## 🚀 Quick Start (v2 Recommended)

### Step 0: Configure IPv6 (REQUIRED!)

**Before starting Docker containers**, you MUST configure IPv6:

```bash
# Run automated setup
sudo ./setup-ipv6.sh

# Verify
sysctl net.ipv6.conf.all.forwarding  # Should be 1
sysctl net.ipv6.conf.eth0.accept_ra  # Should be 2
```

**Why?** Thread uses IPv6, and Linux needs kernel parameters for routing. See [MQTT_BRIDGE_COMPARISON.md](MQTT_BRIDGE_COMPARISON.md#ipv6-kernel-configuration-critical).

### Step 1: Install chip-tool

```bash
sudo snap install chip-tool
```

### Step 2: Start Stack (v2 with IEEE Addresses)

```bash
# Start all services
docker compose -f docker-compose-v2.yml up -d

# Check all services healthy
docker compose -f docker-compose-v2.yml ps

# View logs
docker compose -f docker-compose-v2.yml logs -f
```

### Step 3: Verify Thread Network

```bash
# Check OTBR status
docker exec otbr ot-ctl state
# Should show: leader or router

# Check IPv6 routes
ip -6 route | grep wpan0
# Should show Thread network routes
```

### Step 4: Commission IKEA Devices

```bash
# Get Thread network dataset
docker exec otbr ot-ctl dataset active -x

# Commission device (example with pairing code from packaging)
chip-tool pairing code-thread 1 hex:DATASET_HEX PAIRING_CODE

# Wait 10-30 seconds for commissioning to complete
```

### Step 5: Discover IEEE Addresses

```bash
# Check bridge info for IEEE addresses
mosquitto_sub -t "matter/bridge/info" -v

# You'll see output like:
# {
#   "devices": [
#     {
#       "ieee_address": "0x00124b001f8a9b2c",
#       "friendly_name": "0x00124b001f8a9b2c",
#       "node_id": 1,
#       "available": true
#     }
#   ]
# }
```

### Step 6: Set Friendly Names (Optional)

Edit `bridge-config-v2.yaml`:

```yaml
devices:
  "0x00124b001f8a9b2c":  # Copy IEEE from step 5
    friendly_name: "living_room_temp"
    description: "IKEA Timmerflotte"
    location: "Living Room"
    
  "0x00124b001f8a9b3d":
    friendly_name: "bedroom_air"
    description: "IKEA Alpstuga"
    location: "Bedroom"
```

Restart bridge:

```bash
docker compose -f docker-compose-v2.yml restart matter-mqtt-bridge
```

### Step 7: Monitor MQTT Topics

```bash
# Watch all Matter topics
mosquitto_sub -h localhost -t 'matter/#' -v

# You'll see (with friendly names):
# matter/living_room_temp/temperature {"temperature": 22.5, "unit": "°C"}
# matter/living_room_temp/humidity {"humidity": 45.2, "unit": "%"}
# matter/bedroom_air/air_quality {"quality": "good", "value": 1}
# matter/bridge/state online

# Or with IEEE addresses (if no friendly name set):
# matter/0x00124b001f8a9b2c/temperature {"temperature": 22.5}
```

## 📖 Which Document Should I Read?

**New to Matter?** Start with:
1. `QUICK_START_GUIDE.md` - Get running quickly
2. `MQTT_BRIDGE_COMPARISON.md` - Understand IEEE addresses and IPv6

**Setting up HABApp integration?**
- `HABAPP_MQTT_INTEGRATION.md` - Complete Python examples

**Troubleshooting?**
- `MATTER_SETUP_ANALYSIS.md` - Deep technical guide
- `MDNS_DISCOVERY_GUIDE.md` - mDNS discovery issues

**Want to understand the whole stack?**
- `MATTER_SETUP_ANALYSIS.md` - Everything you need to know (12,000 words)

## 🎯 Your Setup Goals

What you're building:
- ✅ Raspberry Pi as Matter controller
- ✅ SkyConnect (OpenThread RCP firmware) as Thread Border Router
- ✅ IKEA Timmerflotte (temperature/humidity sensor)
- ✅ IKEA Alpstuga (air quality sensor)
- ✅ **IEEE address-based MQTT topics** (like zigbee2mqtt)
- ✅ HABApp Python automation integration
- ✅ 100% open-source, independent of Home Assistant/OpenHAB

## 🛠️ Technology Stack

```
Application:    chip-tool (Matter controller CLI)
                └── python-matter-server (WebSocket API)
                    └── MQTT Bridge v2 (IEEE addresses)
                        └── Mosquitto → HABApp
                
Protocol:       Matter 1.4 (CSA standard)
                └── Over Thread (IEEE 802.15.4 mesh)
                    └── IPv6 (6LoWPAN)
                
Border Router:  OpenThread Border Router (OTBR)
                └── Docker container
                └── Requires IPv6 kernel config
                
Hardware:       SkyConnect USB dongle (Silicon Labs EFR32MG21)
                └── /dev/serial/by-id/usb-Nabu_Casa_SkyConnect...
                └── OpenThread RCP firmware
                
Devices:        IKEA Matter-over-Thread sensors
                └── Alpstuga, Timmerflotte
                
Integration:    MQTT topics (zigbee2mqtt style)
                └── matter/<ieee_address>/temperature
                └── matter/<friendly_name>/humidity
                └── matter/bridge/state
```

## 📡 MQTT Topic Structure Comparison

### v2 (IEEE Address - Recommended)

```
matter/0x00124b001f8a9b2c/temperature    → {"temperature": 22.5, "unit": "°C"}
matter/0x00124b001f8a9b2c/humidity       → {"humidity": 45.2, "unit": "%"}
matter/0x00124b001f8a9b2c/availability   → "online"

# With friendly names configured:
matter/living_room_temp/temperature      → {"temperature": 22.5}
matter/bedroom_air/air_quality           → {"quality": "good"}

# Bridge status (like zigbee2mqtt):
matter/bridge/state                      → "online"
matter/bridge/info                       → JSON with all devices
matter/bridge/devices                    → Device join/leave events
```

**Advantages:**
- ✅ Stable identifiers (don't change on re-commission)
- ✅ Readable friendly names
- ✅ Matches zigbee2mqtt patterns
- ✅ Easy HABApp integration

### v1 (Node ID - Legacy)

```
matter/1/temperature     → 22.5
matter/2/air_quality     → "good"
matter/bridge/status     → "online"
```

**Issues:**
- ❌ Node IDs can change
- ❌ Not human-readable
- ❌ Different from zigbee2mqtt

## 🌐 IPv6 Configuration (Required!)

**Critical:** Thread uses IPv6. The Linux kernel MUST be configured for IPv6 routing.

### Why IPv6 Is Required

1. **Thread protocol** uses IPv6 exclusively (6LoWPAN)
2. **Border Router** forwards packets between Thread mesh and Ethernet
3. **Device discovery** uses IPv6 multicast
4. **Without it:** Thread network won't work at all!

### Quick Setup

```bash
# Run automated script
sudo ./setup-ipv6.sh

# This configures:
# - IPv6 forwarding
# - Router Advertisement processing
# - Thread interface settings
# - Kernel modules
```

### Verification

```bash
# Check forwarding enabled
sysctl net.ipv6.conf.all.forwarding
# Expected: net.ipv6.conf.all.forwarding = 1

# Check RA processing
sysctl net.ipv6.conf.eth0.accept_ra
# Expected: net.ipv6.conf.eth0.accept_ra = 2

# View Thread routes
ip -6 route | grep wpan0
# Should show routes after OTBR starts
```

See `60-otbr-ipv6.conf` for details on kernel parameters.

## 🔧 Bridge Comparison: Custom vs Canonical

### Canonical matter-mqtt-bridge

**Direction:** MQTT devices → exposed **as** Matter  
**Use Case:** Make MQTT/non-Matter devices controllable via Matter  
**GitHub:** https://github.com/canonical/matter-mqtt-bridge

**Not suitable for your use case** - works in opposite direction!

### Custom Bridge v2 (This Project)

**Direction:** Matter devices → publish **to** MQTT  
**Use Case:** Sensor data available in HABApp/OpenHAB  
**Topics:** IEEE addresses (like zigbee2mqtt)

**Perfect for sensor monitoring** ✅

See [MQTT_BRIDGE_COMPARISON.md](MQTT_BRIDGE_COMPARISON.md) for detailed comparison.

## ⏱️ Time Estimates

- **IPv6 configuration**: 5 minutes
- **Reading documentation**: 15-30 minutes
- **Initial setup**: 60-90 minutes
- **Device commissioning**: 30-60 minutes (both devices)
- **Configure friendly names**: 10 minutes
- **Testing & validation**: 30 minutes
- **Total**: 2.5-3.5 hours for first-time setup

## 🔧 Prerequisites

Before starting:

- [x] Raspberry Pi running Raspberry Pi OS (or similar Debian-based)
- [x] SkyConnect with OpenThread RCP firmware
- [x] Docker and docker-compose installed
- [x] Mosquitto MQTT broker running (or in stack)
- [x] IKEA Matter devices with pairing codes
- [x] **IPv6 configured on host** (run `setup-ipv6.sh`)

## 🆘 Troubleshooting

### Container Won't Start

```bash
# Check IPv6 configuration
sysctl net.ipv6.conf.all.forwarding
# Should be 1

# Verify SkyConnect device path
ls -l /dev/serial/by-id/
# Update path in docker-compose-v2.yml if different

# Check logs
docker compose -f docker-compose-v2.yml logs otbr
```

### No Thread Network

```bash
# Check OTBR state
docker exec otbr ot-ctl state
# Should show: leader or router (not disabled)

# Check IPv6 routes
ip -6 route | grep wpan0
# Should show Thread routes

# View dataset
docker exec otbr ot-ctl dataset active
```

### MQTT Not Publishing

```bash
# Test MQTT broker
mosquitto_sub -h localhost -t 'matter/#' -v

# Check bridge connection
docker logs matter-mqtt-bridge | grep -i websocket

# Verify matter-server
docker logs matter-server | grep -i commissioned
```

### Matter Device Not Found

```bash
# Check commissioning succeeded
chip-tool pairing ble-thread <node_id> hex:<dataset> <discriminator> <pin>

# View commissioned devices
docker logs matter-server | grep node

# Check mDNS
avahi-browse -a -r -t | grep -i matter
```

See `docker-compose-v2.yml` for comprehensive troubleshooting section.

## 📚 HABApp Integration

Create rules using familiar zigbee2mqtt patterns:

```python
from HABApp import Rule
from HABApp.mqtt.items import MqttItem
from HABApp.mqtt.events import MqttValueUpdateEvent

class TemperatureMonitor(Rule):
    def __init__(self):
        super().__init__()
        
        # Subscribe using friendly name
        self.temp = MqttItem.get_create_item('matter/living_room_temp/temperature')
        self.temp.listen_event(self.on_temp_change, MqttValueUpdateEvent)
    
    def on_temp_change(self, event):
        # Parse JSON payload
        import json
        data = json.loads(event.value)
        temp = data['temperature']
        
        if temp > 25:
            self.log.warning(f"High temperature: {temp}°C")
```

See [HABAPP_MQTT_INTEGRATION.md](HABAPP_MQTT_INTEGRATION.md) for complete examples.

## 🔄 Migration from v1 to v2

If you have existing v1 setup:

1. **Backup your data**
   ```bash
   cp -r matter-server-data matter-server-data.bak
   ```

2. **Configure IPv6**
   ```bash
   sudo ./setup-ipv6.sh
   ```

3. **Switch to v2**
   ```bash
   docker compose down
   docker compose -f docker-compose-v2.yml up -d
   ```

4. **Discover IEEE addresses**
   ```bash
   mosquitto_sub -t "matter/bridge/info" -v
   ```

5. **Update HABApp rules** with new topic patterns
   - Old: `matter/1/temperature`
   - New: `matter/living_room_temp/temperature` or `matter/0x.../temperature`

## 📦 File Structure

```
/home/honzik/Matter/
├── README.md (this file)
├── MATTER_SETUP_ANALYSIS.md (12,000 words comprehensive guide)
├── QUICK_START_GUIDE.md (fast setup)
├── MQTT_BRIDGE_COMPARISON.md (NEW - v2 features explained)
├── HABAPP_MQTT_INTEGRATION.md (HABApp examples)
├── MDNS_DISCOVERY_GUIDE.md (mDNS explained)
│
├── docker-compose-v2.yml (recommended)
├── docker-compose.yml (v1 legacy)
│
├── bridge-config-v2.yaml (IEEE addresses)
├── bridge-config.yaml (node IDs)
│
├── matter_mqtt_bridge_v2.py (IEEE support)
├── matter_mqtt_bridge.py (v1 legacy)
│
├── Dockerfile.bridge-v2
├── Dockerfile.bridge
│
├── 60-otbr-ipv6.conf (kernel config)
├── setup-ipv6.sh (automated setup)
├── .env.example (MQTT credentials)
└── monitor_sensors.sh (monitoring script)
```

## 🎓 Learning Path

**Beginner:**
1. Read `QUICK_START_GUIDE.md`
2. Run `setup-ipv6.sh`
3. Start `docker-compose-v2.yml`
4. Commission one device
5. Watch MQTT topics

**Intermediate:**
1. Read `MQTT_BRIDGE_COMPARISON.md`
2. Configure friendly names
3. Set up HABApp rules
4. Monitor with `monitor_sensors.sh`

**Advanced:**
1. Read full `MATTER_SETUP_ANALYSIS.md`
2. Understand `MDNS_DISCOVERY_GUIDE.md`
3. Customize bridge code
4. Add more automation rules

## 🙏 Support

This setup is designed to work **independently of Home Assistant** using open-source tools and Docker containers. Perfect for HABApp users who want Matter support without HA.

Questions? Check the troubleshooting sections in:
- `docker-compose-v2.yml` (comprehensive Docker troubleshooting)
- `MQTT_BRIDGE_COMPARISON.md` (IPv6, bridge, topics)
- `MATTER_SETUP_ANALYSIS.md` (deep technical issues)

---

**Last Updated:** February 2026  
**Version:** 2.0 (IEEE Address Support)
