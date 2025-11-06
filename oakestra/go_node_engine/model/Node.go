package model

import (
	"fmt"
	"go_node_engine/logger"
	"go_node_engine/model/gpu"
	"net"
	"os"
	"runtime"
	"strconv"
	"sync"
	"time"

	"github.com/shirou/gopsutil/cpu"
	"github.com/shirou/gopsutil/disk"
	"github.com/shirou/gopsutil/host"
	"github.com/shirou/gopsutil/load"
	"github.com/shirou/gopsutil/mem"
	psnet "github.com/shirou/gopsutil/net"
)

// RuntimeType is the type of runtime that the node executes
type RuntimeType string

// RuntimeType constants
const (
	CONTAINER_RUNTIME RuntimeType = "docker"
	UNIKERNEL_RUNTIME RuntimeType = "unikernel"
)

// AddonType is the type of addon that the node supports
type AddonType string

const (
// Example Addon:
//
//	FLOPS AddonType = "FLOps"
)

// Node is the struct that describes the node
type Node struct {
	Id              string            `json:"id"`
	Host            string            `json:"host"`
	Ip              string            `json:"ip"`
	Port            string            `json:"port"`
	SystemInfo      map[string]string `json:"system_info"`
	CpuUsage        float64           `json:"cpu"`
	CpuCores        int               `json:"free_cores"`
	CpuArch         string            `json:"architecture"`
	MemoryUsed      float64           `json:"memory"`
	MemoryMB        int               `json:"memory_free_in_MB"`
	DiskInfo        map[string]string `json:"disk_info"`
	NetworkInfo     map[string]string `json:"network_info"`
	GpuDriver       string            `json:"gpu_driver"`
	GpuUsage        float64           `json:"gpu_usage"`
	GpuCores        int               `json:"gpu_cores"`
	GpuTemp         float64           `json:"gpu_temp"`
	GpuMemUsage     float64           `json:"gpu_mem_used"`
	GpuTotMem       float64           `json:"gpu_tot_mem"`
	Technology      []RuntimeType     `json:"technology"`
	SupportedAddons []AddonType       `json:"supported_addons"`
	Overlay         bool
	LogDirectory    string
	NetManagerPort  int
	
	// Resource Pool Management
	ResourcePool    *NodeResourcePool `json:"resource_pool,omitempty"`
}

// NodeResourcePool tracks the resource capacity and allocation for this node
type NodeResourcePool struct {
	// Total resources available for donation (user-configured)
	TotalCPUCores    float64 `json:"total_cpu_cores"`     // e.g., 4.0 cores
	TotalMemoryMB    uint64  `json:"total_memory_mb"`     // e.g., 8192 MB
	TotalDiskMB      uint64  `json:"total_disk_mb"`       // e.g., 102400 MB (100GB)
	
	// Currently allocated resources to running services
	AllocatedCPUCores float64 `json:"allocated_cpu_cores"` // e.g., 2.5 cores in use
	AllocatedMemoryMB uint64  `json:"allocated_memory_mb"` // e.g., 3072 MB in use
	AllocatedDiskMB   uint64  `json:"allocated_disk_mb"`   // e.g., 50000 MB in use
	
	// Available resources for new services
	AvailableCPUCores float64 `json:"available_cpu_cores"` // Total - Allocated
	AvailableMemoryMB uint64  `json:"available_memory_mb"` // Total - Allocated
	AvailableDiskMB   uint64  `json:"available_disk_mb"`   // Total - Allocated
	
	// Resource utilization tracking
	LastUpdated       int64   `json:"last_updated"`        // Unix timestamp
	ActiveServices    int     `json:"active_services"`     // Number of running services
	
	// Resource pool lock for thread-safe operations
	mutex sync.RWMutex `json:"-"`
}

var once sync.Once
var node Node

// GetNodeInfo returns the node information
func GetNodeInfo() *Node {
	once.Do(func() {
		node = Node{
			Host:            getHostname(),
			SystemInfo:      getSystemInfo(),
			CpuCores:        getCpuCores(),
			CpuArch:         runtime.GOARCH,
			Port:            getPort(),
			Technology:      make([]RuntimeType, 0),
			SupportedAddons: make([]AddonType, 0),
			Overlay:         false,
		}
	})
	node.updateDynamicInfo()
	return &node
}

