#!/bin/bash
# Enhanced Oakestra Worker Installation with Resource Donation
# Repository: VenkatReddybathuni/Oakestra
# This installs workers that can donate specific amounts of CPU, memory, and disk

echo "🌳 Installing Enhanced Oakestra Worker"
echo "🚀 With Resource Donation System"

# Repository configuration
REPO_URL=${OAKESTRA_ENHANCED_REPO:-"https://raw.githubusercontent.com/VenkatReddybathuni/Oakestra/venkat"}

# Default resource donations (can be overridden by environment variables)
DONATED_CPU=${DONATED_CPU:-4.0}        # Default 4 CPU cores
DONATED_MEMORY=${DONATED_MEMORY:-8192} # Default 8GB in MB  
DONATED_DISK=${DONATED_DISK:-102400}   # Default 100GB in MB

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --cpu)
            DONATED_CPU="$2"
            shift 2
            ;;
        --memory)
            DONATED_MEMORY="$2"
            shift 2
            ;;
        --disk)
            DONATED_DISK="$2"
            shift 2
            ;;
        --root-addr)
            ROOT_ADDR="$2"
            shift 2
            ;;
        --root-port)
            ROOT_PORT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Enhanced Oakestra Worker Installation"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --cpu CORES        CPU cores to donate (default: 4.0)"
            echo "  --memory MB        Memory in MB to donate (default: 8192 = 8GB)"
            echo "  --disk MB          Disk in MB to donate (default: 102400 = 100GB)"
            echo "  --root-addr ADDR   Root orchestrator address (default: localhost)"
            echo "  --root-port PORT   Root orchestrator port (default: 10100)"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Use defaults (4 CPU, 8GB RAM, 100GB disk)"
            echo "  $0 --cpu 8.0 --memory 16384         # Donate 8 CPU cores and 16GB RAM"
            echo "  $0 --root-addr 192.168.1.100        # Connect to remote orchestrator"
            echo ""
            echo "Environment variables:"
            echo "  DONATED_CPU=8.0 DONATED_MEMORY=16384 $0"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Set defaults for connection parameters
ROOT_ADDR=${ROOT_ADDR:-localhost}
ROOT_PORT=${ROOT_PORT:-10100}

echo "📊 Resource Donation Configuration:"
echo "   CPU Cores: $DONATED_CPU"
echo "   Memory: $DONATED_MEMORY MB ($(echo "scale=1; $DONATED_MEMORY/1024" | bc 2>/dev/null || echo "$(($DONATED_MEMORY/1024))")GB)"
echo "   Disk: $DONATED_DISK MB ($(echo "scale=1; $DONATED_DISK/1024" | bc 2>/dev/null || echo "$(($DONATED_DISK/1024))")GB)"
echo "🔗 Root Orchestrator: $ROOT_ADDR:$ROOT_PORT"
echo ""

# Check architecture
ARCH=$(uname -m)
case $ARCH in
    x86_64)
        ARCH_NAME="amd64"
        ;;
    aarch64|arm64)
        ARCH_NAME="arm64"
        ;;
    armv7l)
        ARCH_NAME="armv7"
        ;;
    *)
        echo "❌ Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

echo "🔧 Detected architecture: $ARCH_NAME"

