"""Keeps the local pgserver-managed PostgreSQL instance running.

Used only for local/sandbox development (in Docker, a real postgres container
is used instead). Run:  python scripts/dev_postgres_keeper.py
"""

from __future__ import annotations

import os
import sys
import time

PGDATA = os.environ.get("AITZAZ_PGDATA", "/home/user/.aitzaz-services/pgdata")


def main() -> int:
    import pgserver

    server = pgserver.get_server(PGDATA)
    print("[postgres-keeper] URI:", server.get_uri(), flush=True)
    print("[postgres-keeper] PostgreSQL is up. Keeping alive…", flush=True)
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
