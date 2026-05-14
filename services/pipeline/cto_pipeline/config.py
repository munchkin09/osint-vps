from __future__ import annotations

import os
from dataclasses import dataclass


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    raw_stream: str = os.getenv("RAW_STREAM", "events:raw")
    enriched_stream: str = os.getenv("ENRICHED_STREAM", "events:enriched")
    opensearch_url: str = os.getenv("OPENSEARCH_URL", "https://localhost:9200")
    opensearch_user: str = os.getenv("OPENSEARCH_USER", "admin")
    opensearch_password: str = os.getenv("OPENSEARCH_PASSWORD", "admin")
    opensearch_verify_certs: bool = _bool("OPENSEARCH_VERIFY_CERTS", False)
    opensearch_index_prefix: str = os.getenv("OPENSEARCH_INDEX_PREFIX", "cto-events")
    abuseipdb_api_key: str = os.getenv("ABUSEIPDB_API_KEY", "")
    otx_api_key: str = os.getenv("OTX_API_KEY", "")
    geoip_db_path: str = os.getenv("GEOIP_DB_PATH", "")
    dns_timeout_seconds: float = float(os.getenv("DNS_TIMEOUT_SECONDS", "1.5"))
    whois_enabled: bool = _bool("WHOIS_ENABLED", False)
    osint_timeout_seconds: float = float(os.getenv("OSINT_TIMEOUT_SECONDS", "3"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