// SetLogDirectory sets the directory where the logs will be stored
func (n *Node) SetLogDirectory(dir string) {
	n.LogDirectory = dir
}

// GetDynamicInfo returns the dynamic information of the node (CPU, Memory, GPU usage etc.)
func GetDynamicInfo() Node {
	node.updateDynamicInfo()
	return Node{
		CpuUsage:     node.CpuUsage,
		CpuCores:     node.CpuCores,
		MemoryUsed:   node.MemoryUsed,
		MemoryMB:     node.MemoryMB,
		GpuDriver:    node.GpuDriver,
		GpuTemp:      node.GpuTemp,
		GpuUsage:     node.GpuUsage,
		GpuTotMem:    node.GpuTotMem,
		GpuMemUsage:  node.GpuMemUsage,
		ResourcePool: node.GetResourcePoolStatus(), // Include resource pool status
	}
}

// EnableOverlay enables the overlay network, setting the port
func EnableOverlay(port int) {
	node.Overlay = true
	node.NetManagerPort = port
}

func (n *Node) updateDynamicInfo() {
	// System Info
	n.CpuUsage = getAvgCpuUsage()
	n.Ip = getIp()
	n.MemoryMB = getMemoryMB()
	n.MemoryUsed = getMemoryUsage()
	n.DiskInfo = getDiskinfo()
	n.NetworkInfo = getNetworkInfo()

	// GPU Info
	n.GpuDriver = getGpuDriver()
	n.GpuTotMem = getTotGpuMemFreeMB()
	n.GpuMemUsage = getGpuMemUsage()
	n.GpuUsage = getGpuUsage()
	n.GpuCores = getGpuCores()
	n.GpuTemp = getGpuTemp()

	// Update resource pool timestamp
	if n.ResourcePool != nil {
		n.ResourcePool.mutex.Lock()
		n.ResourcePool.LastUpdated = time.Now().Unix()
		n.ResourcePool.mutex.Unlock()
	}
}

// SetNodeId sets the node id
func SetNodeId(id string) {
	GetNodeInfo()
	node.Id = id
}

func getIp() string {
	addresses, err := net.InterfaceAddrs()
	if err != nil {
		return ""
	}
	for _, address := range addresses {
		if ipnet, ok := address.(*net.IPNet); ok && !ipnet.IP.IsLoopback() {
			if ipnet.IP.To4() != nil {
				return ipnet.IP.String()
			}
		}
	}
	return ""
}

func getHostname() string {
	hostname, err := os.Hostname()
	if err != nil {
		hostname = ""
		logger.ErrorLogger().Fatal("Unable to get Node hostname")
	}
	return hostname
}

func getSystemInfo() map[string]string {
	hostinfo, err := host.Info()
	if err != nil {
		logger.ErrorLogger().Printf("Error: %s", err.Error())
		return make(map[string]string, 0)
	}
	sysInfo := make(map[string]string)
	sysInfo["kernel_version"] = hostinfo.KernelVersion
	sysInfo["architecture"] = hostinfo.KernelArch
	sysInfo["os_version"] = hostinfo.OS
	sysInfo["uptime"] = strconv.Itoa(int(hostinfo.Uptime))
	sysInfo["full_stats"] = hostinfo.String()

	return sysInfo
}

func getCpuCores() int {
	cpu, err := cpu.Counts(true)
	if err != nil {
		logger.ErrorLogger().Printf("Error: %s", err.Error())
		return 0
	}
	return cpu
}

func getAvgCpuUsage() float64 {
	avg, err := load.Avg()
	if err != nil {
		return 100
	}
	return avg.Load5
}

func getMemoryMB() int {
	mem, err := mem.VirtualMemory()
	if err != nil {
		logger.ErrorLogger().Printf("Error: %s", err.Error())
		return 0
	}
	return int(mem.Available >> 20)
}

