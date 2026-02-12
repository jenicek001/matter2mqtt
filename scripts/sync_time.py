#!/usr/bin/env python3
"""Automatic time sync for Matter devices - run on startup or schedule.

WORKAROUND FOR IKEA DEVICES:
IKEA Alpstuga/Timmerflotte have firmware bug - they ignore SetTimeZone offset.
Solution: Send "fake UTC" = real UTC + timezone offset, so display shows correct local time.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import websockets

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

MATTER_WS_URL = "ws://localhost:5580/ws"
TIMEZONE = "Europe/Prague"

# Devices to sync (node_id: friendly_name)
DEVICES = {
    4: "alpstuga",
    # Add more devices here when commissioned:
    # 5: "timmerflotte",
}

# Set to True for IKEA devices with timezone bug
USE_FAKE_UTC_WORKAROUND = True

def get_timezone_offset_hours():
    """Auto-detect timezone offset including DST.
    
    Returns:
        int: Offset in hours (1 for CET winter, 2 for CEST summer)
    """
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    offset_seconds = int(now.utcoffset().total_seconds())
    offset_hours = offset_seconds // 3600
    
    # Log DST status
    dst_active = now.dst() and now.dst().total_seconds() > 0
    logger.debug(f"Timezone: {TIMEZONE}, Offset: UTC+{offset_hours}, DST active: {dst_active}")
    
    return offset_hours

_CHIP_EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)

def to_chip_epoch_us(dt: datetime) -> int:
    """Convert datetime to microseconds since CHIP epoch."""
    dt_utc = dt.astimezone(timezone.utc)
    return int((dt_utc - _CHIP_EPOCH).total_seconds() * 1_000_000)

async def sync_device_time(ws, node_id: int, device_name: str, msg_id_start: int):
    """Sync time to a single Matter device."""
    
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    utc_now = now.astimezone(ZoneInfo("UTC"))
    
    if USE_FAKE_UTC_WORKAROUND:
        # WORKAROUND: Send fake UTC (UTC + offset) since IKEA devices ignore timezone
        # Auto-detect offset (1 hour CET winter, 2 hours CEST summer)
        offset_hours = get_timezone_offset_hours()
        fake_utc = utc_now + timedelta(hours=offset_hours)
        utc_microseconds = to_chip_epoch_us(fake_utc)
        logger.info(f"Syncing {device_name} (node {node_id}) using FAKE UTC workaround (offset: +{offset_hours}h)")
        logger.info(f"  Real UTC: {utc_now.strftime('%H:%M:%S')}, Fake UTC sent: {fake_utc.strftime('%H:%M:%S')}, Display will show: {now.strftime('%H:%M:%S')}")
    else:
        # Normal operation: Send real UTC + timezone offset
        utc_offset = int(now.utcoffset().total_seconds())
        utc_microseconds = to_chip_epoch_us(utc_now)
        far_future_us = to_chip_epoch_us(utc_now + timedelta(days=365))
        logger.info(f"Syncing {device_name} (node {node_id}) to {now.strftime('%H:%M:%S')}")
    
    endpoint_id = 0
    cluster_id = 56  # Time Synchronization cluster
    
    if USE_FAKE_UTC_WORKAROUND:
        # IKEA workaround: Send all 3 commands but use fake UTC for time
        # Device requires TimeZone+DSTOffset before accepting SetUTCTime (even though it ignores them)
        
        # Step 1: SetTimeZone (will be ignored by device, but required)
        request = {
            "message_id": str(msg_id_start),
            "command": "device_command",
            "args": {
                "node_id": node_id,
                "endpoint_id": endpoint_id,
                "cluster_id": cluster_id,
                "command_name": "SetTimeZone",
                "payload": {"timeZone": [{"offset": 0, "validAt": 0}]}  # Send 0, we're using fake UTC
            }
        }
        await ws.send(json.dumps(request))
        await asyncio.sleep(0.5)
        
        # Step 2: SetDSTOffset (required before SetUTCTime)
        far_future_us = to_chip_epoch_us(utc_now + timedelta(days=365))
        request = {
            "message_id": str(msg_id_start + 1),
            "command": "device_command",
            "args": {
                "node_id": node_id,
                "endpoint_id": endpoint_id,
                "cluster_id": cluster_id,
                "command_name": "SetDSTOffset",
                "payload": {
                    "dstOffset": [{
                        "offset": 0,
                        "validStarting": 0,
                        "validUntil": far_future_us
                    }]
                }
            }
        }
        await ws.send(json.dumps(request))
        await asyncio.sleep(0.5)
        
        # Step 3: SetUTCTime with FAKE UTC (real UTC + offset)
        request = {
            "message_id": str(msg_id_start + 2),
            "command": "device_command",
            "args": {
                "node_id": node_id,
                "endpoint_id": endpoint_id,
                "cluster_id": cluster_id,
                "command_name": "SetUTCTime",
                "payload": {
                    "utcTime": utc_microseconds,
                    "granularity": 3
                }
            }
        }
        await ws.send(json.dumps(request))
        await asyncio.sleep(0.5)
        
    else:
        # Standard Matter time sync sequence (for compliant devices)
        # Step 1: SetTimeZone
        request = {
            "message_id": str(msg_id_start),
            "command": "device_command",
            "args": {
                "node_id": node_id,
                "endpoint_id": endpoint_id,
                "cluster_id": cluster_id,
                "command_name": "SetTimeZone",
                "payload": {"timeZone": [{"offset": utc_offset, "validAt": 0}]}
            }
        }
        await ws.send(json.dumps(request))
        await asyncio.sleep(0.5)
        
        # Step 2: SetDSTOffset
        request = {
            "message_id": str(msg_id_start + 1),
            "command": "device_command",
            "args": {
                "node_id": node_id,
                "endpoint_id": endpoint_id,
                "cluster_id": cluster_id,
                "command_name": "SetDSTOffset",
                "payload": {
                    "dstOffset": [{
                        "offset": 0,
                        "validStarting": 0,
                        "validUntil": far_future_us
                    }]
                }
            }
        }
        await ws.send(json.dumps(request))
        await asyncio.sleep(0.5)
        
        # Step 3: SetUTCTime
        request = {
            "message_id": str(msg_id_start + 2),
            "command": "device_command",
            "args": {
                "node_id": node_id,
                "endpoint_id": endpoint_id,
                "cluster_id": cluster_id,
                "command_name": "SetUTCTime",
                "payload": {
                    "utcTime": utc_microseconds,
                    "granularity": 3
                }
            }
        }
        await ws.send(json.dumps(request))
        await asyncio.sleep(0.5)
    
    logger.info(f"✓ {device_name} synced successfully")

async def sync_all_devices():
    """Sync time to all configured Matter devices."""
    
    try:
        async with websockets.connect(MATTER_WS_URL, close_timeout=2) as ws:
            msg_id = 1
            
            for node_id, device_name in DEVICES.items():
                try:
                    await sync_device_time(ws, node_id, device_name, msg_id)
                    msg_id += 10
                except Exception as e:
                    logger.error(f"Failed to sync {device_name}: {e}")
            
            logger.info(f"Time sync completed for {len(DEVICES)} device(s)")
    
    except Exception as e:
        logger.error(f"Failed to connect to matter-server: {e}")

if __name__ == "__main__":
    asyncio.run(sync_all_devices())
