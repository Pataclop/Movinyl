FROM ubuntu:24.04
ENV DEBIAN_FRONTEND noninteractive PYTHONUNBUFFERED 1
RUN apt-get update && \
      apt-get install -y \
        tzdata \
        build-essential \
        libopencv-dev \
        python3 \
        ffmpeg \
        bc \
        python3-pip \
        python3-venv \
        libmagic1 \
        libmagic-dev

ENV VIRTUAL_ENV /opt/venv
ENV PATH "$VIRTUAL_ENV/bin:$PATH"
RUN python3 -m venv /opt/venv

COPY requirements.txt .
RUN which pip3
RUN pip3 install -r requirements.txt

# Install gosu
RUN set -eux; \
	apt-get update; \
	apt-get install -y gosu; \
	rm -rf /var/lib/apt/lists/*; \
# verify that the binary works
	gosu nobody true

RUN useradd app

COPY src /app/src

WORKDIR /app

RUN mkdir PROCESSING_ZONE

RUN cd src/disk && make
RUN cd src/disk_mono && make
RUN cd src/page && make

COPY . /app

RUN chown -R app:app /app

ENTRYPOINT ["/app/docker-entrypoint.sh", "/app/movinyl.py"]
