# mDNS Discovery in Matter Stack

## How mDNS Works in Your Setup

```
┌─────────────────────────────────────────────────────────────────┐
│                    mDNS Discovery Flow                           │
└─────────────────────────────────────────────────────────────────┘

1. System Level (Raspberry Pi)
   ┌──────────────────┐
   │  avahi-daemon    │  ← System service (always running)
   │  (mDNS/DNS-SD)   │
   │                  │
   │  Listens on:     │
   │  - UDP port 5353 │
   │  - 224.0.0.251   │  (mDNS multicast address)
   └────────┬─────────┘
            │
            ▼

2. OTBR Announces Services
   ┌──────────────────────────────────┐
   │  OpenThread Border Router        │
   │                                  │
   │  Advertises:                     │
   │  • _meshcop._udp.local          │  → Thread network joining
   │    - Network Name                │
   │    - Extended PAN ID             │
   │    - Commissioner credentials    │
   │                                  │
   │  • _ipps._tcp.local             │  → Generic IP services
   │  • raspberrypi.local            │  → Hostname resolution
   └──────────────────────────────────┘

3. Matter Devices Announce Themselves

   During Commissioning:
   ┌──────────────────────────────────┐
   │  IKEA Timmerflotte/Alpstuga      │
   │                                  │
   │  Advertises:                     │
   │  • _matterc._udp.local          │  ← Commissioning service
   │    - Discriminator: 3840         │
   │    - Vendor ID: 4447 (IKEA)     │
   │    - Product ID                  │
   │    - Device Type                 │
   │    - Pairing Instructions        │
   └──────────────────────────────────┘
   
   After Commissioned:
   ┌──────────────────────────────────┐
   │  Matter Device (Operational)     │
   │                                  │
   │  Advertises:                     │
   │  • _matter._tcp.local           │  ← Operational service
   │    - Compressed Fabric ID        │
   │    - Node ID                     │
   │    - IPv6 addresses              │
   │    - Port: 5540                  │
   └──────────────────────────────────┘

4. Matter Server Discovers Devices
   ┌──────────────────────────────────┐
   │  python-matter-server            │
   │                                  │
   │  1. Listens for mDNS ads         │
   │  2. Filters _matterc._udp        │  (during pairing)
   │  3. Filters _matter._tcp         │  (operational)
   │  4. Establishes connection       │
   │  5. Maintains device registry    │
   └──────────────────────────────────┘
```

## mDNS Record Examples

### 1. Thread Border Router Advertisement
```
Service Type: _meshcop._udp.local
Service Name: OpenThread BorderRouter
Port: 49191
TXT Record:
  nn=OpenThread
  rv=1
  tv=1.3.0
  xa=<extended_pan_id>
  sb=<service_bitmap>
```

### 2. Matter Device in Commissioning Mode
```
Service Type: _matterc._udp.local
Service Name: _I4447CC4C1F9._matterc._udp.local
Port: 5540
TXT Record:
  D=3840              ← Discriminator
  VP=4447+21075       ← Vendor ID + Product ID
  CM=1                ← Commissioning Mode (1=standard)
  DT=770              ← Device Type (temperature sensor)
  DN=TIMMERFLOTTE     ← Device Name
  SII=5000            ← Sleepy Idle Interval
  SAI=300             ← Sleepy Active Interval
```

### 3. Matter Device Operational
```
Service Type: _matter._tcp.local
Service Name: <compressed_fabric_id>-<node_id>._matter._tcp.local
Port: 5540
IPv6 Address: fd00:1234:5678::abcd

TXT Record:
  SII=5000
  SAI=300
  T=1
```

## Commands to Monitor mDNS

### Scan for All Matter Services
```bash
# All Matter commissioning devices
avahi-browse -rt _matterc._udp

# All Matter operational devices
avahi-browse -rt _matter._tcp

# Thread border routers
avahi-browse -rt _meshcop._udp

# Everything
avahi-browse -a
```

### Example Output During Device Pairing
```bash
$ avahi-browse -rt _matterc._udp

+ wlan0 IPv6 _I4447CC4C1F9                               _matterc._udp        local
= wlan0 IPv6 _I4447CC4C1F9                               _matterc._udp        local
   hostname = [fd00:db8:a0b:12f0::1]
   address = [fd00:db8:a0b:12f0::1]
   port = [5540]
   txt = ["D=3840" "CM=1" "VP=4447+21075" "DT=770" "DN=TIMMERFLOTTE"]
```

## Troubleshooting mDNS

### Check if avahi-daemon is Running
```bash
systemctl status avahi-daemon

# Should show: Active: active (running)
```

