# core/pubsub.py
"""
A minimal asyncio publish / subscribe hub
=========================================

•   topic strings are plain text, e.g. "stim.alarm" or "limbs.command".
•   wild-cards are allowed when *subscribing* (uses fnmatch: "stim.*").
•   every subscriber gets its own asyncio.Queue, so slow consumers
    do not block the rest of the system.
"""

from __future__ import annotations
import asyncio, fnmatch
from collections import defaultdict
from typing import Any, AsyncIterator, Dict, List


class Bus:
    """In-process fan-in / fan-out message hub."""

    def __init__(self) -> None:
        # map subscription pattern -> list of queues
        self._sub: Dict[str, List[asyncio.Queue]] = defaultdict(list)

    # --------------------------------------------------------------------- #
    #  Public API
    # --------------------------------------------------------------------- #

    async def publish(self, topic: str, payload: Any) -> None:
        """
        Fan the message out to every queue whose *pattern* matches *topic*.
        Non-blocking for the caller: we `put_nowait` and let queues fill
        (the consumer decides how big it wants the queue).
        """
        for pattern, queues in self._sub.items():
            if fnmatch.fnmatch(topic, pattern):
                for q in queues:
                    try:
                        q.put_nowait((topic, payload))
                    except asyncio.QueueFull:
                        # optional: drop oldest, log, etc.
                        pass

    async def subscribe(self, patterns: str | List[str],
                        maxsize: int = 0) -> AsyncIterator[tuple[str, Any]]:
        """
        Asynchronous iterator that yields (topic, payload) tuples
        for any published message whose topic matches *patterns*.

        Usage
        -----
        async for topic, payload in bus.subscribe(["stim.*", "mood.*"]):
            ...
        """
        if isinstance(patterns, str):
            patterns = [patterns]

        q: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        for p in patterns:
            self._sub[p].append(q)

        try:
            while True:
                yield await q.get()
        finally:
            # cleanup: remove the queue from all pattern lists
            for p in patterns:
                self._sub[p].remove(q)
