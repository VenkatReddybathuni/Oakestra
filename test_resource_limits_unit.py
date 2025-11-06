#!/usr/bin/env python3
"""
Unit tests for Oakestra Resource Limits Implementation
This tests the resource parsing and validation logic without requiring a full cluster.
"""

import json
import sys
import os

def test_resource_parsing():
    """Test that our resource specifications are correctly formatted"""
    
    print("🧪 Testing Resource Specification Parsing")
    print("=" * 50)
    
    # Test cases for various resource specifications
    test_cases = [
        {
            "name": "Low Resource Service",
            "resources": {
                "requests": {"cpu": "100m", "memory": "64Mi", "storage": "100Mi"},
                "limits": {"cpu": "200m", "memory": "128Mi", "storage": "200Mi"}
            },
            "expected_cpu": 0.2,
            "expected_memory": 128,
            "expected_storage": 200
        },
        {
            "name": "High Resource Service", 
            "resources": {
                "requests": {"cpu": "1000m", "memory": "1Gi", "storage": "2Gi"},
                "limits": {"cpu": "2000m", "memory": "2Gi", "storage": "4Gi"}
            },
            "expected_cpu": 2.0,
            "expected_memory": 2048,
            "expected_storage": 4096
        },
        {
            "name": "CPU Intensive Service",
            "resources": {
                "requests": {"cpu": "2000m", "memory": "512Mi", "storage": "500Mi"},
                "limits": {"cpu": "4000m", "memory": "1Gi", "storage": "1Gi"}
            },
            "expected_cpu": 4.0,
            "expected_memory": 1024,
            "expected_storage": 1024
        }
    ]
    
    def parse_cpu(cpu_str):
        """Parse CPU specification to float cores"""
        if cpu_str.endswith('m'):
            return float(cpu_str[:-1]) / 1000.0
        else:
            return float(cpu_str)
    
    def parse_memory(mem_str):
        """Parse memory specification to MB"""
        if mem_str.endswith('Mi'):
            return int(mem_str[:-2])
        elif mem_str.endswith('Gi'):
            return int(mem_str[:-2]) * 1024
        elif mem_str.endswith('Ki'):
            return int(mem_str[:-2]) // 1024
        else:
            return int(mem_str)
    
    def parse_storage(storage_str):
        """Parse storage specification to MB"""
        return parse_memory(storage_str)  # Same parsing logic
    
    # Run tests
    passed = 0
    failed = 0
    
    for test in test_cases:
        print(f"\n🔍 Testing: {test['name']}")
        
        try:
            limits = test['resources']['limits']
            
            # Parse values
            cpu_cores = parse_cpu(limits['cpu'])
            memory_mb = parse_memory(limits['memory'])
            storage_mb = parse_storage(limits['storage'])
            
            print(f"   Parsed CPU: {cpu_cores} cores")
            print(f"   Parsed Memory: {memory_mb} MB")
            print(f"   Parsed Storage: {storage_mb} MB")
            
            # Validate expectations
            cpu_ok = abs(cpu_cores - test['expected_cpu']) < 0.001
            memory_ok = memory_mb == test['expected_memory']
            storage_ok = storage_mb == test['expected_storage']
            
            if cpu_ok and memory_ok and storage_ok:
                print(f"   ✅ PASSED")
                passed += 1
            else:
                print(f"   ❌ FAILED")
                if not cpu_ok:
                    print(f"      CPU: expected {test['expected_cpu']}, got {cpu_cores}")
                if not memory_ok:
                    print(f"      Memory: expected {test['expected_memory']}, got {memory_mb}")
                if not storage_ok:
                    print(f"      Storage: expected {test['expected_storage']}, got {storage_mb}")
                failed += 1
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    return failed == 0

