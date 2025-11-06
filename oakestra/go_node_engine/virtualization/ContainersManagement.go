package virtualization

import (
	"context"
	"errors"
	"fmt"
	"go_node_engine/logger"
	"go_node_engine/model"
	"go_node_engine/requests"
	"os"
	"reflect"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/containerd/containerd"
	"github.com/containerd/containerd/cio"
	"github.com/containerd/containerd/containers"
	"github.com/containerd/containerd/contrib/nvidia"
	"github.com/containerd/containerd/namespaces"
	"github.com/containerd/containerd/oci"
	"github.com/opencontainers/runtime-spec/specs-go"
	"github.com/shirou/gopsutil/docker"
	"github.com/shirou/gopsutil/process"
	"github.com/struCoder/pidusage"
)

// ContainerRuntime is the struct that describes the container runtime
type ContainerRuntime struct {
	contaierClient *containerd.Client
	killQueue      map[string]*chan bool
	services       []*model.Service
	channelLock    *sync.RWMutex
	ctx            context.Context
}

var runtime = ContainerRuntime{
	channelLock: &sync.RWMutex{},
}

var containerdSingletonCLient sync.Once
var startContainerMonitoring sync.Once

// NAMESPACE is the namespace of the runtime
const NAMESPACE = "oakestra"

// CGROUPV1_BASE_MEM is the base memory path for cgroup v1
const CGROUPV1_BASE_MEM = "/sys/fs/cgroup/memory/" + NAMESPACE

// CGROUPV2_BASE_MEM is the base memory path for cgroup v2
const CGROUPV2_BASE_MEM = "/sys/fs/cgroup/" + NAMESPACE

// GetContainerdClient returns the container runtime client
func GetContainerdClient() *ContainerRuntime {
	containerdSingletonCLient.Do(func() {
		client, err := containerd.New("/run/containerd/containerd.sock")
		if err != nil {
			logger.ErrorLogger().Fatalf("Unable to start the container engine: %v\n", err)
		}
		runtime.contaierClient = client
		runtime.killQueue = make(map[string]*chan bool)
		runtime.ctx = namespaces.WithNamespace(context.Background(), NAMESPACE)
		runtime.forceContainerCleanup()
		model.GetNodeInfo().AddSupportedTechnology(model.CONTAINER_RUNTIME)
	})
	return &runtime
}

// StopContainerdClient stops the container runtime client
func (r *ContainerRuntime) StopContainerdClient() {
	r.channelLock.Lock()
	taskIDs := reflect.ValueOf(r.killQueue).MapKeys()
	r.channelLock.Unlock()

	for _, taskid := range taskIDs {
		err := r.Undeploy(extractSnameFromTaskID(taskid.String()), extractInstanceNumberFromTaskID(taskid.String()))
		if err != nil {
			logger.ErrorLogger().Printf("Unable to undeploy %s, error: %v", taskid.String(), err)
		}
	}
	if err := r.contaierClient.Close(); err != nil {
		logger.ErrorLogger().Printf("Unable to close containerd client: %v", err)
	}

}

