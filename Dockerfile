# Multi-stage / Production Dockerfile for Burn Job Engine
FROM python:3.12-slim-bookworm

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install OpenJDK 17, Maven, C++ build toolchain for llama.cpp
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jdk-headless \
    maven \
    build-essential \
    cmake \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME dynamically
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
RUN if [ ! -d "$JAVA_HOME" ]; then export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which javac)))); fi

WORKDIR /app

# Install Python dependencies first for caching
COPY requirements.txt pyproject.toml /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files
COPY . /app

# Install burn-job package
RUN pip install --no-cache-dir -e .

# Entrypoint configuration
ENTRYPOINT ["burn-job"]
CMD ["run-cycle"]
