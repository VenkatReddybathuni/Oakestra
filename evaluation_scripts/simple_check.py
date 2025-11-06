#!/usr/bin/env python3
"""
Simple Oakestra Environment Checker

This script checks if your Oakestra environment is ready for resource enforcement testing.
No external dependencies required.
"""

import subprocess
import sys
import urllib.request
import urllib.error

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
        print("❌ Docker command not found - Please install Docker")
        return False

def check_url(url, name):
    """Check if a URL is accessible"""
    try:
        response = urllib.request.urlopen(f"{url}/status", timeout=5)
        if response.getcode() == 200:
            print(f"✅ {name} is running at {url}")
            return True
        else:
            print(f"❌ {name} returned status code {response.getcode()}")
            return False
    except urllib.error.URLError:
        print(f"❌ Cannot connect to {name} at {url}")
        return False
    except Exception as e:
        print(f"❌ Error checking {name}: {str(e)}")
        return False

def check_oakestra_containers():
    """Check if Oakestra Docker containers are running"""
    print("📦 Checking Oakestra containers...")
    try:
        result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            containers = result.stdout.strip().split('\n')
            oakestra_containers = [c for c in containers 
                                 if any(keyword in c.lower() for keyword in 
                                       ['oakestra', 'system_manager', 'cluster', 'mongo', 'scheduler'])]
            
            if oakestra_containers:
                print("✅ Found Oakestra containers:")
                for container in oakestra_containers:
                    print(f"   {container}")
                return True
            else:
                print("❌ No Oakestra containers found")
                return False
        else:
            print("❌ Could not list containers")
            return False
    except Exception as e:
        print(f"❌ Error checking containers: {str(e)}")
        return False

def check_processes():
    """Check for Oakestra processes"""
    print("🖥️  Checking Oakestra processes...")
    try:
        # Check for NodeEngine
        result = subprocess.run(['pgrep', '-f', 'NodeEngine'], capture_output=True, text=True)
        node_engine_running = result.returncode == 0
        
        if node_engine_running:
            print("✅ NodeEngine process found")
        else:
            print("❌ NodeEngine process not found")
        
        return node_engine_running
    except Exception as e:
        print(f"❌ Error checking processes: {str(e)}")
        return False

def main():
    """Main environment check"""
    print("🔍 Oakestra Resource Enforcement Environment Check")
    print("=" * 60)
    
    checks = []
    
    # Check Docker
    docker_ok = check_docker()
    checks.append(docker_ok)
    
    # Check containers if Docker is running
    if docker_ok:
        containers_ok = check_oakestra_containers()
        checks.append(containers_ok)
    else:
        containers_ok = False
        checks.append(False)
    
    # Check API endpoints
    print("🔌 Checking API endpoints...")
    root_ok = check_url("http://localhost:10000", "Root Orchestrator")
    cluster_ok = check_url("http://localhost:10001", "Cluster Manager") 
    checks.extend([root_ok, cluster_ok])
    
    # Check processes
    process_ok = check_processes()
    checks.append(process_ok)
    
    # Summary
    print("\n" + "="*60)
    print("📊 ENVIRONMENT CHECK SUMMARY")
    print("="*60)
    
    total_checks = len(checks)
    passed_checks = sum(checks)
    
    print(f"Passed: {passed_checks}/{total_checks} checks")
    
    if all(checks):
        print("🎉 Environment is ready for testing!")
        print("\n🚀 Next steps:")
        print("1. Run: python3 resource_test_generator.py")
        print("2. Use the generated curl commands to test resource enforcement")
        print("3. Check 'docker stats' and logs to verify resource limits")
    else:
        print("❌ Environment not ready")
        print("\n🔧 To start Oakestra:")
        print("1. Start Docker Desktop")
        print("2. cd Leschynski_Materials/oakestra/root_orchestrator && docker-compose up -d")
        print("3. cd ../cluster_orchestrator && docker-compose up -d") 
        print("4. cd ../go_node_engine && ./NodeEngine -n 6000 -p 10000 -r localhost")
    
    # Show available test files
    print(f"\n📁 Available test files:")
    try:
        result = subprocess.run(['ls', '-1', 'test_*.json'], capture_output=True, text=True)
        if result.returncode == 0:
            for filename in result.stdout.strip().split('\n'):
                print(f"   {filename}")
        else:
            print("   No test files found - run resource_test_generator.py first")
    except:
        pass
    
    return 0 if all(checks) else 1

if __name__ == "__main__":
    sys.exit(main())