// Deploy deploys a service
func (r *ContainerRuntime) Deploy(service model.Service, statusChangeNotificationHandler func(service model.Service)) error {
	// Validate resource specifications before deployment
	if err := validateResourceLimits(service); err != nil {
		logger.ErrorLogger().Printf("Resource validation failed for service %s: %v", service.Sname, err)
		return fmt.Errorf("invalid resource specification: %w", err)
	}

	// Get effective resource limits for the service
	resourceLimits := service.GetEffectiveResourceLimits()
	
	// Check if resources are available in the pool
	node := model.GetNodeInfo()
	if !node.CanAllocateResources(resourceLimits.CPUCores, uint64(resourceLimits.MemoryMB), uint64(resourceLimits.DiskMB)) {
		logger.ErrorLogger().Printf("Insufficient resources for service %s: need CPU=%.2f, Memory=%d MB, Disk=%d MB", 
			service.Sname, resourceLimits.CPUCores, resourceLimits.MemoryMB, resourceLimits.DiskMB)
		return fmt.Errorf("insufficient resources: need CPU=%.2f cores, Memory=%d MB, Disk=%d MB", 
			resourceLimits.CPUCores, resourceLimits.MemoryMB, resourceLimits.DiskMB)
	}
	
	// Reserve resources before deployment
	if err := node.AllocateResources(resourceLimits.CPUCores, uint64(resourceLimits.MemoryMB), uint64(resourceLimits.DiskMB)); err != nil {
		logger.ErrorLogger().Printf("Failed to allocate resources for service %s: %v", service.Sname, err)
		return fmt.Errorf("resource allocation failed: %w", err)
	}
	
	// Store resource allocation info for later cleanup
	var deploymentErr error
	defer func() {
		// If deployment fails, release the reserved resources
		if deploymentErr != nil {
			logger.InfoLogger().Printf("Deployment failed, releasing reserved resources for service %s", service.Sname)
			node.ReleaseResources(resourceLimits.CPUCores, uint64(resourceLimits.MemoryMB), uint64(resourceLimits.DiskMB))
		}
	}()

	var image containerd.Image
	// pull the given image
	sysimg, err := r.contaierClient.ImageService().Get(r.ctx, service.Image)
	if err == nil {
		image = containerd.NewImage(r.contaierClient, sysimg)
	} else {
		logger.ErrorLogger().Printf("Error retrieving the image: %v \n Trying to pull the image online.", err)

		image, err = r.contaierClient.Pull(r.ctx, service.Image, containerd.WithPullUnpack)
		if err != nil {
			return err
		}
	}

	killChannel := make(chan bool, 1)
	startupChannel := make(chan bool, 0)
	errorChannel := make(chan error, 0)

	r.channelLock.RLock()
	el, servicefound := r.killQueue[genTaskID(service.Sname, service.Instance)]
	r.channelLock.RUnlock()
	if !servicefound || el == nil {
		r.channelLock.Lock()
		r.killQueue[genTaskID(service.Sname, service.Instance)] = &killChannel
		r.channelLock.Unlock()
	} else {
		return errors.New("Service already deployed")
	}

	// create startup routine which will accompany the container through its lifetime
	go r.containerCreationRoutine(
		r.ctx,
		image,
		service,
		startupChannel,
		errorChannel,
		&killChannel,
		statusChangeNotificationHandler,
	)

	// wait for updates regarding the container creation
	if <-startupChannel != true {
		deploymentErr = <-errorChannel
		return deploymentErr
	}

	return nil
}

// Undeploy undeploys a service
func (r *ContainerRuntime) Undeploy(service string, instance int) error {
	r.channelLock.Lock()
	defer r.channelLock.Unlock()
	taskid := genTaskID(service, instance)
	el, found := r.killQueue[taskid]
	if found && el != nil {
		logger.InfoLogger().Printf("Sending kill signal to %s", taskid)
		*r.killQueue[taskid] <- true
		select {
		case res := <-*r.killQueue[taskid]:
			if res == false {
				logger.ErrorLogger().Printf("Unable to stop service %s", taskid)
			}
		case <-time.After(5 * time.Second):
			logger.ErrorLogger().Printf("Unable to stop service %s", taskid)
		}
		delete(r.killQueue, taskid)
		return nil
	}
	return errors.New("service not found")
}

func (r *ContainerRuntime) WaitForContainerExits() error {
	// This function spins on all of the containers in the runtime
	// and waits for them to all exit. It then returns.
	// It used for the "Improved" soft termination exit procedure.

	// Get the list of containers
	containers, err := r.contaierClient.Containers(r.ctx)
	if err != nil {
		return fmt.Errorf("failed to list containers: %w", err)
	}

	// Create a wait group to track container exit events
	var wg sync.WaitGroup

	for _, container := range containers {
		wg.Add(1)

		go func(c containerd.Container) {
			defer wg.Done()

			// Get the task for the container
			task, err := c.Task(r.ctx, nil)
			if err != nil {
				// Container might not have a task; log the error and continue
				fmt.Printf("failed to get task for container %s: %v\n", c.ID(), err)
				return
			}

			// Wait for the task to exit
			statusC, err := task.Wait(r.ctx)
			if err != nil {
				fmt.Printf("failed to wait for task in container %s: %v\n", c.ID(), err)
				return
			}

			// Consume the exit status
			<-statusC
		}(container)
	}

	// Wait for all goroutines to complete
	wg.Wait()
	return nil
}

