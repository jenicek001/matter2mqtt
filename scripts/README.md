# Utility Scripts

This directory contains utility scripts for managing and interacting with Matter devices.

## 📜 Script Overview

### Setup & Configuration

#### `setup-ipv6.sh` 🔧
**Purpose:** Configure IPv6 kernel parameters required for Thread Border Router

**Usage:**
```bash
sudo ./scripts/setup-ipv6.sh
```

**What it does:**
- Enables IPv6 forwarding (`net.ipv6.conf.all.forwarding = 1`)
- Configures Router Advertisement acceptance (`net.ipv6.conf.eth0.accept_ra = 2`)
- Creates persistent configuration in `/etc/sysctl.d/60-otbr-ipv6.conf`
- Applies settings immediately

**When to use:**
- Before starting the Matter stack for the first time
- When OTBR shows "disabled" state
- After fresh OS installation

---

### Device Management

#### `commission_device.py` 📱
**Purpose:** Commission Matter devices using chip-tool

**Usage:**
```bash
python3 scripts/commission_device.py --node-id 4 --pairing-code MT:XXXXX-XXXXX
```

**Features:**
- Interactive device commissioning
- Thread dataset retrieval
- Error handling and retry logic

**Dependencies:**
- `chip-tool` (snap package)
- Running OTBR container

---

#### `commission_simple.py` 📱
**Purpose:** Simplified commissioning script for quick setup

**Usage:**
```bash
python3 scripts/commission_simple.py <node-id> <pairing-code>
```

**Example:**
```bash
python3 scripts/commission_simple.py 4 MT:Y.K40H142JZ1006KA00
```

---

### Monitoring & Debugging

#### `monitor_sensors.sh` 📊
**Purpose:** Real-time monitoring of Matter sensor data via MQTT

**Usage:**
```bash
./scripts/monitor_sensors.sh
```

**What it shows:**
- All Matter device MQTT topics
- Temperature, humidity, air quality readings
- Device availability status
- Bridge state

**Output example:**
```
matter/bridge/state online
matter/living_room_air/temperature 22.5
matter/living_room_air/humidity 45.2
matter/living_room_air/availability online
```

**Press Ctrl+C to stop**

---

#### `read_temp.py` 🌡️
**Purpose:** Read temperature from a specific Matter device

**Usage:**
```bash
python3 scripts/read_temp.py --node-id 4
```

**Output:**
- Current temperature value
- Device status

---

### Maintenance

#### `sync_time.py` ⏰
**Purpose:** Synchronize time for Matter devices

**Usage:**
```bash
python3 scripts/sync_time.py
```

**When to use:**
- After power outage
- When device clocks drift
- Before commissioning new devices

---

#### `install_cron.sh` ⏲️
**Purpose:** Install cron jobs for automated maintenance

**Usage:**
```bash
./scripts/install_cron.sh
```

**Installs:**
- Periodic sensor monitoring
- Automatic log rotation
- Health checks

---

## 🔧 Making Scripts Executable

If you get "Permission denied" errors:

```bash
chmod +x scripts/*.sh
```

## 📋 Common Workflows

### First-Time Setup
```bash
# 1. Configure IPv6 (required!)
sudo ./scripts/setup-ipv6.sh

# 2. Start the stack
docker compose up -d

# 3. Verify OTBR is running
docker exec otbr ot-ctl state

# 4. Commission your first device
./scripts/commission_simple.py 4 YOUR_PAIRING_CODE
```

### Daily Monitoring
```bash
# Monitor all sensors
./scripts/monitor_sensors.sh

# Check specific device temperature
python3 scripts/read_temp.py --node-id 4
```

### Adding New Devices
```bash
# Commission with next available node ID
./scripts/commission_simple.py 5 NEW_DEVICE_PAIRING_CODE

# Update bridge config with friendly name
nano bridge/bridge-config-v2.yaml

# Restart bridge to pick up new config
docker compose restart matter-mqtt-bridge
```

### Troubleshooting
```bash
# Check IPv6 configuration
sysctl net.ipv6.conf.all.forwarding
sysctl net.ipv6.conf.eth0.accept_ra

# Re-apply IPv6 configuration if needed
sudo ./scripts/setup-ipv6.sh

# Monitor MQTT to see if data is flowing
./scripts/monitor_sensors.sh
```

## 🐍 Python Script Dependencies

Most Python scripts require:
```bash
pip3 install pyyaml paho-mqtt asyncio websockets
```

These are automatically installed if you're running the bridge in Docker.

## 📝 Environment Variables

Some scripts use environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MATTER_SERVER_URL` | `ws://localhost:5580/ws` | Matter server WebSocket URL |
| `MQTT_BROKER` | `localhost` | MQTT broker address |
| `MQTT_PORT` | `1883` | MQTT broker port |

Set these in your `.env` file or export them:
```bash
export MQTT_BROKER=192.168.1.100
python3 scripts/read_temp.py
```

## 🔍 Script Locations

All scripts in this directory should be run from the repository root:

```bash
# Correct (from repo root)
cd /home/honzik/Matter
./scripts/setup-ipv6.sh

# Also works
cd /home/honzik/Matter
./scripts/monitor_sensors.sh
```

## 🛠️ Adding Your Own Scripts

Place custom scripts in this directory and follow these conventions:

1. **Naming**: Use descriptive names with underscores (e.g., `my_custom_script.py`)
2. **Shebang**: Add `#!/usr/bin/env python3` or `#!/bin/bash` at the top
3. **Executable**: Make executable with `chmod +x`
4. **Documentation**: Add usage comments at the top
5. **Error handling**: Exit with non-zero code on errors

Example Python script template:
```python
#!/usr/bin/env python3
"""
My Custom Script - Description

Usage:
    python3 scripts/my_script.py [options]
"""

import sys

def main():
    try:
        # Your code here
        print("Script executed successfully")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## 📚 More Information

- **Full documentation**: See [../docs/](../docs/)
- **Main README**: [../README.md](../README.md)
- **Troubleshooting**: Check the docs directory

---

**Last Updated:** February 2026
