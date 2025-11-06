#!/usr/bin/env python3
"""
Test script to verify multi-deployment resource allocation scenario

Scenario:
1. Initial: Node A (4GB), Node B (8GB) 
2. Deploy Service 1 (2GB) → Should go to Node B → Node A (4GB), Node B (6GB)
3. Deploy Service 2 (4GB) → Should go to Node B → Node A (4GB), Node B (2GB)
4. Verify final state: 4GB and 2GB available as expected
"""

import sys
import os

# Mock the calculation functions (same as before)
def extract_specs(node):
    resource_pool = node.get("resource_pool")
    if resource_pool:
        total_cpu = resource_pool.get("total_cpu_cores", 0)
        allocated_cpu = resource_pool.get("allocated_cpu_cores", 0)
        total_memory = resource_pool.get("total_memory_mb", 0)
        allocated_memory = resource_pool.get("allocated_memory_mb", 0)
        total_disk = resource_pool.get("total_disk_mb", 0)
        allocated_disk = resource_pool.get("allocated_disk_mb", 0)
        
        return {
            "available_cpu": max(0, total_cpu - allocated_cpu),
            "available_memory": max(0, total_memory - allocated_memory),
            "available_disk": max(0, total_disk - allocated_disk),
            "available_gpu": len(node.get("gpu_info", [])),
            "virtualization": node.get("node_info", {}).get("technology", []),
            "arch": node.get("node_info").get("architecture"),
            "total_cpu": total_cpu,
            "total_memory": total_memory,
            "total_disk": total_disk,
        }
    else:
        return {
            "available_cpu": node.get("current_cpu_cores_free", 0) * (100 - node.get("current_memory_percent")) / 100,
            "available_memory": node.get("current_free_memory_in_MB", 0),
            "available_gpu": len(node.get("gpu_info", [])),
            "virtualization": node.get("node_info", {}).get("technology", []),
            "arch": node.get("node_info").get("architecture"),
        }

def does_node_respects_requirements(node_specs, job):
    memory = job.get("memory", 0)
    vcpu = job.get("vcpu", 0)
    vgpu = job.get("vgpu", 0)
    disk = job.get("disk", 0)
    virtualization = job.get("virtualization", "container")

    if (
        node_specs["available_cpu"] >= vcpu
        and node_specs["available_memory"] >= memory
        and node_specs.get("available_disk", float('inf')) >= disk
        and virtualization in node_specs["virtualization"]
        and node_specs["available_gpu"] >= vgpu
    ):
        return True
    return False

def greedy_load_balanced_algorithm(job, active_nodes):
    qualified_nodes = []

    for node in active_nodes:
        if does_node_respects_requirements(extract_specs(node), job):
            qualified_nodes.append(node)

    target_node = None
    best_score = -1

    if len(qualified_nodes) < 1:
        return None

    for node in qualified_nodes:
        node_specs = extract_specs(node)
        available_cpu = node_specs.get("available_cpu", 0)
        available_memory = node_specs.get("available_memory", 0)
        available_disk = node_specs.get("available_disk", 0)
        
        total_cpu = node_specs.get("total_cpu", available_cpu)
        total_memory = node_specs.get("total_memory", available_memory) 
        total_disk = node_specs.get("total_disk", available_disk)
        
        # Scoring algorithm: Prefer nodes with more total capacity, then more available resources
        capacity_score = (total_cpu * 1000) + (total_memory) + (total_disk / 1000)
        availability_score = (available_cpu * 100) + (available_memory / 10) + (available_disk / 10000)
        
        # Combined score: 70% capacity (long-term) + 30% availability (immediate)
        combined_score = (capacity_score * 0.7) + (availability_score * 0.3)
        
        if combined_score > best_score:
            best_score = combined_score
            target_node = node

    return target_node

def deploy_service(nodes, service_job, service_name):
    """Deploy a service and update resource allocation"""
    print(f"\n🚀 Deploying {service_name} (Memory: {service_job['memory']}MB, CPU: {service_job['vcpu']} cores)")
    
    # Show current state before deployment
    print("Current node states:")
    for node in nodes:
        node_name = node['node_info']['host']
        pool = node['resource_pool']
        available_memory = pool['total_memory_mb'] - pool['allocated_memory_mb']
        print(f"  {node_name}: {available_memory}MB available")
    
    # Find best node
    chosen_node = greedy_load_balanced_algorithm(service_job, nodes)
    
    if chosen_node:
        node_name = chosen_node['node_info']['host']
        print(f"✅ {service_name} placed on {node_name}")
        
        # Update resource allocation
        pool = chosen_node['resource_pool']
        pool['allocated_memory_mb'] += service_job['memory']
        pool['allocated_cpu_cores'] += service_job['vcpu']
        pool['allocated_disk_mb'] += service_job.get('disk', 0)
        
        return chosen_node
    else:
        print(f"❌ ERROR: No suitable node found for {service_name}")
        return None

