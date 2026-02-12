#!/usr/bin/env python3
"""Read Temperature/Humidity from node 4."""

import json
from websocket import create_connection

ws = create_connection("ws://localhost:5580/ws")

# Read temperature (cluster 0x0402, attribute 0x0000, endpoint 1)
msg = {
    "message_id": "read_temp",
    "command": "read_attribute",
    "args": {
        "node_id": 4,
        "attribute_path": "1/1026/0"  # endpoint/cluster/attribute
    }
}

print("Reading temperature from node 4...")
ws.send(json.dumps(msg))

# Wait for response
ws.settimeout(5)
result = ws.recv()
print(json.dumps(json.loads(result), indent=2))

ws.close()
