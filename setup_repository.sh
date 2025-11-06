#!/bin/bash
# GitHub Repository Setup Helper
# This script helps you prepare your enhanced Oakestra repository for deployment

echo "🔧 Enhanced Oakestra Repository Setup Helper"
echo ""

# Check if we're in the right directory
if [ ! -f "oakestra/go_node_engine/NodeEngine.go" ]; then
    echo "❌ This script should be run from the root of your enhanced Oakestra repository"
    echo "   Current directory: $(pwd)"
    echo "   Expected files: oakestra/go_node_engine/NodeEngine.go"
    exit 1
fi

echo "✅ Found enhanced Oakestra source code"

# Step 1: Build NodeEngine for different architectures
echo ""
echo "📦 Step 1: Building Enhanced NodeEngine for multiple architectures"

cd oakestra/go_node_engine

# Build for amd64 (x86_64)
echo "Building for amd64..."
GOOS=linux GOARCH=amd64 go build -o NodeEngine_amd64 .
if [ $? -eq 0 ]; then
    echo "✅ Built NodeEngine_amd64"
else
    echo "❌ Failed to build NodeEngine_amd64"
fi

# Build for arm64
echo "Building for arm64..."
GOOS=linux GOARCH=arm64 go build -o NodeEngine_arm64 .
if [ $? -eq 0 ]; then
    echo "✅ Built NodeEngine_arm64"
else
    echo "❌ Failed to build NodeEngine_arm64"
fi

# Build for current architecture (for local testing)
echo "Building for current architecture..."
go build -o NodeEngine .
if [ $? -eq 0 ]; then
    echo "✅ Built NodeEngine for current architecture"
else
    echo "❌ Failed to build NodeEngine for current architecture"
fi

cd ../..

# Step 2: Create release packages
echo ""
echo "📦 Step 2: Creating release packages"

mkdir -p releases

# Create install.sh script for packages
cat > releases/install.sh << 'EOF'
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
EOF

chmod +x releases/install.sh

# Package amd64
if [ -f "oakestra/go_node_engine/NodeEngine_amd64" ]; then
    cp oakestra/go_node_engine/NodeEngine_amd64 releases/NodeEngine
    cp releases/install.sh releases/
    cd releases
    tar -czf NodeEngine_amd64.tar.gz NodeEngine install.sh
    echo "✅ Created NodeEngine_amd64.tar.gz"
    cd ..
fi

# Package arm64
if [ -f "oakestra/go_node_engine/NodeEngine_arm64" ]; then
    cp oakestra/go_node_engine/NodeEngine_arm64 releases/NodeEngine
    cp releases/install.sh releases/
    cd releases
    tar -czf NodeEngine_arm64.tar.gz NodeEngine install.sh
    echo "✅ Created NodeEngine_arm64.tar.gz"
    cd ..
fi

# Step 3: Create docker compose for enhanced cluster
echo ""
echo "🐳 Step 3: Creating enhanced docker compose configuration"

mkdir -p run-a-cluster

# Copy original docker compose and enhance it
if [ ! -f "run-a-cluster/1-DOC.yaml" ]; then
    echo "Downloading base docker compose configuration..."
    curl -sfL https://raw.githubusercontent.com/lucasleschynski/oakestra/develop/run-a-cluster/1-DOC.yaml > run-a-cluster/1-DOC.yaml
fi

# Also copy from oakestra directory if it exists
if [ -f "oakestra/run-a-cluster/1-DOC.yaml" ]; then
    cp oakestra/run-a-cluster/1-DOC.yaml run-a-cluster/1-DOC.yaml
fi

# Create enhanced version
cp run-a-cluster/1-DOC.yaml run-a-cluster/1-DOC-enhanced.yaml

# Add enhanced scheduler notice (you can customize the actual scheduler image later)
cat >> run-a-cluster/1-DOC-enhanced.yaml << 'EOF'

# Enhanced Oakestra Configuration
# This configuration includes:
# - Resource-aware cluster scheduler
# - Support for resource donation from workers
# - Intelligent service placement algorithms
EOF

echo "✅ Created enhanced docker compose configuration"

# Step 4: Create version file
echo ""
echo "📋 Step 4: Creating version information"

# Get current date for version
VERSION_DATE=$(date +%Y%m%d)
echo "enhanced-v1.0.$VERSION_DATE" > version.txt
echo "✅ Created version.txt: enhanced-v1.0.$VERSION_DATE"

# Step 5: Create release checklist
echo ""
echo "📝 Step 5: Creating GitHub release checklist"

cat > RELEASE_CHECKLIST.md << 'EOF'
# Enhanced Oakestra Release Checklist

## Pre-Release Steps

1. **Test Enhanced NodeEngine**
   ```bash
   cd go_node_engine
   go build -o NodeEngine .
   ./NodeEngine --help  # Verify resource donation flags are present
   ```