func (r *ContainerRuntime) PrintContainers() error {
	// Debugging function for printing containers and their attributes.
	containers, err := r.contaierClient.Containers(r.ctx)
	if err != nil {
		return fmt.Errorf("failed to list containers: %w", err)
	}

	for _, container := range containers {
		fmt.Printf("CONTAINER_ID: %s\n", container.ID())
	}

	for _, service := range r.services {
		fmt.Printf("SERVICE: %+v\n", service)
	}
	return nil
}

func (r *ContainerRuntime) GetActiveJobs() []requests.Job {
	// Gets the active jobs/containers running on the worker so that this can
	// be communicated to the cluster orchestrator. This is used by all exit procedures
	// in their communication with the cluster orchestrator during the exit.
	jobs := []requests.Job{}

	for _, service := range r.services {
		jsonService := requests.Job{
			JobID:          service.JobID,
			JobName:        service.Sname,
			InstanceNumber: service.Instance,
		}

		jobs = append(jobs, jsonService)
	}

	return jobs
}

func (r *ContainerRuntime) containerCreationRoutine(
	ctx context.Context,
	image containerd.Image,
	service model.Service,
	startup chan bool,
	errorchan chan error,
	killChannel *chan bool,
	statusChangeNotificationHandler func(service model.Service),
) {

	taskid := genTaskID(service.Sname, service.Instance)
	hostname := fmt.Sprintf("instance-%d", service.Instance)

	revert := func(err error) {
		startup <- false
		errorchan <- err
		r.channelLock.Lock()
		defer r.channelLock.Unlock()
		r.killQueue[taskid] = nil
	}

	// Get effective resource limits from service specification
	resourceLimits := service.GetEffectiveResourceLimits()
	
	logger.InfoLogger().Printf("Applying resource limits - CPU: %.2f cores, Memory: %d MB, Disk: %d MB, GPU: %d", 
		resourceLimits.CPUCores, resourceLimits.MemoryMB, resourceLimits.DiskMB, resourceLimits.GPUCores)

	// Prepare environment variables including disk limits
	env := append([]string{fmt.Sprintf("HOSTNAME=%s", hostname)}, service.Env...)
	if resourceLimits.DiskMB > 0 {
		env = append(env, fmt.Sprintf("OAKESTRA_DISK_LIMIT_MB=%d", resourceLimits.DiskMB))
	}

	//create container general oci specs with resource limits
	specOpts := []oci.SpecOpts{
		oci.WithImageConfig(image),
		oci.WithHostHostsFile,
		oci.WithHostname(hostname),
		oci.WithEnv(env),
	}
	
	// Apply resource limits using available OCI functions
	if resourceLimits.CPUCores > 0 || resourceLimits.MemoryMB > 0 {
		logger.InfoLogger().Printf("Applying resource limits: CPU=%.2f cores, Memory=%d MB, Disk=%d MB", 
			resourceLimits.CPUCores, resourceLimits.MemoryMB, resourceLimits.DiskMB)
		
		// Apply CPU limits (shares - relative weight, 1024 shares = 1 CPU core)
		if resourceLimits.CPUCores > 0 {
			cpuShares := uint64(resourceLimits.CPUCores * 1024)
			specOpts = append(specOpts, oci.WithCPUShares(cpuShares))
			
			// Also set CPU quota/period for hard limits
			cpuPeriod := uint64(100000) // 100ms
			cpuQuota := int64(resourceLimits.CPUCores * float64(cpuPeriod))
			specOpts = append(specOpts, oci.WithCPUCFS(cpuQuota, cpuPeriod))
		}
		
		// Apply Memory limits (convert MB to bytes)
		if resourceLimits.MemoryMB > 0 {
			memoryLimit := uint64(resourceLimits.MemoryMB * 1024 * 1024)
			specOpts = append(specOpts, oci.WithMemoryLimit(memoryLimit))
		}
	}
	
	//add user defined commands
	if len(service.Commands) > 0 {
		specOpts = append(specOpts, oci.WithProcessArgs(service.Commands...))
	}
	
	//add GPU if needed - check both new and legacy GPU specifications
	gpuCount := resourceLimits.GPUCores
	if gpuCount == 0 && service.Vgpus > 0 {
		gpuCount = service.Vgpus // Fallback to legacy field
	}
	if gpuCount > 0 {
		specOpts = append(specOpts, nvidia.WithGPUs(nvidia.WithDevices(0), nvidia.WithAllCapabilities))
		logger.InfoLogger().Printf("NVIDIA - Adding GPU driver for %d GPUs", gpuCount)
	}
	
	// Apply disk/storage limits if specified (basic constraint via environment)
	if resourceLimits.DiskMB > 0 {
		// Set environment variable to inform container about disk limit
		diskLimitEnv := fmt.Sprintf("OAKESTRA_DISK_LIMIT_MB=%d", resourceLimits.DiskMB)
		specOpts = append(specOpts, oci.WithEnv([]string{diskLimitEnv}))
		logger.InfoLogger().Printf("Applied storage constraint via environment: %s", diskLimitEnv)
	}
	
	//add resolve file with default google dns
	resolvconfFile, err := getGoogleDNSResolveConf()
	if err != nil {
		revert(err)
		return
	}
	//defer resolvconfFile.Close()
	defer func() {
		if err := resolvconfFile.Close(); err != nil {
			logger.ErrorLogger().Printf("Unable to close resolvconf file: %v", err)
		}
	}()

	// SA9002: file mode 444 evaluates to 0674, which is not a valid file mode
	_ = resolvconfFile.Chmod(0444)
	specOpts = append(specOpts, withCustomResolvConf(resolvconfFile.Name()))

	// create the container
	container, err := r.contaierClient.NewContainer(
		ctx,
		taskid,
		containerd.WithImage(image),
		containerd.WithNewSnapshot(fmt.Sprintf("%s-snapshotter", taskid), image),
		containerd.WithNewSpec(specOpts...),
	)
	if err != nil {
		revert(err)
		return
	}

	//	start task with /tmp/hostname default log directory
	file, err := os.OpenFile(fmt.Sprintf("%s/%s", model.GetNodeInfo().LogDirectory, taskid), os.O_RDWR|os.O_CREATE|os.O_APPEND, 0644)
	if err != nil {
		revert(err)
		return
	}
	//defer file.Close()
	defer func() {
		if err := file.Close(); err != nil {
			logger.ErrorLogger().Printf("Unable to close log file: %v", err)
		}
	}()

	task, err := container.NewTask(ctx, cio.NewCreator(cio.WithStreams(nil, file, file)))

	if err != nil {
		logger.ErrorLogger().Printf("ERROR: containerd task creation failure: %v", err)
		_ = container.Delete(ctx)
		revert(err)
		return
	}
	defer func(ctx context.Context, task containerd.Task) {
		err := killTask(ctx, task, container)
		//removing from killqueue
		r.channelLock.Lock()
		defer r.channelLock.Unlock()
		r.killQueue[taskid] = nil
		if err != nil {
			*killChannel <- false
		} else {
			*killChannel <- true
		}
	}(ctx, task)

	// get wait channel
	exitStatusC, err := task.Wait(ctx)
	if err != nil {
		logger.ErrorLogger().Printf("ERROR: containerd task wait failure: %v", err)
		revert(err)
		return
	}

	// if Overlay mode is active then attach network to the task
	if model.GetNodeInfo().Overlay {
		taskpid := int(task.Pid())
		err = requests.AttachNetworkToTask(taskpid, service.Sname, service.Instance, service.Ports)
		if err != nil {
			logger.ErrorLogger().Printf("Unable to attach network interface to the task: %v", err)
			revert(err)
			return
		}
	}

	// execute the image's task
	if err := task.Start(ctx); err != nil {
		logger.ErrorLogger().Printf("ERROR: containerd task start failure: %v", err)
		revert(err)
		return
	}

	// adv startup finished
	startup <- true

	// Inject service struct into ContainerRuntime
	r.services = append(r.services, &service)

	// wait for manual task kill or task finish
	select {
	case exitStatus := <-exitStatusC:
		if exitStatus.ExitCode() == 0 && service.OneShot {
			service.Status = model.SERVICE_COMPLETED
		}
		//TODO: container exited, do something, notify to cluster manager
		if err != nil {
			return
		}
		logger.InfoLogger().Printf("WARNING: Container exited with status %d", exitStatus.ExitCode())
		service.StatusDetail = fmt.Sprintf("Container exited with status: %d", exitStatus.ExitCode())
	case <-*killChannel:
		logger.InfoLogger().Printf("Kill channel message received for task %s", task.ID())
	}

	if service.Status != model.SERVICE_COMPLETED {
		service.Status = model.SERVICE_DEAD
	}

	//detaching network
	if model.GetNodeInfo().Overlay {
		_ = requests.DetachNetworkFromTask(service.Sname, service.Instance)
	}
	
	// Release resources when service stops
	resourceLimits = service.GetEffectiveResourceLimits()
	model.GetNodeInfo().ReleaseResources(resourceLimits.CPUCores, uint64(resourceLimits.MemoryMB), uint64(resourceLimits.DiskMB))
	logger.InfoLogger().Printf("Released resources for stopped service %s: CPU=%.2f, Memory=%d MB, Disk=%d MB", 
		service.Sname, resourceLimits.CPUCores, resourceLimits.MemoryMB, resourceLimits.DiskMB)
	
	statusChangeNotificationHandler(service)
	remove(r.services, &service)
	r.removeContainer(container)
}

