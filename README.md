# Cyber Threat Observatory MVP

Defensive, educational threat-observatory stack for a single Ubuntu VPS.

This MVP captures honeypot activity, normalizes it into Redis Streams, enriches it with local and optional OSINT data, and stores enriched events in OpenSearch.

## What Is Included

- VPS hardening scripts and non-destructive validation checks.
- Docker Compose stack with segmented networks.
- Cowrie SSH/Telnet honeypot exposed on port `22`.
- OpenCanary with HTTP, FTP, Redis, and MySQL decoy services.
- Redis Streams event pipeline.
- Python collectors and workers.
- OpenSearch storage using daily `cto-events-*` indices.
- Optional AbuseIPDB and AlienVault OTX enrichment.
- Local/offline fallback enrichment so the stack still works without API keys.

## Repository Layout

```text
.
├── docker-compose.yml
├── .env.example
├── configs/
│   ├── cowrie/
│   ├── opencanary/
│   ├── opensearch/
│   └── logrotate/
├── scripts/
│   ├── harden_ubuntu.sh
│   └── validate_hardening.sh
├── services/
│   └── pipeline/
├── tests/
└── docs/
```

## Quick Start

1. Copy the environment template:

```bash
cp .env.example .env
```

2. Edit `.env`, especially:

```bash
ADMIN_SSH_PORT=2222
OPENSEARCH_INITIAL_ADMIN_PASSWORD=change-me-to-a-long-random-password
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=change-me-to-a-long-random-password
```

3. On a fresh Ubuntu VPS, run hardening first from a console session or a second SSH session:

```bash
sudo bash scripts/harden_ubuntu.sh
sudo bash scripts/validate_hardening.sh
```

4. Start the observatory:

```bash
docker compose up -d --build
```

5. Follow pipeline logs:

```bash
docker compose logs -f cowrie-collector opencanary-collector enrichment-worker opensearch-sink
```

## Event Flow

```text
Cowrie/OpenCanary logs
        |
collectors
        |
Redis Stream: events:raw
        |
enrichment-worker
        |
Redis Stream: events:enriched
        |
opensearch-sink
        |
OpenSearch index: cto-events-YYYY.MM.DD
```

## Safety Boundaries

This project is defensive-only. It observes traffic that reaches your VPS, normalizes and enriches events, and stores them for learning and analysis. It does not scan third parties, exploit systems, pivot, weaponize payloads, or execute malware.

## Documentation

- [Deployment guide](docs/deployment.md)
- [Operations runbook](docs/runbook.md)
- [Event schema](docs/event_schema.md)
