# Utility Scripts

Essential scripts for Matter stack setup and monitoring.

## Scripts

### `setup-ipv6.sh` 🔧

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

**This is CRITICAL** - Thread will not work without proper IPv6 configuration.

---

### `monitor-sensors.sh` 📊

**Purpose:** Real-time monitoring of Matter sensor data via MQTT

**Usage:**
```bash
./scripts/monitor-sensors.sh
```

**What it shows:**
- All Matter device MQTT topics
- Temperature, humidity, air quality readings
- Device availability status
- Bridge state

**Output example:**
```
matter/bridge/state online
matter/alpstuga/temperature 22.5
matter/alpstuga/humidity 45.2
matter/alpstuga/availability online
```

**Press Ctrl+C to stop**

---

## Device Commissioning

**Use the Matter Server Web UI (primary method):**

1. Open http://localhost:5580 in your browser
2. Click "Commission Device"
3. Get Thread dataset:
   ```bash
   docker exec otbr ot-ctl dataset active -x
   ```
4. Paste the dataset when prompted
5. Enter the pairing code from your device
   - IKEA labels often show `MT:12345678901` -> enter digits only (no dashes/spaces)
6. Wait 30-60 seconds for commissioning to complete

The Web UI provides a better experience with real-time status, error messages, and device management.

Alternatively, use `chip-tool` directly:
```bash
chip-tool pairing code-thread <node-id> hex:<dataset> <pairing-code>
```

---

## Common Workflows

### First-Time Setup
```bash
# 1. Configure IPv6 (required!)
sudo ./scripts/setup-ipv6.sh

# 2. Start the stack
docker compose up -d

# 3. Verify OTBR is running
docker exec otbr ot-ctl state
```

### Daily Monitoring
```bash
# Monitor all sensors
./scripts/monitor-sensors.sh
```

### Adding New Devices
```bash
# 1. Get Thread dataset
docker exec otbr ot-ctl dataset active -x

# 2. Commission via Web UI
# Open http://localhost:5580

# 3. Update bridge config with friendly name
nano bridge/bridge-config.yaml

# 4. Restart bridge to pick up new config
docker compose restart matter-mqtt-bridge
```

---

## Troubleshooting

### IPv6 Configuration Not Working

```bash
# Re-apply IPv6 configuration
sudo ./scripts/setup-ipv6.sh

# Verify
sysctl net.ipv6.conf.all.forwarding    # Should be: 1
sysctl net.ipv6.conf.eth0.accept_ra    # Should be: 2

# Reboot if needed
sudo reboot
```

### MQTT Not Showing Data

```bash
# Check MQTT broker is running
sudo systemctl status mosquitto

# Monitor with explicit credentials (if using auth)
mosquitto_sub -h localhost -u USERNAME -P PASSWORD -t 'matter/#' -v
```

For more help, see [docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md).

---

**Last Updated:** February 2026
