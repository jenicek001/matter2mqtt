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
# 1. Clone this repository
git clone https://github.com/jenicek001/matter2mqtt.git
cd matter2mqtt

# 2. Run the automated setup script
# This will install dependencies, configure IPv6, and set up the stack
./setup.sh

# 3. Update device paths if needed (check your SkyConnect/Thread radio)
ls /dev/serial/by-id/
# Edit docker-compose.yml with your specific device path if different

# 4. Configure device friendly names (optional)
nano bridge/bridge-config.yaml

# 5. Get Thread dataset for commissioning (Thread devices)
docker exec otbr ot-ctl dataset active -x

# 6. Commission your Matter devices using Web UI (recommended)
# Open http://localhost:5580 in browser
# Paste the dataset from step 5 when prompted
# IKEA pairing codes: enter digits only (no dashes/spaces)

# 7. Monitor MQTT topics to see sensor data
mosquitto_sub -t 'matter/#' -v

# 8. (Optional) Set timezone for timestamp accuracy
# Edit .env file or set TZ environment variable
# export TZ=Europe/Prague  # Change to your timezone
```

**Note:** The `setup.sh` script handles all prerequisites including Docker, MQTT broker, IPv6 configuration, and can optionally start the stack. If you already have Docker and dependencies installed, you can skip specific steps with flags (see `./setup.sh --help`).

## 📦 What's in This Repository

```
matter2mqtt/
├── README.md                    # This file - main documentation
├── setup.sh                     # Automated setup script
├── docker-compose.yml           # Main Docker stack configuration
├── LICENSE                      # MIT License
├── CONTRIBUTING.md              # Contribution guidelines
│
├── bridge/                      # Matter-MQTT bridge
│   ├── README.md                # Bridge documentation
│   ├── matter_mqtt_bridge.py    # Bridge application
│   ├── bridge-config.yaml       # Device friendly name mapping
│   ├── Dockerfile               # Docker image
│   └── docker-compose.yml       # Bridge-only deployment
│
├── config/                      # Configuration templates
│   ├── bridge-config.yaml.example  # Bridge config template
│   ├── .env.example             # Environment variables template
│   └── 60-otbr-ipv6.conf        # IPv6 kernel configuration
│
├── scripts/                     # Essential utility scripts
│   ├── setup-ipv6.sh            # IPv6 configuration (CRITICAL!)
│   └── monitor-sensors.sh       # Monitor MQTT sensor data
│
├── docs/                        # Documentation
│   ├── COMMISSIONING.md         # Device commissioning (Web UI)
│   ├── INTEGRATION.md           # HABApp/OpenHAB integration
│   └── TROUBLESHOOTING.md       # Common issues and solutions
│
├── archive/                     # Historical reference only
│   └── v1-legacy/               # Original implementation
│
└── matter-server-data/          # Runtime data (persistent)
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

# Timezone for timestamp accuracy (IMPORTANT!)
# All timestamps in MQTT messages use UTC, but this controls bridge logging
# See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
TZ=Europe/Prague

