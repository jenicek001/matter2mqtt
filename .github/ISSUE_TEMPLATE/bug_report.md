---
name: Bug report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug Description
A clear and concise description of what the bug is.

## Environment
- **Hardware**: Raspberry Pi model (e.g., Pi 5, Pi 4)
- **OS**: Output of `uname -a`
- **Docker version**: Output of `docker --version`
- **Thread Radio**: SkyConnect / Other (specify)
- **Matter Devices**: IKEA Alpstuga / Other (specify)

## Steps to Reproduce
1. 
2. 
3. 

## Expected Behavior
What you expected to happen.

## Actual Behavior
What actually happened.

## Logs
```
# Docker logs
docker compose logs matter-mqtt-bridge

# OTBR status
docker exec otbr ot-ctl state

# IPv6 configuration
sysctl net.ipv6.conf.all.forwarding
```

## MQTT Topics
```
# Output from mosquitto_sub if relevant
mosquitto_sub -t 'matter/#' -v
```

## Additional Context
Add any other context about the problem here (screenshots, configuration files, etc.).
