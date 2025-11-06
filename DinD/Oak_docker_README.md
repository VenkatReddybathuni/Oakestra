# Ubuntu Docker Container with Systemd Support

This project provides a Docker container running Ubuntu 22.04 with systemd support and basic Ubuntu commands.

## Features

- **Ubuntu 22.04 LTS** base image
- **systemd** fully functional for service management
- **Basic Ubuntu tools** including:
  - curl, wget, nano, vim
  - htop, net-tools, iputils-ping
  - ssh, rsyslog, cron
  - sudo access
- **Pre-configured user**: `ubuntu` (password: `ubuntu`)
- **Privileged container** with proper systemd support

## Quick Start

### Method 1: Using the Management Script

```bash
# Make script executable (if not already done)
chmod +x ubuntu-docker.sh

# Build the image
./ubuntu-docker.sh build

# Run the container
./ubuntu-docker.sh run

# Access the container shell
./ubuntu-docker.sh shell

# Check status
./ubuntu-docker.sh status
```

### Method 2: Using Docker Compose Directly

```bash
# Build and run
sudo docker compose up -d

# Access shell
sudo docker exec -it ubuntu-systemd /bin/bash

# Check systemd status
sudo docker exec ubuntu-systemd systemctl status
```

## Available Commands

The management script (`ubuntu-docker.sh`) supports these commands:

- `build` - Build the Ubuntu systemd Docker image
- `run` - Run the container using docker-compose
- `start` - Start existing container
- `stop` - Stop the container
- `restart` - Restart the container
- `shell` - Access container shell
- `logs` - Show container logs
- `status` - Show container status
- `clean` - Remove container and image
- `help` - Show help message

## Container Details

- **Container Name**: `ubuntu-systemd`
- **Base Image**: `ubuntu:22.04`
- **Init System**: `systemd` (`/sbin/init`)
- **Default User**: `ubuntu` (with sudo privileges)
- **Working Directory**: `/home/ubuntu`

### Exposed Ports

- `2222` - SSH (mapped to host port 2222)
- `8080` - HTTP (mapped to host port 8080)
- `8443` - HTTPS (mapped to host port 8443)

## Systemd Features

The container runs with full systemd support:

```bash
# Check systemd status
systemctl status

# List active services
systemctl list-units --type=service --state=active

# Start/stop services
systemctl start <service>
systemctl stop <service>

# Enable/disable services
systemctl enable <service>
systemctl disable <service>
```

## Testing

Once the container is running, you can test various features:

```bash
# Test basic commands
sudo docker exec ubuntu-systemd ls -la /
sudo docker exec ubuntu-systemd ps aux
sudo docker exec ubuntu-systemd systemctl status

# Test network connectivity
sudo docker exec ubuntu-systemd ping -c 3 google.com

# Test package management
sudo docker exec ubuntu-systemd apt update
sudo docker exec ubuntu-systemd apt list --installed | head -10

# Access interactive shell
sudo docker exec -it ubuntu-systemd /bin/bash
```

## Requirements

- Docker Engine
- Docker Compose (or `docker compose` plugin)
- sudo privileges (for Docker operations)

## Technical Architecture & Implementation

### How Systemd Works in Docker

Running systemd inside Docker containers requires specific configurations because Docker containers typically run a single process, while systemd is designed to manage multiple services.

#### Key Systemd Requirements:
1. **PID 1**: Systemd must run as the init process (PID 1)
2. **Cgroups**: Access to control groups for process management
3. **Privileged mode**: Required for systemd to manage services properly
4. **Volume mounts**: Specific filesystem access for systemd operation

#### Implementation Steps:

**1. Dockerfile Configuration:**
```dockerfile
# Set systemd as the entry point
CMD ["/sbin/init"]

# Remove problematic systemd services that don't work in containers
RUN (cd /lib/systemd/system/sysinit.target.wants/; for i in *; do [ $i == systemd-tmpfiles-setup.service ] || rm -f $i; done); \
    rm -f /lib/systemd/system/multi-user.target.wants/*; \
    rm -f /etc/systemd/system/*.wants/*; \
    rm -f /lib/systemd/system/local-fs.target.wants/*; \
    rm -f /lib/systemd/system/sockets.target.wants/*udev*; \
    rm -f /lib/systemd/system/sockets.target.wants/*initctl*; \
    rm -f /lib/systemd/system/basic.target.wants/*; \
    rm -f /lib/systemd/system/anaconda.target.wants/*;
```