# Version detection
if [ -z "$OAKESTRA_VERSION" ]; then
    OAKESTRA_VERSION=$(curl -s $REPO_URL/version.txt 2>/dev/null)
    if [ -z "$OAKESTRA_VERSION" ]; then
        # Fallback to original repo version
        OAKESTRA_VERSION=$(curl -s https://raw.githubusercontent.com/lucasleschynski/oakestra/develop/version.txt)
    fi
else 
    if [ "$OAKESTRA_VERSION" = "alpha" ]; then
        OAKESTRA_VERSION=alpha-$(curl -s $REPO_URL/version.txt 2>/dev/null || curl -s https://raw.githubusercontent.com/lucasleschynski/oakestra/develop/version.txt)
    fi
fi

echo "📦 Installing Enhanced Oakestra version: $OAKESTRA_VERSION"

# Clean up previous installations
rm -f NodeEngine_${ARCH_NAME}.tar.gz NetManager_${ARCH_NAME}.tar.gz 2> /dev/null

# Step 1: Try to download enhanced NodeEngine from your repository
echo "⚙️  Step 1: Installing Enhanced NodeEngine..."

ENHANCED_DOWNLOAD_URL="$REPO_URL/releases/download/enhanced-$OAKESTRA_VERSION/NodeEngine_${ARCH_NAME}.tar.gz"
FALLBACK_DOWNLOAD_URL="https://github.com/lucasleschynski/oakestra/releases/download/alpha-$OAKESTRA_VERSION/NodeEngine_${ARCH_NAME}.tar.gz"

# Try enhanced version first
if wget -c "$ENHANCED_DOWNLOAD_URL" 2>/dev/null; then
    echo "✅ Downloaded enhanced NodeEngine"
    ENHANCED_VERSION=true
else
    echo "⚠️  Enhanced NodeEngine not found, using standard version"
    echo "   (You'll need to build and upload the enhanced version to your GitHub releases)"
    
    # Fallback to standard version
    wget -c "$FALLBACK_DOWNLOAD_URL"
    if [ $? -ne 0 ]; then
        echo "❌ Failed to download NodeEngine"
        exit 1
    fi
    ENHANCED_VERSION=false
fi

# Extract and install NodeEngine
tar -xzf NodeEngine_${ARCH_NAME}.tar.gz
chmod +x install.sh
mv NodeEngine NodeEngine_${ARCH_NAME}
./install.sh ${ARCH_NAME}

if [ $? -ne 0 ]; then
    echo "❌ Failed to install NodeEngine"
    exit 1
fi

# Step 2: Install NetManager (standard version is fine)
echo "📡 Step 2: Installing NetManager..."
wget -c "https://github.com/oakestra/oakestra-net/releases/download/alpha-$OAKESTRA_VERSION/NetManager_${ARCH_NAME}.tar.gz"
if [ $? -ne 0 ]; then
    echo "❌ Failed to download NetManager"
    exit 1
fi

tar -xzf NetManager_${ARCH_NAME}.tar.gz
chmod +x install.sh
./install.sh ${ARCH_NAME}

if [ $? -ne 0 ]; then
    echo "❌ Failed to install NetManager"
    exit 1
fi

# Step 3: Create enhanced startup script
echo "📝 Step 3: Creating enhanced startup script..."

cat > /usr/local/bin/oakestra-enhanced-worker << EOF
#!/bin/bash
# Enhanced Oakestra Worker with Resource Donation
# Auto-generated by Enhanced Oakestra installer

# Default resource configuration from installation
DEFAULT_CPU=$DONATED_CPU
DEFAULT_MEMORY=$DONATED_MEMORY
DEFAULT_DISK=$DONATED_DISK
DEFAULT_ROOT_ADDR=$ROOT_ADDR
DEFAULT_ROOT_PORT=$ROOT_PORT

# Allow override via environment variables
DONATED_CPU=\${DONATED_CPU:-\$DEFAULT_CPU}
DONATED_MEMORY=\${DONATED_MEMORY:-\$DEFAULT_MEMORY}
DONATED_DISK=\${DONATED_DISK:-\$DEFAULT_DISK}
ROOT_ADDR=\${ROOT_ADDR:-\$DEFAULT_ROOT_ADDR}
ROOT_PORT=\${ROOT_PORT:-\$DEFAULT_ROOT_PORT}

echo "🌳 Starting Enhanced Oakestra Worker"
echo "📊 Donating: \$DONATED_CPU CPU cores, \$DONATED_MEMORY MB RAM, \$DONATED_DISK MB disk"
echo "🔗 Connecting to: \$ROOT_ADDR:\$ROOT_PORT"

# Use enhanced NodeEngine if available
if $ENHANCED_VERSION; then
    echo "✨ Using Enhanced NodeEngine with resource donation"
    NodeEngine \\
        --donated-cpu \$DONATED_CPU \\
        --donated-memory \$DONATED_MEMORY \\
        --donated-disk \$DONATED_DISK \\
        --rootAddr \$ROOT_ADDR \\
        --rootPort \$ROOT_PORT
else
    echo "⚠️  Using standard NodeEngine (enhanced version not available)"
    echo "   Resource donation configured but not enforced"
    NodeEngine --rootAddr \$ROOT_ADDR --rootPort \$ROOT_PORT
fi
EOF

chmod +x /usr/local/bin/oakestra-enhanced-worker

# Step 4: Create systemd service
echo "⚙️  Step 4: Creating systemd service..."

sudo tee /etc/systemd/system/oakestra-enhanced-worker.service > /dev/null << EOF
[Unit]
Description=Enhanced Oakestra Worker with Resource Donation
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/oakestra-enhanced-worker
Restart=always
RestartSec=10
Environment=DONATED_CPU=$DONATED_CPU
Environment=DONATED_MEMORY=$DONATED_MEMORY
Environment=DONATED_DISK=$DONATED_DISK
Environment=ROOT_ADDR=$ROOT_ADDR
Environment=ROOT_PORT=$ROOT_PORT

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload

# Cleanup
rm -f NodeEngine_${ARCH_NAME}.tar.gz NetManager_${ARCH_NAME}.tar.gz install.sh 2>/dev/null

echo ""
echo "✅ Enhanced Oakestra Worker Installation Complete!"
echo ""
echo "🎯 Usage Options:"
echo ""
echo "1. 🚀 Start immediately:"
echo "   oakestra-enhanced-worker"
echo ""
echo "2. 🔧 Custom resources:"
echo "   DONATED_CPU=8.0 DONATED_MEMORY=16384 oakestra-enhanced-worker"
echo ""
echo "3. 🔄 Systemd service:"
echo "   sudo systemctl enable oakestra-enhanced-worker"
echo "   sudo systemctl start oakestra-enhanced-worker"
echo ""
echo "4. 📊 Check status:"
echo "   sudo systemctl status oakestra-enhanced-worker"
echo ""
echo "📋 Current Configuration:"
echo "   CPU Cores: $DONATED_CPU"
echo "   Memory: $DONATED_MEMORY MB ($(echo "scale=1; $DONATED_MEMORY/1024" | bc 2>/dev/null || echo "$(($DONATED_MEMORY/1024))")GB)"
echo "   Disk: $DONATED_DISK MB ($(echo "scale=1; $DONATED_DISK/1024" | bc 2>/dev/null || echo "$(($DONATED_DISK/1024))")GB)"

if [ "$ENHANCED_VERSION" = "true" ]; then
    echo ""
    echo "🎉 Enhanced NodeEngine Active - Resource donation is fully functional!"
else
    echo ""
    echo "⚠️  Note: Standard NodeEngine installed. To get full resource donation:"
    echo "   1. Build your enhanced NodeEngine: cd go_node_engine && go build -o NodeEngine ."
    echo "   2. Upload to GitHub releases as NodeEngine_${ARCH_NAME}.tar.gz"  
    echo "   3. Reinstall: curl -sfL https://raw.githubusercontent.com/VenkatReddybathuni/Oakestra/venkat/scripts/InstallEnhancedWorker.sh | sh"
fi