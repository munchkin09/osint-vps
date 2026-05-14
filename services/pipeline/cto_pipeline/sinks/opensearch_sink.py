from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from cto_pipeline.config import Settings
from cto_pipeline.logging import configure_logging

LOG = logging.getLogger(__name__)
GROUP = "opensearch"
CONSUMER = "opensearch-sink-1"


def main() -> None:
    import redis
    from opensearchpy import OpenSearch

    from cto_pipeline.redis_io import decode_stream_event, redis_client

    settings = Settings()
    configure_logging(settings.log_level)
    redis_conn = redis_client(settings.redis_url)
    search = OpenSearch(
        hosts=[settings.opensearch_url],
        http_auth=(settings.opensearch_user, settings.opensearch_password),
        verify_certs=settings.opensearch_verify_certs,
        ssl_show_warn=False,
    )
    _ensure_group(redis_conn, settings.enriched_stream, GROUP)
    _install_template(search)
    LOG.info("persisting %s into OpenSearch prefix=%s", settings.enriched_stream, settings.opensearch_index_prefix)

    while True:
        entries = redis_conn.xreadgroup(
            GROUP,
            CONSUMER,
            {settings.enriched_stream: ">"},
            count=10,
            block=5000,
        )
        if not entries:
            continue
        for _, messages in entries:
            for message_id, fields in messages:
                try:
                    event = decode_stream_event(fields)
                    index = index_name(settings.opensearch_index_prefix, event["timestamp"])
                    search.index(index=index, id=event["event_id"], body=event, refresh=False)
                    redis_conn.xack(settings.enriched_stream, GROUP, message_id)
                    LOG.info("indexed event_id=%s index=%s", event.get("event_id"), index)
                except Exception:
                    LOG.exception("failed to index message_id=%s", message_id)
                    time.sleep(1)


def index_name(prefix: str, timestamp: str) -> str:
    date_part = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime("%Y.%m.%d")
    return f"{prefix}-{date_part}"


def _ensure_group(client: Any, stream: str, group: str) -> None:
    import redis

    try:
        client.xgroup_create(stream, group, id="0", mkstream=True)
    except redis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def _install_template(search: OpenSearch) -> None:
    template = {
        "index_patterns": ["cto-events-*"],
        "template": {
            "settings": {"number_of_shards": 1, "number_of_replicas": 0},
            "mappings": {
                "dynamic": True,
                "properties": {
                    "event_id": {"type": "keyword"},
                    "source": {"type": "keyword"},
                    "timestamp": {"type": "date"},
                    "src_ip": {"type": "ip"},
                    "dst_port": {"type": "integer"},
                    "event_type": {"type": "keyword"},
                    "risk_score": {"type": "integer"},
                    "tags": {"type": "keyword"},
                },
            },
        },
    }
    search.indices.put_index_template(name="cto-events-template", body=template)


if __name__ == "__main__":
    main()
