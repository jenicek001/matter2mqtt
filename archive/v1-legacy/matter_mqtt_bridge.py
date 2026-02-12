#!/usr/bin/env python3
"""
Matter to MQTT Bridge
Connects to python-matter-server and publishes device states to MQTT
for integration with HABApp and other automation systems.

Author: Generated for Matter setup
Date: February 2026
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


class MatterMQTTBridge:
    """Bridge between Matter devices and MQTT."""
    
    def __init__(self):
        self.mqtt_client: Optional[mqtt.Client] = None
        self.ws_client: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self.devices: Dict[int, Dict] = {}
        self.message_id = 0
        self.config = self.load_config()
        
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
        
        # Set last will
        self.mqtt_client.will_set(
            f"{MQTT_BASE_TOPIC}/bridge/status",
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
            # Publish online status
            self.mqtt_client.publish(
                f"{MQTT_BASE_TOPIC}/bridge/status",
                payload="online",
                qos=1,
                retain=True
            )
            # Subscribe to command topics
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
            
            # Parse topic: matter/<node_id>/set/<cluster>/<command>
            parts = topic.split('/')
            if len(parts) >= 4 and parts[2] == 'set':
                node_id = int(parts[1])
                cluster = parts[3]
                command = parts[4] if len(parts) > 4 else 'default'
                
                # Queue command to be sent to Matter device
                asyncio.create_task(
                    self.send_matter_command(node_id, cluster, command, payload)
                )
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
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
    
    async def subscribe_to_events(self):
        """Subscribe to Matter device events."""
        try:
            # First, get existing nodes
            self.message_id += 1
            get_nodes_msg = {
                "message_id": str(self.message_id),
                "command": "get_nodes"
            }
            await self.ws_client.send(json.dumps(get_nodes_msg))
            logger.info("Requested existing nodes")
            
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
            
            # Handle different event types
            event_type = data.get('event')
            message_id = data.get('message_id', '')
            
            if event_type == 'attribute_updated':
                await self.handle_attribute_update(data)
            elif event_type == 'node_added':
                await self.handle_node_added(data)
            elif event_type == 'node_removed':
                await self.handle_node_removed(data)
            elif 'result' in data:
                # Response to get_nodes command - result is a list of nodes
                result = data.get('result')
                if isinstance(result, list):
                    logger.info(f"Received {len(result)} existing nodes")
                    for node_data in result:
                        if isinstance(node_data, dict) and 'node_id' in node_data:
                            # Extract node_id and pass in expected format
                            node_id = node_data.get('node_id')
                            await self.handle_node_added({'node_id': node_id, 'data': node_data})
                elif isinstance(result, dict) and 'node_id' in result:
                    # Response to get_node command - single node data
                    node_id = result.get('node_id')
                    if 'attributes' in result:
                        await self.publish_node_attributes(node_id, result['attributes'])
            elif message_id:
                # Other responses
                logger.debug(f"Received response: {data}")
                
        except Exception as e:
            logger.error(f"Error handling Matter message: {e}")
    
    async def handle_attribute_update(self, data: Dict):
        """Handle attribute update from Matter device."""
        try:
            node_id = data.get('node_id')
            attribute_path = data.get('attribute_path', {})
            value = data.get('value')
            
            cluster_id = attribute_path.get('cluster_id')
            attribute_id = attribute_path.get('attribute_id')
            endpoint_id = attribute_path.get('endpoint_id')
            
            # Map cluster/attribute to friendly names and MQTT topics
            topic, payload = self.map_attribute_to_mqtt(
                node_id, cluster_id, attribute_id, endpoint_id, value
            )
            
            if topic and payload is not None:
                # Publish to MQTT
                self.mqtt_client.publish(
                    topic,
                    payload=json.dumps(payload) if isinstance(payload, dict) else str(payload),
                    qos=0,
                    retain=True
                )
                logger.info(f"Published to MQTT: {topic} = {payload}")
                
        except Exception as e:
            logger.error(f"Error handling attribute update: {e}")
    
    def map_attribute_to_mqtt(self, node_id: int, cluster_id: int, 
                              attribute_id: int, endpoint_id: int, 
                              value: Any) -> tuple:
        """Map Matter attribute to MQTT topic and payload."""
        
        # Validate required fields
        if cluster_id is None or attribute_id is None or node_id is None:
            return (None, None)
        
        # Temperature Measurement (0x0402)
        if cluster_id == 0x0402 and attribute_id == 0x0000:  # MeasuredValue
            temp_c = value / 100.0  # Matter uses hundredths of degree
            return (
                f"{MQTT_BASE_TOPIC}/{node_id}/temperature",
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
                f"{MQTT_BASE_TOPIC}/{node_id}/humidity",
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
                f"{MQTT_BASE_TOPIC}/{node_id}/air_quality",
                {
                    "quality": quality_map.get(value, "unknown"),
                    "value": value,
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # OnOff (0x0006)
        elif cluster_id == 0x0006 and attribute_id == 0x0000:  # OnOff
            return (
                f"{MQTT_BASE_TOPIC}/{node_id}/state",
                "ON" if value else "OFF"
            )
        
        # Battery (0x0001)
        elif cluster_id == 0x0001 and attribute_id == 0x0021:  # BatteryPercentageRemaining
            battery = value / 2  # Matter uses 0-200 scale
            return (
                f"{MQTT_BASE_TOPIC}/{node_id}/battery",
                {
                    "battery": battery,
                    "unit": "%",
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # Generic fallback
        else:
            return (
                f"{MQTT_BASE_TOPIC}/{node_id}/cluster_{cluster_id:04x}/attr_{attribute_id:04x}",
                value
            )
    
    async def handle_node_added(self, data: Dict):
        """Handle new node discovery."""
        node_id = data.get('node_id')
        logger.info(f"New Matter node discovered: {node_id}")
        
        # Publish discovery info to MQTT
        self.mqtt_client.publish(
            f"{MQTT_BASE_TOPIC}/bridge/devices",
            payload=json.dumps({"event": "node_added", "node_id": node_id}),
            qos=1
        )
        
        # Fetch full node data to publish initial values
        if 'data' in data and 'attributes' in data['data']:
            # We already have the full node data (from get_nodes response)
            await self.publish_node_attributes(node_id, data['data']['attributes'])
        else:
            # Request node data
            self.message_id += 1
            get_node_msg = {
                "message_id": f"get_node_{node_id}",
                "command": "get_node",
                "args": {"node_id": node_id}
            }
            await self.ws_client.send(json.dumps(get_node_msg))
            logger.info(f"Requested data for node {node_id}")
    
    async def publish_node_attributes(self, node_id: int, attributes: Dict):
        """Publish all attributes of a node to MQTT."""
        logger.info(f"Publishing attributes for node {node_id}")
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
                    node_id, cluster_id, attribute_id, endpoint_id, value
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
        
        logger.info(f"Published {published_count} attributes for node {node_id}")
    
    async def handle_node_removed(self, data: Dict):
        """Handle node removal."""
        node_id = data.get('node_id')
        logger.info(f"Matter node removed: {node_id}")
        
        # Publish removal info to MQTT
        self.mqtt_client.publish(
            f"{MQTT_BASE_TOPIC}/bridge/devices",
            payload=json.dumps({"event": "node_removed", "node_id": node_id}),
            qos=1
        )
    
    async def publish_bridge_info(self):
        """Periodically publish bridge status info."""
        while self.running:
            try:
                info = {
                    "status": "online",
                    "devices": len(self.devices),
                    "timestamp": datetime.now().isoformat()
                }
                
                self.mqtt_client.publish(
                    f"{MQTT_BASE_TOPIC}/bridge/info",
                    payload=json.dumps(info),
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
        
        if self.mqtt_client:
            self.mqtt_client.publish(
                f"{MQTT_BASE_TOPIC}/bridge/status",
                payload="offline",
                qos=1,
                retain=True
            )
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()


async def main():
    """Main entry point."""
    bridge = MatterMQTTBridge()
    
    # Handle signals
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        bridge.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await bridge.run()
    except KeyboardInterrupt:
        bridge.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        bridge.stop()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
