# Matter to MQTT Integration for HABApp
**Integration Guide for OpenHAB + HABApp Python Automations**

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Your Network                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐         ┌──────────────┐       ┌────────────┐ │
│  │ IKEA Devices │────────▶│    OTBR      │◀──────│ SkyConnect │ │
│  │  (Thread)    │  Thread │   (Docker)   │  USB  │   Dongle   │ │
│  │              │   Mesh  │              │       │            │ │
│  │ - Timmerflotte│         │ - Routing    │       │  OpenThread│ │
│  │ - Alpstuga   │         │ - mDNS       │       │  RCP fw    │ │
│  └──────────────┘         └──────┬───────┘       └────────────┘ │
│                                   │                               │
│                                   │ WebSocket                     │
│                                   ▼                               │
│                          ┌─────────────────┐                      │
│                          │ Matter Server   │                      │
│                          │   (Python)      │                      │
│                          │                 │                      │
│                          │ - Device control│                      │
│                          │ - State mgmt    │                      │
│                          │ - WebSocket API │                      │
│                          └────────┬────────┘                      │
│                                   │                               │
│                                   │ WebSocket                     │
│                                   ▼                               │
│                          ┌─────────────────┐                      │
│                          │ MQTT Bridge     │                      │
│                          │   (Python)      │                      │
│                          │                 │                      │
│                          │ - Translates    │                      │
│                          │   Matter→MQTT   │                      │
│                          └────────┬────────┘                      │
│                                   │                               │
│                                   │ MQTT                          │
│                                   ▼                               │
│                          ┌─────────────────┐                      │
│                          │   Mosquitto     │                      │
│                          │  MQTT Broker    │                      │
│                          │                 │                      │
│                          └────────┬────────┘                      │
│                                   │                               │
│                         ┌─────────┴─────────┐                     │
│                         │                   │                     │
│                         ▼                   ▼                     │
│                  ┌────────────┐      ┌────────────┐              │
│                  │  OpenHAB   │      │   HABApp   │              │
│                  │            │      │  (Python)  │              │
│                  │  - Items   │      │            │              │
│                  │  - Rules   │      │ - Your     │              │
│                  │  - UI      │      │   Rules!   │              │
│                  └────────────┘      └────────────┘              │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## mDNS Discovery Explanation

**How Matter devices are discovered automatically:**

1. **avahi-daemon** (system service on Raspberry Pi)
   - Provides mDNS/DNS-SD functionality
   - Runs as system service: `systemctl status avahi-daemon`
   - Listens on UDP port 5353

2. **OTBR announces Thread network**
   - Publishes `_meshcop._udp` service for Thread joining
   - Advertises itself as border router

3. **Matter devices announce themselves**
   - During commissioning: `_matterc._udp` (Matter Commissioning)
   - After commissioning: `_matter._tcp` (Matter Operational)
   - Example: `Alpstuga._matter._tcp.local`

4. **Matter Server discovers devices**
   - Listens for mDNS advertisements
   - Automatically detects new devices in pairing mode
   - Maintains device registry

**You can verify mDNS manually:**
```bash
# See all Matter devices
avahi-browse -rt _matter._tcp

# See devices in commissioning mode
avahi-browse -rt _matterc._udp

# See Thread border routers
avahi-browse -rt _meshcop._udp
```

## MQTT Topic Structure

### Published Topics (Matter → MQTT)

**Sensor Data:**
```
matter/1/temperature        # {"temperature": 22.5, "unit": "°C", "timestamp": "..."}
matter/1/humidity           # {"humidity": 45.2, "unit": "%", "timestamp": "..."}
matter/2/air_quality        # {"quality": "good", "value": 1, "timestamp": "..."}
matter/1/battery            # {"battery": 85, "unit": "%", "timestamp": "..."}
```

**Device State:**
```
matter/1/state              # "ON" or "OFF"
```

**Bridge Status:**
```
matter/bridge/status        # "online" or "offline" (retained)
matter/bridge/info          # {"status": "online", "devices": 2, "timestamp": "..."}
matter/bridge/devices       # {"event": "node_added", "node_id": 1}
```

### Command Topics (MQTT → Matter)

```
matter/1/set/onoff/on       # Turn on
matter/1/set/onoff/off      # Turn off
matter/1/set/onoff/toggle   # Toggle state
```

## HABApp Integration Examples

### 1. Basic Temperature Monitoring

