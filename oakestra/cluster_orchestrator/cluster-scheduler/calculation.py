import logging
from typing import Union

from mongodb_client import mongo_find_all_active_nodes
from oakestra_utils.types.statuses import NegativeSchedulingStatus

# TODO: Introduce proper constraint enums to oakestra-utils.
SUPPORTED_CONSTRAINT_TYPES = ["latency", "geo", "addons"]


def calculate(app, job: dict) -> Union[dict, NegativeSchedulingStatus]:
    print("calculating...")
    app.logger.info("calculating")

    # check here if job has any user preferences, e.g. on a specific node, cpu architecture,
    constraints = job.get("constraints", [])
    requested_constraint_types = [constraint["type"] for constraint in constraints]
    if len(constraints) > 0 and set(requested_constraint_types) & set(SUPPORTED_CONSTRAINT_TYPES):
        return constraint_based_scheduling(job, constraints)
    else:
        return greedy_load_balanced_algorithm(job=job)


def constraint_based_scheduling(job: dict, constraints) -> Union[dict, NegativeSchedulingStatus]:
    filtered_active_nodes = []
    for node in mongo_find_all_active_nodes():
        satisfying = True

        for constraint in constraints:
            constraint_type = constraint.get("type")

            if constraint_type == "direct":
                return deploy_on_best_among_desired_nodes(job, constraint.get("node"))

            if constraint_type == "addons":
                for node in mongo_find_all_active_nodes():
                    node_info = node["node_info"]
                    if not (
                        node_info.get("supported_addons")
                        and constraint.get("needs")
                        and set(constraint.get("needs")).issubset(
                            set(node_info.get("supported_addons"))
                        )
                    ):
                        satisfying = False

        if satisfying:
            filtered_active_nodes.append(node)

    return greedy_load_balanced_algorithm(job=job, active_nodes=filtered_active_nodes)


def first_fit_algorithm(job: dict) -> Union[dict, NegativeSchedulingStatus]:
    """Which of the worker nodes fits the Qos of the deployment file as the first"""
    active_nodes = mongo_find_all_active_nodes()

    print("active_nodes: ")
    for node in active_nodes:
        try:
            available_cpu = node.get("current_cpu_cores_free")
            available_memory = node.get("current_free_memory_in_MB")
            node_info = node.get("node_info")
            technology = node_info.get("technology")

            job_req = job.get("requirements")
            if (
                available_cpu >= job_req.get("cpu")
                and available_memory >= job_req.get("memory")
                and job.get("image_runtime") in technology
            ):
                return node
        except Exception:
            logging.error("Something wrong with job requirements or node infos")

    return NegativeSchedulingStatus.NO_NODE_FOUND


def deploy_on_best_among_desired_nodes(job: dict, nodes) -> Union[dict, NegativeSchedulingStatus]:
    active_nodes = mongo_find_all_active_nodes()
    selected_nodes = []
    if nodes is None or nodes == "":
        selected_nodes = active_nodes
    else:
        desired_nodes_list = nodes.split(";")
        for node in active_nodes:
            if node["node_info"]["host"] in desired_nodes_list:
                selected_nodes.append(node)
    return greedy_load_balanced_algorithm(job, active_nodes=selected_nodes)


def greedy_load_balanced_algorithm(
    job: dict, active_nodes=None
) -> Union[dict, NegativeSchedulingStatus]:
    """Which of the nodes within the cluster have the most capacity for a given job"""
    if active_nodes is None:
        active_nodes = mongo_find_all_active_nodes()
    qualified_nodes = []

    for node in active_nodes:
        if does_node_respects_requirements(extract_specs(node), job):
            qualified_nodes.append(node)

    target_node = None
    target_cpu = 0
    target_mem = 0

    if len(qualified_nodes) < 1:
        return NegativeSchedulingStatus.NO_QUALIFIED_WORKER_FOUND

    # Choose the node with the most available resources to maximize future scheduling flexibility
    # Priority: 1) Total capacity (for long-term scheduling) 2) Available resources (for immediate use)
    target_node = None
    best_score = -1

    for node in qualified_nodes:
        node_specs = extract_specs(node)
        available_cpu = node_specs.get("available_cpu", 0)
        available_memory = node_specs.get("available_memory", 0)
        available_disk = node_specs.get("available_disk", 0)
        
        # For resource pool nodes, consider total capacity for better long-term decisions
        total_cpu = node_specs.get("total_cpu", available_cpu)
        total_memory = node_specs.get("total_memory", available_memory) 
        total_disk = node_specs.get("total_disk", available_disk)
        
        # Scoring algorithm: Prefer nodes with more total capacity, then more available resources
        # This ensures Node B (8GB total) is chosen over Node A (4GB total) for a 2GB service
        capacity_score = (total_cpu * 1000) + (total_memory) + (total_disk / 1000)  # Weight CPU highest
        availability_score = (available_cpu * 100) + (available_memory / 10) + (available_disk / 10000)
        
        # Combined score: 70% capacity (long-term) + 30% availability (immediate)
        combined_score = (capacity_score * 0.7) + (availability_score * 0.3)
        
        if combined_score > best_score:
            best_score = combined_score
            target_node = node

    return target_node


def replicate(job):
    return 1


def extract_specs(node):
    # Check if node has resource pool information (new resource donation system)
    resource_pool = node.get("resource_pool")
    if resource_pool:
        # Use our new resource pool system for accurate resource tracking
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
            # Include total capacities for better scheduling decisions
            "total_cpu": total_cpu,
            "total_memory": total_memory,
            "total_disk": total_disk,
        }
    else:
        # Fallback to old system for compatibility with nodes that haven't been updated
        return {
            "available_cpu": node.get("current_cpu_cores_free", 0)
            * (100 - node.get("current_memory_percent"))
            / 100,
            "available_memory": node.get("current_free_memory_in_MB", 0),
            "available_gpu": len(node.get("gpu_info", [])),
            "virtualization": node.get("node_info", {}).get("technology", []),
            "arch": node.get("node_info").get("architecture"),
        }


def does_node_respects_requirements(node_specs, job):
    memory = 0
    if job.get("memory"):
        memory = job.get("memory")

    vcpu = 0
    if job.get("vcpu"):
        vcpu = job.get("vcpu")

    vgpu = 0
    if job.get("vgpu"):
        vgpu = job.get("vgpu")
        
    # Add disk requirement support for our resource pool system
    disk = 0
    if job.get("disk"):
        disk = job.get("disk")

    virtualization = job.get("virtualization")
    if virtualization == "unikernel":
        arch = job.get("arch")
        arch_fit = False
        if arch:
            for a in arch:
                if a == node_specs["arch"]:
                    arch_fit = True
                    break
        if not arch_fit:
            return False

    # Check all resource requirements including disk
    if (
        node_specs["available_cpu"] >= vcpu
        and node_specs["available_memory"] >= memory
        and node_specs.get("available_disk", float('inf')) >= disk  # Default to unlimited if not specified
        and virtualization in node_specs["virtualization"]
        and node_specs["available_gpu"] >= vgpu
    ):
        return True
    return False
