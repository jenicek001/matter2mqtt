#!/bin/bash
#########################################################################################
# Matter Stack - Automated Setup Script
#########################################################################################
# This script automates the setup of the complete Matter stack including:
# - Dependency installation
# - IPv6 configuration
# - Environment configuration
# - Docker stack deployment
#
# Usage: ./setup.sh [options]
#   Options:
#     --skip-deps      Skip dependency installation
#     --skip-ipv6      Skip IPv6 configuration
#     --skip-docker    Skip Docker installation
#     --unattended     Non-interactive mode (use defaults)
#
#########################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse arguments
SKIP_DEPS=false
SKIP_IPV6=false
SKIP_DOCKER=false
UNATTENDED=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-deps) SKIP_DEPS=true; shift ;;
        --skip-ipv6) SKIP_IPV6=true; shift ;;
        --skip-docker) SKIP_DOCKER=true; shift ;;
        --unattended) UNATTENDED=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

#########################################################################################
# Helper Functions
#########################################################################################

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

ask_yes_no() {
    if [ "$UNATTENDED" = true ]; then
        return 0  # Default to yes in unattended mode
    fi
    
    while true; do
        read -p "$1 (y/n) " yn
        case $yn in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}

check_root() {
    if [ "$EUID" -eq 0 ]; then
        print_error "Please do not run this script as root. It will ask for sudo when needed."
        exit 1
    fi
}

check_os() {
    if [ ! -f /etc/os-release ]; then
        print_error "Cannot detect OS. This script is designed for Debian/Ubuntu/Raspberry Pi OS."
        exit 1
    fi
    
    . /etc/os-release
    print_info "Detected OS: $NAME $VERSION"
}

#########################################################################################
# Installation Functions
#########################################################################################

install_dependencies() {
    print_header "Installing System Dependencies"
    
    if [ "$SKIP_DEPS" = true ]; then
        print_warning "Skipping dependency installation (--skip-deps)"
        return
    fi
    
    print_info "Updating package lists..."
    sudo apt update
    
    print_info "Installing required packages..."
    sudo apt install -y \
        curl \
        git \
        python3 \
        python3-pip \
        mosquitto mosquitto-clients \
        snapd
    
    print_info "Enabling Mosquitto MQTT broker..."
    sudo systemctl enable mosquitto
    sudo systemctl start mosquitto
    
    print_info "Installing chip-tool..."
    if ! command -v chip-tool &> /dev/null; then
        sudo snap install chip-tool
        print_success "chip-tool installed"
    else
        print_success "chip-tool already installed"
    fi
    
    print_success "Dependencies installed"
}

install_docker() {
    print_header "Installing Docker"
    
    if [ "$SKIP_DOCKER" = true ]; then
        print_warning "Skipping Docker installation (--skip-docker)"
        return
    fi
    
    if command -v docker &> /dev/null; then
        print_success "Docker already installed: $(docker --version)"
        
        # Check if user is in docker group
        if groups $USER | grep &>/dev/null '\bdocker\b'; then
            print_success "User already in docker group"
        else
            print_info "Adding user to docker group..."
            sudo usermod -aG docker $USER
            print_warning "You'll need to log out and back in for docker group to take effect"
        fi
    else
        print_info "Installing Docker..."
        curl -fsSL https://get.docker.com | sh
        sudo usermod -aG docker $USER
        print_success "Docker installed"
        print_warning "You'll need to log out and back in for docker group to take effect"
    fi
}

configure_ipv6() {
    print_header "Configuring IPv6 (CRITICAL for Thread)"
    
    if [ "$SKIP_IPV6" = true ]; then
        print_warning "Skipping IPv6 configuration (--skip-ipv6)"
        return
    fi
    
    print_info "Running IPv6 setup script..."
    if [ -f "$SCRIPT_DIR/scripts/setup-ipv6.sh" ]; then
        sudo "$SCRIPT_DIR/scripts/setup-ipv6.sh"
        print_success "IPv6 configured"
        
        # Verify configuration
        print_info "Verifying IPv6 configuration..."
        ipv6_forwarding=$(sysctl -n net.ipv6.conf.all.forwarding)
        if [ "$ipv6_forwarding" = "1" ]; then
            print_success "IPv6 forwarding: enabled"
        else
            print_error "IPv6 forwarding: disabled (expected 1, got $ipv6_forwarding)"
        fi
    else
        print_error "setup-ipv6.sh not found in scripts/ directory"
        exit 1
    fi
}

configure_environment() {
    print_header "Configuring Environment"
    
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        print_info "Creating .env file from template..."
        cp "$SCRIPT_DIR/config/.env.example" "$SCRIPT_DIR/.env"
        print_success ".env file created"
        print_info "Edit .env file to configure MQTT credentials if needed:"
        print_info "  nano $SCRIPT_DIR/.env"
    else
        print_success ".env file already exists"
    fi
}