func (r *ContainerRuntime) HandleJobOperations(decisions []requests.JobDecision) {
	// This is part of the *mechanism* for the heuristic-based exit procedure. It takes
	// the list of job decisions from the cluster orchestrator and carries them out
	// on the running jobs. i.e., it terminates or leaves containers depending on the
	// keep/kill decision.
	for _, decision := range decisions {
		container, err := r.contaierClient.LoadContainer(r.ctx, decision.JobName)
		if err != nil {
			logger.InfoLogger().Printf("Error loading container %s: %v", decision.JobName, err)
			continue
		}

		switch decision.Decision {
		case "KILL":
			task, err := container.Task(r.ctx, nil)
			if err != nil {
				logger.InfoLogger().Printf("Error retrieving task for container %s: %v", decision.JobName, err)
				continue
			}

			// Find and release resources for the service being killed
			r.releaseResourcesForContainer(decision.JobName)

			if err := task.Kill(r.ctx, syscall.SIGKILL); err != nil {
				logger.InfoLogger().Printf("Failed to kill container %s: %v", decision.JobName, err)
				continue
			}
			logger.InfoLogger().Printf("Successfully killed container %s", decision.JobName)

		case "KEEP":
			logger.InfoLogger().Printf("Skipping container %s as decision is %s", decision.JobName, decision.Decision)
		default:
			logger.InfoLogger().Printf("Shouldn't be here, decision is neither keep nor kill.")
		}
	}
}

