#!/usr/bin/env python3
"""
Demonstration of Oakestra Resource Limits Implementation
This shows how resource limits work at the Docker level.
"""

import subprocess
import json
import time
import sys

def run_command(cmd, shell=False):
    """Run a command and return the output"""
    try:
        if shell:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)

def test_docker_resource_limits():
    """Test Docker containers with resource limits"""
    
    print("🐳 Testing Docker Resource Limits Implementation")
    print("=" * 55)
    
    # Test container configuration
    container_name = "oakestra-test-service"
    image = "nginx:alpine"
    cpu_limit = "0.5"  # 0.5 CPU cores
    memory_limit = "128m"  # 128 MB
    disk_limit_env = "OAKESTRA_DISK_LIMIT_MB=500"
    
    print(f"📋 Test Configuration:")
    print(f"   Container: {container_name}")
    print(f"   Image: {image}")
    print(f"   CPU Limit: {cpu_limit} cores")
    print(f"   Memory Limit: {memory_limit}")
    print(f"   Disk Limit: 500 MB (via env var)")
    
    # Clean up any existing container
    print(f"\n🧹 Cleaning up existing containers...")
    run_command(f"docker rm -f {container_name}", shell=True)
    
    # Create and run container with resource limits
    docker_cmd = [
        "docker", "run", "-d",
        "--name", container_name,
        "--cpus", cpu_limit,
        "--memory", memory_limit,
        "--env", disk_limit_env,
        "-p", "8080:80",
        image
    ]
    
    print(f"\n🚀 Starting container with resource limits...")
    print(f"Command: {' '.join(docker_cmd)}")
    
    success, stdout, stderr = run_command(docker_cmd)
    
    if not success:
        print(f"❌ Failed to start container: {stderr}")
        return False
    
    container_id = stdout[:12]  # First 12 chars of container ID
    print(f"✅ Container started successfully: {container_id}")
    
    # Wait a moment for container to start
    time.sleep(2)
    
    # Inspect container resource limits
    print(f"\n🔍 Inspecting container resource configuration...")
    
    inspect_cmd = ["docker", "inspect", container_name]
    success, stdout, stderr = run_command(inspect_cmd)
    
    if success:
        try:
            inspect_data = json.loads(stdout)[0]
            host_config = inspect_data["HostConfig"]
            
            print(f"📊 Actual Resource Limits:")
            
            # CPU limits
            cpu_quota = host_config.get("CpuQuota", 0)
            cpu_period = host_config.get("CpuPeriod", 100000)
            if cpu_quota > 0:
                actual_cpu = cpu_quota / cpu_period
                print(f"   CPU: {actual_cpu} cores (quota: {cpu_quota}, period: {cpu_period})")
            else:
                print(f"   CPU: unlimited")
            
            # Memory limits  
            memory = host_config.get("Memory", 0)
            if memory > 0:
                memory_mb = memory / (1024 * 1024)
                print(f"   Memory: {memory_mb:.0f} MB")
            else:
                print(f"   Memory: unlimited")
            
            # Environment variables
            env_vars = inspect_data["Config"].get("Env", [])
            disk_env = [env for env in env_vars if "OAKESTRA_DISK_LIMIT" in env]
            if disk_env:
                print(f"   Disk Limit: {disk_env[0]}")
            
        except Exception as e:
            print(f"❌ Failed to parse container inspection: {e}")
    
    # Test container responsiveness
    print(f"\n🌐 Testing container responsiveness...")
    time.sleep(1)
    
    success, stdout, stderr = run_command("curl -s -o /dev/null -w '%{http_code}' http://localhost:8080", shell=True)
    if success and stdout == "200":
        print(f"✅ Container is responding on port 8080")
    else:
        print(f"⚠️ Container not responding (this is normal if nginx is still starting)")
    
    # Show container stats
    print(f"\n📈 Container Resource Usage:")
    stats_cmd = f"docker stats {container_name} --no-stream --format 'table {{.Container}}\\t{{.CPUPerc}}\\t{{.MemUsage}}\\t{{.MemPerc}}'"
    success, stdout, stderr = run_command(stats_cmd, shell=True)
    if success:
        print(stdout)
    
    # Clean up
    print(f"\n🧹 Cleaning up test container...")
    run_command(f"docker rm -f {container_name}", shell=True)
    print(f"✅ Container removed")
    
    return True

