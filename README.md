# Enhanced Oakestra - Resource Donation System

**Enhanced Oakestra with Intelligent Resource Management**

This is an enhanced version of Oakestra that adds intelligent resource allocation and user-defined resource donation capabilities.

## 🚀 Quick Installation

### Root + Cluster (Master Node)
```bash
curl -sfL https://raw.githubusercontent.com/VenkatReddybathuni/Oakestra/venkat/scripts/StartEnhancedOakestra.sh | sh -
```

### Worker Node (Default: 4 CPU cores, 8GB RAM, 100GB disk)
```bash
curl -sfL https://raw.githubusercontent.com/VenkatReddybathuni/Oakestra/venkat/scripts/InstallEnhancedWorker.sh | sh
```

### Worker Node (Custom Resources)
```bash
# Donate 8 CPU cores, 16GB RAM, 200GB disk
curl -sfL https://raw.githubusercontent.com/VenkatReddybathuni/Oakestra/venkat/scripts/InstallEnhancedWorker.sh | sh -s -- --cpu 8.0 --memory 16384 --disk 204800
```

## Our Work

Below, we point you to the main files which contain our code for this project. Again, our project was an extension of an exiting version of Oakestra (forked from version ```alpha-v0.4.302``` on 30 October 2024), so our code is nestled into various parts of Oakestra's codebase.

Cluster Orchestrator:
- ```/oakestra/cluster_orchestrator/cluster-manager/cluster_manager.py```
- ```/oakestra/cluster_orchestrator/cluster-manager/mongodb_client.py```

Worker:
- ```/oakestra/go_node_engine/cmd/root.go```
- All files in ```/oakestra/go_node_engine/requests```
- ```/oakestra/go_node_engine/virtualization/ContainersManagement.go```

Root Orchestrator
- ```/oakestra/root_orchestrator/system-manager-python/blueprints/dynamic_participation_blueprints.py```

We describe how to run Oakestra at the end of this file.

## Where data came from

### Elasticity

As described in the project report, the elasticity data came from the cluster's worker status. We ping the cluster manager's API endpoint at ```http://<CLUSTER_ORCH_IP>:10100/api/node/get_workers```. See our test script in ```/evaluation_scripts/elasticity/api_data.py``` to see more detail. 

To make workers join and leave the network, we run lightweight HTTP servers on each worker as well as our personal testing machine (laptop/desktop/whatever). The ```/evaluation_scripts/elasticity/client.py``` script is the one that is run on our machine, and the ```/evaluation_scripts/elasticity/server.py``` is run on each worker. Basically, the client tells the workers to join and leave the network at the specified intervals.

### Preliminary Testing (Motivation) and Termination Resilience

The structure of these test is described in the Motivation and Evaluation chapters of the report. We manually start the specified number of workers, deploy containers to them, and then manually terminate the one specified worker. While we do this, we run ```/evaluation_scripts/termination_resilience/test_rescheduling.py``` to collect data on how many tasks are running, dead, etc.. 

### Efficiency

We also describe the structure of this test in the Evaluation chapter of our report. We deploy the specified number of workers with 4 tasks of the specified length. These tasks are run in the form of a custom container which is specified here in the Oakestra source code: ```/oakestra/testing/timed_container_efficiency```. 

We record the start time of all of our workers/tasks. Then, we terminate one or more of the workers. Each container is running a script which performs dummy work (matmuls) for the specified interval, and when it is done, it pings our coordinating machine which is running a data-gathering http server ```/evaluation_scripts/efficiency/server.py```. This script is recording the start and end times of tasks which *finish* (they only ping the data gathering endpoint if they actually finish the whole interval).

## How data was processed

### Elasticity

This is very trivial. The data we get from the endpoint (described in the previous section) is already in a usable format (e.g., list of JSON objects like ```{time: 12, nodes: 5}```). For the sake of plotting simplicity, we combine the static and dynamic data into one file. It tells us the number of workers in the cluster at each timestamp -- see ```/evaluation_data/final_elasticity_data``` for this data.

### Termination Resilience

This is also relatively trivial. We ping the cluster manager (see the script specified in the previous section) to get data which is in the form of ```{time: 32, running: 4, node_scheduled: 2, failed: 2}```. There is no real processing that is necessary here. 

### Efficiency

This is the only experiment which requires any real "processing". Using all of the **productive** start and end times we described in the previous section, as well as looking at the **total** time taken from the start to end of each task, we calculate the overall efficiency for each test according to the method described in our Evaluation chapter. You can see this processed data in ```/evaluation_data/final_absolute_time_data``` and ```/evaluation_data/final_aggregate_efficiency_data```. 

## How outputs can be generated from the code that you have included

### Plots

All of the processed data we used for our plots is contained in the ```/evaluation_data``` folder. We also provide the file ```plots.ipynb```, where all of the plots are generated.

### Running Oakestra

For the purposes of this project, we run a root orchestrator and cluster orchestrator on the same machine. On this machine, run:

```curl -sfL https://raw.githubusercontent.com/lucasleschynski/oakestra/develop/scripts/StartOakestraFull.sh | sh -  ```

to start the root and clsuter orchestrators. 

On the worker (or workers), run:

```curl -sfL https://raw.githubusercontent.com/lucasleschynski/oakestra/develop/scripts/InstallOakestraWorker.sh | sh -  ```

to install the Oakestra NetManager and NodeEngine. 

To start the NetManager and NodeEngine, run:

```
sudo NetManager -p 6000 &
sudo NodeEngine -n 6000 -p 10000 -r 172.17.177.3
```

For now, you will also need to edit the ```NodePublicAddress``` and ```ClusterUrl``` parameters in the  ```/etc/netmanager/netcfg.json``` file correctly. 


To learn how to run actual containers/tasks on Oakestra, see the Oakestra docs at https://www.oakestra.io/docs/getting-started/welcome-to-oakestra-docs/



To stop the root/cluster orchestrators, run: 

```sudo docker compose -f ~/oakestra/1-DOC.yaml down```

