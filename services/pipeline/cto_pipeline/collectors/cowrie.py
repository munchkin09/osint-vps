from __future__ import annotations

import argparse
import os
from pathlib import Path

from cto_pipeline.config import Settings
from cto_pipeline.collectors.tailer import collect_forever
from cto_pipeline.logging import configure_logging
from cto_pipeline.normalizers import normalize_cowrie
from cto_pipeline.redis_io import redis_client


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_level)
    parser = argparse.ArgumentParser(description="Tail Cowrie JSON logs into Redis Streams.")
    parser.add_argument("--path", default=os.getenv("COWRIE_LOG_PATH", "/cowrie-var/log/cowrie/cowrie.json"))
    args = parser.parse_args()

    client = redis_client(settings.redis_url)
    collect_forever(Path(args.path), normalize_cowrie, client, settings.raw_stream)


if __name__ == "__main__":
    main()
