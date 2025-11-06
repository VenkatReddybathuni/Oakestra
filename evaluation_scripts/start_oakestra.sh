#!/bin/bash
# Oakestra Test Startup Script

echo "🚀 Starting Oakestra for Resource Enforcement Testing"
echo "======================================================"

# Step 1: Check Docker
echo "1. Checking Docker..."
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    echo "   - On macOS: Open Docker Desktop application"
    echo "   - On Linux: sudo systemctl start docker"
    exit 1
else
    echo "✅ Docker is running"
fi

# Step 2: Navigate to Oakestra directory
echo ""
echo "2. Navigating to Oakestra directory..."
cd "$(dirname "$0")/../oakestra" || exit 1
echo "📂 Current directory: $(pwd)"

# Step 3: Start Root Orchestrator
echo ""
echo "3. Starting Root Orchestrator..."
cd root_orchestrator
echo "📂 Starting components in: $(pwd)"
echo "🔨 Building and starting components (this may take a few minutes)..."
docker-compose up --build -d
if [ $? -eq 0 ]; then
    echo "✅ Root Orchestrator started"
else
    echo "❌ Failed to start Root Orchestrator"
    echo "💡 Tip: Check if Docker has enough resources allocated"
    exit 1
fi

# Step 4: Start Cluster Orchestrator  
echo ""
echo "4. Starting Cluster Orchestrator..."
cd ../cluster_orchestrator
echo "📂 Starting components in: $(pwd)"
echo "🔨 Building and starting cluster components..."
docker-compose up --build -d
if [ $? -eq 0 ]; then
    echo "✅ Cluster Orchestrator started"
else
    echo "❌ Failed to start Cluster Orchestrator"
    echo "💡 Tip: Check Docker logs for more details"
    exit 1
fi

# Step 5: Build and prepare Node Engine
echo ""
echo "5. Preparing Node Engine (Worker)..."
cd ../go_node_engine
echo "📂 Building Node Engine in: $(pwd)"

# Check if NodeEngine binary exists
if [ ! -f NodeEngine ]; then
    echo "🔨 Building NodeEngine..."
    go build -o NodeEngine
    if [ $? -eq 0 ]; then
        echo "✅ NodeEngine built successfully"
    else
        echo "❌ Failed to build NodeEngine"
        exit 1
    fi
else
    echo "✅ NodeEngine binary found"
fi

# Step 6: Wait for orchestrators to be ready
echo ""
echo "6. Waiting for orchestrators to be ready..."
echo "⏳ This may take 30-60 seconds for first-time builds..."
sleep 30

echo ""
echo "7. Checking if services are ready..."
# Check Root Orchestrator
if curl -s http://localhost:10000/status > /dev/null; then
    echo "✅ Root Orchestrator is ready (port 10000)"
else
    echo "⏳ Root Orchestrator not ready yet, waiting..."
    sleep 5
fi

# Check Cluster Orchestrator  
if curl -s http://localhost:10001/status > /dev/null; then
    echo "✅ Cluster Orchestrator is ready (port 10001)"
else
    echo "⏳ Cluster Orchestrator not ready yet, waiting..."
    sleep 5
fi

echo ""
echo "🎉 Oakestra components are starting up!"
echo ""
echo "📋 Next steps:"
echo "1. Start worker node:"
echo "   cd $(pwd)"
echo "   ./NodeEngine -n 6000 -p 10000 -r localhost"
echo ""
echo "2. In another terminal, run tests:"
echo "   cd ../evaluation_scripts"
echo "   python3 simple_check.py"
echo "   # Then use the curl commands to test"
echo ""
echo "3. Monitor with:"
echo "   docker ps"
echo "   docker logs system_manager"
echo "   docker stats"
