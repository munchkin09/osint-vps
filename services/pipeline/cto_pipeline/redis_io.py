from __future__ import annotations

import json
from typing import Any

import redis


def redis_client(redis_url: str) -> redis.Redis:
    return redis.Redis.from_url(redis_url, decode_responses=True)


def publish_event(client: redis.Redis, stream: str, event: dict[str, Any]) -> str:
    return client.xadd(stream, {"event": json.dumps(event, sort_keys=True)}, maxlen=100000, approximate=True)


def decode_stream_event(fields: dict[str, str]) -> dict[str, Any]:
    payload = fields.get("event")
    if not payload:
        raise ValueError("stream entry does not contain event field")
    return json.loads(payload)