func getMemoryUsage() float64 {
	mem, err := mem.VirtualMemory()
	if err != nil {
		logger.ErrorLogger().Printf("Error: %s", err.Error())
		return 100
	}
	return mem.UsedPercent
}

func getDiskinfo() map[string]string {
	diskUsageStats, err := disk.Usage("/")
	diskInfoMap := make(map[string]string, 0)
	usage := "100"
	if err == nil {
		usage = strconv.Itoa(int(diskUsageStats.UsedPercent))
	}
	diskInfoMap["/"] = usage
	partitionsStats, err := disk.Partitions(true)
	if err == nil {
		for i, partition := range partitionsStats {
			diskInfoMap[fmt.Sprintf("partition_%d", i)] = partition.String()
		}
	}
	return diskInfoMap
}

func getNetworkInfo() map[string]string {
	netInfoMap := make(map[string]string)
	interfaces, err := psnet.Interfaces()
	if err == nil {
		for i, ifce := range interfaces {
			netInfoMap[fmt.Sprintf("interface_%d", i)] = ifce.String()
		}
	}
	return netInfoMap
}

func getPort() string {
	port := os.Getenv("MY_PORT")
	if port == "" {
		port = "3000"
	}
	return port
}

// AddSupportedTechnology adds a supported technology to the node
func (n *Node) AddSupportedTechnology(tech RuntimeType) {
	n.Technology = append(n.Technology, tech)
}

// GetSupportedTechnologyList returns the list of supported technologies
func (n *Node) GetSupportedTechnologyList() []RuntimeType {
	return n.Technology
}

// AddSupportedAddons adds a supported addon to the node
func (n *Node) AddSupportedAddons(ext AddonType) {
	n.SupportedAddons = append(n.SupportedAddons, ext)
}

// GetSupportedAddonsList returns the list of supported addons
func (n *Node) GetSupportedAddonsList() []AddonType {
	return n.SupportedAddons
}

func getGpuDriver() string {
	n, err := gpu.NvsmiDeviceCount()
	if err != nil {
		return "-"
	}

	var queryResult string
	for i := 0; i < n; i++ {
		res, err := gpu.NvsmiQuery(fmt.Sprintf("%d", i), "driver_version")
		if err != nil {
			continue
		}
		queryResult = res
	}

	if queryResult != "" {
		return "-"
	}
	return queryResult
}

func getGpuMemUsage() float64 {
	n, err := gpu.NvsmiDeviceCount()
	if err != nil || n == 0 {
		return 0
	}

	totMem := 0.0
	for i := 0; i < n; i++ {
		res, err := gpu.NvsmiQuery(fmt.Sprintf("%d", i), "memory.used")
		if err != nil {
			return 0
		}
		totm := getTotGpuMem()
		if totm >= 0 {
			currmem, err := strconv.Atoi(res)
			if err != nil {
				return 0
			}
			totMem += float64(currmem) * 100 / getTotGpuMem()
		}
	}
	return totMem / float64(n)
}

func getGpuCores() int {
	n, err := gpu.NvsmiDeviceCount()
	if err != nil || n == 0 {
		return 0
	}
	return n
}

func getGpuUsage() float64 {
	n, err := gpu.NvsmiDeviceCount()
	if err != nil || n == 0 {
		return 0
	}

	totUage := 0.0
	for i := 0; i < n; i++ {
		res, err := gpu.NvsmiQuery(fmt.Sprintf("%d", i), "utilization.gpu")
		if err != nil {
			return 0
		}
		gpuusage, err := strconv.Atoi(res)
		if err != nil {
			return 0
		}
		totUage += float64(gpuusage)
	}
	return totUage / float64(n)
}

func getTotGpuMem() float64 {
	n, err := gpu.NvsmiDeviceCount()
	if err != nil || n == 0 {
		return 0
	}

	totMem := 0.0
	for i := 0; i < n; i++ {
		res, err := gpu.NvsmiQuery(fmt.Sprintf("%d", i), "memory.total")
		if err != nil {
			return 0
		}
		gpuMem, err := strconv.Atoi(res)
		if err != nil {
			return 0
		}
		totMem += float64(gpuMem)
	}
	return totMem
}

