# 🧪 How to Run Oakestra Resource Enforcement Tests

## Quick Summary
1. **Start Oakestra** (orchestrators + worker)
2. **Check environment** is ready  
3. **Deploy test services** using curl
4. **Verify resource limits** with docker commands

---

## 📋 Step-by-Step Instructions

### **Option 1: Automated Startup (Recommended)**

```bash
# 1. Start Oakestra components
./start_oakestra.sh

# 2. In a NEW terminal, start worker node
cd ../oakestra/go_node_engine
./NodeEngine -n 6000 -p 10000 -r localhost

# 3. In another terminal, check environment
cd ../../evaluation_scripts
python3 simple_check.py

# 4. If all checks pass, run tests
python3 resource_test_generator.py
```

### **Option 2: Manual Startup**

```bash
# 1. Start Docker Desktop (if not running)

# 2. Start Root Orchestrator
cd ../oakestra/root_orchestrator
docker-compose up -d

# 3. Start Cluster Orchestrator
cd ../cluster_orchestrator  
docker-compose up -d

# 4. Build and start worker
cd ../go_node_engine
go build -o NodeEngine
./NodeEngine -n 6000 -p 10000 -r localhost

# 5. Test environment
cd ../../evaluation_scripts
python3 simple_check.py
```

---

## 🧪 Running the Tests

Once Oakestra is running, use these commands:

### **Test 1: New Resource Format**
```bash
curl -X POST http://localhost:10000/api/applications \
     -H "Content-Type: application/json" \
     -d @test_basic_limits.json
```
**Expected**: Service with CPU: 500m, Memory: 256Mi limits

### **Test 2: Legacy Compatibility**  
```bash
curl -X POST http://localhost:10000/api/applications \
     -H "Content-Type: application/json" \
     -d @test_legacy_compatibility.json
```
**Expected**: Service with vcpus: 1, memory: 256 (old format)

### **Test 3: High Resources**
```bash
curl -X POST http://localhost:10000/api/applications \
     -H "Content-Type: application/json" \
     -d @test_high_resources.json
```
**Expected**: Service with CPU: 2 cores, Memory: 1Gi limits

### **Deploy Service Instance**
```bash
# From the API response above, get the SERVICE_ID, then:
curl -X POST http://localhost:10000/api/service/SERVICE_ID/instance

# Check status
curl -X GET http://localhost:10000/api/service/SERVICE_ID
```

---

## 🔍 Verification Commands

### **Check Resource Limits Applied**
```bash
# See all containers and their resource usage
docker stats

# Inspect specific container limits
docker inspect CONTAINER_ID | grep -A 20 "Resources"

# Should show:
# "Memory": 268435456,     # 256MB limit
# "CpuShares": 512,        # CPU weight  
# "CpuQuota": 50000,       # 0.5 CPU limit
```

### **Check Oakestra Logs**
```bash
# Worker node logs (should show resource application)
docker logs WORKER_CONTAINER_NAME

# Look for messages like:
# "Applied CPU limits: shares=512, quota=50000"
# "Applied memory limit: 268435456 bytes (256 MB)"
# "Resource validation passed for service"
```

### **Test Resource Enforcement**
```bash
# Run stress test inside container
docker exec -it CONTAINER_ID sh

# Inside container:
apk add stress-ng
stress-ng --cpu 2 --timeout 60s  # Should be limited by CPU quota
```

---

## 🎯 What to Expect

### ✅ **Success Indicators**
- API returns application/service IDs
- Container appears in `docker ps`
- `docker stats` shows resource usage within limits
- Logs show "Applied CPU limits", "Applied memory limit"
- Stress tests respect the configured limits

### ❌ **Common Issues**  
- **Connection refused**: Oakestra not started
- **No containers**: Check worker node is connected
- **No limits**: Check logs for validation errors
- **Deployment fails**: Check service dependencies

---

## 🔧 Troubleshooting

```bash
# Check all components are running
docker ps

# Check orchestrator logs
docker logs system_manager
docker logs cluster_manager

# Check worker connection
tail -f /var/log/oakestra/node_engine.log

# Reset everything
docker-compose down -v  # In both orchestrator directories
./NodeEngine --help     # Check worker options
```

---

## 📊 Environment Check

Before running tests, always verify with:
```bash
python3 simple_check.py
```

This should show:
- ✅ Docker is running
- ✅ Oakestra containers found  
- ✅ Root Orchestrator running (port 10000)
- ✅ Cluster Manager running (port 10001)
- ✅ NodeEngine process found

---

## 🎉 Test Files Available

- `test_basic_limits.json` - New resource format
- `test_legacy_compatibility.json` - Old format  
- `test_high_resources.json` - High resource requirements
- `test_resource_limits.json` - Multi-service test

Run `python3 resource_test_generator.py` for detailed curl commands!
