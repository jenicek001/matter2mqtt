# Matter-to-MQTT Bridge - Complete Setup

A complete Matter stack setup for Raspberry Pi with Thread Border Router (OTBR), Matter devices (IKEA sensors), and MQTT integration for home automation.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [What's in This Repository](#whats-in-this-repository)
- [Prerequisites](#prerequisites)
- [Step-by-Step Setup](#step-by-step-setup)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Documentation](#documentation)
- [Future Plans](#future-plans)

## 🚀 Quick Start

Get up and running in 15 minutes:

```bash
# 1. Clone or navigate to this repository
cd /path/to/Matter

# 2. Run the automated setup script
./setup.sh

# 3. Start the Matter stack
docker compose up -d

# 4. Verify all services are running
docker compose ps

# 5. Monitor MQTT topics
mosquitto_sub -t 'matter/#' -v
```

## 📦 What's in This Repository

```
Matter/
├── README.md                    # This file - main documentation
├── setup.sh                     # Automated setup script (NEW!)
├── docker-compose.yml           # Main Docker stack configuration
├── .env                         # Your environment configuration  
│
├── bridge/                      # ✅ Current Matter-MQTT bridge (v2)
│   ├── README.md                # Bridge-specific documentation
│   ├── matter_mqtt_bridge_v2.py # Bridge application
│   ├── bridge-config-v2.yaml    # Device friendly name mapping
│   ├── Dockerfile.bridge-v2     # Docker image
│   └── docker-compose-v2.yml    # Standalone bridge deployment
│
├── bridge-legacy/               # 📦 Legacy bridge (v1 - node IDs)
│   └── ...                      # For reference only
│
├── config/                      # ⚙️ Configuration templates
│   ├── bridge-config.yaml.example  # Bridge config template
│   ├── .env.example             # Environment variables template
│   └── 60-otbr-ipv6.conf        # IPv6 kernel configuration
│
├── scripts/                     # 🛠️ Utility scripts
│   ├── setup-ipv6.sh            # IPv6 configuration (CRITICAL!)
│   ├── monitor_sensors.sh       # Monitor IKEA sensors
│   ├── commission_device.py     # Commission Matter devices
│   └── ...                      # Other utilities
│
├── docs/                        # 📚 Documentation
│   ├── MATTER_SETUP_ANALYSIS.md    # Complete technical guide
│   ├── QUICK_START_GUIDE.md        # 5-minute quick start
│   ├── MQTT_BRIDGE_COMPARISON.md   # Architecture decisions
│   ├── HABAPP_MQTT_INTEGRATION.md  # HABApp/OpenHAB integration
│   └── ...                         # Additional guides
│
└── matter-server-data/          # 💾 Runtime data (persistent)
    └── ...                      # Matter server state
```

## ✅ Prerequisites

### Hardware Requirements
- **Raspberry Pi** (3B+, 4, or 5 recommended)
  - 2GB+ RAM recommended
  - Wired Ethernet connection preferred for stability
- **Thread Radio** (one of):
  - Nabu Casa SkyConnect (recommended)
  - Home Assistant Yellow
  - Any Thread-capable radio dongle
- **Matter Devices** (e.g., IKEA Alpstuga, Timmerflotte sensors)

### Software Requirements
- **Operating System**: Raspberry Pi OS (64-bit recommended)
- **Docker**: Version 20.10+ with Docker Compose V2
- **Python**: 3.9+ (for scripts)
- **chip-tool**: Snap package for device commissioning

### Network Requirements
- **IPv6 support** on your network (CRITICAL - see setup below)
- **MQTT Broker** (Mosquitto recommended)
- Stable network connectivity

## 🔧 Step-by-Step Setup

### Step 1: Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker (if not already installed)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Install chip-tool for commissioning
sudo snap install chip-tool

# Install Mosquitto MQTT broker (if not running elsewhere)
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

### Step 2: Configure IPv6 (CRITICAL!)

Thread uses IPv6 exclusively. **This step is not optional!**

```bash
# Run the automated IPv6 setup
sudo ./scripts/setup-ipv6.sh

# Verify configuration
sysctl net.ipv6.conf.all.forwarding          # Should be: 1
sysctl net.ipv6.conf.eth0.accept_ra          # Should be: 2

# Check for IPv6 connectivity
ping6 -c 3 google.com
```

**What this does:**
- Enables IPv6 forwarding (required for Thread Border Router)
- Configures Router Advertisement acceptance
- Creates persistent configuration in `/etc/sysctl.d/60-otbr-ipv6.conf`

### Step 3: Configure Environment

```bash
# Copy example configuration
cp config/.env.example .env

# Edit with your settings (if using MQTT authentication)
nano .env
```

Example `.env` configuration:
```bash
# MQTT Authentication (leave empty for anonymous)
MQTT_USERNAME=
MQTT_PASSWORD=

# MQTT Broker (default: localhost)
MQTT_BROKER=localhost
MQTT_PORT=1883

# MQTT Topic Base
MQTT_BASE_TOPIC=matter

# Logging
LOG_LEVEL=INFO
```

### Step 4: Configure Bridge Device Names

Edit `bridge/bridge-config-v2.yaml` to set friendly names for your devices:

```yaml
devices:
  # IKEA Alpstuga (Air Quality sensor) - Node 4
  4:
    friendly_name: "living_room_air"
    description: "IKEA Alpstuga air quality monitor"
    location: "Living Room"
  
  # IKEA Timmerflotte (Temp + Humidity) - Node 5
  5:
    friendly_name: "bedroom_temp"
    description: "IKEA Timmerflotte sensor"
    location: "Bedroom"
```

### Step 5: Update Hardware Paths (If Needed)

Check your Thread radio device path:

```bash
# List USB devices
ls -la /dev/serial/by-id/

# Look for your SkyConnect or Thread radio
# Example: usb-Nabu_Casa_SkyConnect_v1.0_xxxxx-if00-port0
```

Update the device path in `docker-compose.yml` if different from the default:

```yaml
services:
  otbr:
    command: >
      --radio-url spinel+hdlc+uart:///dev/serial/by-id/YOUR_DEVICE_PATH?uart-baudrate=460800
```

### Step 6: Start the Stack

```bash
# Start all services
docker compose up -d

# Check service status (all should be healthy)
docker compose ps

# View logs
docker compose logs -f

# View logs for a specific service
docker compose logs -f matter-mqtt-bridge
```

Expected output when healthy:
```
NAME                  STATUS          HEALTH
otbr                  Up 2 minutes    healthy
matter-server         Up 2 minutes    healthy  
matter-mqtt-bridge    Up 2 minutes    healthy
```

### Step 7: Verify Thread Network

```bash
# Check OTBR status
docker exec otbr ot-ctl state
# Expected: "leader" or "router"

# Check Thread dataset
docker exec otbr ot-ctl dataset active

# Check IPv6 routing
ip -6 route | grep wpan0
# Should show Thread network routes (fd00::/64 prefix)
```

### Step 8: Commission Matter Devices

```bash
# Get the Thread network dataset (needed for commissioning)
docker exec otbr ot-ctl dataset active -x
# Copy the hex output

# Commission a device using the pairing code from device packaging
# Format: chip-tool pairing code-thread <node-id> hex:<dataset> <pairing-code>
chip-tool pairing code-thread 4 hex:PASTE_DATASET_HERE MT:YOUR_PAIRING_CODE

# Wait 10-30 seconds for commissioning to complete
# Look for "Device commissioning completed with success"
```

**Finding Pairing Codes:**
- IKEA devices: Check QR code on packaging or device
- Format usually: `MT:XXXXX-XXXXX-XXXXX`

### Step 9: Verify MQTT Topics

```bash
# Subscribe to all Matter topics
mosquitto_sub -t 'matter/#' -v

# You should see:
# matter/bridge/state → online
# matter/living_room_air/temperature → 22.5
# matter/living_room_air/humidity → 45.2
# matter/living_room_air/availability → online
```

## 📊 Usage

### Monitor Sensors in Real-Time

```bash
# Use the monitoring script
./scripts/monitor_sensors.sh

# Or subscribe to specific topics
mosquitto_sub -t 'matter/+/temperature' -v
mosquitto_sub -t 'matter/+/humidity' -v
```

### Commission Additional Devices

```bash
# Each device needs a unique node ID
chip-tool pairing code-thread 5 hex:DATASET_HEX PAIRING_CODE_DEVICE2
chip-tool pairing code-thread 6 hex:DATASET_HEX PAIRING_CODE_DEVICE3
```

### Integrate with HABApp/OpenHAB

See detailed guide: [`docs/HABAPP_MQTT_INTEGRATION.md`](docs/HABAPP_MQTT_INTEGRATION.md)

Quick example:
```python
from HABApp import Rule
from HABApp.openhab.items import NumberItem

class MatterSensor(Rule):
    def __init__(self):
        super().__init__()
        self.listen_event('matter/living_room_air/temperature',
                         self.on_temperature,
                         MqttValueUpdate)
    
    def on_temperature(self, event):
        NumberItem.get_item('LivingRoom_Temperature').oh_post_update(event.value)
```

### View Bridge Status

```bash
# Bridge publishes status information
mosquitto_sub -t 'matter/bridge/info' -v

# Response includes:
# - Connected devices
# - Device availability
# - Bridge version
# - Timestamp
```

## 🔍 Troubleshooting

### Services Not Healthy

```bash
# Check logs for errors
docker compose logs otbr
docker compose logs matter-server
docker compose logs matter-mqtt-bridge

# Verify IPv6 is configured
sysctl net.ipv6.conf.all.forwarding  # Must be 1

# Check Thread radio connection
ls -la /dev/serial/by-id/
docker exec otbr ot-ctl state
```

### OTBR Shows "disabled" State

```bash
# IPv6 not configured - run setup
sudo ./scripts/setup-ipv6.sh
sudo reboot

# After reboot, restart containers
docker compose restart
```

### Devices Not Appearing in MQTT

```bash
# Check Matter server sees the device
docker exec matter-server python3 -c "import asyncio; asyncio.run(print('check'))"

# Check bridge logs
docker compose logs -f matter-mqtt-bridge

# Verify device is commissioned
chip-tool pairing read-commissioner-nodeid <node-id>
```

### MQTT Connection Failed

```bash
# Test MQTT broker
mosquitto_sub -t 'test' -v

# Check broker is running
sudo systemctl status mosquitto

# Check credentials in .env
cat .env
```

### More Help

See detailed troubleshooting: [`docs/MATTER_SETUP_ANALYSIS.md`](docs/MATTER_SETUP_ANALYSIS.md#troubleshooting)

## 📚 Documentation

- **[Quick Start Guide](docs/QUICK_START_GUIDE.md)** - 5-minute condensed setup
- **[Matter Setup Analysis](docs/MATTER_SETUP_ANALYSIS.md)** - Complete 12,000+ word technical guide
- **[MQTT Bridge Comparison](docs/MQTT_BRIDGE_COMPARISON.md)** - Architecture and design decisions
- **[HABApp Integration](docs/HABAPP_MQTT_INTEGRATION.md)** - OpenHAB integration examples
- **[mDNS Discovery Guide](docs/MDNS_DISCOVERY_GUIDE.md)** - How device discovery works

### Architecture Overview

```
┌─────────────────┐
│  IKEA Devices   │  (Thread - 802.15.4)
│  - Alpstuga     │
│  - Timmerflotte │
└────────┬────────┘
         │ Thread
         ▼
┌─────────────────┐
│      OTBR       │  (OpenThread Border Router)
│  (Container)    │  Bridges Thread ↔ IPv6
└────────┬────────┘
         │ IPv6
         ▼
┌─────────────────┐
│  Matter Server  │  (WebSocket API)
│python-matter-   │  Device management
│    server       │
└────────┬────────┘
         │ WebSocket
         ▼
┌─────────────────┐
│ Matter-MQTT     │  (This bridge)
│    Bridge       │  Publishes to MQTT
└────────┬────────┘
         │ MQTT
         ▼
┌─────────────────┐
│   Mosquitto     │
│  MQTT Broker    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ HABApp/OpenHAB  │  (Home automation)
└─────────────────┘
```

## 🎯 Future Plans

### matter2mqtt Standalone Repository

This bridge implementation will be extracted into a standalone, production-ready GitHub repository:

**Repository:** `matter2mqtt`

**Features:**
- ✅ Containerized daemon with multi-arch Docker images
- ✅ IEEE address-based MQTT topics (like zigbee2mqtt)
- ✅ Home Assistant MQTT Discovery support
- ✅ Prometheus metrics endpoint
- ✅ Full test coverage and CI/CD
- ✅ PyPI package for `pip install matter2mqtt`
- ✅ Comprehensive documentation

**Timeline:** Q1 2026

See the full plan: Ask about the matter2mqtt extraction plan!

## 🤝 Contributing

This is a personal proof-of-concept repository. For the production version, see the future `matter2mqtt` repository.

## 📄 License

MIT License - See LICENSE file for details.

## 🙏 Acknowledgments

- [python-matter-server](https://github.com/home-assistant-libs/python-matter-server) - Matter server implementation
- [OpenThread](https://openthread.io/) - Thread networking stack
- [IKEA](https://www.ikea.com/) - Matter-compatible sensors
- [Home Assistant](https://www.home-assistant.io/) - Inspiration and tools

## 📞 Support

For issues and questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review detailed docs in `docs/`
3. Check Docker logs: `docker compose logs`
4. Verify IPv6 configuration

---

**Last Updated:** February 2026  
**Version:** 2.0 (IEEE Address Support)