### Check mDNS Network Traffic
```bash
# Install tcpdump if needed
sudo apt install tcpdump

# Capture mDNS packets
sudo tcpdump -i any port 5353 -v
```

### Verify mDNS Hostname Resolution
```bash
# Your Raspberry Pi should resolve to its IP
avahi-resolve-host-name raspberrypi.local

# Ping using mDNS name
ping raspberrypi.local
```

### Check Firewall Rules
```bash
# mDNS must be allowed on UDP 5353
sudo ufw status | grep 5353

# If blocked, allow it:
sudo ufw allow 5353/udp
```

### Manual Service Publishing (Testing)
```bash
# Install avahi-utils
sudo apt install avahi-utils

# Publish a test service
avahi-publish -s "Test Service" _test._tcp 12345 "test=value"

# Browse for your test service
avahi-browse -rt _test._tcp
```

## How chip-tool Uses mDNS

When you run:
```bash
chip-tool pairing code 1 MT:XXXXX
```

Behind the scenes:
1. chip-tool queries mDNS for `_matterc._udp.local`
2. Receives list of devices in pairing mode
3. Filters by discriminator from QR code
4. Connects to device's IPv6 address on port 5540
5. Performs PASE (Password Authenticated Session Establishment)
6. Device transitions to operational mode
7. Device now advertises on `_matter._tcp.local`

## How python-matter-server Uses mDNS

The Matter server maintains:
- **Active scan** for `_matterc._udp` during commissioning
- **Passive monitoring** for `_matter._tcp` for operational devices
- **Automatic reconnection** if device IP changes (Thread devices can roam)
- **Service cache** to speed up repeated connections

## mDNS and Thread Integration

Thread devices announce on 6LoWPAN mesh:
```
Device → Thread Network → Border Router → mDNS on Ethernet/WiFi
```

The OTBR acts as mDNS proxy:
1. Listens for Thread device advertisements (SRP - Service Registration Protocol)
2. Translates to mDNS format
3. Announces on Ethernet/WiFi network
4. Matter server sees device as if it's on local network

## Common mDNS Issues

### Issue: Devices not appearing in avahi-browse
**Causes:**
- Device not in pairing mode
- Firewall blocking port 5353
- avahi-daemon not running
- Network isolation (VLANs)

**Solutions:**
```bash
# Restart avahi
sudo systemctl restart avahi-daemon

# Check firewall
sudo ufw allow 5353/udp

# Verify network
ip addr show
# Ensure device and Pi are on same network
```

### Issue: Intermittent discovery
**Causes:**
- mDNS cache issues
- Network congestion
- WiFi power saving

**Solutions:**
```bash
# Flush mDNS cache
sudo systemctl restart avahi-daemon

# Disable WiFi power saving (if using WiFi)
sudo iwconfig wlan0 power off
```

### Issue: Wrong IP address cached
**Cause:** mDNS TTL hasn't expired

**Solution:**
```bash
# Clear avahi cache
sudo rm -rf /var/run/avahi-daemon/*
sudo systemctl restart avahi-daemon
```

## Advanced: Custom mDNS Services

You can publish custom services for your automation:

```python
# Example: Publish custom Matter bridge service
import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

DBusGMainLoop(set_as_default=True)

bus = dbus.SystemBus()
server = dbus.Interface(
    bus.get_object('org.freedesktop.Avahi', '/'),
    'org.freedesktop.Avahi.Server'
)

group = dbus.Interface(
    bus.get_object('org.freedesktop.Avahi', server.EntryGroupNew()),
    'org.freedesktop.Avahi.EntryGroup'
)

# Publish service
group.AddService(
    -1,                              # interface (all)
    -1,                              # protocol (all)
    0,                               # flags
    'Matter MQTT Bridge',            # name
    '_mqtt._tcp',                    # type
    '',                              # domain
    '',                              # host
    1883,                            # port
    ['version=1.0', 'bridge=matter'] # TXT records
)

group.Commit()
```

## Summary

**Your stack's mDNS architecture:**
```
avahi-daemon (Raspberry Pi)
    ↓
OTBR announces Thread network
    ↓
IKEA devices announce via Thread/SRP
    ↓
OTBR proxies to mDNS
    ↓
python-matter-server discovers devices
    ↓
MQTT bridge publishes states
    ↓
HABApp consumes MQTT topics
```

**All automatic, no manual configuration needed!** ✨

The beauty of mDNS in Matter:
- ✅ Zero-configuration networking
- ✅ Automatic device discovery
- ✅ Dynamic IP handling
- ✅ Service advertisement
- ✅ Works across Thread ↔ WiFi/Ethernet
