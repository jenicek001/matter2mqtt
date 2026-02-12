#!/bin/bash
# OpenThread Border Router IPv6 Setup Script
# This script configures the Linux kernel for proper IPv6 routing with OTBR

set -e

echo "========================================"
echo "OTBR IPv6 Configuration Setup"
echo "========================================"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root"
    echo "Please run: sudo $0"
    exit 1
fi

# Detect network interface
echo "Detecting network interface..."
IFACE=$(ip route | grep default | awk '{print $5}' | head -n1)

if [ -z "$IFACE" ]; then
    echo "WARNING: Could not auto-detect network interface"
    echo "Common interfaces: eth0 (Ethernet), wlan0 (WiFi)"
    read -p "Enter your network interface name: " IFACE
fi

echo "Using network interface: $IFACE"
echo

# Backup existing sysctl configuration
if [ -f /etc/sysctl.d/60-otbr-ipv6.conf ]; then
    echo "Backing up existing configuration..."
    cp /etc/sysctl.d/60-otbr-ipv6.conf /etc/sysctl.d/60-otbr-ipv6.conf.bak
    echo "Backup saved to: /etc/sysctl.d/60-otbr-ipv6.conf.bak"
fi

# Copy configuration file
echo "Installing sysctl configuration..."
cp 60-otbr-ipv6.conf /etc/sysctl.d/60-otbr-ipv6.conf

# Update interface name in config file
echo "Configuring for interface: $IFACE"
sed -i "s/net.ipv6.conf.eth0/net.ipv6.conf.$IFACE/g" /etc/sysctl.d/60-otbr-ipv6.conf

# Apply configuration
echo "Applying kernel parameters..."
sysctl --system > /dev/null 2>&1

echo
echo "========================================"
echo "Verification"
echo "========================================"

# Verify critical settings
echo
echo "IPv6 Forwarding:"
sysctl net.ipv6.conf.all.forwarding | sed 's/^/  /'

echo
echo "IPv4 Forwarding:"
sysctl net.ipv4.ip_forward | sed 's/^/  /'

echo
echo "Router Advertisement (RA) Processing on $IFACE:"
sysctl net.ipv6.conf.$IFACE.accept_ra | sed 's/^/  /'
sysctl net.ipv6.conf.$IFACE.accept_ra_rt_info_max_plen | sed 's/^/  /'

echo
echo "========================================"
echo "Kernel Modules"
echo "========================================"

# Load required kernel modules
echo "Loading IPv6 netfilter modules..."
modprobe -q ip6table_filter 2>/dev/null || echo "  ip6table_filter already loaded"
modprobe -q ip6table_mangle 2>/dev/null || echo "  ip6table_mangle already loaded"
modprobe -q nf_conntrack_ipv6 2>/dev/null || echo "  nf_conntrack_ipv6 already loaded (or built-in)"

echo
echo "========================================"
echo "Network Interface Status"
echo "========================================"
echo
echo "Active interfaces:"
ip -br addr show | grep UP | sed 's/^/  /'

echo
echo "IPv6 addresses on $IFACE:"
ip -6 addr show dev $IFACE | grep inet6 | sed 's/^/  /'

echo
echo "========================================"
echo "IPv6 Routing Table"
echo "========================================"
echo
ip -6 route show | sed 's/^/  /'

echo
echo "========================================"
echo "Configuration Complete!"
echo "========================================"
echo
echo "Next steps:"
echo "  1. Start OTBR: docker compose up -d otbr"
echo "  2. Wait 30 seconds for OTBR to initialize"
echo "  3. Check Thread routes: ip -6 route | grep wpan0"
echo "  4. Commission Matter devices"
echo
echo "Troubleshooting commands:"
echo "  - View all IPv6 settings: sysctl -a | grep ipv6"
echo "  - Check OTBR logs: docker logs otbr"
echo "  - Monitor IPv6 neighbors: watch -n1 'ip -6 neigh show'"
echo "  - Test IPv6 connectivity: ping6 ff02::1%$IFACE"
echo
echo "To persist across reboots: Configuration already saved to /etc/sysctl.d/"
echo