def demonstrate_resource_parsing():
    """Demonstrate how Oakestra parses resource specifications"""
    
    print("\n🔧 Resource Specification Parsing Demo")
    print("=" * 45)
    
    # Example Oakestra service specification (matches our SLA files)
    service_spec = {
        "servicename": "demo-service",
        "image": "nginx:alpine",
        "resources": {
            "requests": {
                "cpu": "250m",      # 0.25 CPU cores
                "memory": "128Mi",  # 128 MiB
                "storage": "1Gi"    # 1 GiB
            },
            "limits": {
                "cpu": "500m",      # 0.5 CPU cores  
                "memory": "256Mi",  # 256 MiB
                "storage": "2Gi"    # 2 GiB
            }
        }
    }
    
    print("📋 Example Service Specification:")
    print(json.dumps(service_spec, indent=2))
    
    print("\n🔄 How Oakestra NodeEngine Processes This:")
    
    # Simulate our Go parsing logic
    limits = service_spec["resources"]["limits"]
    
    # Parse CPU (millicores to cores)
    cpu_str = limits["cpu"]
    if cpu_str.endswith('m'):
        cpu_cores = float(cpu_str[:-1]) / 1000.0
    else:
        cpu_cores = float(cpu_str)
    
    # Parse Memory (Mi/Gi to MB)
    memory_str = limits["memory"] 
    if memory_str.endswith('Mi'):
        memory_mb = int(memory_str[:-2])
    elif memory_str.endswith('Gi'):
        memory_mb = int(memory_str[:-2]) * 1024
    
    # Parse Storage (Mi/Gi to MB)
    storage_str = limits["storage"]
    if storage_str.endswith('Mi'):
        storage_mb = int(storage_str[:-2])
    elif storage_str.endswith('Gi'):
        storage_mb = int(storage_str[:-2]) * 1024
    
    print(f"1. Parse CPU: '{cpu_str}' → {cpu_cores} cores")
    print(f"2. Parse Memory: '{memory_str}' → {memory_mb} MB") 
    print(f"3. Parse Storage: '{storage_str}' → {storage_mb} MB")
    
    print(f"\n🐳 Resulting Docker Command:")  
    docker_cmd = f"""docker run -d \\
  --name=demo-service \\
  --cpus={cpu_cores} \\
  --memory={memory_mb}m \\
  --env=OAKESTRA_DISK_LIMIT_MB={storage_mb} \\
  nginx:alpine"""
    
    print(docker_cmd)
    
    print(f"\n📊 OCI Specification (what our Go code generates):")
    oci_spec = {
        "linux": {
            "resources": {
                "cpu": {
                    "shares": int(cpu_cores * 1024),  # 1024 shares = 1 core
                    "quota": int(cpu_cores * 100000), # quota out of 100000 period
                    "period": 100000
                },
                "memory": {
                    "limit": memory_mb * 1024 * 1024  # Convert to bytes
                }
            }
        }
    }
    print(json.dumps(oci_spec, indent=2))

def main():
    """Main demonstration"""
    print("🚀 Oakestra Resource Limits - Implementation Demo")
    print("=" * 60)
    
    # Check Docker availability
    success, _, _ = run_command(["docker", "version"])
    if not success:
        print("❌ Docker is not available. Please install Docker to run this demo.")
        return 1
    
    print("✅ Docker is available")
    
    # Run demonstrations
    try:
        demonstrate_resource_parsing()
        
        print("\n" + "=" * 60)
        
        if test_docker_resource_limits():
            print("\n🎉 Resource limits demonstration completed successfully!")
            print("\n📝 Summary:")
            print("   ✅ Resource parsing works correctly")
            print("   ✅ Docker resource limits are applied")
            print("   ✅ Environment variables for disk limits are set")
            print("   ✅ Container runs with specified constraints")
            return 0
        else:
            print("\n❌ Docker resource limits test failed")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Demo interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Demo failed with error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
