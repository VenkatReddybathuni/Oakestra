#!/usr/bin/env bash
set -euo pipefail

# ======= CONFIG (edit or override via flags) =======
HOST_PUBLIC_IP="128.105.145.242"     # Public IP on the host that should receive traffic
VM_IP="192.168.122.49"               # VM (guest) IP (e.g., on default libvirt NAT)
HOST_PORT="8080"                     # Port on the host/public IP to receive traffic
VM_PORT="8080"                       # Destination port on the VM
PROTO="tcp"                          # tcp|udp
PERSIST_SYSCTL="false"               # true|false — write /etc/sysctl.d/99-portfwd.conf
# ===================================================

usage() {
  cat <<USAGE
Usage: $0 [add|delete|status] [--host-ip IP] [--vm-ip IP] [--host-port N] [--vm-port N] [--proto tcp|udp] [--persist-sysctl true|false]

Examples:
  sudo $0 add --host-ip 128.105.145.242 --host-port 8080 --vm-ip 192.168.122.49 --vm-port 8080
  sudo $0 delete --host-ip 128.105.145.242 --host-port 8080 --vm-ip 192.168.122.49 --vm-port 8080
  sudo $0 status
USAGE
}

require() { command -v "$1" >/dev/null 2>&1 || { echo "Missing: $1"; exit 1; }; }

# Parse args
ACTION="${1:-}"; shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --host-ip)        HOST_PUBLIC_IP="$2"; shift 2;;
    --vm-ip)          VM_IP="$2"; shift 2;;
    --host-port)      HOST_PORT="$2"; shift 2;;
    --vm-port)        VM_PORT="$2"; shift 2;;
    --proto)          PROTO="$2"; shift 2;;
    --persist-sysctl) PERSIST_SYSCTL="$2"; shift 2;;
    -h|--help)        usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

if [[ -z "${ACTION:-}" ]]; then usage; exit 1; fi

require iptables
require sysctl

enable_ip_forward() {
  echo "[*] Enabling IPv4 forwarding (runtime)…"
  sysctl -w net.ipv4.ip_forward=1 >/dev/null

  if [[ "$PERSIST_SYSCTL" == "true" ]]; then
    echo "[*] Persisting IPv4 forwarding to /etc/sysctl.d/99-portfwd.conf"
    echo "net.ipv4.ip_forward = 1" | sudo tee /etc/sysctl.d/99-portfwd.conf >/dev/null
    sysctl --system >/dev/null
  fi
}

ipt_has() {
  # iptables -C returns 0 if rule exists
  if iptables -C "$@"; then return 0; else return 1; fi
}

ipt_add_once() {
  if ! ipt_has "$@"; then iptables -I "$@"; fi
}

ipt_nat_add_once() {
  # For nat table we maintain order with -A (append), but still avoid dupes
  if ! ipt_has -t nat "$@"; then iptables -t nat -A "$@"; fi
}

ipt_delete_if() {
  while ipt_has "$@"; do iptables -D "$@"; done
}

add_rules() {
  echo "[*] Adding DNAT/SNAT/forward rules for $PROTO $HOST_PUBLIC_IP:$HOST_PORT -> $VM_IP:$VM_PORT"

  enable_ip_forward

  # Allow FORWARD to the VM:PORT (ingress path)
  ipt_add_once FORWARD -p "$PROTO" -d "$VM_IP" --dport "$VM_PORT" -j ACCEPT
  # Allow established return traffic (usually already present, but ensure)
  ipt_add_once FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

  # DNAT: send traffic arriving at host public IP:HOST_PORT to VM_IP:VM_PORT
  ipt_nat_add_once PREROUTING -p "$PROTO" -d "$HOST_PUBLIC_IP" --dport "$HOST_PORT" \
    -j DNAT --to-destination "${VM_IP}:${VM_PORT}"

  # SNAT/MASQUERADE the return path so replies go back via the host
  ipt_nat_add_once POSTROUTING -p "$PROTO" -d "$VM_IP" --dport "$VM_PORT" -j MASQUERADE

  echo "[*] Done. Use '$0 status' to review current rules."
}

delete_rules() {
  echo "[*] Deleting rules for $PROTO $HOST_PUBLIC_IP:$HOST_PORT -> $VM_IP:$VM_PORT"

  # Delete nat rules
  ipt_delete_if -t nat PREROUTING -p "$PROTO" -d "$HOST_PUBLIC_IP" --dport "$HOST_PORT" \
    -j DNAT --to-destination "${VM_IP}:${VM_PORT}"
  ipt_delete_if -t nat POSTROUTING -p "$PROTO" -d "$VM_IP" --dport "$VM_PORT" -j MASQUERADE

  # Delete forward rules
  ipt_delete_if FORWARD -p "$PROTO" -d "$VM_IP" --dport "$VM_PORT" -j ACCEPT
  ipt_delete_if FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

  echo "[*] Done."
}

status_rules() {
  echo "=== SYSCTL ==="
  sysctl net.ipv4.ip_forward
  echo
  echo "=== FILTER TABLE (FORWARD) ==="
  iptables -S FORWARD | sed 's/^/- /'
  echo
  echo "=== NAT TABLE (PREROUTING/POSTROUTING) ==="
  echo "[PREROUTING]"
  iptables -t nat -S PREROUTING | sed 's/^/- /'
  echo "[POSTROUTING]"
  iptables -t nat -S POSTROUTING | sed 's/^/- /'
}

case "$ACTION" in
  add) add_rules ;;
  delete) delete_rules ;;
  status) status_rules ;;
  *) usage; exit 1 ;;
esac

# --- USAGE ---
# chmod +x port_forward.sh
# sudo ./port_forward.sh add --host-ip 128.105.145.203 --host-port 8080 --vm-ip 192.168.122.106 --vm-port 8080 --proto tcp --persist-sysctl true
