#!/bin/bash
# Enhanced NodeEngine installation script
ARCH=$1
if [ -z "$ARCH" ]; then
    ARCH=$(uname -m)
    case $ARCH in
        x86_64) ARCH="amd64" ;;
        aarch64|arm64) ARCH="arm64" ;;
    esac
fi

echo "Installing Enhanced NodeEngine for $ARCH"

# Copy NodeEngine to system location
sudo cp NodeEngine_${ARCH} /usr/local/bin/NodeEngine
sudo chmod +x /usr/local/bin/NodeEngine

echo "Enhanced NodeEngine installed successfully"
echo "Features: Resource donation, intelligent scheduling, container resource limits"
