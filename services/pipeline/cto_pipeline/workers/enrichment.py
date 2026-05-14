from __future__ import annotations

import logging
import time

import redis

from cto_pipeline.config import Settings
from cto_pipeline.enrichment import Enricher
from cto_pipeline.logging import configure_logging
from cto_pipeline.redis_io import decode_stream_event, publish_event, redis_client

LOG = logging.getLogger(__name__)
GROUP = "enrichment"
CONSUMER = "enrichment-worker-1"


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_level)
    client = redis_client(settings.redis_url)
    _ensure_group(client, settings.raw_stream, GROUP)
    enricher = Enricher(settings)
    LOG.info("consuming %s as group=%s consumer=%s", settings.raw_stream, GROUP, CONSUMER)

    while True:
        entries = client.xreadgroup(
            GROUP,
            CONSUMER,
            {settings.raw_stream: ">"},
            count=10,
            block=5000,
        )
        if not entries:
            continue
        for _, messages in entries:
            for message_id, fields in messages:
                try:
                    event = decode_stream_event(fields)
                    enriched = enricher.enrich(event)
                    publish_event(client, settings.enriched_stream, enriched)
                    client.xack(settings.raw_stream, GROUP, message_id)
                    LOG.info("enriched event_id=%s message_id=%s", enriched.get("event_id"), message_id)
                except Exception:
                    LOG.exception("failed to enrich message_id=%s", message_id)
                    time.sleep(1)


def _ensure_group(client: redis.Redis, stream: str, group: str) -> None:
    try:
        client.xgroup_create(stream, group, id="0", mkstream=True)
    except redis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


if __name__ == "__main__":
    main()