// releaseResourcesForContainer finds a service by container name and releases its resources
func (r *ContainerRuntime) releaseResourcesForContainer(containerName string) {
	r.channelLock.RLock()
	defer r.channelLock.RUnlock()
	
	// Find the service that matches this container
	for _, service := range r.services {
		if genTaskID(service.Sname, service.Instance) == containerName {
			resourceLimits := service.GetEffectiveResourceLimits()
			model.GetNodeInfo().ReleaseResources(resourceLimits.CPUCores, uint64(resourceLimits.MemoryMB), uint64(resourceLimits.DiskMB))
			logger.InfoLogger().Printf("Released resources for killed service %s: CPU=%.2f, Memory=%d MB, Disk=%d MB", 
				service.Sname, resourceLimits.CPUCores, resourceLimits.MemoryMB, resourceLimits.DiskMB)
			return
		}
	}
	logger.InfoLogger().Printf("Could not find service for container %s to release resources", containerName)
}

func remove[T comparable](l []T, item T) []T {
	for i, other := range l {
		if other == item {
			return append(l[:i], l[i+1:]...)
		}
	}
	return l
}

func getTotalCpuUsageByPid(pid int32) (float64, error) {
	totCpu := 0.0
	procs, err := process.NewProcess(pid)
	if err != nil {
		logger.ErrorLogger().Printf("ERROR: %v", err)
		return 0, err
	}

	children, err := procs.Children()
	if err != nil {
		return 0, err
	}

	for _, child := range children {
		cpuUsage, err := child.CPUPercent()
		if err != nil {
			logger.ErrorLogger().Printf("ERROR: %v", err)
			return 0, err
		}
		totCpu += cpuUsage
	}
	return totCpu / float64(model.GetNodeInfo().CpuCores), nil
}

