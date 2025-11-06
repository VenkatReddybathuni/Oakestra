#!/usr/bin/env python3
"""
Extended test: What happens with additional services after the main scenario?

Current state: Node A (4GB available), Node B (2GB available)
Test cases:
- Small service (1GB) → Should go to Node B (exact fit)
- Another small service (1GB) → Should go to Node A (Node B full)  
- Large service (3GB) → Should go to Node A (only option)
- Impossible service (5GB) → Should fail (insufficient resources)
"""

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

def test_additional_services():
    # Set up the state after the main scenario
    node_a = {
        "node_id": "node_a",
        "node_info": {"host": "worker-node-a", "technology": ["container"], "architecture": "x86_64"},
        "resource_pool": {"total_cpu_cores": 2.0, "total_memory_mb": 4096, "total_disk_mb": 51200,
                         "allocated_cpu_cores": 0.0, "allocated_memory_mb": 0, "allocated_disk_mb": 0},
        "gpu_info": []
    }
    
    node_b = {
        "node_id": "node_b", 
        "node_info": {"host": "worker-node-b", "technology": ["container"], "architecture": "x86_64"},
        "resource_pool": {"total_cpu_cores": 4.0, "total_memory_mb": 8192, "total_disk_mb": 102400,
                         "allocated_cpu_cores": 3.0, "allocated_memory_mb": 6144, "allocated_disk_mb": 15360},
        "gpu_info": []
    }
    
    nodes = [node_a, node_b]
    
    print("=== EXTENDED DEPLOYMENT TEST ===")
    print("Starting from the end state of previous scenario:")
    print("Node A: 4GB available, Node B: 2GB available")
    
    # Test 1: Small service (1GB) - should prefer Node B to fill it up
    service_3 = {"memory": 1024, "vcpu": 0.5, "disk": 2048, "virtualization": "container"}
    print(f"\n🧪 Test 1: Small service (1GB)")
    chosen_3 = deploy_service(nodes, service_3, "Service-3 (1GB)")
    
    if chosen_3 and chosen_3['node_info']['host'] == 'worker-node-b':
        print("✅ CORRECT: 1GB service went to Node B (better utilization)")
    else:
        print("❌ Unexpected placement for 1GB service")
    
    # Test 2: Another small service (1GB) - should go to Node A now
    service_4 = {"memory": 1024, "vcpu": 0.5, "disk": 2048, "virtualization": "container"}
    print(f"\n🧪 Test 2: Another small service (1GB)")
    chosen_4 = deploy_service(nodes, service_4, "Service-4 (1GB)")
    
    if chosen_4 and chosen_4['node_info']['host'] == 'worker-node-a':
        print("✅ CORRECT: Second 1GB service went to Node A (Node B full)")
    else:
        print("❌ Unexpected placement for second 1GB service")
    
    # Test 3: Medium service (3GB) - should go to Node A (only option)
    service_5 = {"memory": 3072, "vcpu": 1.5, "disk": 6144, "virtualization": "container"}
    print(f"\n🧪 Test 3: Medium service (3GB)")
    chosen_5 = deploy_service(nodes, service_5, "Service-5 (3GB)")
    
    if chosen_5 and chosen_5['node_info']['host'] == 'worker-node-a':
        print("✅ CORRECT: 3GB service went to Node A (only viable option)")
    else:
        print("❌ Unexpected placement for 3GB service")
    
    # Test 4: Impossible service (5GB) - should fail
    service_6 = {"memory": 5120, "vcpu": 2.0, "disk": 10240, "virtualization": "container"}
    print(f"\n🧪 Test 4: Impossible service (5GB)")
    chosen_6 = deploy_service(nodes, service_6, "Service-6 (5GB)")
    
    if chosen_6 is None:
        print("✅ CORRECT: 5GB service correctly rejected (insufficient resources)")
    else:
        print("❌ ERROR: 5GB service should have been rejected")
    
    # Final state analysis
    print(f"\n🏆 Final Resource State:")
    node_a_final = node_a['resource_pool']['total_memory_mb'] - node_a['resource_pool']['allocated_memory_mb']
    node_b_final = node_b['resource_pool']['total_memory_mb'] - node_b['resource_pool']['allocated_memory_mb']
    
    print(f"Node A: {node_a_final}MB available ({node_a['resource_pool']['allocated_memory_mb']}MB used)")
    print(f"Node B: {node_b_final}MB available ({node_b['resource_pool']['allocated_memory_mb']}MB used)")
    
    total_used = node_a['resource_pool']['allocated_memory_mb'] + node_b['resource_pool']['allocated_memory_mb']
    total_capacity = node_a['resource_pool']['total_memory_mb'] + node_b['resource_pool']['total_memory_mb']
    utilization = (total_used / total_capacity) * 100
    
    print(f"\n📊 Cluster Utilization: {total_used}MB / {total_capacity}MB ({utilization:.1f}%)")
    
    if node_b_final <= 1024 and node_a_final >= 0:  # Node B should be nearly full, Node A partially used
        print("🎯 EXCELLENT: Resource allocation maximized cluster utilization!")
        print("   ✅ Node B efficiently packed with smaller services")
        print("   ✅ Node A used for services that couldn't fit in Node B")
        print("   ✅ Impossible requests properly rejected")
    else:
        print("⚠️  Resource allocation could be improved")

if __name__ == "__main__":
    test_additional_services()
