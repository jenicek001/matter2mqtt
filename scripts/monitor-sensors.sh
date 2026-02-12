#!/bin/bash

#############################################################
# Matter Sensor Monitor Script
# Monitors IKEA Timmerflotte and Alpstuga sensors
# Usage: ./monitor_sensors.sh
#############################################################

set -e

# Configuration
TEMP_SENSOR_NODE_ID=1
AIR_QUALITY_NODE_ID=2
UPDATE_INTERVAL=30  # seconds between readings

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}  Matter Sensor Monitoring Started  ${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""

# Function to check if OTBR is running
check_otbr() {
    if docker ps | grep -q otbr; then
        echo -e "${GREEN}✓${NC} OTBR is running"
        OTBR_STATE=$(docker exec otbr ot-ctl state 2>/dev/null)
        echo -e "  Thread state: ${BLUE}${OTBR_STATE}${NC}"
        return 0
    else
        echo -e "${RED}✗${NC} OTBR is not running!"
        echo "  Start with: docker-compose up -d"
        return 1
    fi
}

# Function to read temperature
read_temperature() {
    TEMP_OUTPUT=$(chip-tool temperaturemeasurement read measured-value $TEMP_SENSOR_NODE_ID 1 2>&1)
    
    if echo "$TEMP_OUTPUT" | grep -q "MeasuredValue"; then
        TEMP_RAW=$(echo "$TEMP_OUTPUT" | grep -oP 'Int16s.*:\s*\K[-]?\d+' | head -1)
        TEMP_C=$(echo "scale=1; $TEMP_RAW / 100" | bc)
        TEMP_F=$(echo "scale=1; ($TEMP_C * 9/5) + 32" | bc)
        echo -e "${BLUE}🌡️  Temperature:${NC} ${TEMP_C}°C (${TEMP_F}°F)"
    else
        echo -e "${RED}✗ Failed to read temperature${NC}"
    fi
}

# Function to read humidity
read_humidity() {
    HUM_OUTPUT=$(chip-tool relativehumiditymeasurement read measured-value $TEMP_SENSOR_NODE_ID 1 2>&1)
    
    if echo "$HUM_OUTPUT" | grep -q "MeasuredValue"; then
        HUM_RAW=$(echo "$HUM_OUTPUT" | grep -oP 'Int16u.*:\s*\K\d+' | head -1)
        HUM=$(echo "scale=1; $HUM_RAW / 100" | bc)
        echo -e "${BLUE}💧 Humidity:${NC} ${HUM}%"
    else
        echo -e "${RED}✗ Failed to read humidity${NC}"
    fi
}

# Function to read air quality
read_air_quality() {
    AQ_OUTPUT=$(chip-tool airquality read air-quality $AIR_QUALITY_NODE_ID 1 2>&1)
    
    if echo "$AQ_OUTPUT" | grep -q "AirQuality"; then
        AQ_RAW=$(echo "$AQ_OUTPUT" | grep -oP 'AirQuality.*:\s*\K\d+' | head -1)
        
        case $AQ_RAW in
            0) AQ_TEXT="Unknown" ;;
            1) AQ_TEXT="Good" ;;
            2) AQ_TEXT="Fair" ;;
            3) AQ_TEXT="Moderate" ;;
            4) AQ_TEXT="Poor" ;;
            5) AQ_TEXT="Very Poor" ;;
            6) AQ_TEXT="Extremely Poor" ;;
            *) AQ_TEXT="Unknown ($AQ_RAW)" ;;
        esac
        
        echo -e "${BLUE}🌫️  Air Quality:${NC} ${AQ_TEXT}"
    else
        echo -e "${RED}✗ Failed to read air quality${NC}"
    fi
}

# Function to check Thread network health
check_thread_health() {
    CHILD_COUNT=$(docker exec otbr ot-ctl child table 2>/dev/null | grep -c "Ext Addr" || echo "0")
    echo -e "${BLUE}👥 Thread Devices:${NC} ${CHILD_COUNT} connected"
}

# Main monitoring loop
echo "Checking system status..."
if ! check_otbr; then
    exit 1
fi
echo ""

echo "Starting sensor monitoring (Ctrl+C to stop)..."
echo "Update interval: ${UPDATE_INTERVAL} seconds"
echo ""

# Trap Ctrl+C to clean exit
trap 'echo -e "\n${YELLOW}Monitoring stopped${NC}"; exit 0' INT

COUNTER=1
while true; do
    echo -e "${YELLOW}=== Reading #${COUNTER} ===${NC} $(date '+%Y-%m-%d %H:%M:%S')"
    
    # Read from Timmerflotte (temp/humidity sensor)
    echo -e "\n📊 ${GREEN}Timmerflotte Sensor (Node ${TEMP_SENSOR_NODE_ID}):${NC}"
    read_temperature
    read_humidity
    
    # Read from Alpstuga (air quality sensor)
    echo -e "\n📊 ${GREEN}Alpstuga Sensor (Node ${AIR_QUALITY_NODE_ID}):${NC}"
    read_air_quality
    
    # Thread network health
    echo -e "\n🔗 ${GREEN}Thread Network:${NC}"
    check_thread_health
    
    echo ""
    echo -e "${YELLOW}Next reading in ${UPDATE_INTERVAL} seconds...${NC}"
    echo "—————————————————————————————————————————"
    echo ""
    
    COUNTER=$((COUNTER + 1))
    sleep $UPDATE_INTERVAL
done
