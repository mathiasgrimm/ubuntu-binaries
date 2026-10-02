FROM ubuntu:24.04
RUN apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates file binutils python3 python3-pil libimage-exiftool-perl php-cli php-imagick \
    && rm -rf /var/lib/apt/lists/*
