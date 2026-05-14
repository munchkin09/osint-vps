# Event Schema

Version: `1.0`

```json
{
  "schema_version": "1.0",
  "event_id": "uuid",
  "source": "cowrie|opencanary",
  "timestamp": "ISO-8601 UTC",
  "src_ip": "string",
  "dst_port": 22,
  "event_type": "login_attempt|connection|command|service_probe",
  "username": "string|null",
  "password": "string|null",
  "raw": {},
  "geo": {},
  "asn": {},
  "threat_intel": {},
  "risk_score": 0,
  "tags": []
}
```

## Streams

- Raw events: `events:raw`
- Enriched events: `events:enriched`

## Index Naming

Enriched events are written to daily OpenSearch indices:

```text
cto-events-YYYY.MM.DD
```

## Risk Score

The MVP scoring is intentionally simple and explainable:

- login attempt: +20
- common password: +15
- observed command: +25
- AbuseIPDB reputation: up to +40
- OTX pulse match: up to +30

Scores are capped at `100`.
