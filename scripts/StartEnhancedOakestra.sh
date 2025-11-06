#!/bin/bash
# Enhanced Oakestra Root + Cluster Installation
# Repository: VenkatReddybathuni/Oakestra
# This installs the root orchestrator and cluster manager with enhanced resource-aware scheduling

echo "🌳 Installing Enhanced Oakestra Root + Cluster"
echo "🚀 With Resource-Aware Scheduling System"

# Check if this is being run from the original repo by mistake
if [[ "$0" == *"lucasleschynski"* ]]; then
    echo "⚠️  This appears to be running from the original repo"
    echo "   For enhanced features, use: VenkatReddybathuni/Oakestra"
fi

# Detect GitHub repository URL if running from curl
REPO_URL=${OAKESTRA_ENHANCED_REPO:-"https://raw.githubusercontent.com/VenkatReddybathuni/Oakestra/venkat"}

# Oakestra branch/version
if [ -z "$OAKESTRA_BRANCH" ]; then
    OAKESTRA_BRANCH='venkat'  # Use venkat branch for your enhanced version
fi

# Check if docker and docker compose installed 
if [ ! -x "$(command -v docker)" ]; then
  echo "Docker is not installed. Please refer to the official Docker documentation for installation instructions specific to your OS: https://docs.docker.com/engine/install/"
  exit 1
fi

echo "Checking docker compose version"
sudo docker compose version
if [ $? -ne 0 ]; then
    echo "Docker compose v2 or higher is required. Please refer to the official Docker documentation for installation instructions specific to your OS: https://docs.docker.com/compose/migrate/"
    exit 1
fi

# Detect OS
current_os=$(uname)

# Install jq if not present
if [ ! -x "$(command -v jq)" ]; then
  echo "jq is not installed. Installing..."
  if [ $current_os = "Darwin" ]; then
    # Install jq on macOS using Homebrew
    brew install jq
  else
    # Install jq on Ubuntu/Debian based systems using apt
    sudo apt update && sudo apt install -y jq
  fi
  echo "jq installation complete."
else
  echo "jq is already installed."
fi

if [ $? -ne 0 ]; then
    echo "Error: Failed to install jq. Please install it manually."
    exit 1
fi

# Default configuration
if [ "$2" != "custom" ]; then
    echo "🔧 Using default configuration with enhanced resource management"

    # Get IP address of this machine
    if [ -z "$SYSTEM_MANAGER_URL" ]; then
      if [ $current_os = "Darwin" ]; then
        export SYSTEM_MANAGER_URL=$(ipconfig getifaddr en0)
      else
        export SYSTEM_MANAGER_URL=$(ip route get 1.1.1.1 | grep -oP 'src \K\S+')
      fi
      if [ $? -ne 0 ]; then
          echo "Error: Failed to retrieve interface IP."
          exit 1
      fi
    fi
    echo "Default node IP: $SYSTEM_MANAGER_URL"

    # Get public IP and location
    PUBLIC_IP=$(curl -sLf "https://api.ipify.org")
    if [ $? -ne 0 ]; then
        echo "Error: Failed to retrieve your public IP address."
        exit 1
    fi

    # Get geo coordinates of public IP
    ipLocation=$(curl -sLf "https://ipinfo.io/$PUBLIC_IP/json")
    if [ $? -ne 0 ]; then
        echo "Error: Failed to retrieve your public IP address."
        exit 1
    fi

    # Extract latitude and longitude
    latitude=$(echo "$ipLocation" | jq -r '.loc | split(",") | .[0]')
    longitude=$(echo "$ipLocation" | jq -r '.loc | split(",") | .[1]')

    echo "Default cluster location $(echo $latitude,$longitude,1000)"
    export CLUSTER_LOCATION=$(echo $latitude,$longitude,1000)
    export CLUSTER_NAME=enhanced_cluster
fi

# Clean up and create directories
rm -rf ~/oakestra-enhanced 2> /dev/null
mkdir ~/oakestra-enhanced 2> /dev/null
cd ~/oakestra-enhanced 

# Download enhanced configuration files
echo "📦 Downloading enhanced Oakestra configuration..."

# Download docker compose files with enhanced scheduler
curl -sfL $REPO_URL/run-a-cluster/1-DOC-enhanced.yaml > 1-DOC-enhanced.yaml
curl -sfL $REPO_URL/scripts/utils/downloadConfigFiles.sh > downloadConfigFiles.sh

chmod +x downloadConfigFiles.sh

# Use enhanced config files that include resource-aware scheduler
./downloadConfigFiles.sh run-a-cluster $OAKESTRA_BRANCH enhanced

if [ $? -ne 0 ]; then
    echo "Error: Failed to retrieve enhanced config files"
    echo "Falling back to standard configuration..."
    # Fallback to original repo
    curl -sfL https://raw.githubusercontent.com/lucasleschynski/oakestra/develop/run-a-cluster/1-DOC.yaml > 1-DOC.yaml
    curl -sfL https://raw.githubusercontent.com/lucasleschynski/oakestra/develop/scripts/utils/downloadConfigFiles.sh > downloadConfigFiles.sh
    chmod +x downloadConfigFiles.sh
    ./downloadConfigFiles.sh run-a-cluster develop
fi

# Handle override files if provided
OAK_OVERRIDES=''
if [ ! -z "$OVERRIDE_FILES" ]; then
    IFS=, 
    for element in $OVERRIDE_FILES; do
        echo "Download override: $element"
        curl -sfL $REPO_URL/run-a-cluster/$element > $element
        OAK_OVERRIDES="${OAK_OVERRIDES}-f ${element} " 
    done
    IFS= 
fi

# Check for existing containers
if sudo docker ps -a | grep oakestra >/dev/null 2>&1; then
  echo "🚨 Oakestra containers are already running. Please stop them before starting enhanced cluster."
  echo "🪫 You can turn off the current cluster using: \$ docker compose -f ~/oakestra-enhanced/1-DOC-enhanced.yaml down"
  exit 1
fi

# Start enhanced Oakestra cluster
COMPOSE_FILE="1-DOC-enhanced.yaml"
if [ ! -f "$COMPOSE_FILE" ]; then
    COMPOSE_FILE="1-DOC.yaml"  # Fallback
fi

command_exec="sudo -E docker compose -f $COMPOSE_FILE ${OAK_OVERRIDES}up --pull=always -d"
echo "Executing: $command_exec"
eval "$command_exec"

echo ""
echo "🌳 Enhanced Oakestra Cluster is now starting up..."
echo "✨ Features: Resource-aware scheduling, intelligent placement, resource donation system"
echo ""
echo "🖥️  Oakestra dashboard available at http://$SYSTEM_MANAGER_URL"
echo "📊 Grafana dashboard available at http://$SYSTEM_MANAGER_URL:3000"
echo "📈 Enhanced APIs at http://$SYSTEM_MANAGER_URL:10000/api/docs"
echo ""
echo "🎯 Next Steps:"
echo "   1. Install enhanced workers: curl -sfL https://raw.githubusercontent.com/VenkatReddybathuni/Oakestra/venkat/scripts/InstallEnhancedWorker.sh | sh"
echo "   2. Deploy services with resource specifications"
echo "   3. Monitor intelligent resource allocation in dashboard"
echo ""
echo "🪫 You can turn off the cluster using: \$ docker compose -f ~/oakestra-enhanced/$COMPOSE_FILE down"