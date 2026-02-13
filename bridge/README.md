# Matter-MQTT Bridge

This directory contains the Matter-to-MQTT bridge application that publishes Matter device data to MQTT topics.

## Features

- ✅ IEEE address-based MQTT topics (like zigbee2mqtt)
- ✅ Friendly device name mapping
- ✅ Device availability tracking
- ✅ zigbee2mqtt-compatible topic structure
- ✅ Automatic reconnection to Matter server and MQTT broker

## Files

- `matter_mqtt_bridge.py` - Main bridge application
- `bridge-config.yaml` - Device friendly name configuration
- `docker-compose.yml` - Bridge-only deployment
- `Dockerfile` - Docker image definition

## Configuration

Edit `bridge-config.yaml` to map device node IDs to friendly names:

```yaml
devices:
  # IKEA Alpstuga (Air Quality sensor) - Node 4
  4:
    friendly_name: "alpstuga"
    description: "IKEA Alpstuga air quality monitor"
    location: "Living Room"
  
  # IKEA Timmerflotte (Temperature + Humidity sensor) - Node 5
  5:
    friendly_name: "bedroom_temp"
    description: "IKEA Timmerflotte sensor"
    location: "Bedroom"
```

## MQTT Topics

With friendly names configured, you'll see topics like:

```
matter/alpstuga/temperature         → 22.5
matter/alpstuga/humidity            → 45.2
matter/alpstuga/availability        → online

matter/bedroom_temp/temperature     → 21.3
matter/bedroom_temp/humidity        → 48.0
matter/bedroom_temp/availability    → online

matter/bridge/state                 → online
matter/bridge/info                  → {"state": "online", "devices": [...]}
```

## MQTT Settings (Env vs Config)

The bridge loads MQTT settings from environment variables first (via `docker-compose.yml` and optional `.env`).
If a value is not provided via environment variables, the bridge falls back to the `mqtt:` section in
`bridge-config.yaml`.

**Recommended:** use `.env` for secrets (username/password) and keep `bridge-config.yaml` for device mapping.

## Environment Variables

Configure via environment variables or `.env` file:

- `MATTER_SERVER_URL` - WebSocket URL (default: `ws://localhost:5580/ws`)
- `MQTT_BROKER` - MQTT broker address (default: `localhost`)
- `MQTT_PORT` - MQTT broker port (default: `1883`)
- `MQTT_USERNAME` - MQTT username (optional)
- `MQTT_PASSWORD` - MQTT password (optional)
- `MQTT_BASE_TOPIC` - Base topic (default: `matter`)
- `CONFIG_FILE` - Config file path (default: `/app/config.yaml`)

## Running Standalone

To run just the bridge (requires Matter server and MQTT broker already running):

```bash
# Using Docker Compose
docker compose up -d

# Or build and run manually
docker build -t matter-mqtt-bridge .
docker run -d \
  --network host \
  -e MATTER_SERVER_URL=ws://localhost:5580/ws \
  -e MQTT_BROKER=localhost \
  -v ./bridge-config.yaml:/app/config.yaml:ro \
  matter-mqtt-bridge
```

## Running Full Stack

Use the root `docker-compose.yml` to run the complete stack (OTBR + Matter Server + Bridge):

```bash
cd ..
docker compose up -d
```

See main [README.md](../README.md) for complete setup instructions.

## Integration

See [docs/INTEGRATION.md](../docs/INTEGRATION.md) for HABApp/OpenHAB integration examples.

## Troubleshooting

**Bridge not connecting to Matter server:**
```bash
# Check Matter server is running
docker ps | grep matter-server

# Check WebSocket URL is correct
docker compose logs matter-mqtt-bridge | grep "Connecting to Matter server"
```

**Bridge not publishing to MQTT:**
```bash
# Check MQTT broker is running
mosquitto_sub -t 'test' -v

# Check bridge MQTT connection
docker compose logs matter-mqtt-bridge | grep "MQTT"
```

**Devices not appearing:**
```bash
# Check devices are commissioned
# Open Matter Server Web UI: http://localhost:5580

# Check bridge logs
docker compose logs matter-mqtt-bridge
```

For more troubleshooting, see [docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md).
