"""Create a new Orchestrix API key.

Usage (inside container):
    python -m app.scripts.create_api_key [--name NAME]

Prints the raw key ONCE. Store it immediately — it cannot be recovered.
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from app.core.security import generate_api_key, hash_api_key
from app.db.models import ApiKey
from app.db.session import dispose_engine, get_sessionmaker


async def _create(name: str) -> str:
    raw = generate_api_key()
    digest = hash_api_key(raw)
    try:
        async with get_sessionmaker()() as session:
            session.add(ApiKey(name=name, key_hash=digest))
            await session.commit()
    finally:
        await dispose_engine()
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an Orchestrix API key.")
    parser.add_argument("--name", default="default", help="Human-readable label for the key.")
    args = parser.parse_args()

    raw = asyncio.run(_create(args.name))

    print()
    print("API key created.")
    print(f"  name: {args.name}")
    print(f"  key:  {raw}")
    print()
    print("Save this now — it will NOT be shown again.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
