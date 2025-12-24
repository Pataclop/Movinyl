# Multi-platform Dockerfile for Movinyl
FROM --platform=$BUILDPLATFORM ubuntu:22.04 AS base

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libopencv-dev \
    python3-dev \
    python3-opencv \
    python3-pip \
    ffmpeg \
    bc \
    imagemagick \
    libmagickwand-dev \
    pkg-config \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash app

# Set work directory
WORKDIR /app

# Copy and install Python requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Install additional Python packages that might be missing
RUN pip3 install --no-cache-dir \
    scikit-learn \
    matplotlib \
    extcolors \
    tmdbsimple

# Copy source code
COPY src/ src/

# Build C++ programs
RUN cd src/disk && make && cp disk /app/
RUN cd src/page && make && cp page /app/
RUN if [ -d "src/disk_mono" ]; then cd src/disk_mono && make && cp disk /app/disk_mono; fi

# Copy application code
COPY . /app/

# Create necessary directories
RUN mkdir -p PROCESSING_ZONE PAGE_ZONE && \
    chown -R app:app /app

# Switch to app user
USER app

# Health check
HEALTH_CHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 --version || exit 1

# Default command
CMD ["python3", "movinyl.py", "--help"]
