#!/bin/bash

# Movinyl Runner Script - Cross-platform container launcher
# This script automatically detects your OS and runs Movinyl in a container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is installed and running
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first:"
        case "$(uname -s)" in
            Darwin)
                echo "  macOS: https://docs.docker.com/docker-for-mac/install/"
                ;;
            Linux)
                echo "  Linux: https://docs.docker.com/engine/install/"
                ;;
            CYGWIN*|MINGW32*|MSYS*|MINGW*)
                echo "  Windows: https://docs.docker.com/docker-for-windows/install/"
                ;;
            *)
                echo "  Visit: https://docs.docker.com/get-docker/"
                ;;
        esac
        exit 1
    fi

    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi

    print_success "Docker is installed and running"
}

# Function to build the Docker image
build_image() {
    print_info "Building Movinyl Docker image..."
    if ! docker build -t movinyl:latest .; then
        print_error "Failed to build Docker image"
        exit 1
    fi
    print_success "Docker image built successfully"
}

# Function to check if image exists, build if not
ensure_image() {
    if ! docker images movinyl:latest | grep -q movinyl; then
        print_info "Movinyl image not found locally"
        build_image
    else
        print_success "Movinyl image found"
    fi
}

# Function to run movinyl command
run_movinyl() {
    local cmd="$@"

    # Create necessary directories if they don't exist
    mkdir -p PROCESSING_ZONE PAGE_ZONE

    print_info "Running: movinyl $cmd"

    # Run the container with volume mounts (ENTRYPOINT is `python3 -m movinyl`).
    docker run --rm -it \
        -v "$(pwd)/PROCESSING_ZONE:/app/PROCESSING_ZONE:rw" \
        -v "$(pwd)/PAGE_ZONE:/app/PAGE_ZONE:rw" \
        -w /app \
        movinyl:latest \
        $cmd
}

# Function to show usage
show_usage() {
    cat << EOF
Movinyl - Capture the colors of your favorite movie!

USAGE:
    ./run.sh [COMMAND] [OPTIONS]

COMMANDS:
    disk [DIR]     Generate disks from videos in directory (default: PROCESSING_ZONE)
    page [DIR]     Generate pages from disk images in directory (default: PROCESSING_ZONE)
    build          Build the Docker image
    shell          Start an interactive shell in the container
    help           Show this help message

EXAMPLES:
    # Build the image
    ./run.sh build

    # Generate disks from videos in PROCESSING_ZONE
    ./run.sh disk

    # Generate disks from videos in a specific directory
    ./run.sh disk /path/to/videos

    # Generate pages from disk images
    ./run.sh page

    # Start interactive shell
    ./run.sh shell

SETUP:
    1. Place your video files in the PROCESSING_ZONE directory
    2. Run: ./run.sh disk
    3. Move generated PNG files to PAGE_ZONE directory
    4. Run: ./run.sh page

The script will automatically create PROCESSING_ZONE and PAGE_ZONE directories if they don't exist.
EOF
}

# Main script logic
main() {
    # Check if Docker is available
    check_docker

    # Make script executable
    chmod +x "$0"

    case "${1:-help}" in
        "build")
            build_image
            ;;
        "shell")
            ensure_image
            print_info "Starting interactive shell..."
            docker run --rm -it --entrypoint bash \
                -v "$(pwd)/PROCESSING_ZONE:/app/PROCESSING_ZONE:rw" \
                -v "$(pwd)/PAGE_ZONE:/app/PAGE_ZONE:rw" \
                -w /app \
                movinyl:latest
            ;;
        "disk"|"page")
            ensure_image
            shift
            run_movinyl "$@"
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            print_error "Unknown command: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"