**2. Docker Compose Configuration:**
```yaml
privileged: true              # Required for systemd
volumes:
  - /sys/fs/cgroup:/sys/fs/cgroup:ro  # Cgroup access for process management
cap_add:
  - SYS_ADMIN                # Administrative capabilities
security_opt:
  - seccomp:unconfined       # Unrestricted system calls
```

### Docker-in-Docker (DinD) Implementation

Docker-in-Docker allows running Docker containers inside a Docker container. This is complex because it involves nested containerization.

#### Why DinD is Needed:
- NetManager deploys applications as containers
- The host Docker daemon needs to be accessible from inside the container
- Container images need to be managed and executed

#### DinD Architecture:
```
Host Machine
├── Docker Daemon (dockerd)
├── Ubuntu Container (systemd)
    ├── Docker Client (docker)
    ├── Containerd Runtime
    └── NetManager Application
        └── Deployed Containers
```

#### Implementation Components:

**1. Docker Socket Mount:**
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```
- **Purpose**: Shares the host Docker daemon with the container
- **How it works**: Container uses host's Docker engine instead of running its own
- **Why needed**: Avoids running multiple Docker daemons

**2. Docker Data Volumes:**
```yaml
volumes:
  - /var/lib/docker:/var/lib/docker
  - /var/lib/containerd:/var/lib/containerd
```
- **Purpose**: Persistent storage for Docker images and container data
- **Why needed**: Prevents data loss when container restarts

**3. Additional Capabilities:**
```yaml
cap_add:
  - SYS_ADMIN    # System administration
  - SYS_TIME     # System time modification
  - SYS_PTRACE   # Process tracing (debugging)
  - NET_ADMIN    # Network administration
  - NET_RAW      # Raw socket access
```

**4. Security Configuration:**
```yaml
security_opt:
  - seccomp:unconfined    # Disable seccomp filtering
  - apparmor:unconfined   # Disable AppArmor restrictions
```

### Containerd Configuration & Overlay Filesystem Issues

Containerd is the runtime that actually manages containers. It uses "snapshotters" to manage container filesystem layers.

#### The Problem:
```
ERROR: containerd task creation failure: failed to mount rootfs component
{overlay overlay [...]}: invalid argument: unknown
```

#### Root Cause Analysis:
1. **Overlay Filesystem**: Default snapshotter for containerd
2. **Kernel Modules**: Overlay module not available in nested containers
3. **Mount Permissions**: Filesystem mounting restrictions in containers

#### Solution Implementation:

**1. Identify Available Snapshotters:**
```bash
# Check what snapshotters are available
containerd config default | grep snapshotter
```

**2. Configure Native Snapshotter:**
```bash
# Generate default config
mkdir -p /etc/containerd
containerd config default > /etc/containerd/config.toml

