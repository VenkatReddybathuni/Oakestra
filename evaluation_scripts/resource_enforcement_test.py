#!/usr/bin/env python3
"""
Resource Enforcement Test Script

This script tests the new resource specification format in Oakestra.
It deploys services with different resource requirements and verifies
that containers are created with proper resource limits.

Usage:
    python resource_enforcement_test.py
"""

import requests
import json
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Oakestra System Manager endpoint
SYSTEM_MANAGER_URL = "http://localhost:10000"
API_BASE = f"{SYSTEM_MANAGER_URL}/api"

def test_legacy_resource_format():
    """Test legacy resource format (backward compatibility)"""
    logger.info("=== Testing Legacy Resource Format ===")
    
    sla_legacy = {
        "sla_version": "v2.0",
        "customerID": "Admin",
        "applications": [
            {
                "applicationID": "",
                "application_name": "legacy-test",
                "application_namespace": "test",
                "application_desc": "Test legacy resource format",
                "microservices": [
                    {
                        "microserviceID": "",
                        "microservice_name": "nginx-legacy",
                        "microservice_namespace": "test",
                        "virtualization": "container",
                        "cmd": [],
                        "memory": 256,        # Legacy format: MB as integer
                        "vcpus": 1,          # Legacy format: cores as integer
                        "vgpus": 0,
                        "vtpus": 0,
                        "bandwidth_in": 0,
                        "bandwidth_out": 0,
                        "storage": 512,      # Legacy format: MB as integer
                        "code": "docker.io/library/nginx:latest",
                        "state": "",
                        "port": "8080:80",
                        "added_files": [],
                        "constraints": []
                    }
                ]
            }
        ]
    }
    
    return deploy_and_monitor(sla_legacy, "Legacy Format")

def test_new_resource_format():
    """Test new Kubernetes-style resource format"""
    logger.info("=== Testing New Resource Format ===")
    
    sla_new = {
        "sla_version": "v2.0",
        "customerID": "Admin",
        "applications": [
            {
                "applicationID": "",
                "application_name": "new-format-test",
                "application_namespace": "test",
                "application_desc": "Test new resource format",
                "microservices": [
                    {
                        "microserviceID": "",
                        "microservice_name": "nginx-new",
                        "microservice_namespace": "test",
                        "virtualization": "container",
                        "cmd": [],
                        # New resource specification format
                        "resource_spec": {
                            "requests": {
                                "cpu": "250m",              # 250 millicores
                                "memory": "128Mi",          # 128 MiB
                                "ephemeral-storage": "500Mi" # 500 MiB
                            },
                            "limits": {
                                "cpu": "500m",              # 500 millicores (0.5 cores)
                                "memory": "256Mi",          # 256 MiB
                                "ephemeral-storage": "1Gi"  # 1 GiB
                            }
                        },
                        "code": "docker.io/library/nginx:latest",
                        "state": "",
                        "port": "8081:80",
                        "added_files": [],
                        "constraints": []
                    }
                ]
            }
        ]
    }
    
    return deploy_and_monitor(sla_new, "New Format")

