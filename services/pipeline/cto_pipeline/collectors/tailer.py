from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from cto_pipeline.redis_io import publish_event
from cto_pipeline.schema import validate_event

LOG = logging.getLogger(__name__)


def follow_json_lines(path: Path, poll_seconds: float = 1.0) -> Iterator[dict[str, Any]]:
    handle = None
    while True:
        if handle is None:
            if not path.exists():
                LOG.info("waiting for log file %s", path)
                time.sleep(poll_seconds)
                continue
            handle = path.open("r", encoding="utf-8")
            handle.seek(0, 2)

        line = handle.readline()
        if not line:
            time.sleep(poll_seconds)
            continue
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            LOG.warning("skipping malformed json line from %s", path)


def collect_forever(path: Path, normalizer: Callable[[dict[str, Any]], dict[str, Any]], redis_client, stream: str) -> None:
    LOG.info("tailing %s into Redis stream %s", path, stream)
    for raw in follow_json_lines(path):
        event = normalizer(raw)
        valid, error = validate_event(event)
        if not valid:
            LOG.warning("dropping invalid event from %s: %s", path, error)
            continue
        message_id = publish_event(redis_client, stream, event)
        LOG.info("published %s event_id=%s message_id=%s", event["source"], event["event_id"], message_id)
