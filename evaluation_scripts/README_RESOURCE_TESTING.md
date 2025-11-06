# Resource Enforcement Testing Guide

## 🎯 What We've Implemented

We've successfully implemented **user-defined resource limits** for Docker containers in Oakestra! Here's what's new:

### ✅ Completed Features:
1. **New Resource Specification Format** (Kubernetes-style)
2. **Docker Container Resource Enforcement** 
3. **Backward Compatibility** with legacy format
4. **Resource Validation**
5. **Comprehensive Test Suite**

---

## 🏗️ Architecture Changes

### Modified Files:
- **`Service.go`**: Added `ResourceSpec` with requests/limits
- **`ContainersManagement.go`**: Applied resource limits via OCI specs
- **Test Scripts**: Created comprehensive test cases

### New Resource Format:
```json
{
  "resource_spec": {
    "requests": {
      "cpu": "250m",              // 250 millicores guaranteed
      "memory": "128Mi",          // 128 MiB guaranteed  
      "ephemeral-storage": "500Mi" // 500 MiB storage
    },
    "limits": {
      "cpu": "500m",              // Max 0.5 CPU cores
      "memory": "256Mi",          // Max 256 MiB
      "ephemeral-storage": "1Gi"  // Max 1 GiB storage
    }
  }
}
```

---

## 🚀 How to Test

### Prerequisites:
1. **Docker** must be running
2. **Oakestra** must be running (root orchestrator + cluster orchestrator + workers)

### Step 1: Start Oakestra
```bash
# Navigate to Oakestra directory
cd Leschynski_Materials/oakestra

# Start root orchestrator
cd root_orchestrator
docker-compose up -d

# Start cluster orchestrator  
cd ../cluster_orchestrator
docker-compose up -d

# Start worker node
cd ../go_node_engine
# Build if needed
go build -o NodeEngine
# Run worker
./NodeEngine -n 6000 -p 10000 -r CLUSTER_MANAGER_IP
```

### Step 2: Test Resource Enforcement
```bash
# Navigate to evaluation scripts
cd evaluation_scripts

# Test 1: New Resource Format
curl -X POST http://localhost:10000/api/applications \
     -H "Content-Type: application/json" \
     -d @test_basic_limits.json

# Test 2: Legacy Compatibility
curl -X POST http://localhost:10000/api/applications \
     -H "Content-Type: application/json" \
     -d @test_legacy_compatibility.json

# Test 3: High Resources
curl -X POST http://localhost:10000/api/applications \
     -H "Content-Type: application/json" \
     -d @test_high_resources.json
```

### Step 3: Deploy Service Instances
```bash
# From the response of step 2, get the SERVICE_ID
# Deploy an instance
curl -X POST http://localhost:10000/api/service/SERVICE_ID/instance

# Check status
curl -X GET http://localhost:10000/api/service/SERVICE_ID
```

---

## 🔍 Verification

### Expected Log Messages:
Look for these in the worker node logs:
```
Applied CPU limits: shares=512, quota=50000, period=100000
Applied memory limit: 268435456 bytes (256 MB)
Applied storage constraints: tmpfs size limit 512 MB
Resource validation passed for service nginx-basic - CPU: 0.50, Memory: 256 MB
```

### Docker Verification:
```bash
# Check container resource limits
docker stats

# Inspect applied limits
docker inspect CONTAINER_ID | grep -A 20 "Resources"

# Should see something like:
# "Memory": 268435456,  # 256 MB limit
# "CpuShares": 512,     # CPU weight
# "CpuQuota": 50000,    # CPU quota (0.5 cores)
```

### Test Resource Enforcement:
```bash
# Run stress test to verify limits work
docker exec -it CONTAINER_ID sh
# Inside container:
apk add stress-ng
stress-ng --cpu 2 --timeout 60s  # Should be limited by CPU quota
```

---

## 📋 Test Cases Available

1. **`test_basic_limits.json`** - New resource format with moderate limits
2. **`test_legacy_compatibility.json`** - Old format (memory/vcpus fields)  
3. **`test_high_resources.json`** - High resource requirements
4. **`test_resource_limits.json`** - Multi-service test

---

## 🎯 What Should Happen

### ✅ Success Scenarios:
- **New Format**: Containers created with precise CPU/memory limits
- **Legacy Format**: Still works using old memory/vcpus fields
- **Resource Limits**: `docker stats` shows usage within limits
- **Validation**: Clear error messages for invalid specs

### ❌ Expected Failures:
- **Invalid Specs**: Negative values should be rejected  
- **Excessive Resources**: Very high limits should be rejected
- **Request > Limit**: Should fail validation

---

## 🐛 Troubleshooting

### Connection Refused (port 10000):
- Make sure root orchestrator is running
- Check `docker ps` for system_manager container
- Check `curl http://localhost:10000/status`

### Service Deployment Fails:
- Check cluster orchestrator is running
- Check worker nodes are connected
- Look at worker logs for validation errors

### Container Not Respecting Limits:
- Check worker logs for "Applied CPU limits" messages  
- Verify with `docker inspect CONTAINER_ID`
- Make sure containerd/Docker supports resource limits

---

## 🎉 Success Indicators

When everything works correctly, you should see:

1. **API Response**: Service deployment returns success with service IDs
2. **Container Creation**: `docker ps` shows containers running
3. **Resource Limits**: `docker stats` shows CPU/memory within limits
4. **Log Messages**: Worker logs show resource application
5. **Enforcement**: Stress tests respect the configured limits

---

## 🔄 Next Steps

After verifying Docker-level enforcement works:

1. **Resource Pool Management** - Track donated vs. available resources
2. **Admission Control** - Check availability before scheduling  
3. **Scheduler Updates** - Consider resource pools in placement decisions
4. **Worker Configuration** - Let users specify donated resources

---

## 📞 Support

If tests fail, check:
- Docker daemon is running
- Oakestra components are running
- Network connectivity between components
- Log files for error messages

The current implementation provides **Docker-level resource enforcement** - the foundation for your complete resource management system!
