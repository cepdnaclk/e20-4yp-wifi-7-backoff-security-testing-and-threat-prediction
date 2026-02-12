FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Core build dependencies for ns-3
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    cmake \
    ninja-build \
    python3 \
    python3-pip \
    python3-setuptools \
    python3-dev \
    pkg-config \
    ca-certificates \
    wget \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Use a fixed ns-3 tag for reproducibility.
# NOTE: You can change NS3_TAG later once you confirm the Wi-Fi 7/MLO support you need.
ARG NS3_TAG=ns-3.46.1
WORKDIR /opt

RUN git clone https://gitlab.com/nsnam/ns-3-dev.git ns-3-dev \
    && cd ns-3-dev \
    && git checkout ${NS3_TAG} \
    && ./ns3 configure -d optimized \
    && ./ns3 build

# Create a working directory for scenario code + outputs
WORKDIR /work

# Create a non-root user and make scratch writable
ARG USERNAME=ns3
ARG USER_UID=1000
ARG USER_GID=1000

# Create runtime user
RUN groupadd --gid 1000 ns3 \
 && useradd --uid 1000 --gid 1000 -m ns3 \
 # make the whole ns-3 tree writable for rebuilds during `ns3 run`
 && chown -R ns3:ns3 /opt/ns-3-dev

USER ns3
WORKDIR /work
