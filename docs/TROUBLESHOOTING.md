# Troubleshooting

Common issues and solutions for the Matter-to-MQTT bridge.

## Table of Contents

- [IPv6 and Thread Issues](#ipv6-and-thread-issues)
- [OTBR Problems](#otbr-problems)
- [Device Commissioning](#device-commissioning)
- [MQTT Connection](#mqtt-connection)
- [Docker Issues](#docker-issues)

## IPv6 and Thread Issues

### OTBR shows "disabled" state

**Symptoms:**
```bash
$ docker exec otbr ot-ctl state
disabled
```

**Solution:**
IPv6 forwarding is not enabled. Thread requires IPv6.

```bash
# Run IPv6 setup script
sudo ./scripts/setup-ipv6.sh

# Verify configuration
sysctl net.ipv6.conf.all.forwarding    # Should be: 1
sysctl net.ipv6.conf.eth0.accept_ra    # Should be: 2

# Restart Docker containers
docker compose restart
```

### No IPv6 routes for Thread network

**Symptoms:**
```bash
$ ip -6 route | grep wpan0
# No output
```

**Solution:**
```bash
# Check OTBR status
docker exec otbr ot-ctl state    # Should show "leader" or "router"

# Check Thread dataset
docker exec otbr ot-ctl dataset active

# If OTBR is disabled, see above section
```

## OTBR Problems

### OTBR container not starting

**Check logs:**
```bash
docker compose logs otbr
```

**Common issues:**

1. **Serial device not found**
   ```bash
   # List USB devices
   ls -la /dev/serial/by-id/
   
   # Update device path in docker-compose.yml
   nano docker-compose.yml
   # Look for: --radio-url spinel+hdlc+uart:///dev/serial/by-id/YOUR_DEVICE
   ```

2. **Permission denied on /dev**
   ```bash
   # OTBR needs privileged mode (already in docker-compose.yml)
   # Verify: docker compose config | grep privileged
   ```

3. **Network mode conflict**
   ```bash
   # OTBR requires host networking for IPv6
   # Verify: docker compose config | grep "network_mode: host"
   ```

### OTBR shows "detached" instead of "leader"

**Normal behavior** - Wait 30-60 seconds after startup. OTBR will become leader.

If it stays detached:
```bash
# Reset Thread network (will disconnect all devices!)
docker exec otbr ot-ctl factoryreset
docker compose restart otbr

# Wait for leader state
docker exec otbr ot-ctl state
```

## Device Commissioning

### Cannot commission device

**Use Matter Server Web UI** (recommended):
1. Open http://localhost:5580 in browser
2. Click "Commission Device"
3. Get Thread dataset: `docker exec otbr ot-ctl dataset active -x`
4. Paste the dataset when prompted
5. Enter pairing code from device packaging
   - IKEA labels often show `MT:12345678901` -> enter digits only (no dashes/spaces)
6. Wait 30-60 seconds

**If Web UI doesn't work:**
```bash
# Check Matter server is running
docker compose ps matter-server

# Check logs
docker compose logs matter-server

# Try commissioning via chip-tool
chip-tool pairing code-thread <node-id> hex:<dataset> <pairing-code>
```

### Commissioning hangs

**Symptoms:** Commissioning starts but never completes.

**Solutions:**

1. **Check Thread network**
   ```bash
   docker exec otbr ot-ctl state    # Must be "leader" or "router"
   ```

2. **Check IPv6**
   ```bash
   ip -6 route | grep wpan0    # Should show routes
   ```

3. **Device too far from border router**
   - Move device closer
   - Thread range is typically 10-30 meters

4. **Restart device**
   - Remove battery and reinsert
   - Or reset device per manufacturer instructions

### Device commissioned but not appearing in MQTT

**Check bridge logs:**
```bash
docker compose logs matter-mqtt-bridge
```

**Common issues:**

1. **Bridge not connected to Matter server**
   ```bash
   # Restart bridge
   docker compose restart matter-mqtt-bridge
   
   # Check connection
   docker compose logs matter-mqtt-bridge | grep "Connected to Matter server"
   ```

2. **Device not in bridge config**
   ```bash
   # Configure friendly name
   nano bridge/bridge-config.yaml
   
   # Add your device (use node ID from commissioning)
   devices:
     4:
       friendly_name: "my_sensor"
       description: "My Matter sensor"
   
   # Restart bridge
   docker compose restart matter-mqtt-bridge
   ```

3. **Check device in Matter server**
   - Open http://localhost:5580
   - Verify device is listed
   - Check device is online

## MQTT Connection

### Bridge not connecting to MQTT broker

**Check broker is running:**
```bash
# For local Mosquitto
sudo systemctl status mosquitto

# Test MQTT
mosquitto_sub -t 'test' -v
```

**Check bridge configuration:**
```bash
# View environment variables
docker compose config | grep MQTT

# Check credentials in .env
cat .env
```

**Common fixes:**
```bash
# Restart Mosquitto
sudo systemctl restart mosquitto

# Restart bridge
docker compose restart matter-mqtt-bridge

# Check authentication
# If using auth, ensure MQTT_USERNAME and MQTT_PASSWORD are set in .env
```

### No MQTT topics appearing

**Test MQTT subscription:**
```bash
# Subscribe to all Matter topics
mosquitto_sub -t 'matter/#' -v

# If using authentication:
mosquitto_sub -h localhost -u USERNAME -P PASSWORD -t 'matter/#' -v
```

**Check bridge state:**
```bash
# Should see bridge/state = online
mosquitto_sub -t 'matter/bridge/state' -v
```

**If nothing appears:**
1. Check bridge logs: `docker compose logs matter-mqtt-bridge`
2. Verify bridge is running: `docker compose ps`
3. Check Matter server has devices: http://localhost:5580
4. Restart bridge: `docker compose restart matter-mqtt-bridge`

## Docker Issues

### Services not healthy

```bash
# Check service status
docker compose ps

# View logs for unhealthy service
docker compose logs <service-name>
```

**Common issues:**

1. **OTBR unhealthy**: See [OTBR Problems](#otbr-problems)

2. **Matter server unhealthy**:
   ```bash
   # Check logs
   docker compose logs matter-server
   
   # Check port 5580 is available
   netstat -tlnp | grep 5580
   ```

3. **Bridge unhealthy**:
   ```bash
   # Health check tries to connect to MQTT
   # Ensure Mosquitto is running
   sudo systemctl status mosquitto
   ```

### Docker compose build fails

```bash
# Clean build cache
docker compose build --no-cache matter-mqtt-bridge

# Check Dockerfile exists
ls bridge/Dockerfile
```

### Containers keep restarting

```bash
# Check logs for error
docker compose logs --tail=50 <service-name>

# Common causes:
# - IPv6 not configured (OTBR)
# - Serial device not found (OTBR)
# - MQTT broker not running (bridge)
# - Matter server not accessible (bridge)
```

## Getting Help

If you're still having issues:

1. **Check all services are healthy:**
   ```bash
   docker compose ps
   ```

2. **Collect logs:**
   ```bash
   docker compose logs > matter-stack-logs.txt
   ```

3. **Check IPv6 configuration:**
   ```bash
   sysctl net.ipv6.conf.all.forwarding
   sysctl net.ipv6.conf.eth0.accept_ra
   ip -6 route | grep wpan0
   ```

4. **Verify hardware:**
   ```bash
   ls -la /dev/serial/by-id/
   lsusb | grep -i "skyconnect\|thread"
   ```

5. **Create GitHub issue** with:
   - Hardware: Raspberry Pi model, Thread radio
   - OS version: `uname -a`
   - Docker version: `docker --version`
   - Logs and error messages
   - Steps to reproduce

---

**Most issues are solved by:**
1. Running `sudo ./scripts/setup-ipv6.sh`
2. Restarting containers: `docker compose restart`
3. Using Matter Server Web UI for commissioning: http://localhost:5580
