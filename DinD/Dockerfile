# Ubuntu Docker image with systemd support
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install systemd and basic Ubuntu packages
RUN apt-get update && \
    apt-get install -y \
    systemd \
    systemd-sysv \
    init \
    sudo \
    curl \
    wget \
    nano \
    vim \
    htop \
    net-tools \
    iputils-ping \
    iproute2 \
    iptables \
    iptables-persistent \
    netfilter-persistent \
    ufw \
    bridge-utils \
    dnsutils \
    tcpdump \
    ssh \
    rsyslog \
    cron \
    procps \
    ca-certificates \
    gnupg \
    lsb-release \
    fuse \
    overlayroot \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Docker
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Remove systemd services that don't work well in containers
RUN (cd /lib/systemd/system/sysinit.target.wants/; for i in *; do [ $i == systemd-tmpfiles-setup.service ] || rm -f $i; done); \
    rm -f /lib/systemd/system/multi-user.target.wants/*; \
    rm -f /etc/systemd/system/*.wants/*; \
    rm -f /lib/systemd/system/local-fs.target.wants/*; \
    rm -f /lib/systemd/system/sockets.target.wants/*udev*; \
    rm -f /lib/systemd/system/sockets.target.wants/*initctl*; \
    rm -f /lib/systemd/system/basic.target.wants/*; \
    rm -f /lib/systemd/system/anaconda.target.wants/*;

# Create a systemd user
RUN useradd -m -s /bin/bash -G sudo,docker ubuntu && \
    echo "ubuntu:ubuntu" | chpasswd && \
    echo "ubuntu ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Enable Docker service
RUN systemctl enable docker && \
    systemctl enable containerd

# Set working directory
WORKDIR /home/ubuntu

# Expose common ports
EXPOSE 22 80 443

# Set the default command to systemd
VOLUME ["/sys/fs/cgroup"]
CMD ["/sbin/init"]
