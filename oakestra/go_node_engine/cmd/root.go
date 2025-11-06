package cmd

import (
	"go_node_engine/jobs"
	"go_node_engine/logger"
	"go_node_engine/model"
	"go_node_engine/mqtt"
	"go_node_engine/requests"
	"go_node_engine/virtualization"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/spf13/cobra"
)

var (
	rootCmd = &cobra.Command{
		Use:   "NodeEngine",
		Short: "Start a NoderEngine",
		Long:  `Start a New Oakestra Worker Node`,
		RunE: func(_ *cobra.Command, _ []string) error {
			return startNodeEngine()
		},
	}
	rootAddress      string
	rootPort         int
	clusterAddress   string
	clusterPort      int
	overlayNetwork   int
	unikernelSupport bool
	logDirectory     string
	
	// Resource pool configuration
	donatedCPU    float64
	donatedMemory uint64
	donatedDisk   uint64
)

// MONITORING_CYCLE defines the interval at which the system should perform monitoring tasks.
const MONITORING_CYCLE = time.Second * 2

// Execute is the entry point of the NodeEngine
func Execute() error {
	rootCmd.CompletionOptions.DisableDefaultCmd = true
	return rootCmd.Execute()
}

func init() {
	rootCmd.Flags().StringVarP(&rootAddress, "rootAddr", "r", "localhost", "Address of the root orchestrator without port")
	rootCmd.Flags().IntVarP(&rootPort, "rootPort", "p", 10100, "Port of the root orchestrator")
	// rootCmd.Flags().StringVarP(&clusterAddress, "clusterAddr", "a", "localhost", "Address of the cluster orchestrator without port")
	// rootCmd.Flags().IntVarP(&clusterPort, "clusterPort", "p", 10100, "Port of the cluster orchestrator")
	rootCmd.Flags().IntVarP(&overlayNetwork, "netmanagerPort", "n", 6000, "Port of the NetManager component, if any. This enables the overlay network across nodes. Use -1 to disable Overlay Network Mode.")
	rootCmd.Flags().BoolVarP(&unikernelSupport, "unikernel", "u", false, "Enable Unikernel support. [qemu/kvm required]")
	rootCmd.Flags().StringVarP(&logDirectory, "logs", "l", "/tmp", "Directory for application's logs")
	
	// Resource pool configuration flags
	rootCmd.Flags().Float64Var(&donatedCPU, "donated-cpu", 2.0, "CPU cores to donate to Oakestra (e.g., 2.0 for 2 cores)")
	rootCmd.Flags().Uint64Var(&donatedMemory, "donated-memory", 4096, "Memory in MB to donate to Oakestra (e.g., 4096 for 4GB)")
	rootCmd.Flags().Uint64Var(&donatedDisk, "donated-disk", 20480, "Disk space in MB to donate to Oakestra (e.g., 20480 for 20GB)")
}

