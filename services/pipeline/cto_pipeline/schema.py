from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any


SCHEMA_VERSION = "1.0"


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def normalize_timestamp(value: Any) -> str:
    if not value:
        return utc_now()
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, UTC).isoformat().replace("+00:00", "Z")
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).astimezone(UTC).isoformat().replace("+00:00", "Z")
    except ValueError:
        return utc_now()


def stable_event_id(source: str, raw: dict[str, Any]) -> str:
    eventid = raw.get("eventid") or raw.get("logtype") or raw.get("id")
    timestamp = raw.get("timestamp") or raw.get("local_time") or raw.get("utc_time")
    src_ip = raw.get("src_ip") or raw.get("src_host") or raw.get("dst_host")
    material = json.dumps(
        {"source": source, "eventid": eventid, "timestamp": timestamp, "src_ip": src_ip, "raw": raw},
        sort_keys=True,
        default=str,
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return str(uuid.UUID(digest[:32]))


def base_event(source: str, raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": stable_event_id(source, raw),
        "source": source,
        "timestamp": normalize_timestamp(raw.get("timestamp") or raw.get("local_time") or raw.get("utc_time")),
        "src_ip": raw.get("src_ip") or raw.get("src_host") or raw.get("remote_host"),
        "dst_port": None,
        "event_type": "connection",
        "username": None,
        "password": None,
        "raw": raw,
        "geo": {},
        "asn": {},
        "threat_intel": {},
        "risk_score": 0,
        "tags": [],
    }


def validate_event(event: dict[str, Any]) -> tuple[bool, str | None]:
    required = ["schema_version", "event_id", "source", "timestamp", "src_ip", "event_type"]
    for key in required:
        if not event.get(key):
            return False, f"missing required field: {key}"
    if not isinstance(event.get("tags"), list):
        return False, "tags must be a list"
    return True, None