func (r *ContainerRuntime) ResourceMonitoring(every time.Duration, notifyHandler func(res []model.Resources)) {
	//start container monitoring service
	startContainerMonitoring.Do(func() {
		for true {
			select {
			case <-time.After(every):
				deployedContainers, err := r.contaierClient.Containers(r.ctx)
				if err != nil {
					logger.ErrorLogger().Printf("Unable to fetch running containers: %v", err)
				}

				resourceList := make([]model.Resources, 0)

				for _, container := range deployedContainers {
					task, err := container.Task(r.ctx, nil)
					if err != nil {
						logger.ErrorLogger().Printf("Unable to fetch container task: %v", err)
						continue
					}

					cpuUsage, err := getTotalCpuUsageByPid(int32(task.Pid()))
					if err != nil {
						sysInfo, err := pidusage.GetStat(int(task.Pid()))
						if err != nil {
							logger.ErrorLogger().Printf("Unable to fetch task info: %v", err)
							continue
						}
						cpuUsage = sysInfo.CPU / float64(model.GetNodeInfo().CpuCores)
					}

					mem, err := r.getContainerMemoryUsage(container.ID(), int(task.Pid()))
					if err != nil {
						logger.ErrorLogger().Printf("Unable to fetch container Memory: %v", err)
						mem = 0
					}

					containerMetadata, err := container.Info(r.ctx)
					if err != nil {
						logger.ErrorLogger().Printf("Unable to fetch container metadata: %v", err)
						continue
					}
					currentsnapshotter := r.contaierClient.SnapshotService(containerd.DefaultSnapshotter)
					usage, err := currentsnapshotter.Usage(r.ctx, containerMetadata.SnapshotKey)
					if err != nil {
						logger.ErrorLogger().Printf("Unable to fetch task disk usage: %v", err)
						continue
					}

					resourceList = append(resourceList, model.Resources{
						Cpu:      fmt.Sprintf("%f", cpuUsage),
						Memory:   fmt.Sprintf("%f", mem),
						Disk:     fmt.Sprintf("%d", usage.Size),
						Sname:    extractSnameFromTaskID(container.ID()),
						Runtime:  string(model.CONTAINER_RUNTIME),
						Logs:     getLogs(container.ID()),
						Instance: extractInstanceNumberFromTaskID(container.ID()),
					})
				}
				//NOTIFY WITH THE CURRENT CONTAINERS STATUS
				notifyHandler(resourceList)
			}
		}
	})
}

func (r *ContainerRuntime) forceContainerCleanup() {
	deployedContainers, err := r.contaierClient.Containers(r.ctx)
	if err != nil {
		logger.ErrorLogger().Printf("Unable to fetch running containers: %v", err)
	}
	for _, container := range deployedContainers {
		r.removeContainer(container)
	}
}

func (r *ContainerRuntime) removeContainer(container containerd.Container) {
	logger.InfoLogger().Printf("Clenaning up container: %s", container.ID())
	task, err := container.Task(r.ctx, nil)
	if err != nil {
		logger.ErrorLogger().Printf("Unable to fetch container task: %v", err)
	}
	if err == nil {
		err = killTask(r.ctx, task, container)
		if err != nil {
			logger.ErrorLogger().Printf("Unable to fetch kill task: %v", err)
		}
	}
	err = container.Delete(r.ctx)
	if err != nil {
		logger.ErrorLogger().Printf("Unable to delete container: %v", err)
	}
}

func (r *ContainerRuntime) getContainerMemoryUsage(containerID string, pid int) (float64, error) {
	//trying fetching memory using CGROUP_V1 path
	mem, err := docker.CgroupMem(containerID, CGROUPV1_BASE_MEM)
	if err != nil {
		//trying fetching memory using CGROUP_V2 path
		mem, err = docker.CgroupMem(containerID, CGROUPV2_BASE_MEM)
		if err != nil {
			//unable to get memory usage from CGROUPS, likely disabled. Defaulting to PID memory consumption
			sysInfo, err := pidusage.GetStat(pid)
			if err != nil {
				return 0, err
			}
			return sysInfo.Memory, nil
		}
	}
	return float64(mem.MemUsageInBytes), nil
}

func withCustomResolvConf(src string) func(context.Context, oci.Client, *containers.Container, *oci.Spec) error {
	return func(_ context.Context, _ oci.Client, _ *containers.Container, s *oci.Spec) error {
		s.Mounts = append(s.Mounts, specs.Mount{
			Destination: "/etc/resolv.conf",
			Type:        "bind",
			Source:      src,
			Options:     []string{"rbind", "ro"},
		})
		return nil
	}
}