func startNodeEngine() error {
	// set log directory
	model.GetNodeInfo().SetLogDirectory(logDirectory)

	// Initialize resource pool with donated resources
	logger.InfoLogger().Printf("Initializing resource pool with donated resources: CPU=%.2f cores, Memory=%d MB, Disk=%d MB", 
		donatedCPU, donatedMemory, donatedDisk)
	model.GetNodeInfo().InitializeResourcePool(donatedCPU, donatedMemory, donatedDisk)

	// connect to container runtime
	runtime := virtualization.GetContainerdClient()
	defer runtime.StopContainerdClient()

	if unikernelSupport {
		unikernelRuntime := virtualization.GetUnikernelRuntime()
		defer unikernelRuntime.StopUnikernelRuntime()
	}

	rootHandshakeResult := rootHandshake()

	clusterAddress = rootHandshakeResult.ClusterManagerAddr
	clusterPort = rootHandshakeResult.ClusterManagerPort

	logger.InfoLogger().Printf("Received cluster Manager IP/Port: %s:%d", rootHandshakeResult.ClusterManagerAddr, rootHandshakeResult.ClusterManagerPort)

	// hadshake with the cluster orchestrator to get mqtt port and node id
	handshakeResult := clusterHandshake()

	// enable overlay network if required
	if overlayNetwork > 0 {
		model.EnableOverlay(overlayNetwork)
		err := requests.RegisterSelfToNetworkComponent()
		if err != nil {
			logger.ErrorLogger().Fatalf("Unable to register to NetManager: %v", err)
		}
	}

	// binding the node MQTT client
	mqtt.InitMqtt(handshakeResult.NodeId, clusterAddress, handshakeResult.MqttPort)

	// starting node status background job.
	jobs.NodeStatusUpdater(MONITORING_CYCLE, mqtt.ReportNodeInformation)
	// starting container resources background monitor.
	jobs.StartServicesMonitoring(MONITORING_CYCLE, mqtt.ReportServiceResources)

	// catch SIGETRM or SIGINTERRUPT
	termination := make(chan os.Signal, 1)
	// SIGKILL cannot be trapped, using SIGTERM instead
	signal.Notify(termination, syscall.SIGTERM, syscall.SIGINT)

	select {
	case ossignal := <-termination:
		// Note: One of these sections must be uncommented depending on the desired exit method.
		////////////// "Naive" Solution - Hard Termination ////////////////
		// logger.InfoLogger().Printf("Terminating the NodeEngine, signal: %v", ossignal)
		// jobs := runtime.GetActiveJobs()
		// exitResponse := requests.NotifyClusterExit(clusterAddress, clusterPort, handshakeResult.NodeId, jobs)
		// logger.InfoLogger().Printf("Got response from cluster regarding exit: %s", exitResponse.Message)

		////////////// "Improved" Solution - Waiting for  Exits ////////////////
		logger.InfoLogger().Printf("Terminating the NodeEngine, signal: %v", ossignal)
		jobs := runtime.GetActiveJobs()
		exitResponse := requests.NotifyClusterExit(clusterAddress, clusterPort, handshakeResult.NodeId, jobs)
		logger.InfoLogger().Printf("Got response from cluster regarding exit: %s", exitResponse.Message)

		// call function which waits for containers to exit
		logger.InfoLogger().Printf("Waiting for all containers to exit...")
		runtime.PrintContainers()
		runtime.WaitForContainerExits()
		logger.InfoLogger().Printf("All containers have exited")
		////////////////////////////////////////////////////////////////////////

		/////////////////////// Negotiation-Based Solution (WIP) ///////////////////////
		// Note: This method is a work in progress. The mechanism for negoatiation is in place,
		// but the policy used for job keep/kill decisions is not properly implemented.
		//
		// logger.InfoLogger().Printf("Terminating the NodeEngine, signal: %v", ossignal)
		// logger.InfoLogger().Printf("PRINTING CONTAINERS")
		// runtime.PrintContainers()

		// logger.InfoLogger().Printf("STARTING NEGOTIATION PROCEDURE")
		// i := 0
		// for {
		// 	jobs := runtime.GetActiveJobs()
		// 	logger.InfoLogger().Printf("CYCLE %d", i)
		// 	logger.InfoLogger().Printf("ACTIVE JOBS: %+v", jobs)
		// 	if len(jobs) == 0 {
		// 		break
		// 	}
		// 	jobDecisions := requests.Negotiate(clusterAddress, clusterPort, handshakeResult.NodeId, jobs).Decisions
		// 	logger.InfoLogger().Printf("JOB DECISIONS: %+v", jobDecisions)
		// 	runtime.HandleJobOperations(jobDecisions)
		// 	time.Sleep(2 * time.Second)
		// 	i += 1
		// }
		// requests.ConfirmExit(clusterAddress, clusterPort, handshakeResult.NodeId)
		// runtime.WaitForContainerExits()
	}

	return nil
}

func rootHandshake() requests.RootHandshakeAnswer {
	rootResponse := requests.RootHandshake(rootAddress, rootPort)
	return rootResponse
}

func clusterHandshake() requests.ClusterHandshakeAnswer {
	logger.InfoLogger().Printf("INIT: Starting handshake with cluster orchestrator %s:%d", clusterAddress, clusterPort)
	node := model.GetNodeInfo()
	logger.InfoLogger().Printf("Node Statistics: \n__________________")
	logger.InfoLogger().Printf("CPU Cores: %d", node.CpuCores)
	logger.InfoLogger().Printf("CPU Usage: %f", node.CpuUsage)
	logger.InfoLogger().Printf("Mem Usage: %f", node.MemoryUsed)
	logger.InfoLogger().Printf("GPU Driver: %s", node.GpuDriver)
	logger.InfoLogger().Printf("\n________________")
	clusterReponse := requests.ClusterHandshake(clusterAddress, clusterPort)
	logger.InfoLogger().Printf("Got cluster response with MQTT port %s and node ID %s", clusterReponse.MqttPort, clusterReponse.NodeId)

	model.SetNodeId(clusterReponse.NodeId)
	return clusterReponse
}