func getTotGpuMemFreeMB() float64 {
	n, err := gpu.NvsmiDeviceCount()
	if err != nil || n == 0 {
		return 0
	}

	totMem := 0.0
	for i := 0; i < n; i++ {
		res, err := gpu.NvsmiQuery(fmt.Sprintf("%d", i), "memory.free")
		if err != nil {
			return 0
		}
		gpuMem, err := strconv.Atoi(res)
		if err != nil {
			return 0
		}
		totMem += float64(gpuMem)
	}
	return totMem
}

func getGpuTemp() float64 {
	n, err := gpu.NvsmiDeviceCount()
	if err != nil || n == 0 {
		return 0
	}

	totTemp := 0.0
	for i := 0; i < n; i++ {
		res, err := gpu.NvsmiQuery(fmt.Sprintf("%d", i), "temperature.gpu")
		if err != nil {
			return 0
		}
		currTemp, err := strconv.Atoi(res)
		if err != nil {
			return 0
		}
		totTemp += float64(currTemp)
	}
	return totTemp / float64(n)
}

// InitializeResourcePool initializes the resource pool with user-donated capacity
func (n *Node) InitializeResourcePool(cpuCores float64, memoryMB uint64, diskMB uint64) {
	n.ResourcePool = &NodeResourcePool{
		TotalCPUCores:     cpuCores,
		TotalMemoryMB:     memoryMB,
		TotalDiskMB:       diskMB,
		AllocatedCPUCores: 0.0,
		AllocatedMemoryMB: 0,
		AllocatedDiskMB:   0,
		AvailableCPUCores: cpuCores,
		AvailableMemoryMB: memoryMB,
		AvailableDiskMB:   diskMB,
		LastUpdated:       0,
		ActiveServices:    0,
	}
	logger.InfoLogger().Printf("Resource pool initialized: CPU=%.2f cores, Memory=%d MB, Disk=%d MB", 
		cpuCores, memoryMB, diskMB)
}

// CanAllocateResources checks if the requested resources are available
func (n *Node) CanAllocateResources(cpuCores float64, memoryMB uint64, diskMB uint64) bool {
	if n.ResourcePool == nil {
		return false
	}
	
	n.ResourcePool.mutex.RLock()
	defer n.ResourcePool.mutex.RUnlock()
	
	canAllocate := n.ResourcePool.AvailableCPUCores >= cpuCores &&
		n.ResourcePool.AvailableMemoryMB >= memoryMB &&
		n.ResourcePool.AvailableDiskMB >= diskMB
	
	logger.InfoLogger().Printf("Resource check: need CPU=%.2f/%.2f, Memory=%d/%d, Disk=%d/%d - %v",
		cpuCores, n.ResourcePool.AvailableCPUCores,
		memoryMB, n.ResourcePool.AvailableMemoryMB,
		diskMB, n.ResourcePool.AvailableDiskMB,
		canAllocate)
	
	return canAllocate
}

// AllocateResources reserves the specified resources
func (n *Node) AllocateResources(cpuCores float64, memoryMB uint64, diskMB uint64) error {
	if n.ResourcePool == nil {
		return fmt.Errorf("resource pool not initialized")
	}
	
	n.ResourcePool.mutex.Lock()
	defer n.ResourcePool.mutex.Unlock()
	
	// Double-check availability under lock
	if n.ResourcePool.AvailableCPUCores < cpuCores ||
		n.ResourcePool.AvailableMemoryMB < memoryMB ||
		n.ResourcePool.AvailableDiskMB < diskMB {
		return fmt.Errorf("insufficient resources: need CPU=%.2f/%.2f, Memory=%d/%d, Disk=%d/%d",
			cpuCores, n.ResourcePool.AvailableCPUCores,
			memoryMB, n.ResourcePool.AvailableMemoryMB,
			diskMB, n.ResourcePool.AvailableDiskMB)
	}
	
	// Allocate resources
	n.ResourcePool.AllocatedCPUCores += cpuCores
	n.ResourcePool.AllocatedMemoryMB += memoryMB
	n.ResourcePool.AllocatedDiskMB += diskMB
	
	// Update available resources
	n.ResourcePool.AvailableCPUCores = n.ResourcePool.TotalCPUCores - n.ResourcePool.AllocatedCPUCores
	n.ResourcePool.AvailableMemoryMB = n.ResourcePool.TotalMemoryMB - n.ResourcePool.AllocatedMemoryMB
	n.ResourcePool.AvailableDiskMB = n.ResourcePool.TotalDiskMB - n.ResourcePool.AllocatedDiskMB
	
	n.ResourcePool.ActiveServices++
	
	logger.InfoLogger().Printf("Resources allocated: CPU=%.2f, Memory=%d MB, Disk=%d MB. Available: CPU=%.2f, Memory=%d MB, Disk=%d MB",
		cpuCores, memoryMB, diskMB,
		n.ResourcePool.AvailableCPUCores, n.ResourcePool.AvailableMemoryMB, n.ResourcePool.AvailableDiskMB)
	
	return nil
}

