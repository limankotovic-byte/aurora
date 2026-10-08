import asyncio

import pytest

from app.services.cache import CacheService


def test_ttl_starts_after_load_and_returns_isolated_values() -> None:
    async def run() -> None:
        now = [0.0]
        calls = 0
        cache = CacheService(clock=lambda: now[0])

        async def load() -> list[int]:
            nonlocal calls
            calls += 1
            now[0] += 10
            return [calls]

        first = await cache.get("a", load, 5)
        first.append(99)
        now[0] = 14
        assert await cache.get("a", load, 5) == [1]
        now[0] = 15
        assert await cache.get("a", load, 5) == [2]
        await cache.close()

    asyncio.run(run())


def test_lru_is_bounded_and_hits_refresh_recency() -> None:
    async def run() -> None:
        cache = CacheService(max_entries=2)
        calls = 0

        async def load() -> int:
            nonlocal calls
            calls += 1
            return calls

        assert await cache.get("a", load, 60) == 1
        assert await cache.get("b", load, 60) == 2
        assert await cache.get("a", load, 60) == 1
        assert await cache.get("c", load, 60) == 3
        assert len(cache.entries) == 2
        assert await cache.get("b", load, 60) == 4
        await cache.close()

    asyncio.run(run())


def test_single_flight_survives_waiter_cancellation() -> None:
    async def run() -> None:
        cache = CacheService()
        started, release = asyncio.Event(), asyncio.Event()
        calls = 0

        async def load() -> str:
            nonlocal calls
            calls += 1
            started.set()
            await release.wait()
            return "ok"

        first = asyncio.create_task(cache.get("a", load, 60))
        await started.wait()
        second = asyncio.create_task(cache.get("a", load, 60))
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        release.set()
        assert await second == "ok"
        assert calls == 1
        await cache.close()

    asyncio.run(run())


def test_errors_are_not_cached() -> None:
    async def run() -> None:
        cache = CacheService()
        calls = 0

        async def load() -> str:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ValueError("upstream failure")
            return "recovered"

        with pytest.raises(ValueError):
            await cache.get("a", load, 60)
        assert await cache.get("a", load, 60) == "recovered"
        assert calls == 2
        await cache.close()

    asyncio.run(run())


def test_close_cancels_inflight_before_http_shutdown() -> None:
    async def run() -> None:
        cache = CacheService()
        started, cancelled = asyncio.Event(), asyncio.Event()

        async def load() -> None:
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        waiter = asyncio.create_task(cache.get("a", load, 60))
        await started.wait()
        await cache.close()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        assert cancelled.is_set() and not cache.entries and not cache.pending

    asyncio.run(run())