# Logging
LOG_LEVEL=INFO
```

**⏰ Timezone Configuration:**
- `TZ` controls logging timestamps and bridge diagnostics
- MQTT message timestamps are always **UTC with timezone offset** (e.g., `2026-02-19T14:30:45.123456+00:00`)
- Set to your local timezone for readable logs: `Europe/Prague`, `America/New_York`, `Asia/Tokyo`, etc.
- Leave empty or omit to default to `UTC`

**MQTT config precedence:** environment variables override the `mqtt:` section in `bridge/bridge-config.yaml`.

### Step 4: Configure Bridge Device Names

Edit `bridge/bridge-config.yaml` to set friendly names for your devices:

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

### Step 8: Commission Matter Devices (Web UI)

1. Get the Thread dataset:
  ```bash
  docker exec otbr ot-ctl dataset active -x
  ```
2. Open http://localhost:5580
3. Click "Commission Device"
4. Paste the dataset when prompted
5. Enter the pairing code from the device label

**IKEA pairing codes:** labels often show `MT:12345678901` -> enter digits only (no dashes/spaces).

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

### MQTT Message Structure (Practical Summary)

**Topic layout**
- Base: `matter/<device>/...` where `<device>` is the friendly name from `bridge-config.yaml` (falls back to `node_<id>`).
- Availability: `matter/<device>/availability` with payload `online` or `offline` (retained).
- Bridge status: `matter/bridge/state` and `matter/bridge/info`.

**Common sensor payloads (human-friendly topics)**
- `matter/<device>/temperature` → JSON object with `temperature`, `unit`, `timestamp`.
- `matter/<device>/humidity` → JSON object with `humidity`, `unit`, `timestamp`.
- `matter/<device>/air_quality` → JSON object with `quality`, `value`, `timestamp`.
- `matter/<device>/battery` → JSON object with `battery`, `unit`, `timestamp`.

**Example payloads (ISO 8601 timestamps with UTC timezone):**
```json
{"temperature": 22.5, "unit": "°C", "timestamp": "2026-02-19T15:30:45.123456+00:00"}
{"humidity": 45.2, "unit": "%", "timestamp": "2026-02-19T15:30:46.654321+00:00"}
{"quality": "good", "value": 1, "timestamp": "2026-02-19T15:30:47.789012+00:00"}
{"battery": 85, "unit": "%", "timestamp": "2026-02-19T15:30:48.234567+00:00"}
```

**⏰ Timestamp Details:**
- Format: ISO 8601 with UTC timezone (`+00:00`)
- Always UTC for consistency across timezones
- Includes microseconds for precision
- Parse with: `datetime.fromisoformat(timestamp)` (Python 3.7+)
- See [docs/INTEGRATION.md](docs/INTEGRATION.md) for full timestamp documentation and parsing examples

**Raw attribute stream (if you need full Matter data)**
- `matter/<device>/cluster_XXXX/attr_YYYY` for every attribute the bridge receives.
- Useful for debugging or building custom mappings; not meant for everyday use.

Full details and command topics are in [docs/INTEGRATION.md](docs/INTEGRATION.md).

## 📊 Usage

### Monitor Sensors in Real-Time

```bash
# Use the monitoring script
./scripts/monitor-sensors.sh

# Or subscribe to specific topics
mosquitto_sub -t 'matter/+/temperature' -v
mosquitto_sub -t 'matter/+/humidity' -v
```

### Commission Additional Devices

**Use Matter Server Web UI (recommended):**
1. Open http://localhost:5580
2. Click "Commission Device"
3. Get Thread dataset: `docker exec otbr ot-ctl dataset active -x`
4. Paste the dataset when prompted
5. Enter pairing code from device
  - IKEA labels: digits only (no dashes/spaces)
6. Wait for completion

**Or use chip-tool:**
```bash
chip-tool pairing code-thread 5 hex:DATASET_HEX PAIRING_CODE_DEVICE2
```

### Integrate with HABApp/OpenHAB

See detailed guide: [`docs/INTEGRATION.md`](docs/INTEGRATION.md)

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

**First, check Matter Server Web UI:**
1. Open http://localhost:5580
2. Verify device is listed and online

**Then check bridge:**
```bash
# Check bridge logs
docker compose logs -f matter-mqtt-bridge

# Verify device is in configuration
cat bridge/bridge-config.yaml
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

See detailed troubleshooting: [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)

## 📚 Documentation

- **[Commissioning](docs/COMMISSIONING.md)** - Web UI commissioning steps
- **[Integration Guide](docs/INTEGRATION.md)** - HABApp/OpenHAB integration examples
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Bridge README](bridge/README.md)** - Bridge-specific documentation
- **[Scripts README](scripts/README.md)** - Utility scripts documentation

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
