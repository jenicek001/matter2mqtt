#!/usr/bin/env python3
"""
Commission Matter devices to python-matter-server via WebSocket API.
Usage: ./commission_device.py <pairing_code> [node_id]
"""

import asyncio
import json
import sys
import websocket
from websocket import create_connection

def commission_device(pairing_code: str, node_id: int = None):
    """Commission a device using Matter server's WebSocket API."""
    
    # Thread dataset from OTBR
    thread_dataset = "0e08000000000001000000030000174a0300000b35060004001fffe002089cdf38a3c06c8eb40708fde2ba6d7f61c0b205102ac1455c3a0a671fe8249f4d08e873c8030f4f70656e5468726561642d383634360102864604105731b6d01936ffa58fe69f38c99c7f420c0402a0f7f8"
    
    # Connect to matter-server WebSocket
    ws_url = "ws://localhost:5580/ws"
    
    print(f"Connecting to Matter server at {ws_url}...")
    ws = create_connection(ws_url)
    
    try:
        # Step 1: Set Thread credentials
        thread_cmd = {
            "message_id": "set_thread",
            "command": "set_thread_dataset",
            "args": {
                "dataset": thread_dataset
            }
        }
        
        print("Step 1: Setting Thread dataset...")
        ws.send(json.dumps(thread_cmd))
        
        # Wait for response
        ws.settimeout(5)
        result = ws.recv()
        print(f"Thread dataset response: {result}")
        
        # Step 2: Commission device
        commission_cmd = {
            "message_id": "commission",
            "command": "commission_with_code",
            "args": {
                "code": pairing_code
            }
        }
        
        print(f"\nStep 2: Commissioning device with code: {pairing_code}")
        print(f"Command: {json.dumps(commission_cmd, indent=2)}")
        
        # Send commission command
        ws.send(json.dumps(commission_cmd))
        
        # Wait for responses
        print("\nWaiting for commissioning to complete...")
        print("(This may take 30-60 seconds - please wait)\n")
        
        timeout = 120  # 2 minutes
        start_time = asyncio.get_event_loop().time() if hasattr(asyncio, 'get_event_loop') else 0
        
        while True:
            try:
                ws.settimeout(5)  # 5 second receive timeout
                result = ws.recv()
                
                if result:
                    data = json.loads(result)
                    print(f"Response: {json.dumps(data, indent=2)}")
                    
                    # Check for success
                    if data.get("message_id") == "commission":
                        if "result" in data:
                            print("\n✅ SUCCESS: Device commissioned!")
                            print(f"Node ID: {data['result'].get('node_id', 'unknown')}")
                            return True
                        elif "error" in data:
                            print(f"\n❌ ERROR: {data['error']}")
                            return False
                    
                    # Check for events
                    if data.get("event") == "node_added":
                        print("\n✅ Device added to Matter network!")
                        
            except websocket.WebSocketTimeoutError:
                # Timeout waiting for data, check if we should continue
                if start_time and (asyncio.get_event_loop().time() - start_time > timeout):
                    print("\n⏱️  Timeout waiting for commissioning to complete")
                    print("Check matter-server logs: docker logs matter-server --tail 50")
                    return False
                continue
                
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted by user")
                return False
                
    finally:
        ws.close()
        print("\nClosed connection to Matter server")

def main():
    if len(sys.argv) < 2:
        print("Usage: ./commission_device.py <pairing_code> [node_id]")
        print("Example: ./commission_device.py 21780414151")
        print("         ./commission_device.py MT:Y.K90-000-0000-0000")
        sys.exit(1)
    
    pairing_code = sys.argv[1]
    node_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    # Install websocket-client if not available
    try:
        import websocket
    except ImportError:
        print("Installing required package: websocket-client")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "websocket-client"])
        import websocket
    
    success = commission_device(pairing_code, node_id)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
