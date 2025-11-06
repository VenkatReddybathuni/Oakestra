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
