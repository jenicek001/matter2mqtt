#!/usr/bin/env python3
"""Simple Matter device commissioning via WebSocket API."""

import json
import sys
import time
from websocket import create_connection

def commission(code):
    """Commission device using manual pairing code."""
    
    # Thread dataset
    dataset = "0e08000000000001000000030000174a0300000b35060004001fffe002089cdf38a3c06c8eb40708fde2ba6d7f61c0b205102ac1455c3a0a671fe8249f4d08e873c8030f4f70656e5468726561642d383634360102864604105731b6d01936ffa58fe69f38c99c7f420c0402a0f7f8"
    
    ws = create_connection("ws://localhost:5580/ws")
    print("✅ Connected to Matter server\n")
    
    # Subscribe to events first
    ws.send(json.dumps({"message_id": "subscribe", "command": "start_listening"}))
    print("📡 Subscribed to Matter events\n")
    
    # Set Thread dataset
    ws.send(json.dumps({
        "message_id": "thread",
        "command": "set_thread_dataset",
        "args": {"dataset": dataset}
    }))
    print("🔧 Thread credentials set\n")
    
    # Start commissioning
    ws.send(json.dumps({
        "message_id": "commission",
        "command": "commission_with_code",
        "args": {"code": code}
    }))
    
    print(f"🔍 Commissioning with code: {code}")
    print("⏳ This may take 30-60 seconds. Waiting for device...\n")
    print("-" * 60)
    
    # Listen for responses
    start = time.time()
    timeout = 120
    
    while time.time() - start < timeout:
        try:
            ws.settimeout(5)
            msg = ws.recv()
            data = json.loads(msg)
            
            # Print all events for debugging
            if data.get("event") == "node_added":
                print(f"\n✅ SUCCESS! Device added:")
                print(f"   Node ID: {data.get('node_id')}")
                print(f"   Event: {json.dumps(data, indent=2)[:500]}")
                return True
                
            elif data.get("message_id") == "commission":
                if "error" in data:
                    print(f"\n❌ Commission ERROR: {data.get('error_code')} - {data.get('details')}")
                    return False
                elif "result" in data:
                    print(f"\n✅ Commission response: {data.get('result')}")
                    
            elif data.get("event") == "attribute_updated":
                node = data.get("node_id")
                print(f"📊 Attribute update on node {node}")
                
        except Exception as e:
            continue
    
    print(f"\n⏱️  Timeout after {timeout}s")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ./commission_simple.py <pairing_code>")
        print("Example: ./commission_simple.py 21780414151")
        sys.exit(1)
    
    success = commission(sys.argv[1])
    sys.exit(0 if success else 1)
