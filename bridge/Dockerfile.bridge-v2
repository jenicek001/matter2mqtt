FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    aiohttp \
    paho-mqtt \
    pyyaml \
    asyncio \
    websockets

# Copy bridge script (v2 with IEEE address support)
COPY matter_mqtt_bridge_v2.py /app/matter_mqtt_bridge.py
COPY bridge-config-v2.yaml /app/config.yaml

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python3 -c "import socket; s=socket.socket(); s.connect(('localhost',1883)); s.close()" || exit 1

# Run the bridge
CMD ["python", "-u", "matter_mqtt_bridge.py"]
