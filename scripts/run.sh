#!/bin/bash
#
# Docker Compose Runner Script for Audio Detection System
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
DOCKER_COMPOSE_DIR="docker"

# Script banner
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Audio Detection System - Docker Runner ${NC}"
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

# Function to check for Docker and Docker Compose
check_docker() {
    log_info "Checking Docker installation..."
    
    if ! command -v docker &>/dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check if docker compose is available (v2 or v1)
    if docker compose version &>/dev/null; then
        log_info "Docker Compose v2 detected"
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &>/dev/null; then
        log_info "Docker Compose v1 detected"
        COMPOSE_CMD="docker-compose"
    else
        log_error "Docker Compose is not installed"
        exit 1
    fi
}

# Function to run docker compose commands
run_compose() {
    # Navigate to the docker directory
    cd "$(dirname "$0")/../${DOCKER_COMPOSE_DIR}"
    
    log_info "Running command: ${COMPOSE_CMD} $COMMAND $ARGS"
    ${COMPOSE_CMD} $COMMAND $ARGS
    
    EXIT_CODE=$?
    if [[ $EXIT_CODE -eq 0 ]]; then
        log_info "Command completed successfully"
    else
        log_error "Command failed with exit code ${EXIT_CODE}"
        exit $EXIT_CODE
    fi
}

# Function to display help
show_help() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  up        Start the services (default)"
    echo "  down      Stop and remove the services"
    echo "  build     Build the services"
    echo "  ps        List running services"
    echo "  logs      View service logs"
    echo ""
    echo "Examples:"
    echo "  $0                   # Start services in detached mode"
    echo "  $0 up                # Same as above"
    echo "  $0 up -d             # Start services in detached mode" 
    echo "  $0 down              # Stop services"
    echo "  $0 logs -f api       # Follow logs for the API service"
    echo "  $0 build --no-cache  # Build services without cache"
    echo ""
}

# Main execution
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

# Check Docker and Docker Compose
check_docker

# Handle special cases
case $COMMAND in
    "up")
        # Default to detached mode if not specified
        if [[ "$*" != *"-d"* && "$*" != *"--detach"* ]]; then
            ARGS="-d ${@:2}"
        else
            ARGS="${@:2}"
        fi
        ;;
    *)
        # Pass all arguments after the command
        ARGS="${@:2}"
        ;;
esac

# Run Docker Compose
run_compose

exit 0