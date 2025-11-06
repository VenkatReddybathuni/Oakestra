#!/bin/bash
# Simple Oakestra Startup using Pre-built Images

echo "🚀 Starting Oakestra (Simple Setup with Pre-built Images)"
echo "========================================================="

# Step 1: Check Docker
echo "1. Checking Docker..."
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
else
    echo "✅ Docker is running"
fi

# Step 2: Navigate to run-a-cluster
echo ""
echo "2. Using run-a-cluster setup..."
cd "$(dirname "$0")/../oakestra/run-a-cluster" || exit 1
echo "📂 Current directory: $(pwd)"

# Step 3: Set environment variables
echo ""
echo "3. Setting environment variables..."
export SYSTEM_MANAGER_URL=localhost

# Step 4: Start complete setup
echo ""
echo "4. Starting complete Oakestra setup..."
echo "🔄 Using pre-built images (faster than building locally)"
docker-compose -f 1-DOC.yaml up -d

if [ $? -eq 0 ]; then
    echo "✅ Oakestra started successfully"
else
    echo "❌ Failed to start Oakestra"
    echo "💡 Check Docker logs for details:"
    echo "   docker-compose -f 1-DOC.yaml logs"
    exit 1
fi

# Step 5: Wait for services to be ready
echo ""
echo "5. Waiting for services to initialize..."
echo "⏳ Please wait 30-60 seconds..."
sleep 45

# Step 6: Check service status
echo ""
echo "6. Checking service status..."
if curl -s http://localhost:10000/status > /dev/null; then
    echo "✅ Root Orchestrator is ready (port 10000)"
else
    echo "⏳ Root Orchestrator still starting up..."
fi

echo ""
echo "🎉 Oakestra startup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Build and start worker node:"
echo "   cd ../go_node_engine"
echo "   go build -o NodeEngine"  
echo "   ./NodeEngine -n 6000 -p 10000 -r localhost"
echo ""
echo "2. Test the setup:"
echo "   cd ../../evaluation_scripts"
echo "   python3 simple_check.py"
echo ""
echo "3. Run resource enforcement tests:"
echo "   python3 resource_test_generator.py"
echo ""
echo "📊 Monitor with:"
echo "   docker ps                    # See running containers"
echo "   docker-compose -f 1-DOC.yaml logs  # View logs"
echo "   curl http://localhost:10000/status  # Test API"
