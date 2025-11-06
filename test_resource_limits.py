#!/usr/bin/env python3
"""
Test script to deploy services with resource limits to Oakestra
"""

import json
import requests
import time
import sys

# Oakestra API endpoints
SYSTEM_MANAGER_URL = "http://localhost:10000"
SERVICE_MANAGER_URL = "http://localhost:10099"

def deploy_service(sla_file):
    """Deploy a service using Oakestra APIs"""
    print(f"🚀 Deploying service from {sla_file}")
    
    # Read SLA file
    try:
        with open(sla_file, 'r') as f:
            sla_data = json.load(f)
        print(f"✅ Loaded SLA: {sla_data['application_name']}")
    except Exception as e:
        print(f"❌ Failed to load SLA file: {e}")
        return False
    
    # Deploy application
    try:
        response = requests.post(
            f"{SYSTEM_MANAGER_URL}/api/application",
            json=sla_data,
            timeout=10
        )
        
        if response.status_code == 200:
            app_data = response.json()
            app_id = app_data.get("applicationID", "unknown")
            print(f"✅ Application deployed successfully! ID: {app_id}")
            
            # Wait a moment then check service status
            time.sleep(2)
            check_service_status(app_id)
            return True
        else:
            print(f"❌ Failed to deploy application: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error deploying application: {e}")
        return False

def check_service_status(app_id):
    """Check the status of deployed services"""
    try:
        response = requests.get(f"{SYSTEM_MANAGER_URL}/api/application/{app_id}")
        if response.status_code == 200:
            app_data = response.json()
            print(f"📊 Application Status: {app_data.get('application_name', 'Unknown')}")
            
            # Check services
            services = app_data.get('application_descriptor', {}).get('services', [])
            for service in services:
                service_name = service.get('servicename', 'unknown')
                print(f"   Service: {service_name}")
                
                # Check resource specifications
                if 'resources' in service:
                    resources = service['resources']
                    if 'requests' in resources:
                        print(f"     Requested: {resources['requests']}")
                    if 'limits' in resources:
                        print(f"     Limits: {resources['limits']}")
                
        else:
            print(f"❌ Failed to get application status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error checking service status: {e}")

def list_active_services():
    """List all active services"""
    try:
        response = requests.get(f"{SYSTEM_MANAGER_URL}/api/applications")
        if response.status_code == 200:
            apps = response.json()
            print(f"📝 Found {len(apps)} applications:")
            for app in apps:
                print(f"   - {app.get('application_name', 'Unknown')} (ID: {app.get('applicationID', 'unknown')})")
        else:
            print(f"❌ Failed to list applications: {response.status_code}")
    except Exception as e:
        print(f"❌ Error listing applications: {e}")

def main():
    """Main test function"""
    print("🧪 Testing Oakestra Resource Limits Implementation")
    print("=" * 50)
    
    # Check if Oakestra is accessible
    try:
        response = requests.get(f"{SYSTEM_MANAGER_URL}/api/applications", timeout=5)
        if response.status_code == 200:
            print("✅ Oakestra System Manager is accessible")
        else:
            print(f"⚠️ Oakestra System Manager returned {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to Oakestra System Manager: {e}")
        print("Make sure Oakestra is running with: docker-compose up -d")
        return
    
    # List current applications
    print("\n📋 Current Applications:")
    list_active_services()
    
    # Test deployment with resource limits
    test_files = [
        "test_low_resource_service.json",
        "test_high_resource_service.json", 
        "test_memory_intensive_service.json",
        "test_cpu_intensive_service.json"
    ]
    
    if len(sys.argv) > 1:
        # Deploy specific service
        sla_file = sys.argv[1]
        if deploy_service(sla_file):
            print(f"\n✅ Successfully deployed {sla_file}")
        else:
            print(f"\n❌ Failed to deploy {sla_file}")
    else:
        # Deploy all test services
        print(f"\n🚀 Deploying test services...")
        for sla_file in test_files:
            print(f"\n--- Testing {sla_file} ---")
            deploy_service(sla_file)
            time.sleep(3)  # Wait between deployments
    
    print("\n🏁 Test completed!")

if __name__ == "__main__":
    main()
