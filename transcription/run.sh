#!/bin/bash
#
# Docker Compose Platform-Aware Runner Script
# This script detects the platform, proxy settings, and sudo requirements
# before running docker compose commands.
#

set -e

# Colors for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
COMMAND=${1:-"up"} # Default command is "up"
DOCKER_CMD="docker"
COMPOSE_CMD="compose"
USE_SUDO=false
USE_PROXY=false
PROXY_SERVER=""
DETECT_PROXY=true

# Script banner
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Docker Compose Platform-Aware Runner ${NC}"
echo -e "${BLUE}========================================${NC}"

# Function to print status messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Function to detect the platform
detect_platform() {
    log_info "Detecting platform..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        PLATFORM="macOS"
        log_info "Detected platform: ${PLATFORM}"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        PLATFORM="Linux"
        log_info "Detected platform: ${PLATFORM}"
        
        # Check if it's a remote server by checking hostname pattern
        if hostname | grep -q "\.idm\.dhib\.io$"; then
            log_info "Detected remote server environment"
            ENVIRONMENT="remote"
        else
            ENVIRONMENT="local"
        fi
    else
        PLATFORM="Unknown"
        log_warn "Unknown platform: ${OSTYPE}"
    fi
}

# Function to check if sudo is required for Docker
check_sudo_required() {
    log_info "Checking if sudo is required for Docker..."
    
    # Try to run a simple docker command without sudo
    if docker info &>/dev/null; then
        log_info "Docker can be run without sudo"
        USE_SUDO=false
    else
        # Try with sudo
        if command -v sudo &>/dev/null && sudo docker info &>/dev/null; then
            log_info "Docker requires sudo privileges"
            USE_SUDO=true
        else
            log_error "Cannot run Docker with or without sudo. Please check Docker installation."
            exit 1
        fi
    fi
}

# Function to detect proxy settings
detect_proxy() {
    log_info "Detecting proxy settings..."
    
    # Check environment variables first
    if [[ -n "$http_proxy" || -n "$HTTP_PROXY" ]]; then
        USE_PROXY=true
        PROXY_SERVER="${http_proxy:-$HTTP_PROXY}"
        log_info "Proxy detected from environment variables: ${PROXY_SERVER}"
        return
    fi
    
    # Check if on a remote server known to use proxy
    if [[ "$ENVIRONMENT" == "remote" ]]; then
        # First try curl to detect if a proxy is needed
        if ! curl -s --connect-timeout 5 https://www.google.com &>/dev/null; then
            log_info "Internet connectivity issue detected, checking known proxy..."
            
            # Try with known proxy
            PROXY_SERVER="http://proxy.idm.dhib.io:3128"
            if curl -s --connect-timeout 5 -x "$PROXY_SERVER" https://www.google.com &>/dev/null; then
                USE_PROXY=true
                log_info "Confirmed working proxy: ${PROXY_SERVER}"
            else
                log_warn "Known proxy doesn't work. Will proceed without proxy."
            fi
        else
            log_info "Direct internet connection available, no proxy needed."
        fi
    else
        log_info "Local environment detected, assuming no proxy needed."
    fi
}

# Function to export proxy environment variables
export_proxy_variables() {
    if [[ "$USE_PROXY" == true ]]; then
        log_info "Exporting proxy environment variables"
        export http_proxy="${PROXY_SERVER}"
        export https_proxy="${PROXY_SERVER}"
        export HTTP_PROXY="${PROXY_SERVER}"
        export HTTPS_PROXY="${PROXY_SERVER}"
    fi
}

# Function to build docker compose command with appropriate settings
build_docker_command() {
    CMD=""
    
    # Add sudo if required
    if [[ "$USE_SUDO" == true ]]; then
        CMD+="sudo "
    fi
    
    # Base docker compose command
    CMD+="${DOCKER_CMD} ${COMPOSE_CMD}"
    
    # Add the command
    CMD+=" ${COMMAND}"
    
    # Add any additional arguments
    if [[ "$#" -gt 1 ]]; then
        shift
        CMD+=" $@"
    elif [[ "$COMMAND" == "up" ]]; then
        # Default to detached mode for 'up'
        CMD+=" -d"
    fi
    
    echo "$CMD"
}

# Function to run the docker compose command
run_docker_compose() {
    # If using a proxy, export the environment variables
    if [[ "$USE_PROXY" == true ]]; then
        export_proxy_variables
    fi
    
    CMD=$(build_docker_command "$@")
    
    log_info "Running command: ${CMD}"
    echo -e "${BLUE}----------------------------------------${NC}"
    
    # Execute the command
    eval "$CMD"
    
    EXIT_CODE=$?
    if [[ $EXIT_CODE -eq 0 ]]; then
        echo -e "${BLUE}----------------------------------------${NC}"
        log_info "Command completed successfully"
    else
        echo -e "${BLUE}----------------------------------------${NC}"
        log_error "Command failed with exit code ${EXIT_CODE}"
        exit $EXIT_CODE
    fi
}

# Function to check for Docker installation
check_docker_installed() {
    log_info "Checking Docker installation..."
    
    if ! command -v docker &>/dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check if docker compose is available (v2 or v1)
    if docker compose version &>/dev/null; then
        log_info "Docker Compose v2 detected"
        COMPOSE_CMD="compose"
    elif command -v docker-compose &>/dev/null; then
        log_info "Docker Compose v1 detected"
        DOCKER_CMD="docker-compose"
        COMPOSE_CMD=""
    else
        log_error "Docker Compose is not installed"
        exit 1
    fi
}

# Function to check if docker-compose.yml exists
check_compose_file() {
    log_info "Checking for Docker Compose files..."
    
    if [[ -f "docker-compose.yml" ]]; then
        log_info "Found docker-compose.yml"
    elif [[ -f "docker-compose.yaml" ]]; then
        log_info "Found docker-compose.yaml"
    elif [[ -f "compose.yml" ]]; then
        log_info "Found compose.yml"
    elif [[ -f "compose.yaml" ]]; then
        log_info "Found compose.yaml"
    else
        log_error "No Docker Compose file found in current directory"
        exit 1
    fi
}

# Function to provide usage information
show_usage() {
    echo -e "Usage: $0 [command] [options]"
    echo -e ""
    echo -e "Commands:"
    echo -e "  up        Start the services (default)"
    echo -e "  down      Stop and remove the services"
    echo -e "  build     Build the services"
    echo -e "  ps        List running services"
    echo -e "  logs      View service logs"
    echo -e ""
    echo -e "Options:"
    echo -e "  Any additional options are passed directly to docker compose"
    echo -e ""
    echo -e "Examples:"
    echo -e "  $0                   # Equivalent to 'docker compose up -d'"
    echo -e "  $0 up               # Start containers in detached mode"
    echo -e "  $0 build            # Build containers with appropriate proxy settings"
    echo -e "  $0 down -v          # Stop containers and remove volumes"
    echo -e "  $0 logs -f          # Follow service logs"
    echo -e ""
}

# Main execution starts here
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_usage
    exit 0
fi

# Run all the checks
check_docker_installed
detect_platform
check_sudo_required
check_compose_file

# Only detect proxy if needed for build or up commands
if [[ "$COMMAND" == "build" || "$COMMAND" == "up" ]]; then
    if [[ "$DETECT_PROXY" == true ]]; then
        detect_proxy
    fi
fi

# Run Docker Compose with appropriate settings
run_docker_compose "$@"

exit 0