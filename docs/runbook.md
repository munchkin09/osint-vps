# Operations Runbook

## Daily Checks

```bash
docker compose ps
docker compose logs --since 24h enrichment-worker opensearch-sink
docker system df
```

## Check Pipeline Lag

```bash
docker compose exec redis redis-cli XINFO STREAM events:raw
docker compose exec redis redis-cli XINFO GROUPS events:raw
docker compose exec redis redis-cli XINFO GROUPS events:enriched
```

## Restart One Worker

```bash
docker compose restart enrichment-worker
```

## Rotate or Inspect Honeypot Logs

Cowrie logs are stored in the `cowrie-var` Docker volume. OpenCanary logs are stored in `opencanary-logs`.

```bash
docker compose logs cowrie
docker compose logs opencanary
```

## Common Failure Modes

- No events in Redis: confirm honeypot containers are running and logs exist.
- Events in `events:raw` but not `events:enriched`: inspect `enrichment-worker` logs.
- Events in `events:enriched` but not OpenSearch: inspect `opensearch-sink` and OpenSearch health.
- OpenSearch unhealthy: verify memory availability and `OPENSEARCH_INITIAL_ADMIN_PASSWORD`.

## Security Boundaries

- Do not scan third parties from this VPS.
- Do not replay attacker payloads outside an isolated sandbox.
- Do not expose Redis or OpenSearch to the public internet.
- Keep administrative SSH on the high port and Cowrie on port `22`.
