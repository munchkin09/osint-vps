from __future__ import annotations

import ipaddress
import logging
import socket
from dataclasses import dataclass
from typing import Any

from .config import Settings

LOG = logging.getLogger(__name__)


@dataclass
class Enricher:
    settings: Settings

    def enrich(self, event: dict[str, Any]) -> dict[str, Any]:
        src_ip = str(event.get("src_ip") or "")
        event["geo"] = self._geo(src_ip)
        event["asn"] = self._asn(src_ip)
        event["threat_intel"] = self._threat_intel(src_ip)
        event["risk_score"], event["tags"] = score_event(event)
        return event

    def _geo(self, ip: str) -> dict[str, Any]:
        if not _public_ip(ip):
            return {"source": "fallback", "is_public": False}
        if self.settings.geoip_db_path:
            try:
                import maxminddb

                with maxminddb.open_database(self.settings.geoip_db_path) as reader:
                    record = reader.get(ip) or {}
                country = record.get("country", {})
                city = record.get("city", {})
                return {
                    "source": "maxmind",
                    "is_public": True,
                    "country_code": country.get("iso_code"),
                    "country_name": country.get("names", {}).get("en"),
                    "city": city.get("names", {}).get("en"),
                }
            except Exception as exc:
                LOG.warning("GeoIP lookup failed for %s: %s", ip, exc)
        return {"source": "fallback", "is_public": True}

    def _asn(self, ip: str) -> dict[str, Any]:
        return {"source": "fallback", "number": None, "organization": None, "ip": ip}

    def _threat_intel(self, ip: str) -> dict[str, Any]:
        data: dict[str, Any] = {"providers": []}
        if not _public_ip(ip):
            return data

        if self.settings.abuseipdb_api_key:
            data["abuseipdb"] = self._abuseipdb(ip)
            data["providers"].append("abuseipdb")
        else:
            data["abuseipdb"] = {"enabled": False}

        if self.settings.otx_api_key:
            data["otx"] = self._otx(ip)
            data["providers"].append("otx")
        else:
            data["otx"] = {"enabled": False}

        data["reverse_dns"] = reverse_dns(ip, self.settings.dns_timeout_seconds)
        return data

    def _abuseipdb(self, ip: str) -> dict[str, Any]:
        try:
            import requests
        except ImportError:
            return {"error": "requests_not_installed"}

        url = "https://api.abuseipdb.com/api/v2/check"
        headers = {"Key": self.settings.abuseipdb_api_key, "Accept": "application/json"}
        params = {"ipAddress": ip, "maxAgeInDays": "90", "verbose": ""}
        try:
            response = requests.get(url, headers=headers, params=params, timeout=self.settings.osint_timeout_seconds)
            response.raise_for_status()
            payload = response.json().get("data", {})
            return {
                "abuse_confidence_score": payload.get("abuseConfidenceScore"),
                "total_reports": payload.get("totalReports"),
                "usage_type": payload.get("usageType"),
            }
        except requests.RequestException as exc:
            LOG.warning("AbuseIPDB lookup failed for %s: %s", ip, exc)
            return {"error": "lookup_failed"}

    def _otx(self, ip: str) -> dict[str, Any]:
        try:
            import requests
        except ImportError:
            return {"error": "requests_not_installed"}

        url = f"https://otx.alienvault.com/api/v1/indicators/IPv4/{ip}/general"
        headers = {"X-OTX-API-KEY": self.settings.otx_api_key}
        try:
            response = requests.get(url, headers=headers, timeout=self.settings.osint_timeout_seconds)
            response.raise_for_status()
            payload = response.json()
            pulse_info = payload.get("pulse_info", {})
            return {
                "pulse_count": pulse_info.get("count", 0),
                "reputation": payload.get("reputation"),
            }
        except requests.RequestException as exc:
            LOG.warning("OTX lookup failed for %s: %s", ip, exc)
            return {"error": "lookup_failed"}


def reverse_dns(ip: str, timeout: float) -> dict[str, Any]:
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return {"hostname": host}
    except (socket.herror, socket.gaierror, TimeoutError, OSError):
        return {}
    finally:
        socket.setdefaulttimeout(old_timeout)


def score_event(event: dict[str, Any]) -> tuple[int, list[str]]:
    score = int(event.get("risk_score") or 0)
    tags = list(dict.fromkeys(event.get("tags", [])))
    event_type = event.get("event_type")
    ti = event.get("threat_intel", {})

    if event_type == "login_attempt":
        score += 20
        tags.append("credential_activity")
    if event.get("password") in {"admin", "root", "password", "123456", "toor"}:
        score += 15
        tags.append("common_password")
    if "command_observed" in tags:
        score += 25
    abuse_score = ti.get("abuseipdb", {}).get("abuse_confidence_score")
    if isinstance(abuse_score, int):
        score += min(40, abuse_score // 2)
        if abuse_score >= 50:
            tags.append("reported_ip")
    pulse_count = ti.get("otx", {}).get("pulse_count")
    if isinstance(pulse_count, int) and pulse_count > 0:
        score += min(30, pulse_count * 5)
        tags.append("otx_pulse")

    return min(score, 100), sorted(set(tags))


def _public_ip(ip: str) -> bool:
    try:
        parsed = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return parsed.is_global
