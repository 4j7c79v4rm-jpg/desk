"""Scanner agent stub. Talks only through bus.py and db."""
import asyncio

async def run(bus, db_conn, settings):
    while True:
        await asyncio.sleep(30)
