package model

import (
	"strconv"
	"strings"
)

// Service is the struct that describes the service
type Service struct {
	JobID           string   `json:"_id"`
	Sname           string   `json:"job_name"`
	Instance        int      `json:"instance_number"`
	Image           string   `json:"image"`
	Commands        []string `json:"cmd"`
	Env             []string `json:"environment"`
	Ports           string   `json:"port"`
	Status          string   `json:"status"`
	Runtime         string   `json:"virtualization"`
	StatusDetail    string   `json:"status_detail"`
	
	// Legacy fields - kept for backward compatibility
	Vtpus           int      `json:"vtpus"`
	Vgpus           int      `json:"vgpus"`
	Vcpus           int      `json:"vcpus"`
	Memory          int      `json:"memory"`
	
	// New resource management fields
	ResourceSpec    ResourceSpec `json:"resource_spec,omitempty"`
	
	UnikernelImages []string `json:"vm_images"`
	Architectures   []string `json:"arch"`
	Pid             int
	OneShot         bool `json:"one_shot"`
}

// ResourceSpec defines the resource requirements and limits for a service
type ResourceSpec struct {
	Requests ResourceQuantity `json:"requests"`
	Limits   ResourceQuantity `json:"limits"`
}

// ResourceQuantity represents resource amounts using standard units
type ResourceQuantity struct {
	CPU              string `json:"cpu"`                // e.g., "250m", "0.5", "1"
	Memory           string `json:"memory"`             // e.g., "256Mi", "512MB", "1Gi"
	EphemeralStorage string `json:"ephemeral-storage"`  // e.g., "1Gi", "500Mi"
	GPU              string `json:"nvidia.com/gpu"`     // e.g., "1", "2"
}

// ResourceLimits represents numeric resource limits for internal calculations
type ResourceLimits struct {
	CPUCores    float64 `json:"cpu_cores"`
	MemoryMB    int64   `json:"memory_mb"`
	DiskMB      int64   `json:"disk_mb"`
	GPUCores    int     `json:"gpu_cores"`
}

// Resources is the struct that describes the resources
type Resources struct {
	Cpu      string `json:"cpu"`
	Memory   string `json:"memory"`
	Disk     string `json:"disk"`
	Logs     string `json:"logs"`
	Sname    string `json:"job_name"`
	Runtime  string `json:"virtualization"`
	Instance int    `json:"instance"`
}

// ServiceStatus is the struct that describes the service status
const (
	SERVICE_CREATING   = "CREATING"
	SERVICE_CREATED    = "CREATED"
	SERVICE_FAILED     = "FAILED"
	SERVICE_DEAD       = "DEAD"
	SERVICE_COMPLETED  = "COMPLETED"
	SERVICE_UNDEPLOYED = "UNDEPLOYED"
)

// GetEffectiveResourceLimits returns the actual resource limits to use for container creation
// Combines new ResourceSpec with legacy fields for backward compatibility
func (s *Service) GetEffectiveResourceLimits() ResourceLimits {
	limits := ResourceLimits{}
	
	// If new ResourceSpec is provided, use it
	if s.ResourceSpec.Limits.CPU != "" || s.ResourceSpec.Limits.Memory != "" {
		limits.CPUCores = parseCPUQuantity(s.ResourceSpec.Limits.CPU)
		limits.MemoryMB = parseMemoryQuantity(s.ResourceSpec.Limits.Memory)
		limits.DiskMB = parseStorageQuantity(s.ResourceSpec.Limits.EphemeralStorage)
		limits.GPUCores = parseGPUQuantity(s.ResourceSpec.Limits.GPU)
	} else {
		// Fall back to legacy fields for backward compatibility
		limits.CPUCores = float64(s.Vcpus)
		limits.MemoryMB = int64(s.Memory)
		limits.DiskMB = 0 // Legacy didn't have disk limits
		limits.GPUCores = s.Vgpus
	}
	
	return limits
}

// GetEffectiveResourceRequests returns the minimum guaranteed resources
func (s *Service) GetEffectiveResourceRequests() ResourceLimits {
	requests := ResourceLimits{}
	
	// If new ResourceSpec is provided, use it
	if s.ResourceSpec.Requests.CPU != "" || s.ResourceSpec.Requests.Memory != "" {
		requests.CPUCores = parseCPUQuantity(s.ResourceSpec.Requests.CPU)
		requests.MemoryMB = parseMemoryQuantity(s.ResourceSpec.Requests.Memory)
		requests.DiskMB = parseStorageQuantity(s.ResourceSpec.Requests.EphemeralStorage)
		requests.GPUCores = parseGPUQuantity(s.ResourceSpec.Requests.GPU)
	} else {
		// Fall back to legacy fields - assume requests = limits for backward compatibility
		requests.CPUCores = float64(s.Vcpus)
		requests.MemoryMB = int64(s.Memory)
		requests.DiskMB = 0
		requests.GPUCores = s.Vgpus
	}
	
	return requests
}

// parseCPUQuantity parses CPU resource strings like "250m", "0.5", "1"
func parseCPUQuantity(cpu string) float64 {
	if cpu == "" {
		return 0
	}
	
	// Handle millicores (e.g., "250m" = 0.25 cores)
	if strings.HasSuffix(cpu, "m") {
		milliStr := strings.TrimSuffix(cpu, "m")
		if milli, err := strconv.ParseFloat(milliStr, 64); err == nil {
			return milli / 1000.0
		}
	}
	
	// Handle direct core count (e.g., "0.5", "1", "2")
	if cores, err := strconv.ParseFloat(cpu, 64); err == nil {
		return cores
	}
	
	return 0
}

// parseMemoryQuantity parses memory resource strings like "256Mi", "512MB", "1Gi"
func parseMemoryQuantity(memory string) int64 {
	if memory == "" {
		return 0
	}
	
	// Convert to MB for internal use
	if strings.HasSuffix(memory, "Mi") {
		mbStr := strings.TrimSuffix(memory, "Mi")
		if mb, err := strconv.ParseInt(mbStr, 10, 64); err == nil {
			return mb
		}
	}
	
	if strings.HasSuffix(memory, "MB") {
		mbStr := strings.TrimSuffix(memory, "MB")
		if mb, err := strconv.ParseInt(mbStr, 10, 64); err == nil {
			return mb
		}
	}
	
	if strings.HasSuffix(memory, "Gi") {
		gbStr := strings.TrimSuffix(memory, "Gi")
		if gb, err := strconv.ParseInt(gbStr, 10, 64); err == nil {
			return gb * 1024 // Convert GB to MB
		}
	}
	
	if strings.HasSuffix(memory, "GB") {
		gbStr := strings.TrimSuffix(memory, "GB")
		if gb, err := strconv.ParseInt(gbStr, 10, 64); err == nil {
			return gb * 1000 // Convert GB to MB (decimal)
		}
	}
	
	// Try direct MB value
	if mb, err := strconv.ParseInt(memory, 10, 64); err == nil {
		return mb
	}
	
	return 0
}

// parseStorageQuantity parses storage resource strings like "1Gi", "500Mi"
func parseStorageQuantity(storage string) int64 {
	// Reuse memory parsing logic since format is the same
	return parseMemoryQuantity(storage)
}

// parseGPUQuantity parses GPU resource strings like "1", "2"
func parseGPUQuantity(gpu string) int {
	if gpu == "" {
		return 0
	}
	
	if gpuCount, err := strconv.Atoi(gpu); err == nil {
		return gpuCount
	}
	
	return 0
}
