# Matter Setup - Project Files

This directory contains everything you need to set up Matter on your Raspberry Pi with SkyConnect and IKEA devices.

## 📁 Files Overview

### Documentation
- **`MATTER_SETUP_ANALYSIS.md`** ⭐ - Complete technical analysis and step-by-step implementation guide (12,000+ words)
- **`QUICK_START_GUIDE.md`** ⚡ - Condensed quick-start for fast setup (5-10 minutes read)
- **`HABAPP_MQTT_INTEGRATION.md`** 🔗 - HABApp/OpenHAB integration via MQTT with Python examples
- **`MDNS_DISCOVERY_GUIDE.md`** 📡 - Detailed explanation of mDNS discovery in Matter stack
- **`README.md`** - This file

### Configuration
- **`docker-compose.yml`** - Ready-to-use Docker configuration for OTBR + Matter Server + MQTT Bridge
- **`bridge-config.yaml`** - MQTT bridge configuration for custom device mappings
- **`.env.example`** - Environment variables template (copy to `.env`)
- **`monitor_sensors.sh`** - Script to monitor your IKEA sensors in real-time

### Python Scripts
- **`matter_mqtt_bridge.py`** - MQTT bridge for HABApp/OpenHAB integration
- **`Dockerfile.bridge`** - Docker container for MQTT bridge

## 🚀 Quick Start (30 seconds)

```bash
# 1. Install chip-tool
sudo snap install chip-tool

# 2. Start OpenThread Border Router
docker-compose up -d

# 3. Verify it's running
docker exec otbr ot-ctl state

# 4. Commission your IKEA devices (see QUICK_START_GUIDE.md)
chip-tool pairing code 1 MT:YOUR_QR_CODE

# 5. Test sensor readings
chip-tool temperaturemeasurement read measured-value 1 1

# 6. Monitor sensors continuously
./monitor_sensors.sh
```

## 📖 Which Document Should I Read?

**Start with:** `QUICK_START_GUIDE.md` if you want to get started quickly

**Read later:** `MATTER_SETUP_ANALYSIS.md` for:
- Deep understanding of the Matter/Thread stack
- Troubleshooting specific issues
- Advanced automation ideas
- Integration with other systems
- Security best practices
- Future expansion plans

## 🎯 Your Setup Goals

What you're building:
- ✅ Raspberry Pi as Matter controller
- ✅ SkyConnect (OpenThread RCP firmware) as Thread Border Router
- ✅ IKEA Timmerflotte (temperature/humidity sensor)
- ✅ IKEA Alpstuga (air quality sensor)
- ✅ 100% open-source, independent of Home Assistant/OpenHAB

## 🛠️ Technology Stack

```
Application:    chip-tool (Matter controller CLI)
                └── or python-matter-server (WebSocket API)
                    └── MQTT Bridge → Mosquitto → HABApp
                
Protocol:       Matter 1.4 (CSA standard)
                └── Over Thread (IEEE 802.15.4 mesh)
                
Border Router:  OpenThread Border Router (OTBR)
                └── Docker container
                
Hardware:       SkyConnect USB dongle (Silicon Labs EFR32MG21)
                └── /dev/serial/by-id/usb-Nabu_Casa_SkyConnect...
                └── OpenThread RCP firmware
                
Devices:        IKEA Matter-over-Thread sensors
                └── Alpstuga, Timmerflotte
                
Integration:    MQTT topics for HABApp Python automations
                └── matter/<node_id>/temperature,humidity,air_quality
```

## ⏱️ Time Estimates

- **Reading documentation**: 15-30 minutes
- **Initial setup**: 60-90 minutes
- **Device commissioning**: 30-60 minutes (both devices)
- **Testing & validation**: 30 minutes
- **Total**: 2.5-3.5 hours for first-time setup

## 🔧 Prerequisites

Hardware:
- [x] Raspberry Pi 4 (2GB+ RAM)
- [x] SkyConnect with OpenThread RCP firmware (you have this!)
- [ ] IKEA Alpstuga sensor
- [ ] IKEA Timmerflotte sensor
- [x] Network connection (Ethernet preferred)

Software:
- [ ] Raspberry Pi OS (Debian-based)
- [ ] Docker & docker-compose
- [ ] chip-tool (installed via snap)

## 📊 Project Status

As of February 2026:
- ✅ Matter 1.4/1.4.1 specification released (May 2025)
- ✅ chip-tool stable and available via snap
- ✅ OTBR mature and well-documented
- ✅ IKEA Matter devices available in market
- ⚠️ python-matter-server in maintenance mode (being replaced by matter.js)
- ✅ Full open-source stack available

## 🆘 Quick Troubleshooting

**"Device won't pair"**
→ Move device very close to SkyConnect during commissioning

**"OTBR not starting"**
→ Check: `ls -la /dev/ttyUSB0` (device might be ttyACM0)

**"chip-tool not found"**
→ Run: `sudo snap install chip-tool`

**"Can't read sensor values"**
→ Check Thread network: `docker exec otbr ot-ctl child table`

See `MATTER_SETUP_ANALYSIS.md` Section 7 for comprehensive troubleshooting.

## 🔗 Useful Links

- OpenThread Border Router: https://openthread.io/guides/border-router
- Matter SDK: https://github.com/project-chip/connectedhomeip
- chip-tool snap: https://snapcraft.io/chip-tool
- Matter Specification: https://csa-iot.org/all-solutions/matter/
- Community: r/MatterProtocol on Reddit

## 📝 Next Steps

1. Read `QUICK_START_GUIDE.md` (5 minutes)
2. Run `docker-compose up -d` to start OTBR
3. Follow commissioning steps for your IKEA devices
4. Run `./monitor_sensors.sh` to see live sensor data
5. Explore automation ideas in main documentation

## 💡 Tips

- Keep devices close to SkyConnect during initial pairing
- Let OTBR run for 1-2 minutes after starting before pairing
- Check OTBR status frequently: `docker exec otbr ot-ctl state`
- Use node IDs 1, 2, 3, etc. for different devices
- Monitor logs if issues occur: `docker logs -f otbr`

## 🎓 Learning Resources

After your setup works, consider:
- Building custom Matter devices with ESP32
- Creating automation scripts (examples in analysis doc)
- Setting up Grafana for sensor data visualization
- Integrating with MQTT for home automation
- Adding more Matter-compatible devices

## 📞 Support

Questions? Ideas? Issues?
- Check troubleshooting section in `MATTER_SETUP_ANALYSIS.md`
- Search r/MatterProtocol on Reddit
- Open GitHub issues on relevant projects
- Thread community Discord servers

---

**Version**: 1.0  
**Date**: February 5, 2026  
**Status**: Ready for implementation  

Good luck with your Matter setup! 🚀
