#!/usr/bin/env python3
"""
Oakestra Environment Checker

This script checks if your Oakestra environment is ready for resource enforcement testing.
"""

import requests
import subprocess
import json
import sys

def check_docker():
    """Check if Docker is running"""
    print("🐳 Checking Docker...")
    try:
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Docker is running")
            return True
        else:
            print("❌ Docker is not running or not accessible")
            print("   Please start Docker Desktop or Docker daemon")
            return False
    except FileNotFoundError:
        print("❌ Docker command not found")
        print("   Please install Docker")
        return False

def check_oakestra_component(name, url, description):
    """Check if an Oakestra component is running"""
    print(f"🔍 Checking {name}...")
    try:
        response = requests.get(f"{url}/status", timeout=5)
        if response.status_code == 200:
            print(f"✅ {name} is running at {url}")
            return True
        else:
            print(f"❌ {name} returned status code {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {name} at {url}")
        print(f"   {description}")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ {name} request timed out")
        return False
    except Exception as e:
        print(f"❌ Error checking {name}: {str(e)}")
        return False

def check_oakestra_containers():
    """Check if Oakestra Docker containers are running"""
    print("📦 Checking Oakestra containers...")
    try:
        result = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            containers = result.stdout
            oakestra_containers = [line for line in containers.split('\n') 
                                 if any(keyword in line.lower() for keyword in 
                                       ['oakestra', 'system_manager', 'cluster', 'mongo', 'scheduler'])]
            
            if oakestra_containers:
                print("✅ Found Oakestra containers:")
                for container in oakestra_containers:
                    if container.strip():
                        print(f"   {container}")
                return True
            else:
                print("❌ No Oakestra containers found")
                print("   Please start Oakestra components")
                return False
        else:
            print("❌ Could not list containers")
            return False
    except Exception as e:
        print(f"❌ Error checking containers: {str(e)}")
        return False

def test_api_endpoints():
    """Test key API endpoints"""
    print("🔌 Testing API endpoints...")
    
    endpoints = [
        ("Root Orchestrator", "http://localhost:10000", "Start root orchestrator"),
        ("Cluster Manager", "http://localhost:10001", "Start cluster orchestrator"),
    ]
    
    results = []
    for name, url, instruction in endpoints:
        success = check_oakestra_component(name, url, instruction)
        results.append(success)
    
    return all(results)

def check_node_engine():
    """Check if node engine (worker) is running"""
    print("🖥️  Checking Node Engine (Worker)...")
    try:
        # Check for NodeEngine process
        result = subprocess.run(['pgrep', '-f', 'NodeEngine'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ NodeEngine process found")
            return True
        else:
            print("❌ NodeEngine process not found")
            print("   Please start a worker node with: ./NodeEngine -n 6000 -p 10000 -r CLUSTER_IP")
            return False
    except Exception as e:
        print(f"❌ Error checking NodeEngine: {str(e)}")
        return False

def provide_startup_instructions():
    """Provide instructions to start Oakestra"""
    print("\n" + "="*60)
    print("🚀 OAKESTRA STARTUP INSTRUCTIONS")
    print("="*60)
    
    print("\n1. Start Docker:")
    print("   # On macOS/Windows: Start Docker Desktop")
    print("   # On Linux: sudo systemctl start docker")
    
    print("\n2. Start Root Orchestrator:")
    print("   cd Leschynski_Materials/oakestra/root_orchestrator")
    print("   docker-compose up -d")
    
    print("\n3. Start Cluster Orchestrator:")
    print("   cd ../cluster_orchestrator")
    print("   docker-compose up -d")
    
    print("\n4. Start Worker Node:")
    print("   cd ../go_node_engine")
    print("   go build -o NodeEngine")
    print("   ./NodeEngine -n 6000 -p 10000 -r localhost")
    
    print("\n5. Verify Setup:")
    print("   python3 check_environment.py")
    
    print("\n6. Run Tests:")
    print("   python3 resource_test_generator.py")
    print("   # Then use the generated curl commands")

def main():
    """Main environment check"""
    print("🔍 Oakestra Resource Enforcement Environment Check")
    print("=" * 60)
    
    checks = []
    
    # Check Docker
    checks.append(check_docker())
    
    # Check Oakestra containers
    if checks[0]:  # Only if Docker is running
        checks.append(check_oakestra_containers())
    else:
        checks.append(False)
    
    # Check API endpoints
    checks.append(test_api_endpoints())
    
    # Check node engine
    checks.append(check_node_engine())
    
    # Summary
    print("\n" + "="*60)
    print("📊 ENVIRONMENT CHECK SUMMARY")
    print("="*60)
    
    total_checks = len(checks)
    passed_checks = sum(checks)
    
    print(f"Passed: {passed_checks}/{total_checks} checks")
    
    if all(checks):
        print("🎉 Environment is ready for testing!")
        print("\nNext steps:")
        print("1. Run: python3 resource_test_generator.py")
        print("2. Use the generated curl commands to test resource enforcement")
        print("3. Check logs and docker stats to verify resource limits")
    else:
        print("❌ Environment not ready")
        provide_startup_instructions()
    
    return 0 if all(checks) else 1

if __name__ == "__main__":
    sys.exit(main())