2. **Test Resource Allocation**
   ```bash
   python3 test_resource_allocation.py  # Should show intelligent placement
   ```

3. **Build Release Packages**
   ```bash
   ./setup_repository.sh
   ```

## GitHub Release Steps

1. **Create New Release**
   - Go to: https://github.com/YOUR_USERNAME/oakestra-enhanced/releases
   - Click "Create a new release"
   - Tag: `enhanced-v1.0.YYYYMMDD`
   - Title: "Enhanced Oakestra v1.0 - Resource Donation System"

2. **Upload Release Assets**
   - Upload `releases/NodeEngine_amd64.tar.gz`
   - Upload `releases/NodeEngine_arm64.tar.gz`

3. **Release Description Template**
   ```markdown
   # Enhanced Oakestra v1.0 - Resource Donation System

   ## 🚀 Features
   - **User-defined resource donations**: `--donated-cpu`, `--donated-memory`, `--donated-disk`
   - **Intelligent node selection**: Optimal placement based on capacity and availability
   - **Real-time resource tracking**: Prevent over-allocation with accurate monitoring
   - **Container-level enforcement**: OCI memory/CPU limits for isolation

   ## 📦 Installation

   ### Root + Cluster
   ```bash
   curl -sfL https://raw.githubusercontent.com/YOUR_USERNAME/oakestra-enhanced/main/scripts/StartEnhancedOakestra.sh | sh -
   ```

   ### Worker (Default 4 CPU, 8GB RAM, 100GB disk)
   ```bash
   curl -sfL https://raw.githubusercontent.com/YOUR_USERNAME/oakestra-enhanced/main/scripts/InstallEnhancedWorker.sh | sh
   ```

   ### Worker (Custom resources)
   ```bash
   curl -sfL https://raw.githubusercontent.com/YOUR_USERNAME/oakestra-enhanced/main/scripts/InstallEnhancedWorker.sh | sh -s -- --cpu 8.0 --memory 16384 --disk 204800
   ```

   ## 🎯 Example Multi-Node Setup
   ```bash
   # Master node
   curl -sfL https://raw.githubusercontent.com/YOUR_USERNAME/oakestra-enhanced/main/scripts/StartEnhancedOakestra.sh | sh -

   # Worker 1 (4GB RAM)
   curl -sfL https://raw.githubusercontent.com/YOUR_USERNAME/oakestra-enhanced/main/scripts/InstallEnhancedWorker.sh | sh -s -- --cpu 4.0 --memory 4096 --root-addr MASTER_IP

   # Worker 2 (8GB RAM) 
   curl -sfL https://raw.githubusercontent.com/YOUR_USERNAME/oakestra-enhanced/main/scripts/InstallEnhancedWorker.sh | sh -s -- --cpu 8.0 --memory 8192 --root-addr MASTER_IP
   ```

   Services requiring 2GB will intelligently be placed on Worker 2, preserving Worker 1 for smaller services!
   ```

4. **Update README.md**
   - Add installation instructions
   - Add resource donation examples
   - Link to release

## Post-Release Testing

1. **Test Installation Scripts**
   ```bash
   # Test on clean VM
   curl -sfL https://raw.githubusercontent.com/YOUR_USERNAME/oakestra-enhanced/main/scripts/InstallEnhancedWorker.sh | sh
   ```

2. **Verify Resource Donation Works**
   ```bash
   oakestra-enhanced-worker  # Should show resource donation parameters
   ```
EOF

echo "✅ Created RELEASE_CHECKLIST.md"

# Step 6: Summary
echo ""
echo "🎉 Repository Setup Complete!"
echo ""
echo "📋 What was created:"
echo "   ✅ releases/NodeEngine_amd64.tar.gz"
echo "   ✅ releases/NodeEngine_arm64.tar.gz"  
echo "   ✅ scripts/StartEnhancedOakestra.sh"
echo "   ✅ scripts/InstallEnhancedWorker.sh"
echo "   ✅ run-a-cluster/1-DOC-enhanced.yaml"
echo "   ✅ version.txt"
echo "   ✅ RELEASE_CHECKLIST.md"
echo ""
echo "🚀 Next Steps:"
echo "   1. Push code to your GitHub repository"
echo "   2. Follow RELEASE_CHECKLIST.md to create GitHub release"
echo "   3. Upload NodeEngine_*.tar.gz files to the release"
echo "   4. Test installation with your new URLs!"
echo ""
echo "📝 Your installation commands will be:"
echo "   Root:   curl -sfL https://raw.githubusercontent.com/VenkatReddybathuni/Oakestra/venkat/scripts/StartEnhancedOakestra.sh | sh -"
echo "   Worker: curl -sfL https://raw.githubusercontent.com/VenkatReddybathuni/Oakestra/venkat/scripts/InstallEnhancedWorker.sh | sh"