```python
# rules/matter_temperature.py
from HABApp import Rule
from HABApp.mqtt.items import MqttItem
from HABApp.mqtt.events import MqttValueUpdateEvent
import json

class MatterTemperatureMonitor(Rule):
    def __init__(self):
        super().__init__()
        
        # Subscribe to Timmerflotte temperature
        self.temp_item = MqttItem.get_create_item('matter/1/temperature')
        self.temp_item.listen_event(self.on_temperature, MqttValueUpdateEvent)
        
        self.log.info("Matter Temperature Monitor started")
    
    def on_temperature(self, event):
        """Handle temperature updates from IKEA Timmerflotte"""
        try:
            data = json.loads(event.value)
            temp = data['temperature']
            timestamp = data['timestamp']
            
            self.log.info(f"Temperature: {temp}°C at {timestamp}")
            
            # Example: Trigger heating/cooling
            if temp < 18:
                self.log.warning(f"Temperature too low: {temp}°C")
                # Send command to heating system
                # self.openhab.post_update('Heating_Setpoint', 22)
            
            elif temp > 25:
                self.log.warning(f"Temperature too high: {temp}°C")
                # Trigger cooling or ventilation
                # self.mqtt.publish('ventilation/1/set', 'ON')
                
        except Exception as e:
            self.log.error(f"Error processing temperature: {e}")

MatterTemperatureMonitor()
```

### 2. Air Quality Alerts

```python
# rules/matter_air_quality.py
from HABApp import Rule
from HABApp.mqtt.items import MqttItem
from HABApp.mqtt.events import MqttValueUpdateEvent
from HABApp.openhab.items import SwitchItem
import json

class AirQualityMonitor(Rule):
    def __init__(self):
        super().__init__()
        
        # Subscribe to Alpstuga air quality
        self.air_item = MqttItem.get_create_item('matter/2/air_quality')
        self.air_item.listen_event(self.on_air_quality, MqttValueUpdateEvent)
        
        # OpenHAB ventilation switch (example)
        self.ventilation = SwitchItem.get_item('Ventilation_Switch')
        
        self.log.info("Air Quality Monitor started")
    
    def on_air_quality(self, event):
        """Handle air quality updates from IKEA Alpstuga"""
        try:
            data = json.loads(event.value)
            quality = data['quality']  # good, fair, moderate, poor, very_poor, extremely_poor
            value = data['value']
            
            self.log.info(f"Air Quality: {quality} (value: {value})")
            
            # Automatic ventilation control
            if quality in ['poor', 'very_poor', 'extremely_poor']:
                self.log.warning(f"Poor air quality detected: {quality}")
                # Turn on ventilation
                self.ventilation.oh_send_command('ON')
                
                # Send notification (if you have notification system)
                # self.send_notification(f"Air quality is {quality}. Ventilation activated.")
            
            elif quality in ['good', 'fair'] and self.ventilation.is_on():
                # Turn off ventilation if air quality improved
                self.log.info("Air quality improved, stopping ventilation")
                self.ventilation.oh_send_command('OFF')
                
        except Exception as e:
            self.log.error(f"Error processing air quality: {e}")

AirQualityMonitor()
```

### 3. Combined Climate Control

