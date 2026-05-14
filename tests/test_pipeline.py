import json
from pathlib import Path

from cto_pipeline.config import Settings
from cto_pipeline.enrichment import Enricher, score_event
from cto_pipeline.normalizers import normalize_cowrie, normalize_opencanary
from cto_pipeline.schema import validate_event
from cto_pipeline.sinks.opensearch_sink import index_name


FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_cowrie_login_normalization_contract():
    event = normalize_cowrie(load_fixture("cowrie_login_failed.json"))

    valid, error = validate_event(event)
    assert valid, error
    assert event["schema_version"] == "1.0"
    assert event["source"] == "cowrie"
    assert event["event_type"] == "login_attempt"
    assert event["dst_port"] == 22
    assert event["username"] == "root"
    assert event["password"] == "admin"
    assert "auth_failed" in event["tags"]


def test_opencanary_service_probe_normalization_contract():
    event = normalize_opencanary(load_fixture("opencanary_http.json"))

    valid, error = validate_event(event)
    assert valid, error
    assert event["source"] == "opencanary"
    assert event["event_type"] == "service_probe"
    assert event["src_ip"] == "198.51.100.20"
    assert event["dst_port"] == 80
    assert "http" in event["tags"]


def test_enrichment_works_without_osint_keys():
    settings = Settings(abuseipdb_api_key="", otx_api_key="", geoip_db_path="")
    event = normalize_cowrie(load_fixture("cowrie_login_failed.json"))

    enriched = Enricher(settings).enrich(event)

    valid, error = validate_event(enriched)
    assert valid, error
    assert enriched["geo"]["source"] == "fallback"
    assert enriched["threat_intel"]["abuseipdb"]["enabled"] is False
    assert enriched["threat_intel"]["otx"]["enabled"] is False
    assert enriched["risk_score"] >= 35
    assert "credential_activity" in enriched["tags"]
    assert "common_password" in enriched["tags"]


def test_score_caps_at_100_and_keeps_tags_unique():
    event = {
        "event_type": "login_attempt",
        "password": "admin",
        "tags": ["command_observed", "command_observed"],
        "threat_intel": {
            "abuseipdb": {"abuse_confidence_score": 100},
            "otx": {"pulse_count": 99},
        },
    }

    score, tags = score_event(event)

    assert score == 100
    assert tags.count("command_observed") == 1
    assert "reported_ip" in tags
    assert "otx_pulse" in tags


def test_opensearch_daily_index_name():
    assert index_name("cto-events", "2026-05-14T12:30:00Z") == "cto-events-2026.05.14"