detect_thread_radio() {
    print_header "Detecting Thread Radio"
    
    print_info "Scanning for Thread radio devices..."
    
    if [ -d "/dev/serial/by-id" ]; then
        RADIO_DEVICES=$(ls /dev/serial/by-id/ | grep -i "skyconnect\|thread\|otbr" || true)
        
        if [ -n "$RADIO_DEVICES" ]; then
            print_success "Found Thread radio device(s):"
            echo "$RADIO_DEVICES" | while read device; do
                echo "  - $device"
            done
            
            # Get the first device
            FIRST_DEVICE=$(echo "$RADIO_DEVICES" | head -n 1)
            DEVICE_PATH="/dev/serial/by-id/$FIRST_DEVICE"
            
            print_info "Will use: $DEVICE_PATH"
            print_warning "If this is not correct, update the device path in docker-compose.yml"
            
            # Update docker-compose.yml if needed
            if ask_yes_no "Update docker-compose.yml with this device path?"; then
                print_info "Updating docker-compose.yml..."
                # This is a simplified update - in production, use proper YAML parsing
                print_warning "Please manually update the device path in docker-compose.yml"
                print_info "  Line: --radio-url spinel+hdlc+uart:///$DEVICE_PATH?uart-baudrate=460800"
            fi
        else
            print_warning "No Thread radio device found"
            print_info "Please connect your SkyConnect or Thread radio dongle"
            print_info "After connecting, update the device path in docker-compose.yml"
        fi
    else
        print_warning "/dev/serial/by-id not found - cannot detect USB devices"
    fi
}

build_docker_images() {
    print_header "Building Docker Images"
    
    print_info "Building Matter-MQTT bridge image..."
    cd "$SCRIPT_DIR"
    docker compose build matter-mqtt-bridge
    print_success "Docker images built"
}

start_stack() {
    print_header "Starting Matter Stack"
    
    if ask_yes_no "Start the Matter stack now?"; then
        print_info "Starting services..."
        cd "$SCRIPT_DIR"
        docker compose up -d
        
        print_info "Waiting for services to become healthy (30s)..."
        sleep 30
        
        print_info "Service status:"
        docker compose ps
        
        print_success "Matter stack started"
    else
        print_info "Skipping stack startup"
        print_info "To start manually: docker compose up -d"
    fi
}

show_next_steps() {
    print_header "Setup Complete!"
    
    echo -e "${GREEN}The Matter stack is configured and ready to use.${NC}\n"
    
    echo "Next steps:"
    echo ""
    echo "1. Verify all services are healthy:"
    echo "   ${BLUE}docker compose ps${NC}"
    echo ""
    echo "2. Check OTBR status:"
    echo "   ${BLUE}docker exec otbr ot-ctl state${NC}"
    echo "   ${YELLOW}Should show: leader or router${NC}"
    echo ""
    echo "3. Get Thread dataset for commissioning:"
    echo "   ${BLUE}docker exec otbr ot-ctl dataset active -x${NC}"
    echo ""
    echo "4. Commission your first Matter device:"
    echo "   ${BLUE}chip-tool pairing code-thread 4 hex:<DATASET> <PAIRING_CODE>${NC}"
    echo ""
    echo "5. Configure device friendly names:"
    echo "   ${BLUE}nano bridge/bridge-config-v2.yaml${NC}"
    echo ""
    echo "6. Monitor MQTT topics:"
    echo "   ${BLUE}mosquitto_sub -t 'matter/#' -v${NC}"
    echo ""
    echo "📚 Documentation:"
    echo "   - Quick Start: ${BLUE}docs/QUICK_START_GUIDE.md${NC}"
    echo "   - Full Guide: ${BLUE}docs/MATTER_SETUP_ANALYSIS.md${NC}"
    echo "   - Troubleshooting: ${BLUE}README.md${NC}"
    echo ""
    
    if groups $USER | grep -qv '\bdocker\b'; then
        print_warning "IMPORTANT: You need to log out and back in for docker group changes to take effect!"
    fi
}

#########################################################################################
# Main Setup Flow
#########################################################################################

main() {
    clear
    
    echo -e "${BLUE}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║           Matter-to-MQTT Bridge Setup                     ║
║                                                           ║
║   Complete setup for Matter devices with MQTT             ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    check_root
    check_os
    
    print_info "This script will:"
    echo "  1. Install system dependencies (Docker, MQTT, chip-tool)"
    echo "  2. Configure IPv6 (required for Thread)"
    echo "  3. Set up environment configuration"
    echo "  4. Detect Thread radio device"
    echo "  5. Build Docker images"
    echo "  6. Start the Matter stack"
    echo ""
    
    if ! ask_yes_no "Continue with setup?"; then
        print_info "Setup cancelled"
        exit 0
    fi
    
    # Run setup steps
    install_dependencies
    install_docker
    configure_ipv6
    configure_environment
    detect_thread_radio
    build_docker_images
    start_stack
    
    # Show next steps
    show_next_steps
}

# Run main function
main "$@"