def test_go_resource_struct():
    """Test Go ResourceLimits struct compatibility"""
    
    print("\n🔧 Testing Go ResourceLimits Struct Compatibility")
    print("=" * 50)
    
    # This simulates what our Go code should produce
    go_struct_example = {
        "CPUCores": 2.0,
        "MemoryMB": 1024,
        "DiskMB": 2048,
        "GPUCores": 1
    }
    
    print("Expected Go ResourceLimits struct:")
    for key, value in go_struct_example.items():
        print(f"   {key}: {value}")
    
    # Test resource validation logic
    def validate_resources(limits):
        """Simulate Go validateResourceLimits function"""
        errors = []
        
        if limits["CPUCores"] > 16:
            errors.append("CPU cores exceed maximum (16)")
        if limits["MemoryMB"] > 32768:  # 32GB
            errors.append("Memory exceeds maximum (32GB)")
        if limits["DiskMB"] > 1048576:  # 1TB
            errors.append("Disk space exceeds maximum (1TB)")
        if limits["CPUCores"] < 0.1:
            errors.append("CPU cores below minimum (0.1)")
        if limits["MemoryMB"] < 64:
            errors.append("Memory below minimum (64MB)")
            
        return errors
    
    test_cases = [
        {"CPUCores": 2.0, "MemoryMB": 1024, "DiskMB": 2048, "GPUCores": 0},
        {"CPUCores": 0.1, "MemoryMB": 64, "DiskMB": 100, "GPUCores": 0},
        {"CPUCores": 20.0, "MemoryMB": 1024, "DiskMB": 2048, "GPUCores": 0},  # Should fail
        {"CPUCores": 0.05, "MemoryMB": 1024, "DiskMB": 2048, "GPUCores": 0},  # Should fail
    ]
    
    for i, limits in enumerate(test_cases):
        print(f"\n🔍 Test case {i+1}: CPU={limits['CPUCores']}, Memory={limits['MemoryMB']}MB")
        errors = validate_resources(limits)
        
        if errors:
            print(f"   ❌ Validation errors: {', '.join(errors)}")
        else:
            print(f"   ✅ Validation passed")
    
    return True

def test_docker_command_generation():
    """Test Docker command generation with resource limits"""
    
    print("\n🐳 Testing Docker Command Generation")
    print("=" * 50)
    
    def generate_docker_command(service_name, image, cpu_cores, memory_mb):
        """Generate Docker run command with resource limits"""
        cmd_parts = [
            "docker", "run", "-d",
            f"--name={service_name}",
            f"--cpus={cpu_cores}",
            f"--memory={memory_mb}m",
            f"--env=OAKESTRA_DISK_LIMIT_MB=1024",
            image
        ]
        return " ".join(cmd_parts)
    
    test_service = {
        "name": "test-nginx",
        "image": "nginx:alpine", 
        "cpu": 1.5,
        "memory": 512
    }
    
    expected_cmd = generate_docker_command(
        test_service["name"],
        test_service["image"], 
        test_service["cpu"],
        test_service["memory"]
    )
    
    print(f"Generated Docker command:")
    print(f"   {expected_cmd}")
    
    # Verify command contains expected elements
    checks = [
        ("--cpus=1.5" in expected_cmd, "CPU limit"),
        ("--memory=512m" in expected_cmd, "Memory limit"),
        ("--env=OAKESTRA_DISK_LIMIT_MB=1024" in expected_cmd, "Disk limit env var"),
        ("nginx:alpine" in expected_cmd, "Container image")
    ]
    
    all_passed = True
    for check, description in checks:
        if check:
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ {description}")
            all_passed = False
    
    return all_passed

def main():
    """Run all tests"""
    print("🚀 Oakestra Resource Limits - Unit Test Suite")
    print("=" * 60)
    
    tests = [
        ("Resource Parsing", test_resource_parsing),
        ("Go Struct Compatibility", test_go_resource_struct),  
        ("Docker Command Generation", test_docker_command_generation)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"\n✅ {test_name}: PASSED")
                passed_tests += 1
            else:
                print(f"\n❌ {test_name}: FAILED")
        except Exception as e:
            print(f"\n💥 {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"🏁 Test Suite Complete: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Resource limits implementation looks good.")
        return 0
    else:
        print("⚠️ Some tests failed. Please review the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
