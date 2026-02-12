# Archive

This directory contains historical implementations for reference only.

**Do not use these files in production.**

## v1-legacy/

Original Matter-MQTT bridge implementation using numeric node IDs.

**Superseded by**: Current IEEE address-based implementation in `/bridge`

**Key differences:**
- v1 used node IDs in MQTT topics: `matter/4/temperature`
- Current version uses IEEE addresses/friendly names: `matter/alpstuga/temperature`
- v1 lacked device registry and availability tracking
- Current version is more feature-complete and maintainable

**Historical reference only** - refer to main `/bridge` directory for current implementation.
