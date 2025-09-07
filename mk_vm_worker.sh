#!/usr/bin/env bash
set -euo pipefail

# =================== CONFIG ===================
VM1_NAME="worker-vm1"
VM2_NAME="worker-vm2"

VM_RAM_MB=2048
VM_VCPUS=2
VM_DISK_GB=10

# Unique NetManager/NodeEngine ports per VM
NM1=6001; NE1=10001
NM2=6002; NE2=10002

LIBVIRT_DIR="/var/lib/libvirt/images"
CLOUD_IMG_URL="https://cloud-images.ubuntu.com/focal/current/focal-server-cloudimg-amd64.img"
BASE_IMG="$LIBVIRT_DIR/ubuntu-20.04-amd64.img"
# ==============================================

require() { command -v "$1" >/dev/null 2>&1 || { echo "Missing: $1"; exit 1; }; }

echo "[*] Checking deps…"
for c in qemu-system-x86_64 virt-install cloud-localds wget; do require "$c"; done

echo "[*] Ensuring storage dir: $LIBVIRT_DIR"
mkdir -p "$LIBVIRT_DIR"

echo "[*] Fetching Ubuntu 20.04 cloud image (once)…"
if [[ ! -f "$BASE_IMG" ]]; then
  wget -O "$BASE_IMG" "$CLOUD_IMG_URL"
fi

# Create SSH key
PUBKEY_PATH="${HOME}/.ssh/id_ed25519.pub"
if [[ ! -f "$PUBKEY_PATH" ]]; then
  echo "[*] No SSH key found. Generating one (ed25519)…"
  ssh-keygen -t ed25519 -N "" -f "${HOME}/.ssh/id_ed25519"
fi
PUBKEY="$(cat "$PUBKEY_PATH")"

# -------- Function to create a worker VM --------
make_vm () {
  local NAME="$1" NM_PORT="$2" NE_PORT="$3"

  local QCOW="$LIBVIRT_DIR/${NAME}.qcow2"
  local SEED_ISO="$LIBVIRT_DIR/${NAME}-seed.iso"

  echo "[*] Building cloud-init for $NAME (NM=$NM_PORT, NE=$NE_PORT)…"
  
  # user-data
  cat > "user-data-${NAME}.yaml" <<EOF
#cloud-config
hostname: ${NAME}
package_update: true
packages:
  - qemu-guest-agent
users:
  - name: ubuntu
    sudo: ALL=(ALL) NOPASSWD:ALL
    groups: [sudo]
    shell: /bin/bash
    lock_passwd: false
    ssh_authorized_keys:
      - $(echo "$PUBKEY" | tr -d '\n')
chpasswd:
  list: |
    ubuntu:ubuntu
  expire: false
ssh_pwauth: true
disable_root: false
write_files:
  - path: /etc/systemd/system/netmanager.service
    permissions: "0644"
    content: |
      [Unit]
      Description=Oakestra NetManager
      After=network-online.target
      Wants=network-online.target

      [Service]
      Type=simple
      ExecStart=/usr/bin/NetManager -p 6000
      Restart=always
      RestartSec=2

      [Install]
      WantedBy=multi-user.target

  - path: /etc/systemd/system/nodeengine.service
    permissions: "0644"
    content: |
      [Unit]
      Description=Oakestra NodeEngine
      After=netmanager.service
      Requires=netmanager.service

      [Service]
      Type=simple 
      ExecStart=/usr/bin/NodeEngine -r 192.168.122.1 -p 10000
      Restart=always
      RestartSec=2

      [Install]
      WantedBy=multi-user.target

runcmd:
  # Install worker stack (Lucas script)
  - curl -sfL https://raw.githubusercontent.com/lucasleschynski/oakestra/develop/scripts/InstallOakestraWorker.sh | sh -

  # Write netcfg.json dynamically and enable services (as one shell block)
  - |
    set -e
    install -d -m 0755 /etc/netmanager
    printf '%s\n' \
      '{' \
      '  "NodePublicAddress": "192.168.122.61",' \
      '  "NodePublicPort": "50103",' \
      '  "ClusterUrl": "192.168.122.1",' \
      '  "ClusterMqttPort": "10003"' \
      '}' > /etc/netmanager/netcfg.json

    systemctl daemon-reload
    apt-get update
    apt-get install -y qemu-guest-agent
    # Note: On Ubuntu the usual config path is /etc/default/qemu-guest-agent (the /etc/sysconfig path is RHEL/CentOS)
    # Leaving your line harmless if the file doesn't exist:
    echo "QEMU_GUEST_AGENT_OPTIONS=-o -l debug" > /etc/sysconfig/qemu-ga || true
    echo "d /var/lib/cloud/sem" > /etc/tmpfiles.d/cloud-init-sem.conf || true
    systemctl enable qemu-guest-agent.service
    systemctl restart qemu-guest-agent.service
    sleep 10
    systemctl enable --now netmanager.service
    systemctl enable --now nodeengine.service

final_message: "Oakestra worker ${NAME} is up (NM:${NM_PORT}, NE:${NE_PORT})"
EOF

  # meta-data
  cat > "meta-data-${NAME}.yaml" <<EOF
instance-id: ${NAME}
local-hostname: ${NAME}
EOF

  # network-config - CRITICAL for proper networking
  cat > "network-config-${NAME}.yaml" <<EOF
network:
  version: 2
  renderer: networkd
  ethernets:
    anynic:
      match:
        name: "e*"
      dhcp4: true
      dhcp6: false
      optional: true
      nameservers:
        addresses: [8.8.8.8, 1.1.1.1]
EOF

  echo "[*] Build seed ISO for $NAME…"
  cloud-localds --network-config "network-config-${NAME}.yaml" "$SEED_ISO" "user-data-${NAME}.yaml" "meta-data-${NAME}.yaml"

  echo "[*] Create bootable disk for $NAME…"
  qemu-img create -f qcow2 -F qcow2 -b "$BASE_IMG" "$QCOW" "${VM_DISK_GB}G"

  echo "[*] Install & boot $NAME…"
  virt-install \
    --name "$NAME" \
    --memory "$VM_RAM_MB" \
    --vcpus "$VM_VCPUS" \
    --disk "path=$QCOW,format=qcow2,bus=virtio" \
    --disk "path=$SEED_ISO,device=cdrom,bus=scsi" \
    --network network=default,model=virtio \
    --channel unix,target_type=virtio,name=org.qemu.guest_agent.0 \
    --os-variant ubuntu20.04 \
    --graphics=none \
    --noautoconsole \
    --import

  echo "[*] $NAME created & started. To get IP: virsh domifaddr $NAME"
}

make_vm "$VM1_NAME" "$NM1" "$NE1"
make_vm "$VM2_NAME" "$NM2" "$NE2"

echo
echo "================ Next steps ================"
echo "sudo virsh list --all"
echo 
echo "[*] Giving VMs time to boot (60 seconds) before checking status..."
sleep 60
echo
echo "Console login (if needed): sudo virsh console $VM1_NAME   (user/pass: ubuntu / ubuntu, exit with Ctrl+])"
echo "Inside VM, check:"
echo "  sudo cloud-init status --wait"
echo "  cat /etc/netmanager/netcfg.json"
echo "  sudo journalctl -u netmanager -n 100 --no-pager"
echo "  sudo journalctl -u nodeengine -n 100 --no-pager"
echo "==========================================="