// ReleaseResources frees the specified resources
func (n *Node) ReleaseResources(cpuCores float64, memoryMB uint64, diskMB uint64) {
	if n.ResourcePool == nil {
		return
	}
	
	n.ResourcePool.mutex.Lock()
	defer n.ResourcePool.mutex.Unlock()
	
	// Release resources (ensure we don't go negative)
	n.ResourcePool.AllocatedCPUCores = max(0, n.ResourcePool.AllocatedCPUCores-cpuCores)
	n.ResourcePool.AllocatedMemoryMB = max(0, n.ResourcePool.AllocatedMemoryMB-memoryMB)
	n.ResourcePool.AllocatedDiskMB = max(0, n.ResourcePool.AllocatedDiskMB-diskMB)
	
	// Update available resources
	n.ResourcePool.AvailableCPUCores = n.ResourcePool.TotalCPUCores - n.ResourcePool.AllocatedCPUCores
	n.ResourcePool.AvailableMemoryMB = n.ResourcePool.TotalMemoryMB - n.ResourcePool.AllocatedMemoryMB
	n.ResourcePool.AvailableDiskMB = n.ResourcePool.TotalDiskMB - n.ResourcePool.AllocatedDiskMB
	
	n.ResourcePool.ActiveServices = max(0, n.ResourcePool.ActiveServices-1)
	
	logger.InfoLogger().Printf("Resources released: CPU=%.2f, Memory=%d MB, Disk=%d MB. Available: CPU=%.2f, Memory=%d MB, Disk=%d MB",
		cpuCores, memoryMB, diskMB,
		n.ResourcePool.AvailableCPUCores, n.ResourcePool.AvailableMemoryMB, n.ResourcePool.AvailableDiskMB)
}

// GetResourcePoolStatus returns the current resource pool status
func (n *Node) GetResourcePoolStatus() *NodeResourcePool {
	if n.ResourcePool == nil {
		return nil
	}
	
	n.ResourcePool.mutex.RLock()
	defer n.ResourcePool.mutex.RUnlock()
	
	// Return a copy to avoid race conditions
	return &NodeResourcePool{
		TotalCPUCores:     n.ResourcePool.TotalCPUCores,
		TotalMemoryMB:     n.ResourcePool.TotalMemoryMB,
		TotalDiskMB:       n.ResourcePool.TotalDiskMB,
		AllocatedCPUCores: n.ResourcePool.AllocatedCPUCores,
		AllocatedMemoryMB: n.ResourcePool.AllocatedMemoryMB,
		AllocatedDiskMB:   n.ResourcePool.AllocatedDiskMB,
		AvailableCPUCores: n.ResourcePool.AvailableCPUCores,
		AvailableMemoryMB: n.ResourcePool.AvailableMemoryMB,
		AvailableDiskMB:   n.ResourcePool.AvailableDiskMB,
		LastUpdated:       n.ResourcePool.LastUpdated,
		ActiveServices:    n.ResourcePool.ActiveServices,
	}
}

// max helper function for resource calculations
func max[T ~int | ~int64 | ~uint64 | ~float64](a, b T) T {
	if a > b {
		return a
	}
	return b
}
