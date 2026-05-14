#!/usr/bin/env bash
set -euo pipefail

ADMIN_SSH_PORT="${ADMIN_SSH_PORT:-2222}"
ADMIN_USER="${ADMIN_USER:-cto-admin}"
SSH_CONFIG="/etc/ssh/sshd_config.d/99-cto-hardening.conf"
SYSCTL_CONFIG="/etc/sysctl.d/99-cto-hardening.conf"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo ADMIN_USER=${ADMIN_USER} ADMIN_SSH_PORT=${ADMIN_SSH_PORT} bash scripts/harden_ubuntu.sh" >&2
  exit 1
fi

echo "[cto] Installing baseline packages"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  auditd \
  ca-certificates \
  curl \
  fail2ban \
  ufw \
  unattended-upgrades

if ! id "${ADMIN_USER}" >/dev/null 2>&1; then
  echo "[cto] Creating non-root admin user: ${ADMIN_USER}"
  adduser --disabled-password --gecos "" "${ADMIN_USER}"
  usermod -aG sudo "${ADMIN_USER}"
else
  echo "[cto] Admin user already exists: ${ADMIN_USER}"
fi

if [[ ! -d "/home/${ADMIN_USER}/.ssh" ]]; then
  mkdir -p "/home/${ADMIN_USER}/.ssh"
  chmod 700 "/home/${ADMIN_USER}/.ssh"
  chown -R "${ADMIN_USER}:${ADMIN_USER}" "/home/${ADMIN_USER}/.ssh"
fi

echo "[cto] Writing SSH hardening config to ${SSH_CONFIG}"
cat > "${SSH_CONFIG}" <<EOF
Port ${ADMIN_SSH_PORT}
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PubkeyAuthentication yes
X11Forwarding no
AllowTcpForwarding no
ClientAliveInterval 300
ClientAliveCountMax 2
EOF

echo "[cto] Validating SSH config"
sshd -t

echo "[cto] Configuring UFW"
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow "${ADMIN_SSH_PORT}/tcp" comment "administrative SSH"
ufw allow 22/tcp comment "Cowrie SSH honeypot"
ufw allow 21/tcp comment "OpenCanary FTP honeypot"
ufw allow 80/tcp comment "OpenCanary HTTP honeypot"
ufw allow 2323/tcp comment "Cowrie Telnet honeypot"
ufw allow 3306/tcp comment "OpenCanary MySQL honeypot"
ufw allow 6379/tcp comment "OpenCanary Redis honeypot"
ufw --force enable

echo "[cto] Configuring Fail2Ban for administrative SSH"
cat > /etc/fail2ban/jail.d/cto-sshd.conf <<EOF
[sshd]
enabled = true
port = ${ADMIN_SSH_PORT}
maxretry = 5
findtime = 10m
bantime = 1h
EOF

echo "[cto] Configuring sysctl hardening"
cat > "${SYSCTL_CONFIG}" <<'EOF'
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.tcp_syncookies = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
kernel.randomize_va_space = 2
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
EOF
sysctl --system

echo "[cto] Enabling unattended upgrades"
dpkg-reconfigure -f noninteractive unattended-upgrades
systemctl enable --now auditd fail2ban unattended-upgrades

echo "[cto] Restarting SSH service"
systemctl restart ssh || systemctl restart sshd

echo "[cto] Hardening complete. Test a new SSH session on port ${ADMIN_SSH_PORT} before closing your current session."
