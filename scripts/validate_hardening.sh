#!/usr/bin/env bash
set -euo pipefail

ADMIN_SSH_PORT="${ADMIN_SSH_PORT:-2222}"
SSH_CONFIG="/etc/ssh/sshd_config.d/99-cto-hardening.conf"

failures=0

check() {
  local name="$1"
  shift
  if "$@"; then
    echo "[ok] ${name}"
  else
    echo "[fail] ${name}"
    failures=$((failures + 1))
  fi
}

check "SSH hardening config exists" test -f "${SSH_CONFIG}"
check "SSH password auth disabled" grep -qi '^PasswordAuthentication no' "${SSH_CONFIG}"
check "SSH root login disabled" grep -qi '^PermitRootLogin no' "${SSH_CONFIG}"
check "SSH admin port configured" grep -qi "^Port ${ADMIN_SSH_PORT}$" "${SSH_CONFIG}"
check "UFW active" bash -c "ufw status | grep -qi 'Status: active'"
check "UFW allows admin SSH" bash -c "ufw status | grep -q '${ADMIN_SSH_PORT}/tcp'"
check "Fail2Ban service active" systemctl is-active --quiet fail2ban
check "auditd service active" systemctl is-active --quiet auditd
check "unattended-upgrades active" systemctl is-active --quiet unattended-upgrades
check "sysctl tcp syncookies enabled" test "$(sysctl -n net.ipv4.tcp_syncookies)" = "1"

if [[ "${failures}" -gt 0 ]]; then
  echo "[cto] ${failures} hardening check(s) failed"
  exit 1
fi

echo "[cto] Hardening checks passed"