```python
# rules/matter_climate_control.py
from HABApp import Rule
from HABApp.mqtt.items import MqttItem
from HABApp.mqtt.events import MqttValueUpdateEvent
from HABApp.core.events import ValueUpdateEvent
from HABApp.openhab.items import NumberItem, SwitchItem
import json
from datetime import datetime, timedelta

class ClimateController(Rule):
    def __init__(self):
        super().__init__()
        
        # Matter sensor items
        self.temp_item = MqttItem.get_create_item('matter/1/temperature')
        self.humidity_item = MqttItem.get_create_item('matter/1/humidity')
        self.air_item = MqttItem.get_create_item('matter/2/air_quality')
        
        # Listen to updates
        self.temp_item.listen_event(self.on_sensor_update, MqttValueUpdateEvent)
        self.humidity_item.listen_event(self.on_sensor_update, MqttValueUpdateEvent)
        self.air_item.listen_event(self.on_sensor_update, MqttValueUpdateEvent)
        
        # State tracking
        self.current_temp = None
        self.current_humidity = None
        self.current_air_quality = None
        self.last_update = datetime.now()
        
        # Run climate check every 5 minutes
        self.run.every(timedelta(minutes=5), timedelta(seconds=30), self.check_climate)
        
        self.log.info("Climate Controller started")
    
    def on_sensor_update(self, event):
        """Track sensor states"""
        try:
            data = json.loads(event.value)
            topic = event.name
            
            if 'temperature' in topic:
                self.current_temp = data['temperature']
            elif 'humidity' in topic:
                self.current_humidity = data['humidity']
            elif 'air_quality' in topic:
                self.current_air_quality = data['quality']
            
            self.last_update = datetime.now()
            
        except Exception as e:
            self.log.error(f"Error in sensor update: {e}")
    
    def check_climate(self):
        """Periodic climate check and control"""
        if not all([self.current_temp, self.current_humidity, self.current_air_quality]):
            self.log.warning("Not all sensor data available yet")
            return
        
        self.log.info(
            f"Climate Status - Temp: {self.current_temp}°C, "
            f"Humidity: {self.current_humidity}%, "
            f"Air Quality: {self.current_air_quality}"
        )
        
        # Example: Complex climate rules
        comfort_score = self.calculate_comfort_score()
        self.log.info(f"Comfort score: {comfort_score}")
        
        # Act based on comfort score
        if comfort_score < 60:
            self.log.warning("Comfort score low, adjusting environment")
            # Your custom actions here
    
    def calculate_comfort_score(self):
        """Calculate comfort score based on all sensors"""
        score = 100
        
        # Temperature scoring (optimal: 20-22°C)
        if self.current_temp < 18:
            score -= (18 - self.current_temp) * 5
        elif self.current_temp > 24:
            score -= (self.current_temp - 24) * 5
        
        # Humidity scoring (optimal: 40-60%)
        if self.current_humidity < 30:
            score -= (30 - self.current_humidity) * 2
        elif self.current_humidity > 70:
            score -= (self.current_humidity - 70) * 2
        
        # Air quality scoring
        quality_scores = {
            'good': 0,
            'fair': -10,
            'moderate': -20,
            'poor': -40,
            'very_poor': -60,
            'extremely_poor': -80
        }
        score += quality_scores.get(self.current_air_quality, 0)
        
        return max(0, min(100, score))

ClimateController()
```

### 4. Battery Level Monitoring

```python
# rules/matter_battery.py
from HABApp import Rule
from HABApp.mqtt.items import MqttItem
from HABApp.mqtt.events import MqttValueUpdateEvent
import json

class BatteryMonitor(Rule):
    def __init__(self):
        super().__init__()
        
        # Subscribe to battery levels
        self.battery_item = MqttItem.get_create_item('matter/1/battery')
        self.battery_item.listen_event(self.on_battery_update, MqttValueUpdateEvent)
        
        self.low_battery_threshold = 20  # percent
        self.critical_battery_threshold = 10
        
        self.log.info("Battery Monitor started")
    
    def on_battery_update(self, event):
        """Monitor battery levels"""
        try:
            data = json.loads(event.value)
            battery = data['battery']
            
            if battery <= self.critical_battery_threshold:
                self.log.error(f"CRITICAL: Battery at {battery}%")
                # Send urgent notification
                
            elif battery <= self.low_battery_threshold:
                self.log.warning(f"Low battery: {battery}%")
                # Send notification
                
            else:
                self.log.debug(f"Battery level: {battery}%")
                
        except Exception as e:
            self.log.error(f"Error processing battery level: {e}")

BatteryMonitor()
```

### 5. Data Logging to InfluxDB

```python
# rules/matter_influxdb.py
from HABApp import Rule
from HABApp.mqtt.items import MqttItem
from HABApp.mqtt.events import MqttValueUpdateEvent
import json
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

class MatterInfluxLogger(Rule):
    def __init__(self):
        super().__init__()
        
        # InfluxDB connection
        self.influx_client = InfluxDBClient(
            url="http://localhost:8086",
            token="your-token",
            org="your-org"
        )
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
        
        # Subscribe to all Matter sensors
        for node_id in [1, 2]:
            for sensor in ['temperature', 'humidity', 'air_quality']:
                item = MqttItem.get_create_item(f'matter/{node_id}/{sensor}')
                item.listen_event(self.on_sensor_data, MqttValueUpdateEvent)
        
        self.log.info("InfluxDB Logger started")
    
    def on_sensor_data(self, event):
        """Log sensor data to InfluxDB"""
        try:
            topic_parts = event.name.split('/')
            node_id = topic_parts[1]
            sensor_type = topic_parts[2]
            
            data = json.loads(event.value)
            
            # Create InfluxDB point
            point = Point("matter_sensors") \
                .tag("node_id", node_id) \
                .tag("sensor_type", sensor_type)
            
            # Add fields based on sensor type
            if sensor_type == 'temperature':
                point.field("temperature", float(data['temperature']))
            elif sensor_type == 'humidity':
                point.field("humidity", float(data['humidity']))
            elif sensor_type == 'air_quality':
                point.field("air_quality_value", data['value']) \
                     .field("air_quality_text", data['quality'])
            
            # Write to InfluxDB
            self.write_api.write(bucket="home", record=point)
            
        except Exception as e:
            self.log.error(f"Error logging to InfluxDB: {e}")

MatterInfluxLogger()
```