def test_multi_deployment():
    # Create Node A: 4GB RAM, 2 CPU cores
    node_a = {
        "node_id": "node_a",
        "node_info": {
            "host": "worker-node-a",
            "technology": ["container"],
            "architecture": "x86_64"
        },
        "resource_pool": {
            "total_cpu_cores": 2.0,
            "total_memory_mb": 4096,  # 4GB
            "total_disk_mb": 51200,   # 50GB
            "allocated_cpu_cores": 0.0,
            "allocated_memory_mb": 0,
            "allocated_disk_mb": 0,
        },
        "gpu_info": []
    }
    
    # Create Node B: 8GB RAM, 4 CPU cores
    node_b = {
        "node_id": "node_b", 
        "node_info": {
            "host": "worker-node-b",
            "technology": ["container"],
            "architecture": "x86_64"
        },
        "resource_pool": {
            "total_cpu_cores": 4.0,
            "total_memory_mb": 8192,  # 8GB
            "total_disk_mb": 102400,  # 100GB
            "allocated_cpu_cores": 0.0,
            "allocated_memory_mb": 0,
            "allocated_disk_mb": 0,
        },
        "gpu_info": []
    }
    
    nodes = [node_a, node_b]
    
    print("=== MULTI-DEPLOYMENT RESOURCE ALLOCATION TEST ===")
    print("\n📊 Initial State:")
    print(f"Node A: {node_a['resource_pool']['total_memory_mb']}MB RAM total")
    print(f"Node B: {node_b['resource_pool']['total_memory_mb']}MB RAM total")
    
    # Service 1: 2GB RAM requirement
    service_1 = {
        "memory": 2048,  # 2GB
        "vcpu": 1.0,
        "disk": 5120,    # 5GB
        "virtualization": "container"
    }
    
    # Service 2: 4GB RAM requirement  
    service_2 = {
        "memory": 4096,  # 4GB
        "vcpu": 2.0,
        "disk": 10240,   # 10GB
        "virtualization": "container"
    }
    
    # Deploy Service 1
    chosen_1 = deploy_service(nodes, service_1, "Service-1 (2GB)")
    
    # Check intermediate state
    print(f"\n📈 After Service-1:")
    node_a_avail_1 = node_a['resource_pool']['total_memory_mb'] - node_a['resource_pool']['allocated_memory_mb']
    node_b_avail_1 = node_b['resource_pool']['total_memory_mb'] - node_b['resource_pool']['allocated_memory_mb']
    print(f"Node A: {node_a_avail_1}MB available")
    print(f"Node B: {node_b_avail_1}MB available")
    
    # Verify first deployment went to Node B
    if chosen_1 and chosen_1['node_info']['host'] == 'worker-node-b':
        if node_a_avail_1 == 4096 and node_b_avail_1 == 6144:
            print("✅ CORRECT: Service-1 went to Node B, resources updated properly")
        else:
            print(f"❌ ERROR: Resource calculation wrong. Expected Node A=4096, Node B=6144")
    else:
        print("❌ ERROR: Service-1 should have gone to Node B")
    
    # Deploy Service 2
    chosen_2 = deploy_service(nodes, service_2, "Service-2 (4GB)")
    
    # Check final state
    print(f"\n🏁 Final State:")
    node_a_final = node_a['resource_pool']['total_memory_mb'] - node_a['resource_pool']['allocated_memory_mb']
    node_b_final = node_b['resource_pool']['total_memory_mb'] - node_b['resource_pool']['allocated_memory_mb']
    print(f"Node A: {node_a_final}MB available")
    print(f"Node B: {node_b_final}MB available")
    
    # Verify second deployment went to Node B and final state
    if chosen_2 and chosen_2['node_info']['host'] == 'worker-node-b':
        if node_a_final == 4096 and node_b_final == 2048:
            print("✅ PERFECT: Service-2 went to Node B, final state = 4GB and 2GB available!")
            print("✅ All deployments optimal, resource tracking accurate")
        else:
            print(f"❌ ERROR: Final state wrong. Expected Node A=4096, Node B=2048")
            print(f"   Got Node A={node_a_final}, Node B={node_b_final}")
    else:
        print("❌ ERROR: Service-2 should have gone to Node B")
    
    print(f"\n🔍 Verification Summary:")
    print(f"Expected final state: Node A = 4GB, Node B = 2GB")
    print(f"Actual final state:   Node A = {node_a_final/1024:.0f}GB, Node B = {node_b_final/1024:.0f}GB")
    
    if node_a_final == 4096 and node_b_final == 2048:
        print("🎉 SUCCESS: Multi-deployment scenario works perfectly!")
        print("   ✅ Intelligent placement preserved larger node capacity")
        print("   ✅ Resource tracking accurately reflects allocations")
        print("   ✅ System ready for additional services on both nodes")
    else:
        print("❌ FAILURE: Resource allocation or tracking issue detected")

    # Show detailed resource allocation
    print(f"\n📋 Detailed Resource Allocation:")
    print(f"Node A - Total: {node_a['resource_pool']['total_memory_mb']}MB, Allocated: {node_a['resource_pool']['allocated_memory_mb']}MB, Available: {node_a_final}MB")
    print(f"Node B - Total: {node_b['resource_pool']['total_memory_mb']}MB, Allocated: {node_b['resource_pool']['allocated_memory_mb']}MB, Available: {node_b_final}MB")

if __name__ == "__main__":
    test_multi_deployment()
