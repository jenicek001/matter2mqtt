# Matter on Raspberry Pi - Quick Start Guide
**TL;DR Implementation Guide**

> **Note**: For HABApp/OpenHAB MQTT integration, see `HABAPP_MQTT_INTEGRATION.md`

## Prerequisites Checklist
- [ ] Raspberry Pi 4 (2GB+ RAM) with Raspberry Pi OS
- [ ] SkyConnect dongle with OpenThread RCP firmware (✓ you have this)
- [ ] IKEA Alpstuga and Timmerflotte devices
- [ ] Stable network connection (Ethernet recommended)
- [ ] SD card with 16GB+ storage

## One-Command Install (Easiest Path)

### Option 1: Snap-based Setup (Recommended)
```bash
# Install everything via snap
sudo snap install chip-tool
sudo snap install openthread-border-router

# Configure OTBR
sudo openthread-border-router.otbr-agent -I eth0 'spinel+hdlc+uart:///dev/ttyUSB0?uart-baudrate=460800'
```

### Option 2: Docker-based Setup (Recommended - includes MQTT)
```bash
# Install Docker (if not already installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and back in

# The docker-compose.yml is already provided!
# It includes:
# - OTBR (OpenThread Border Router)
# - python-matter-server (WebSocket API)
# - matter-mqtt-bridge (for HABApp integration)

# Just start everything:
docker-compose up -d

# Verify all containers are running
docker-compose ps

# Install chip-tool for device commissioning
sudo snap install chip-tool
```

## 30-Second Verification
```bash
# Check OTBR is running
docker exec otbr ot-ctl state
# Should output: leader

# Check chip-tool works
chip-tool
# Should show help text

# Check SkyConnect is detected
ls -la /dev/ttyUSB0
# Should show the device

# Check mDNS is working
avahi-browse -a | grep thread
```

## Commission Your First Device (5 minutes)

### Step 1: Prepare IKEA Device
1. Remove from packaging
2. Power on (battery or plug in)
3. If previously paired, reset: Press button 4x quickly
4. Device should flash/blink (pairing mode)
5. Keep device VERY CLOSE to SkyConnect during pairing

### Step 2: Get Device Info
Look on device or packaging for:
- QR Code (starts with "MT:")
- Manual pairing code (11-digit number like "20202021")
- Discriminator (4-digit number like "3840")

### Step 3: Commission with chip-tool
```bash
# Method A: Using QR Code (easiest)
chip-tool pairing code 1 MT:YOUR_QR_CODE_HERE

# Method B: Using manual code
chip-tool pairing onnetwork-long 1 20202021 3840
```

Replace:
- `1` = Node ID (you choose this, use 1, 2, 3, etc.)
- `20202021` = PIN from device label
- `3840` = Discriminator from device label

### Step 4: Test the Device
```bash
# For Timmerflotte (temperature sensor):
chip-tool temperaturemeasurement read measured-value 1 1
chip-tool relativehumiditymeasurement read measured-value 1 1

# For Alpstuga (air quality):
chip-tool airquality read air-quality 2 1
```

## Troubleshooting One-Liners

```bash
# Device not found during pairing
avahi-browse -rt _matterc._udp
# Should see your device appear here

# OTBR not responding
docker restart otbr && sleep 5 && docker exec otbr ot-ctl state

# Check Thread network is formed
docker exec otbr ot-ctl panid
docker exec otbr ot-ctl dataset active

# Device paired but not responding
docker exec otbr ot-ctl child table
# Your device should be listed

# Reset chip-tool storage (clean slate)
sudo rm -rf /root/snap/chip-tool/common/*
```

## Daily Use Commands

```bash
# Read temperature
chip-tool temperaturemeasurement read measured-value 1 1

# Read humidity  
chip-tool relativehumiditymeasurement read measured-value 1 1

# Read air quality
chip-tool airquality read air-quality 2 1

# Monitor in real-time (updates every 10-60 seconds)
chip-tool temperaturemeasurement subscribe measured-value 10 60 1 1
```

## If Something Breaks

```bash
# Nuclear option - restart everything
docker-compose down
docker-compose up -d
sleep 10

# Check network is back
docker exec otbr ot-ctl state

# Re-pair devices if needed (they might auto-reconnect)
```

## Next Steps

After everything works:
1. See `MATTER_SETUP_ANALYSIS.md` for automation ideas
2. Add more devices (use node IDs 3, 4, 5, etc.)
3. Create monitoring scripts (examples in main doc)
4. Consider adding Home Assistant later for UI

## Need Help?

- Check logs: `docker logs otbr`
- Community: r/MatterProtocol on Reddit
- Official docs: https://openthread.io/guides/border-router
- Matter docs: https://github.com/project-chip/connectedhomeip

---

**Estimated time to first working sensor: 45-60 minutes**
