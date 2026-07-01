# Optional containerized build for Movinyl (Linux).
# The first-class path is native (`python -m movinyl setup`); this image is a
# convenience for reproducible Linux runs.
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Build toolchain + OpenCV + ffmpeg (no ImageMagick / libmagic needed anymore).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        libopencv-dev \
        ffmpeg \
        pkg-config \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps first for layer caching.
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Build the C++ renderers with CMake (binaries land in /app/build).
COPY src/ src/
RUN cmake -S src -B build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build --parallel

# Application code.
COPY . /app/
RUN mkdir -p PROCESSING_ZONE PAGE_ZONE

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -m movinyl doctor || exit 1

# Default: show the doctor report. Override with e.g. `disk` / `page`.
ENTRYPOINT ["python3", "-m", "movinyl"]
CMD ["doctor"]
