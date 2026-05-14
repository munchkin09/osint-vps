from __future__ import annotations

from typing import Any

from .schema import base_event


COWRIE_EVENT_TYPES = {
    "cowrie.login.success": "login_attempt",
    "cowrie.login.failed": "login_attempt",
    "cowrie.command.input": "command",
    "cowrie.session.connect": "connection",
    "cowrie.session.closed": "connection",
    "cowrie.client.version": "service_probe",
}


def normalize_cowrie(raw: dict[str, Any]) -> dict[str, Any]:
    event = base_event("cowrie", raw)
    eventid = str(raw.get("eventid", ""))
    event["event_type"] = COWRIE_EVENT_TYPES.get(eventid, "connection")
    event["dst_port"] = int(raw.get("dst_port") or raw.get("dest_port") or 22)
    event["username"] = raw.get("username")
    event["password"] = raw.get("password")

    if eventid.endswith(".failed"):
        event["tags"].append("auth_failed")
    if eventid.endswith(".success"):
        event["tags"].append("auth_success")
    if raw.get("input"):
        event["tags"].append("command_observed")
    return event


def normalize_opencanary(raw: dict[str, Any]) -> dict[str, Any]:
    event = base_event("opencanary", raw)
    logtype = int(raw.get("logtype", 0) or 0)
    event["src_ip"] = raw.get("src_host") or raw.get("src_ip") or raw.get("remote_host")
    event["dst_port"] = _int_or_none(raw.get("dst_port") or raw.get("local_port"))
    event["event_type"] = "service_probe"
    event["username"] = raw.get("logdata", {}).get("USERNAME") if isinstance(raw.get("logdata"), dict) else None
    event["password"] = raw.get("logdata", {}).get("PASSWORD") if isinstance(raw.get("logdata"), dict) else None

    service = raw.get("logtype_name") or raw.get("service") or _opencanary_service(logtype)
    if service:
        event["tags"].append(str(service).lower())
    return event


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _opencanary_service(logtype: int) -> str | None:
    services = {
        2000: "ftp",
        3000: "http",
        5001: "mysql",
        6001: "redis",
    }
    return services.get(logtype)
