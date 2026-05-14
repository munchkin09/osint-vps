# Deployment Guide

Target: one Ubuntu 24.04 VPS.

## 1. Prepare DNS and Access

- Keep provider console access available.
- Add your SSH public key to the initial root or provider user.
- Decide the administrative SSH port. The default is `2222`.

## 2. Harden the VPS

Run this from the repository on the VPS:

```bash
sudo ADMIN_USER=cto-admin ADMIN_SSH_PORT=2222 bash scripts/harden_ubuntu.sh
sudo ADMIN_SSH_PORT=2222 bash scripts/validate_hardening.sh
```

Open a second terminal and confirm you can log in:

```bash
ssh -p 2222 cto-admin@your-vps-ip
```

Do not close the original session until the new SSH session works.

## 3. Install Docker

```bash
sudo bash scripts/install_docker_ubuntu.sh
```

Log out and back in if your user was added to the Docker group.

## 4. Configure Environment

```bash
cp .env.example .env
openssl rand -base64 32
```

Put the generated value in both:

```bash
OPENSEARCH_INITIAL_ADMIN_PASSWORD=
OPENSEARCH_PASSWORD=
```

External OSINT keys are optional:

```bash
ABUSEIPDB_API_KEY=
OTX_API_KEY=
```

## 5. Start the Stack

```bash
docker compose up -d --build
docker compose ps
```

Expected long-running services:

- `redis`
- `opensearch`
- `cowrie`
- `opencanary`
- `cowrie-collector`
- `opencanary-collector`
- `enrichment-worker`
- `opensearch-sink`

## 6. Verify Event Flow

From a separate machine, make a harmless connection to the VPS:

```bash
ssh root@your-vps-ip
curl http://your-vps-ip/
```

Then inspect logs:

```bash
docker compose logs -f cowrie-collector enrichment-worker opensearch-sink
```

Check Redis stream lengths:

```bash
docker compose exec redis redis-cli XLEN events:raw
docker compose exec redis redis-cli XLEN events:enriched
```

## 7. Query OpenSearch

```bash
curl -k -u admin:YOUR_PASSWORD https://localhost:9200/cto-events-*/_search?pretty
```

OpenSearch is not exposed publicly by default. Keep it that way unless you place it behind authentication, TLS, and firewall restrictions.