# Switch from overlay to native snapshotter
sed -i 's/snapshotter = "overlayfs"/snapshotter = "native"/' /etc/containerd/config.toml
```

**Why Native Snapshotter Works:**
- **Overlay**: Requires kernel overlay module and specific mount capabilities
- **Native**: Uses regular filesystem operations, more compatible with containers
- **Trade-off**: Slightly more disk usage but better compatibility

**3. Clean State and Restart:**
```bash
# Remove corrupted snapshots
systemctl stop containerd
rm -rf /var/lib/containerd/*
systemctl start containerd
```

#### Snapshotter Comparison:

| Snapshotter | Pros | Cons | Use Case |
|-------------|------|------|----------|
| **overlayfs** | Fast, efficient, copy-on-write | Requires kernel modules | Production hosts |
| **native** | Simple, compatible, no special requirements | More disk usage | Containers, testing |
| **btrfs** | Advanced features, snapshots | Requires btrfs filesystem | Specialized setups |

### Network Configuration

The container network setup enables external access to deployed services:

```yaml
ports:
  - "2222:22"     # SSH access to container
  - "8080:8080"   # Direct port mapping for applications
  - "8443:443"    # HTTPS services
  - "6000:6000"   # NetManager management interface
```

#### Access Path for External Clients:
```
Internet/Network Client
    ↓ (Host IP:8080)
Host Machine Docker Daemon
    ↓ (Container IP:8080)
Ubuntu Container
    ↓ (localhost:8080)
Deployed Application Container
```

### Service Startup Order

1. **Host Docker Daemon** starts
2. **Ubuntu Container** starts with systemd as PID 1
3. **Systemd** initializes and starts enabled services
4. **Containerd** starts with native snapshotter
5. **Docker client** connects to host daemon via socket
6. **NetManager** starts and can deploy containers
7. **Deployed containers** run via containerd with native snapshotter

### Verification Commands

```bash
# Check systemd is running as PID 1
sudo docker exec ubuntu-systemd ps aux | grep systemd

# Verify containerd configuration
sudo docker exec ubuntu-systemd cat /etc/containerd/config.toml | grep snapshotter

# Test containerd functionality
sudo docker exec ubuntu-systemd ctr --version
sudo docker exec ubuntu-systemd ctr namespaces list

# Check Docker socket connectivity
sudo docker exec ubuntu-systemd docker version

# Verify network connectivity
sudo docker exec ubuntu-systemd netstat -tlnp | grep :8080
```

This architecture provides a fully functional Ubuntu environment with systemd service management and the ability to deploy containerized applications through NetManager.

## Troubleshooting

### Container won't start with systemd
Ensure the container is run with:
- `--privileged` flag
- Proper volume mounts for `/sys/fs/cgroup`
- `--cap-add SYS_ADMIN` capability

### Permission issues
Make sure to run Docker commands with `sudo` if your user isn't in the docker group.

### Systemd services not working
Some systemd services are disabled by default in containers. The Dockerfile removes services that don't work well in containerized environments.

### NetManager containerd overlay filesystem errors

If you encounter errors like:
```
ERROR: containerd task creation failure: failed to create shim task: failed to mount rootfs component
```

This indicates containerd overlay filesystem issues in Docker-in-Docker scenarios. Here's how to fix it:

1. **Install missing packages** (if iptables errors occur):
```bash
# Inside the container
sudo docker exec ubuntu-systemd bash -c "apt-get update && apt-get install -y iptables iptables-persistent netfilter-persistent"
```

2. **Configure containerd to use native snapshotter**:
```bash
# Inside the container
sudo docker exec ubuntu-systemd bash -c "mkdir -p /etc/containerd && containerd config default > /etc/containerd/config.toml"
sudo docker exec ubuntu-systemd bash -c "sed -i 's/snapshotter = \"overlayfs\"/snapshotter = \"native\"/' /etc/containerd/config.toml"
```

3. **Clean containerd state and restart**:
```bash
# Inside the container
sudo docker exec ubuntu-systemd bash -c "systemctl stop containerd && rm -rf /var/lib/containerd/* && systemctl start containerd"
```

4. **Verify containerd is working**:
```bash
sudo docker exec ubuntu-systemd systemctl status containerd
sudo docker exec ubuntu-systemd ctr --version
```

5. **Restart NetManager**:
```bash
# Inside the container
sudo docker exec ubuntu-systemd bash -c "pkill NetManager || echo 'NetManager not running'"
# Then restart NetManager
sudo docker exec ubuntu-systemd NetManager -p 6000
```

### Docker-in-Docker Requirements

The container is configured with:
- **Docker socket mount**: `/var/run/docker.sock:/var/run/docker.sock`
- **Docker data volumes**: `/var/lib/docker` and `/var/lib/containerd`
- **Additional capabilities**: `SYS_ADMIN`, `SYS_TIME`, `SYS_PTRACE`, `NET_ADMIN`, `NET_RAW`
- **Security options**: `seccomp:unconfined`, `apparmor:unconfined`
- **FUSE device**: `/dev/fuse:/dev/fuse` for overlay filesystem support

### Port Conflicts

The container exposes:
- Port `8080:8080` - Direct mapping for applications
- Port `2222:22` - SSH access
- Port `8443:443` - HTTPS
- Port `6000:6000` - NetManager port

## Security Note

This container runs in privileged mode to support systemd and Docker-in-Docker. Use appropriate security measures in production environments.
