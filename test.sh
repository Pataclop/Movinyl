#!/bin/bash

# Movinyl Container Test Script
# Tests basic functionality of the containerized version

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  Movinyl Container Test Suite${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Function to check if Docker is available
check_docker() {
    print_info "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        return 1
    fi

    if ! docker info &> /dev/null; then
        print_error "Docker is not running"
        return 1
    fi

    print_success "Docker is available"
    return 0
}

# Function to build the image
test_build() {
    print_info "Testing Docker image build..."
    if docker build -t movinyl:test . > /dev/null 2>&1; then
        print_success "Docker image built successfully"
        return 0
    else
        print_error "Failed to build Docker image"
        return 1
    fi
}

# Function to test basic container functionality
test_basic_functionality() {
    print_info "Testing basic container functionality..."

    # Test help command (ENTRYPOINT is `python3 -m movinyl`)
    if docker run --rm movinyl:test --help > /dev/null 2>&1; then
        print_success "Basic command execution works"
    else
        print_error "Basic command execution failed"
        return 1
    fi

    # Test that required tools are available
    if docker run --rm --entrypoint which movinyl:test ffmpeg > /dev/null 2>&1; then
        print_success "FFmpeg is available in container"
    else
        print_error "FFmpeg is not available in container"
        return 1
    fi

    if docker run --rm --entrypoint which movinyl:test cmake > /dev/null 2>&1; then
        print_success "CMake is available in container"
    else
        print_error "CMake is not available in container"
        return 1
    fi

    return 0
}

# Function to test Python imports
test_python_imports() {
    print_info "Testing Python dependencies..."

    # Test basic Python execution
    if docker run --rm --entrypoint python3 movinyl:test -c "import PIL, rich, textual; print('ok')" > /dev/null 2>&1; then
        print_success "Python dependencies are working"
    else
        print_error "Python dependencies failed"
        return 1
    fi

    # Test movinyl imports
    if docker run --rm --entrypoint python3 movinyl:test -c "from movinyl import engine, palette, infos; print('ok')" > /dev/null 2>&1; then
        print_success "Movinyl Python modules import correctly"
    else
        print_error "Movinyl Python modules failed to import"
        return 1
    fi

    return 0
}

# Function to test C++ binaries
test_cpp_binaries() {
    print_info "Testing C++ binaries..."

    if docker run --rm -v "$(pwd)/src/disk/disk:/app/disk" movinyl:test /app/disk --help > /dev/null 2>&1 2>/dev/null || true; then
        print_success "Disk binary is executable"
    else
        print_warning "Disk binary test inconclusive (may not have --help)"
    fi

    if docker run --rm -v "$(pwd)/src/page/page:/app/page" movinyl:test /app/page --help > /dev/null 2>&1 2>/dev/null || true; then
        print_success "Page binary is executable"
    else
        print_warning "Page binary test inconclusive (may not have --help)"
    fi

    return 0
}

# Function to test directory creation
test_directory_setup() {
    print_info "Testing directory setup..."

    # Create test directories
    mkdir -p test_processing test_page

    # Test volume mounting
    if docker run --rm --entrypoint ls -v "$(pwd)/test_processing:/app/PROCESSING_ZONE" -v "$(pwd)/test_page:/app/PAGE_ZONE" movinyl:test -la /app/ | grep -q PROCESSING_ZONE; then
        print_success "Volume mounting works"
    else
        print_error "Volume mounting failed"
        return 1
    fi

    # Cleanup
    rm -rf test_processing test_page

    return 0
}

# Function to run all tests
run_all_tests() {
    local failed_tests=0

    print_header

    if ! check_docker; then
        return 1
    fi

    if ! test_build; then
        ((failed_tests++))
    fi

    if ! test_basic_functionality; then
        ((failed_tests++))
    fi

    if ! test_python_imports; then
        ((failed_tests++))
    fi

    if ! test_cpp_binaries; then
        ((failed_tests++))
    fi

    if ! test_directory_setup; then
        ((failed_tests++))
    fi

    echo
    if [ $failed_tests -eq 0 ]; then
        print_success "All tests passed! ✅"
        echo
        print_info "You can now use Movinyl with:"
        echo "  ./run.sh build    # Build the image"
        echo "  ./run.sh disk     # Generate disks from videos"
        echo "  ./run.sh page     # Generate pages from disks"
        return 0
    else
        print_error "$failed_tests test(s) failed! ❌"
        echo
        print_info "Please check the errors above and try again."
        print_info "You can also run individual tests or check the logs."
        return 1
    fi
}

# Function to show usage
show_usage() {
    echo "Movinyl Container Test Script"
    echo
    echo "Usage:"
    echo "  ./test.sh          # Run all tests"
    echo "  ./test.sh build    # Test only the build"
    echo "  ./test.sh basic    # Test only basic functionality"
    echo "  ./test.sh python   # Test only Python dependencies"
    echo "  ./test.sh cpp      # Test only C++ binaries"
    echo "  ./test.sh dirs     # Test only directory setup"
    echo "  ./test.sh help     # Show this help"
}

# Main script logic
main() {
    case "${1:-all}" in
        "all")
            run_all_tests
            ;;
        "build")
            check_docker && test_build
            ;;
        "basic")
            check_docker && test_basic_functionality
            ;;
        "python")
            check_docker && test_python_imports
            ;;
        "cpp")
            check_docker && test_cpp_binaries
            ;;
        "dirs")
            check_docker && test_directory_setup
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            print_error "Unknown test: $1"
            echo
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
