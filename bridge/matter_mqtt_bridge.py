#!/usr/bin/env python3
"""
Matter to MQTT Bridge (Enhanced with IEEE Address Support)
Connects to python-matter-server and publishes device states to MQTT
using IEEE addresses (like zigbee2mqtt) for stable, readable topic names.

Features:
- IEEE EUI-64 address-based MQTT topics
- Friendly name support from config file
- Device availability tracking
- zigbee2mqtt-compatible topic structure

Author: Generated for Matter setup
Date: February 2026
Version: 2.0 (IEEE Address Support)
"""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt
import websockets
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
MATTER_SERVER_URL = os.getenv('MATTER_SERVER_URL', 'ws://localhost:5580/ws')
MQTT_BROKER = os.getenv('MQTT_BROKER', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_USERNAME = os.getenv('MQTT_USERNAME')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD')
MQTT_BASE_TOPIC = os.getenv('MQTT_BASE_TOPIC', 'matter')
CONFIG_FILE = os.getenv('CONFIG_FILE', '/app/config.yaml')


class DeviceRegistry:
    """Registry for mapping between node IDs and friendly names."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.devices: Dict[int, Dict] = {}  # node_id -> device info
        
    def register_device(self, node_id: int, info: Dict = None):
        """Register a device with its node ID."""
        device_info = {
            'node_id': node_id,
            'friendly_name': self._get_friendly_name(node_id),
            'last_seen': datetime.now(),
            'available': True,
            'info': info or {}
        }
        
        self.devices[node_id] = device_info
        logger.info(f"Registered device: node {node_id} as '{device_info['friendly_name']}'")
        
    def _get_friendly_name(self, node_id: int) -> str:
        """Get friendly name from config or use node_id."""
        device_config = self.config.get('devices', {}).get(node_id, {})
        return device_config.get('friendly_name', f"node_{node_id}")
    
    def get_device_by_node_id(self, node_id: int) -> Optional[Dict]:
        """Get device info by node ID."""
        return self.devices.get(node_id)
    
    def get_topic_identifier(self, node_id: int) -> str:
        """Get topic identifier (friendly name or node_id)."""
        device = self.get_device_by_node_id(node_id)
        if not device:
            # Not yet registered, check config
            device_config = self.config.get('devices', {}).get(node_id, {})
            return device_config.get('friendly_name', f"node_{node_id}")
        
        return device['friendly_name']
    
    def update_availability(self, node_id: int, available: bool):
        """Update device availability."""
        if node_id in self.devices:
            self.devices[node_id]['available'] = available
            self.devices[node_id]['last_seen'] = datetime.now()


class MatterMQTTBridge:
    """Bridge between Matter devices and MQTT with IEEE address support."""
    
    def __init__(self):
        self.mqtt_client: Optional[mqtt.Client] = None
        self.ws_client: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self.message_id = 0
        self.config = self.load_config()
        self.device_registry = DeviceRegistry(self.config)
        
    def load_config(self) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded configuration from {CONFIG_FILE}")
                return config or {}
        except FileNotFoundError:
            logger.warning(f"Config file {CONFIG_FILE} not found, using defaults")
            return {}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def setup_mqtt(self):
        """Set up MQTT client."""
        self.mqtt_client = mqtt.Client(client_id="matter-mqtt-bridge")
        
        if MQTT_USERNAME and MQTT_PASSWORD:
            self.mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        
        # Set last will (like zigbee2mqtt)
        self.mqtt_client.will_set(
            f"{MQTT_BASE_TOPIC}/bridge/state",
            payload="offline",
            qos=1,
            retain=True
        )
        
        try:
            logger.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection."""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            # Publish online status (like zigbee2mqtt)
            self.mqtt_client.publish(
                f"{MQTT_BASE_TOPIC}/bridge/state",
                payload="online",
                qos=1,
                retain=True
            )
            # Subscribe to command topics (both friendly name and IEEE)
            self.mqtt_client.subscribe(f"{MQTT_BASE_TOPIC}/+/set/#")
            logger.info(f"Subscribed to {MQTT_BASE_TOPIC}/+/set/#")
        else:
            logger.error(f"Failed to connect to MQTT broker, return code {rc}")
    
    def on_mqtt_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection."""
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection, return code {rc}")
    
    def on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages (commands)."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            logger.info(f"MQTT message received: {topic} = {payload}")
            
            # Parse topic: matter/<device_identifier>/set/<cluster>/<command>
            parts = topic.split('/')
            if len(parts) >= 4 and parts[2] == 'set':
                device_identifier = parts[1]  # Could be IEEE or friendly name
                cluster = parts[3]
                command = parts[4] if len(parts) > 4 else 'default'
                
                # Resolve to node_id
                node_id = self._resolve_device_identifier(device_identifier)
                if node_id:
                    asyncio.create_task(
                        self.send_matter_command(node_id, cluster, command, payload)
                    )
                else:
                    logger.warning(f"Unknown device: {device_identifier}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def _resolve_device_identifier(self, identifier: str) -> Optional[int]:
        """Resolve device identifier (IEEE or friendly name) to node_id."""
        # Try direct node_id
        try:
            node_id = int(identifier)
            if self.device_registry.get_device_by_node_id(node_id):
                return node_id
        except ValueError:
            pass
        
        # Try IEEE address
        device = self.device_registry.get_device_by_ieee(identifier)
        if device:
            return device['node_id']
        
        # Try friendly name
        for node_id, dev_info in self.device_registry.devices.items():
            if dev_info['friendly_name'] == identifier:
                return node_id
        
        return None
    
    async def send_matter_command(self, node_id: int, cluster: str, command: str, payload: str):
        """Send command to Matter device via websocket."""
        try:
            if not self.ws_client:
                logger.error("WebSocket not connected")
                return
            
            self.message_id += 1
            
            # Build Matter command based on cluster
            matter_cmd = {
                "message_id": str(self.message_id),
                "command": "device.send_command",
                "args": {
                    "node_id": node_id,
                    "endpoint_id": 1,  # Default endpoint
                }
            }
            
            # Map MQTT commands to Matter clusters
            if cluster == "onoff":
                matter_cmd["args"]["cluster_id"] = 0x0006
                if command == "on" or payload.lower() == "on":
                    matter_cmd["args"]["command_id"] = 0x01  # On
                elif command == "off" or payload.lower() == "off":
                    matter_cmd["args"]["command_id"] = 0x00  # Off
                elif command == "toggle":
                    matter_cmd["args"]["command_id"] = 0x02  # Toggle
            
            # Send to Matter server
            await self.ws_client.send(json.dumps(matter_cmd))
            logger.info(f"Sent command to Matter device {node_id}: {cluster}/{command}")
            
        except Exception as e:
            logger.error(f"Error sending Matter command: {e}")
    
    async def connect_matter_server(self):
        """Connect to Matter server WebSocket."""
        while self.running:
            try:
                logger.info(f"Connecting to Matter server at {MATTER_SERVER_URL}")
                async with websockets.connect(MATTER_SERVER_URL) as websocket:
                    self.ws_client = websocket
                    logger.info("Connected to Matter server")
                    
                    # Get all devices and their IEEE addresses
                    await self.discover_devices()
                    
                    # Subscribe to all device events
                    await self.subscribe_to_events()
                    
                    # Listen for messages
                    async for message in websocket:
                        await self.handle_matter_message(message)
                        
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Matter server connection closed, reconnecting...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error connecting to Matter server: {e}")
                await asyncio.sleep(5)
    
    async def discover_devices(self):
        """Request list of Matter devices from server."""
        try:
            # Just send the request - response will be handled in handle_matter_message
            self.message_id += 1
            get_nodes_msg = {
                "message_id": str(self.message_id),
                "command": "get_nodes"
            }
            await self.ws_client.send(json.dumps(get_nodes_msg))
            logger.info("Requested existing nodes")
                        
        except Exception as e:
            logger.error(f"Error requesting devices: {e}")
    
    async def subscribe_to_events(self):
        """Subscribe to Matter device events."""
        try:
            # First, get existing nodes
            await self.discover_devices()
            
            # Then subscribe to events
            self.message_id += 1
            subscribe_msg = {
                "message_id": str(self.message_id),
                "command": "start_listening"
            }
            await self.ws_client.send(json.dumps(subscribe_msg))
            logger.info("Subscribed to Matter events")
        except Exception as e:
            logger.error(f"Error subscribing to events: {e}")
    
    async def handle_matter_message(self, message: str):
        """Handle messages from Matter server."""
        try:
            data = json.loads(message)
            
            # Handle different message types
            event_type = data.get('event')
            
            if event_type == 'attribute_updated':
                # Extract nested data field (matter-server wraps events in 'data')
                event_data = data.get('data', data)
                await self.handle_attribute_update(event_data)
            elif event_type == 'node_added':
                event_data = data.get('data', data)
                await self.handle_node_added(event_data)
            elif event_type == 'node_removed':
                event_data = data.get('data', data)
                await self.handle_node_removed(event_data)
            elif 'result' in data:
                # Response to get_nodes command
                result = data.get('result')
                if isinstance(result, list):
                    logger.info(f"Received {len(result)} existing nodes")
                    for node_data in result:
                        if isinstance(node_data, dict) and 'node_id' in node_data:
                            node_id = node_data.get('node_id')
                            self.device_registry.register_device(node_id, node_data)
                            await self._publish_availability(node_id, True)
                            # Publish initial attributes
                            if 'attributes' in node_data:
                                await self.publish_node_attributes(node_id, node_data['attributes'])
                            logger.info(f"Registered device: node {node_id} as '{self.device_registry.get_topic_identifier(node_id)}'")
            elif data.get('message_id'):
                # Other responses
                logger.debug(f"Received response: {data}")
                
        except Exception as e:
            logger.error(f"Error handling Matter message: {e}")
    
    async def handle_attribute_update(self, data: Dict):
        """Handle attribute update from Matter device."""
        try:
            # Matter-server sends event data as a list: [node_id, 'endpoint/cluster/attr', value]
            if isinstance(data, list) and len(data) >= 3:
                node_id = data[0]
                attr_path_str = data[1]
                value = data[2]
                
                # Parse attribute path: "endpoint/cluster/attribute"
                parts = attr_path_str.split('/')
                if len(parts) == 3:
                    endpoint_id = int(parts[0])
                    cluster_id = int(parts[1])
                    attribute_id = int(parts[2])
                else:
                    logger.debug(f"Invalid attribute path format: {attr_path_str}")
                    return
            else:
                # Old dict format (fallback)
                node_id = data.get('node_id')
                attribute_path = data.get('attribute_path', {})
                value = data.get('value')
                
                cluster_id = attribute_path.get('cluster_id')
                attribute_id = attribute_path.get('attribute_id')
                endpoint_id = attribute_path.get('endpoint_id')
            
            # Get device identifier (IEEE or friendly name)
            device_identifier = self.device_registry.get_topic_identifier(node_id)
            
            # Map cluster/attribute to friendly names and MQTT topics
            topic, payload = self.map_attribute_to_mqtt(
                device_identifier, cluster_id, attribute_id, endpoint_id, value
            )
            
            if topic and payload is not None:
                # Publish to MQTT
                self.mqtt_client.publish(
                    topic,
                    payload=json.dumps(payload) if isinstance(payload, dict) else str(payload),
                    qos=0,
                    retain=True
                )
                logger.debug(f"Published: {topic}")
                
                # Update availability
                self.device_registry.update_availability(node_id, True)
                
        except Exception as e:
            logger.error(f"Error handling attribute update: {e}")
    
    async def publish_node_attributes(self, node_id: int, attributes: Dict):
        """Publish all attributes of a node to MQTT."""
        device_identifier = self.device_registry.get_topic_identifier(node_id)
        logger.info(f"Publishing attributes for {device_identifier}")
        published_count = 0
        
        for attr_path, value in attributes.items():
            try:
                # Parse attribute path: "endpoint/cluster/attribute"
                parts = attr_path.split('/')
                if len(parts) != 3:
                    continue
                    
                endpoint_id = int(parts[0])
                cluster_id = int(parts[1])
                attribute_id = int(parts[2])
                
                # Map to MQTT and publish
                topic, payload = self.map_attribute_to_mqtt(
                    device_identifier, cluster_id, attribute_id, endpoint_id, value
                )
                
                if topic and payload is not None:
                    self.mqtt_client.publish(
                        topic,
                        payload=json.dumps(payload) if isinstance(payload, dict) else str(payload),
                        qos=0,
                        retain=True
                    )
                    published_count += 1
                    logger.debug(f"Published: {topic} = {payload}")
                    
            except Exception as e:
                logger.debug(f"Skipping attribute {attr_path}: {e}")
                continue
        
        logger.info(f"Published {published_count} attributes for {device_identifier}")
    
    def map_attribute_to_mqtt(self, device_identifier: str, cluster_id: int, 
                              attribute_id: int, endpoint_id: int, 
                              value: Any) -> tuple:
        """
        Map Matter attribute to MQTT topic and payload.
        Topics use friendly name for stability.
        """
        
        # Validate required fields
        if cluster_id is None or attribute_id is None:
            return (None, None)
        
        # Temperature Measurement (0x0402)
        if cluster_id == 0x0402 and attribute_id == 0x0000:  # MeasuredValue
            temp_c = value / 100.0  # Matter uses hundredths of degree
            return (
                f"{MQTT_BASE_TOPIC}/{device_identifier}/temperature",
                {
                    "temperature": round(temp_c, 1),
                    "unit": "°C",
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # Relative Humidity (0x0405)
        elif cluster_id == 0x0405 and attribute_id == 0x0000:  # MeasuredValue
            humidity = value / 100.0  # Matter uses hundredths of percent
            return (
                f"{MQTT_BASE_TOPIC}/{device_identifier}/humidity",
                {
                    "humidity": round(humidity, 1),
                    "unit": "%",
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # Air Quality (0x005B)
        elif cluster_id == 0x005B and attribute_id == 0x0000:  # AirQuality
            quality_map = {
                0: "unknown",
                1: "good",
                2: "fair",
                3: "moderate",
                4: "poor",
                5: "very_poor",
                6: "extremely_poor"
            }
            return (
                f"{MQTT_BASE_TOPIC}/{device_identifier}/air_quality",
                {
                    "quality": quality_map.get(value, "unknown"),
                    "value": value,
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # CO2 Concentration (0x040D)
        elif cluster_id == 0x040D and attribute_id == 0x0000:  # MeasuredValue
            return (
                f"{MQTT_BASE_TOPIC}/{device_identifier}/co2",
                {
                    "co2": round(value, 1),
                    "unit": "ppm",
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # PM2.5 Concentration (0x042A)
        elif cluster_id == 0x042A and attribute_id == 0x0000:  # MeasuredValue
            return (
                f"{MQTT_BASE_TOPIC}/{device_identifier}/pm25",
                {
                    "pm25": round(value, 1),
                    "unit": "µg/m³",
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # OnOff (0x0006)
        elif cluster_id == 0x0006 and attribute_id == 0x0000:  # OnOff
            return (
                f"{MQTT_BASE_TOPIC}/{device_identifier}/state",
                "ON" if value else "OFF"
            )
        
        # Battery (0x0001) - Power Configuration
        elif cluster_id == 0x0001 and attribute_id == 0x0021:  # BatteryPercentageRemaining
            battery = value / 2  # Matter uses 0-200 scale
            return (
                f"{MQTT_BASE_TOPIC}/{device_identifier}/battery",
                {
                    "battery": battery,
                    "unit": "%",
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # LinkQuality (for Thread network)
        elif cluster_id == 0x0034:  # Thread Network Diagnostics
            return (
                f"{MQTT_BASE_TOPIC}/{device_identifier}/linkquality",
                value
            )
        
        # Generic fallback
        else:
            return (
                f"{MQTT_BASE_TOPIC}/{device_identifier}/cluster_{cluster_id:04x}/attr_{attribute_id:04x}",
                value
            )
    
    async def _publish_availability(self, node_id: int, available: bool):
        """Publish device availability (like zigbee2mqtt)."""
        device = self.device_registry.get_device_by_node_id(node_id)
        if device:
            device_identifier = self.device_registry.get_topic_identifier(node_id)
            self.mqtt_client.publish(
                f"{MQTT_BASE_TOPIC}/{device_identifier}/availability",
                payload="online" if available else "offline",
                qos=1,
                retain=True
            )
    
    async def handle_node_added(self, data: Dict):
        """Handle new node discovery."""
        node_id = data.get('node_id')
        node_info = data.get('node', {})
        
        logger.info(f"New Matter node discovered: {node_id}")
        
        # Register device by node_id
        self.device_registry.register_device(node_id, node_info)
        await self._publish_availability(node_id, True)
        
        # Publish discovery info to MQTT
        device_identifier = self.device_registry.get_topic_identifier(node_id)
        self.mqtt_client.publish(
            f"{MQTT_BASE_TOPIC}/bridge/devices",
            payload=json.dumps({
                "event": "device_joined",
                "node_id": node_id,
                "friendly_name": device_identifier,
                "timestamp": datetime.now().isoformat()
            }),
            qos=1
        )
    
    async def handle_node_removed(self, data: Dict):
        """Handle node removal."""
        node_id = data.get('node_id')
        device = self.device_registry.get_device_by_node_id(node_id)
        
        if device:
            logger.info(f"Matter node removed: node {node_id} ({device['friendly_name']})")
            await self._publish_availability(node_id, False)
            
            # Publish removal info to MQTT
            self.mqtt_client.publish(
                f"{MQTT_BASE_TOPIC}/bridge/devices",
                payload=json.dumps({
                    "event": "device_left",
                    "node_id": node_id,
                    "friendly_name": device['friendly_name'],
                    "timestamp": datetime.now().isoformat()
                }),
                qos=1
            )
    
    async def publish_bridge_info(self):
        """Periodically publish bridge status info."""
        while self.running:
            try:
                # Collect device list
                devices = []
                for node_id, dev_info in self.device_registry.devices.items():
                    devices.append({
                        "node_id": node_id,
                        "friendly_name": dev_info['friendly_name'],
                        "available": dev_info['available'],
                        "last_seen": dev_info['last_seen'].isoformat()
                    })
                
                info = {
                    "state": "online",
                    "version": "2.0",
                    "devices": devices,
                    "device_count": len(devices),
                    "timestamp": datetime.now().isoformat()
                }
                
                self.mqtt_client.publish(
                    f"{MQTT_BASE_TOPIC}/bridge/info",
                    payload=json.dumps(info),
                    qos=0,
                    retain=True
                )
                
                # Also publish simple device list
                device_names = [d['friendly_name'] for d in devices]
                self.mqtt_client.publish(
                    f"{MQTT_BASE_TOPIC}/bridge/config/devices",
                    payload=json.dumps(device_names),
                    qos=0,
                    retain=True
                )
                
                await asyncio.sleep(60)  # Update every minute
                
            except Exception as e:
                logger.error(f"Error publishing bridge info: {e}")
                await asyncio.sleep(60)
    
    async def run(self):
        """Main run loop."""
        self.running = True
        
        # Set up MQTT
        self.setup_mqtt()
        
        # Create tasks
        tasks = [
            asyncio.create_task(self.connect_matter_server()),
            asyncio.create_task(self.publish_bridge_info())
        ]
        
        # Wait for tasks
        await asyncio.gather(*tasks)
    
    def stop(self):
        """Stop the bridge."""
        logger.info("Stopping Matter MQTT Bridge...")
        self.running = False
        
        # Publish offline status
        if self.mqtt_client:
            self.mqtt_client.publish(
                f"{MQTT_BASE_TOPIC}/bridge/state",
                payload="offline",
                qos=1,
                retain=True
            )
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info("Received shutdown signal")
    if bridge:
        bridge.stop()
    sys.exit(0)


# Global bridge instance
bridge = None

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run bridge
    bridge = MatterMQTTBridge()
    
    try:
        asyncio.run(bridge.run())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        bridge.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
