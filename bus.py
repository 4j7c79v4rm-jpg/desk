"""Queues: scanner -> auditor -> analyst -> executor -> risk. Agents talk only through this."""

import asyncio
from typing import Any, Dict

class Bus:
    def __init__(self):
        self.scanner_to_auditor = asyncio.Queue()
        self.auditor_to_analyst = asyncio.Queue()
        self.analyst_to_executor = asyncio.Queue()
        self.executor_to_risk = asyncio.Queue()
        self.risk_out = asyncio.Queue()

    async def put(self, queue: asyncio.Queue, msg: Dict[str, Any]):
        await queue.put(msg)

    async def get(self, queue: asyncio.Queue) -> Dict[str, Any]:
        return await queue.get()