## OpenHAB Items Configuration

If you want to also use OpenHAB items (optional):

```
// things/matter.things
Thing mqtt:topic:matter_bridge "Matter Bridge" (mqtt:broker:mosquitto) {
    Channels:
        Type string : bridge_status "Bridge Status" [ stateTopic="matter/bridge/status" ]
        Type number : temperature "Living Room Temperature" [ stateTopic="matter/1/temperature", transformationPattern="JSONPATH:$.temperature" ]
        Type number : humidity "Living Room Humidity" [ stateTopic="matter/1/humidity", transformationPattern="JSONPATH:$.humidity" ]
        Type string : air_quality "Living Room Air Quality" [ stateTopic="matter/2/air_quality", transformationPattern="JSONPATH:$.quality" ]
}

// items/matter.items
Number Temperature_LivingRoom "Temperature [%.1f °C]" <temperature> { channel="mqtt:topic:matter_bridge:temperature" }
Number Humidity_LivingRoom "Humidity [%.1f %%]" <humidity> { channel="mqtt:topic:matter_bridge:humidity" }
String AirQuality_LivingRoom "Air Quality [%s]" <flow> { channel="mqtt:topic:matter_bridge:air_quality" }
```

## Testing the Integration

### 1. Start the Stack
```bash
# Start everything
docker-compose up -d

# Check logs
docker-compose logs -f matter-mqtt-bridge
```

### 2. Monitor MQTT Messages
```bash
# Subscribe to all Matter topics
mosquitto_sub -h localhost -t 'matter/#' -v

# Just temperature
mosquitto_sub -h localhost -t 'matter/1/temperature' -v

# Just air quality
mosquitto_sub -h localhost -t 'matter/2/air_quality' -v

# Bridge status
mosquitto_sub -h localhost -t 'matter/bridge/#' -v
```

### 3. Test Commands
```bash
# Turn device on (if you have controllable devices)
mosquitto_pub -h localhost -t 'matter/1/set/onoff/on' -m 'on'

# Turn device off
mosquitto_pub -h localhost -t 'matter/1/set/onoff/off' -m 'off'
```

## Troubleshooting

### Bridge not connecting to Matter Server
```bash
# Check if matter-server is running
docker ps | grep matter-server

# Check matter-server logs
docker logs matter-server

# Test WebSocket connection manually
wscat -c ws://localhost:5580/ws
```

### No MQTT messages
```bash
# Check if Mosquitto is running
systemctl status mosquitto

# Check bridge logs
docker logs -f matter-mqtt-bridge

# Test MQTT broker
mosquitto_pub -h localhost -t 'test' -m 'hello'
mosquitto_sub -h localhost -t 'test' -v
```

### mDNS not working
```bash
# Check avahi-daemon
systemctl status avahi-daemon

# Scan for Matter devices
avahi-browse -a

# Check if port 5353 is open
sudo netstat -tuln | grep 5353
```

## Security Considerations

### MQTT Authentication
Create `.env` file:
```bash
MQTT_USERNAME=your_username
MQTT_PASSWORD=your_strong_password
```

### Mosquitto Configuration
Edit `/etc/mosquitto/mosquitto.conf`:
```
# Enable authentication
allow_anonymous false
password_file /etc/mosquitto/passwd

# ACL for Matter bridge
acl_file /etc/mosquitto/acl

# TLS (optional but recommended)
listener 8883
cafile /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key
```

Create password file:
```bash
sudo mosquitto_passwd -c /etc/mosquitto/passwd matter_bridge
sudo mosquitto_passwd /etc/mosquitto/passwd habapp_user
```

## Performance Tuning

### MQTT Broker
```
# /etc/mosquitto/mosquitto.conf
max_connections 100
max_queued_messages 1000
message_size_limit 10240
```

### Bridge Configuration
Adjust update intervals in `bridge-config.yaml`:
```yaml
intervals:
  bridge_status: 60  # Seconds between status updates
```

## Next Steps

1. Add more devices and expand device mapping
2. Create custom automation rules in HABApp
3. Set up Grafana dashboards for visualization
4. Add alerting via Telegram/Email
5. Implement scene control
6. Add energy monitoring

---

**Questions?** Check the main `MATTER_SETUP_ANALYSIS.md` for additional details.
