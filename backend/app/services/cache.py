import asyncio
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from copy import deepcopy
from time import monotonic
from typing import cast


class CacheService:
    """Bounded per-process TTL/LRU cache with cancellation-safe single flight."""

    def __init__(self, max_entries: int = 128, clock: Callable[[], float] = monotonic) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self.max_entries = max_entries
        self.clock = clock
        self.entries: OrderedDict[str, tuple[float, object]] = OrderedDict()
        self.pending: dict[str, asyncio.Task[object]] = {}

    async def get[T](self, key: str, loader: Callable[[], Awaitable[T]], ttl: float) -> T:
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        now = self.clock()
        for expired in [k for k, (until, _) in self.entries.items() if until <= now]:
            del self.entries[expired]
        if key in self.entries:
            self.entries.move_to_end(key)
            return deepcopy(cast(T, self.entries[key][1]))

        async def load() -> object:
            value = await loader()
            self.entries[key] = (self.clock() + ttl, deepcopy(value))
            self.entries.move_to_end(key)
            while len(self.entries) > self.max_entries:
                self.entries.popitem(last=False)
            return value

        def completed(task: asyncio.Task[object]) -> None:
            self.pending.pop(key, None)
            if not task.cancelled():
                task.exception()  # Retrieve failures even if every waiter cancelled.

        if key not in self.pending:
            task = asyncio.create_task(load())
            self.pending[key] = task
            task.add_done_callback(completed)
        return deepcopy(cast(T, await asyncio.shield(self.pending[key])))

    async def close(self) -> None:
        tasks = list(self.pending.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.pending.clear()
        self.entries.clear()
