import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "pipeline"))

from cto_pipeline.config import Settings
from cto_pipeline.enrichment import Enricher, score_event
from cto_pipeline.normalizers import normalize_cowrie, normalize_opencanary
from cto_pipeline.schema import validate_event
from cto_pipeline.sinks.opensearch_sink import index_name


FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    print(f"[ok] {name}")


def main():
    cowrie = normalize_cowrie(load_fixture("cowrie_login_failed.json"))
    valid, error = validate_event(cowrie)
    check("cowrie event validates", valid and error is None)
    check("cowrie login type", cowrie["event_type"] == "login_attempt")
    check("cowrie credentials preserved", cowrie["username"] == "root" and cowrie["password"] == "admin")

    opencanary = normalize_opencanary(load_fixture("opencanary_http.json"))
    valid, error = validate_event(opencanary)
    check("opencanary event validates", valid and error is None)
    check("opencanary service probe", opencanary["event_type"] == "service_probe")
    check("opencanary http tag", "http" in opencanary["tags"])

    settings = Settings(abuseipdb_api_key="", otx_api_key="", geoip_db_path="")
    enriched = Enricher(settings).enrich(cowrie)
    check("enrichment without keys", enriched["threat_intel"]["abuseipdb"]["enabled"] is False)
    check("fallback risk score", enriched["risk_score"] >= 35)

    score, tags = score_event({
        "event_type": "login_attempt",
        "password": "admin",
        "tags": ["command_observed", "command_observed"],
        "threat_intel": {
            "abuseipdb": {"abuse_confidence_score": 100},
            "otx": {"pulse_count": 99},
        },
    })
    check("score capped", score == 100)
    check("tags unique", tags.count("command_observed") == 1)
    check("index name", index_name("cto-events", "2026-05-14T12:30:00Z") == "cto-events-2026.05.14")


if __name__ == "__main__":
    main()