func getGoogleDNSResolveConf() (*os.File, error) {
	//file, err := ioutil.TempFile("/tmp", "edgeio-resolv-conf")
	file, err := os.CreateTemp("/tmp", "edgeio-resolv-conf")

	if err != nil {
		logger.ErrorLogger().Printf("Unable to create temp resolv file: %v", err)
		return nil, err
	}
	_, err = file.WriteString(fmt.Sprintf("nameserver 8.8.8.8\n"))
	if err != nil {
		logger.ErrorLogger().Printf("Unable to write temp resolv file: %v", err)
		return nil, err
	}
	return file, err
}

func killTask(ctx context.Context, task containerd.Task, container containerd.Container) error {
	//removing the task
	p, err := task.LoadProcess(ctx, task.ID(), nil)
	if err != nil {
		logger.ErrorLogger().Printf("ERROR deleting the task, LoadProcess: %v", err)
		return err
	}
	_, err = p.Delete(ctx, containerd.WithProcessKill)
	if err != nil {
		logger.ErrorLogger().Printf("ERROR deleting the task, Delete: %v", err)
		return err
	}
	_, _ = task.Delete(ctx)
	_ = container.Delete(ctx)

	logger.ErrorLogger().Printf("Task %s terminated", task.ID())
	return nil
}

func extractSnameFromTaskID(taskid string) string {
	sname := taskid
	index := strings.LastIndex(taskid, ".instance")
	if index > 0 {
		sname = taskid[0:index]
	}
	return sname
}

func extractInstanceNumberFromTaskID(taskid string) int {
	instance := 0
	separator := ".instance"
	index := strings.LastIndex(taskid, separator)
	if index > 0 {
		number, err := strconv.Atoi(taskid[index+len(separator)+1:])
		if err == nil {
			instance = number
		}
	}
	return instance
}

// validateResourceLimits validates that resource specifications are reasonable
func validateResourceLimits(service model.Service) error {
	limits := service.GetEffectiveResourceLimits()
	requests := service.GetEffectiveResourceRequests()
	
	// Validate CPU limits
	if limits.CPUCores < 0 {
		return fmt.Errorf("CPU limit cannot be negative: %.2f", limits.CPUCores)
	}
	if limits.CPUCores > 32 { // Reasonable upper bound for edge devices
		return fmt.Errorf("CPU limit too high: %.2f cores (max: 32)", limits.CPUCores)
	}
	if requests.CPUCores > limits.CPUCores {
		return fmt.Errorf("CPU request (%.2f) cannot exceed limit (%.2f)", requests.CPUCores, limits.CPUCores)
	}
	
	// Validate memory limits
	if limits.MemoryMB < 0 {
		return fmt.Errorf("memory limit cannot be negative: %d MB", limits.MemoryMB)
	}
	if limits.MemoryMB > 32768 { // 32GB reasonable upper bound
		return fmt.Errorf("memory limit too high: %d MB (max: 32768)", limits.MemoryMB)
	}
	if requests.MemoryMB > limits.MemoryMB {
		return fmt.Errorf("memory request (%d MB) cannot exceed limit (%d MB)", requests.MemoryMB, limits.MemoryMB)
	}
	
	// Validate disk limits
	if limits.DiskMB < 0 {
		return fmt.Errorf("disk limit cannot be negative: %d MB", limits.DiskMB)
	}
	if limits.DiskMB > 1024000 { // 1TB reasonable upper bound
		return fmt.Errorf("disk limit too high: %d MB (max: 1024000)", limits.DiskMB)
	}
	
	// Validate GPU limits
	if limits.GPUCores < 0 {
		return fmt.Errorf("GPU limit cannot be negative: %d", limits.GPUCores)
	}
	if limits.GPUCores > 8 { // Reasonable upper bound
		return fmt.Errorf("GPU limit too high: %d (max: 8)", limits.GPUCores)
	}
	
	logger.InfoLogger().Printf("Resource validation passed for service %s - CPU: %.2f, Memory: %d MB, Disk: %d MB, GPU: %d", 
		service.Sname, limits.CPUCores, limits.MemoryMB, limits.DiskMB, limits.GPUCores)
	
	return nil
}

func genTaskID(sname string, instancenumber int) string {
	return fmt.Sprintf("%s.instance.%d", sname, instancenumber)
}
