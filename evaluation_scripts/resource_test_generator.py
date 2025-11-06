#!/usr/bin/env python3
"""
Simple Resource Test

This script demonstrates the new resource specification format.
Deploy it manually using curl or the Oakestra dashboard.

Test Steps:
1. Start Oakestra (root orchestrator, cluster orchestrator, workers)
2. Deploy this SLA via API or dashboard
3. Check container resource limits using: docker stats
4. Verify logs show resource application
"""

import json

# Test cases for different resource scenarios
test_cases = {
    "basic_limits": {
        "sla_version": "v2.0",
        "customerID": "Admin",
        "applications": [
            {
                "applicationID": "",
                "application_name": "basic-limits",
                "application_namespace": "test",
                "application_desc": "Basic resource limits test",
                "microservices": [
                    {
                        "microserviceID": "",
                        "microservice_name": "nginx-basic",
                        "microservice_namespace": "test",
                        "virtualization": "container",
                        "cmd": [],
                        # NEW RESOURCE FORMAT - This is what we implemented!
                        "resource_spec": {
                            "requests": {
                                "cpu": "250m",      # 0.25 CPU cores guaranteed
                                "memory": "128Mi",  # 128 MiB guaranteed
                                "ephemeral-storage": "500Mi"  # 500 MiB storage
                            },
                            "limits": {
                                "cpu": "500m",      # Max 0.5 CPU cores
                                "memory": "256Mi",  # Max 256 MiB
                                "ephemeral-storage": "1Gi"    # Max 1 GiB storage
                            }
                        },
                        "code": "docker.io/library/nginx:latest",
                        "state": "",
                        "port": "8080:80",
                        "added_files": [],
                        "constraints": []
                    }
                ]
            }
        ]
    },
    
    "legacy_compatibility": {
        "sla_version": "v2.0",
        "customerID": "Admin",
        "applications": [
            {
                "applicationID": "",
                "application_name": "legacy-compat",
                "application_namespace": "test",
                "application_desc": "Legacy format compatibility test",
                "microservices": [
                    {
                        "microserviceID": "",
                        "microservice_name": "nginx-legacy",
                        "microservice_namespace": "test",
                        "virtualization": "container",
                        "cmd": [],
                        # LEGACY FORMAT - Should still work!
                        "memory": 256,    # 256 MB
                        "vcpus": 1,       # 1 CPU core
                        "vgpus": 0,
                        "vtpus": 0,
                        "bandwidth_in": 0,
                        "bandwidth_out": 0,
                        "storage": 512,   # 512 MB storage
                        "code": "docker.io/library/nginx:latest",
                        "state": "",
                        "port": "8081:80",
                        "added_files": [],
                        "constraints": []
                    }
                ]
            }
        ]
    },
    
    "high_resources": {
        "sla_version": "v2.0",
        "customerID": "Admin",
        "applications": [
            {
                "applicationID": "",
                "application_name": "high-resources",
                "application_namespace": "test",
                "application_desc": "High resource requirements test",
                "microservices": [
                    {
                        "microserviceID": "",
                        "microservice_name": "resource-heavy",
                        "microservice_namespace": "test",
                        "virtualization": "container",
                        "cmd": ["sleep", "300"],  # Sleep for 5 minutes
                        "resource_spec": {
                            "requests": {
                                "cpu": "1",         # 1 full CPU core
                                "memory": "512Mi",  # 512 MiB
                                "ephemeral-storage": "2Gi"  # 2 GiB
                            },
                            "limits": {
                                "cpu": "2",         # Max 2 CPU cores
                                "memory": "1Gi",    # Max 1 GiB
                                "ephemeral-storage": "4Gi"  # Max 4 GiB
                            }
                        },
                        "code": "docker.io/library/alpine:latest",
                        "state": "",
                        "port": "",
                        "added_files": [],
                        "constraints": []
                    }
                ]
            }
        ]
    }
}

def save_test_cases():
    """Save test cases to individual JSON files"""
    for name, sla in test_cases.items():
        filename = f"test_{name}.json"
        with open(filename, 'w') as f:
            json.dump(sla, f, indent=2)
        print(f"✅ Saved {filename}")

def print_curl_commands():
    """Print curl commands to test the SLAs"""
    print("\n" + "="*60)
    print("CURL COMMANDS TO TEST RESOURCE ENFORCEMENT")
    print("="*60)
    
    base_url = "http://localhost:10000/api"
    
    for name, sla in test_cases.items():
        print(f"\n📋 Test: {name.replace('_', ' ').title()}")
        print("-" * 40)
        
        # Step 1: Register application
        print("1. Register application:")
        print(f'curl -X POST {base_url}/applications \\')
        print('     -H "Content-Type: application/json" \\')
        print(f'     -d @test_{name}.json')
        
        # Step 2: Deploy instance (you'll need the service ID from step 1)
        print("\n2. Deploy instance (replace SERVICE_ID with actual ID from response):")
        print(f'curl -X POST {base_url}/service/SERVICE_ID/instance')
        
        # Step 3: Check status
        print("\n3. Check service status:")
        print(f'curl -X GET {base_url}/service/SERVICE_ID')
        
        print("\n" + "="*40)

def print_verification_commands():
    """Print commands to verify resource enforcement"""
    print("\n" + "="*60)
    print("VERIFICATION COMMANDS")
    print("="*60)
    
    print("\n🔍 Check container resource limits:")
    print("docker stats  # Shows real-time resource usage")
    print("docker inspect CONTAINER_ID | grep -A 20 'Resources'  # Shows applied limits")
    
    print("\n📋 Check Oakestra logs:")
    print("# Node engine logs (should show resource application)")
    print("docker logs WORKER_CONTAINER")
    print("# Or if running directly:")
    print("tail -f /var/log/oakestra/node_engine.log")
    
    print("\n🧪 Test resource enforcement:")
    print("# Run stress test inside container to verify limits")
    print("docker exec -it CONTAINER_ID sh")
    print("# Inside container:")
    print("# apk add stress-ng  # For Alpine containers")
    print("# stress-ng --cpu 2 --timeout 60s  # Should be limited by CPU quota")

def main():
    print("🚀 Oakestra Resource Enforcement Test Generator")
    print("=" * 60)
    
    # Save test case files
    save_test_cases()
    
    # Print usage instructions
    print_curl_commands()
    print_verification_commands()
    
    print(f"\n✅ Generated {len(test_cases)} test cases")
    print("\n📝 Instructions:")
    print("1. Make sure Oakestra is running (root + cluster orchestrators + workers)")
    print("2. Use the curl commands above to deploy test cases")
    print("3. Use verification commands to check resource enforcement")
    print("4. Look for log messages showing resource limits being applied")
    
    print("\n🎯 What to expect:")
    print("- Containers should be created with CPU/memory limits")
    print("- Logs should show 'Applied CPU limits', 'Applied memory limit', etc.")
    print("- 'docker stats' should show resource usage within limits")
    print("- Invalid resource specs should be rejected with validation errors")

if __name__ == "__main__":
    main()