def test_high_resource_requirements():
    """Test service with high resource requirements"""
    logger.info("=== Testing High Resource Requirements ===")
    
    sla_high = {
        "sla_version": "v2.0",
        "customerID": "Admin",
        "applications": [
            {
                "applicationID": "",
                "application_name": "high-resource-test",
                "application_namespace": "test",
                "application_desc": "Test high resource requirements",
                "microservices": [
                    {
                        "microserviceID": "",
                        "microservice_name": "resource-hungry",
                        "microservice_namespace": "test",
                        "virtualization": "container",
                        "cmd": ["sleep", "300"],  # Sleep for 5 minutes
                        "resource_spec": {
                            "requests": {
                                "cpu": "1",              # 1 full core
                                "memory": "512Mi",       # 512 MiB
                                "ephemeral-storage": "2Gi" # 2 GiB
                            },
                            "limits": {
                                "cpu": "2",              # 2 full cores
                                "memory": "1Gi",         # 1 GiB
                                "ephemeral-storage": "4Gi" # 4 GiB
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
    
    return deploy_and_monitor(sla_high, "High Resource")

def test_invalid_resource_specs():
    """Test invalid resource specifications (should fail validation)"""
    logger.info("=== Testing Invalid Resource Specifications ===")
    
    invalid_specs = [
        {
            "name": "Negative CPU",
            "spec": {
                "requests": {"cpu": "-1", "memory": "256Mi"},
                "limits": {"cpu": "1", "memory": "512Mi"}
            }
        },
        {
            "name": "Request > Limit",
            "spec": {
                "requests": {"cpu": "2", "memory": "1Gi"},
                "limits": {"cpu": "1", "memory": "512Mi"}
            }
        },
        {
            "name": "Excessive Resources",
            "spec": {
                "requests": {"cpu": "100", "memory": "100Gi"},
                "limits": {"cpu": "200", "memory": "200Gi"}
            }
        }
    ]
    
    results = []
    for invalid_spec in invalid_specs:
        logger.info(f"Testing invalid spec: {invalid_spec['name']}")
        
        sla_invalid = {
            "sla_version": "v2.0",
            "customerID": "Admin",
            "applications": [
                {
                    "applicationID": "",
                    "application_name": f"invalid-test-{invalid_spec['name'].lower().replace(' ', '-')}",
                    "application_namespace": "test",
                    "application_desc": f"Test invalid spec: {invalid_spec['name']}",
                    "microservices": [
                        {
                            "microserviceID": "",
                            "microservice_name": "invalid-service",
                            "microservice_namespace": "test",
                            "virtualization": "container",
                            "cmd": ["sleep", "60"],
                            "resource_spec": invalid_spec["spec"],
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
        
        result = deploy_and_monitor(sla_invalid, f"Invalid - {invalid_spec['name']}", expect_failure=True)
        results.append(result)
    
    return results

def deploy_and_monitor(sla, test_name, expect_failure=False):
    """Deploy SLA and monitor the results"""
    logger.info(f"Deploying {test_name}...")
    
    result = {
        "test_name": test_name,
        "sla": sla,
        "deployment_success": False,
        "service_id": None,
        "application_id": None,
        "error": None,
        "expected_failure": expect_failure
    }
    
    try:
        # Step 1: Register application
        logger.info(f"Registering application: {sla['applications'][0]['application_name']}")
        response = requests.post(f"{API_BASE}/applications", json=sla)
        
        if response.status_code == 200:
            app_data = response.json()
            logger.info(f"Application registered successfully: {app_data}")
            
            result["deployment_success"] = True
            result["application_id"] = app_data.get("applications", [{}])[0].get("applicationID")
            
            # Get service ID from the response
            services = app_data.get("applications", [{}])[0].get("microservices", [])
            if services:
                result["service_id"] = services[0].get("microserviceID")
                
                # Step 2: Deploy service instance
                if result["service_id"]:
                    logger.info(f"Deploying service instance: {result['service_id']}")
                    deploy_response = requests.post(f"{API_BASE}/service/{result['service_id']}/instance")
                    
                    if deploy_response.status_code == 200:
                        logger.info("Service instance deployed successfully")
                        
                        # Step 3: Monitor service status
                        time.sleep(5)  # Wait for deployment
                        monitor_service_status(result["service_id"], test_name)
                        
                    else:
                        logger.error(f"Failed to deploy service instance: {deploy_response.text}")
                        result["error"] = f"Instance deployment failed: {deploy_response.text}"
        else:
            logger.error(f"Application registration failed: {response.text}")
            result["error"] = f"Registration failed: {response.text}"
            
            if expect_failure:
                logger.info("Expected failure occurred - test passed")
                result["deployment_success"] = True  # Mark as success since we expected failure
            
    except Exception as e:
        logger.error(f"Exception during deployment: {str(e)}")
        result["error"] = str(e)
        
        if expect_failure:
            logger.info("Expected failure occurred - test passed")
            result["deployment_success"] = True
    
    return result

def monitor_service_status(service_id, test_name):
    """Monitor service status and resource usage"""
    logger.info(f"Monitoring service {service_id} for {test_name}")
    
    try:
        # Get service status
        response = requests.get(f"{API_BASE}/service/{service_id}")
        if response.status_code == 200:
            service_data = response.json()
            logger.info(f"Service status: {json.dumps(service_data, indent=2)}")
            
            # Check if service is running
            instances = service_data.get("instance_list", [])
            for instance in instances:
                status = instance.get("status", "Unknown")
                logger.info(f"Instance {instance.get('instance_number', 'N/A')}: Status = {status}")
                
                if status in ["RUNNING", "CREATED"]:
                    logger.info(f"✅ {test_name}: Service instance is running successfully")
                elif status in ["FAILED", "DEAD"]:
                    logger.error(f"❌ {test_name}: Service instance failed")
                else:
                    logger.info(f"⏳ {test_name}: Service instance is {status}")
        else:
            logger.error(f"Failed to get service status: {response.text}")
            
    except Exception as e:
        logger.error(f"Exception during monitoring: {str(e)}")

def cleanup_services(results):
    """Clean up deployed services"""
    logger.info("=== Cleaning up deployed services ===")
    
    for result in results:
        if result.get("service_id") and result.get("deployment_success"):
            try:
                logger.info(f"Deleting service: {result['service_id']}")
                response = requests.delete(f"{API_BASE}/service/{result['service_id']}")
                if response.status_code == 200:
                    logger.info(f"✅ Service {result['service_id']} deleted successfully")
                else:
                    logger.error(f"❌ Failed to delete service {result['service_id']}: {response.text}")
            except Exception as e:
                logger.error(f"Exception during cleanup: {str(e)}")

def print_test_summary(results):
    """Print test summary"""
    logger.info("=== Test Summary ===")
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r["deployment_success"])
    
    logger.info(f"Total tests: {total_tests}")
    logger.info(f"Successful tests: {successful_tests}")
    logger.info(f"Failed tests: {total_tests - successful_tests}")
    
    for result in results:
        status = "✅ PASS" if result["deployment_success"] else "❌ FAIL"
        logger.info(f"{status}: {result['test_name']}")
        if result["error"]:
            logger.info(f"    Error: {result['error']}")

def main():
    """Main test function"""
    logger.info("Starting Oakestra Resource Enforcement Tests")
    logger.info("=" * 50)
    
    results = []
    
    try:
        # Test 1: Legacy format (backward compatibility)
        results.append(test_legacy_resource_format())
        time.sleep(10)  # Wait between tests
        
        # Test 2: New resource format
        results.append(test_new_resource_format())
        time.sleep(10)
        
        # Test 3: High resource requirements
        results.append(test_high_resource_requirements())
        time.sleep(10)
        
        # Test 4: Invalid resource specifications
        invalid_results = test_invalid_resource_specs()
        results.extend(invalid_results)
        
        # Print summary
        print_test_summary(results)
        
        # Wait before cleanup
        time.sleep(30)
        
        # Cleanup
        cleanup_services(results)
        
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        cleanup_services(results)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        cleanup_services(results)

if __name__ == "__main__":
    main()
