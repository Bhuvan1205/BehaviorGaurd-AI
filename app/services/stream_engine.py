"""
stream_engine.py — In-process SSE event bus for BehaviorGuard-AI real-time streaming.

Usage
-----
Publishing (from any route or background task):
    from app.services.stream_engine import stream_engine
    await stream_engine.publish(event_dict)

Subscribing (SSE endpoint):
    async for chunk in stream_engine.subscribe():
        yield chunk

Thread-safety: publish() is called from sync FastAPI routes via
asyncio.run_coroutine_threadsafe so it is safe even when uvicorn
is running synchronous route handlers.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


class StreamEngine:
    """
    Lightweight in-process pub/sub bus.

    Each connected SSE client registers an asyncio.Queue.
    When publish() is called the event dict is placed on every queue.
    Clients read from their queue inside an async generator and
    the generator is closed when the client disconnects.
    """

    def __init__(self) -> None:
        self._queues: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()
        self._event_count: int = 0
        self._scenario: str = "normal"
        self._replay_running: bool = False

    # ------------------------------------------------------------------
    # Scenario / status management (used by replay engine & UI)
    # ------------------------------------------------------------------

    def set_scenario(self, scenario: str) -> None:
        """Set the active scenario for the replay engine."""
        self._scenario = scenario
        logger.info("Stream scenario changed to: %s", scenario)

    def get_scenario(self) -> str:
        return self._scenario

    def set_replay_running(self, running: bool) -> None:
        self._replay_running = running

    def get_status(self) -> dict:
        return {
            "replay_running": self._replay_running,
            "scenario": self._scenario,
            "connected_clients": len(self._queues),
            "events_published": self._event_count,
        }

    # ------------------------------------------------------------------
    # Pub/Sub core
    # ------------------------------------------------------------------

    async def publish(self, event: dict) -> None:
        """Broadcast a scored event to every connected SSE client."""
        self._event_count += 1
        # Stamp with server time if not already present
        if "server_ts" not in event:
            event["server_ts"] = datetime.utcnow().isoformat() + "Z"

        payload = json.dumps(event, default=str)
        dead: list[asyncio.Queue] = []

        async with self._lock:
            for q in self._queues:
                try:
                    q.put_nowait(payload)
                except asyncio.QueueFull:
                    # Slow client — mark for removal
                    dead.append(q)

            for q in dead:
                self._queues.remove(q)
                logger.warning("Dropped slow SSE client (queue full)")

    def publish_sync(self, event: dict) -> None:
        """
        Thread-safe wrapper for publishing from synchronous code.
        Falls back to a fresh event loop if none is running (e.g. scripts).
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self.publish(event), loop)
            else:
                loop.run_until_complete(self.publish(event))
        except RuntimeError:
            # No event loop in this thread — best-effort fire-and-forget
            asyncio.run(self.publish(event))

    async def subscribe(self) -> AsyncGenerator[str, None]:
        """
        Async generator yielding SSE-formatted strings.
        Each yielded value is a complete ``data: ...\\n\\n`` SSE frame.
        The generator runs until the client disconnects (GeneratorExit).
        """
        q: asyncio.Queue = asyncio.Queue(maxsize=200)

        async with self._lock:
            self._queues.append(q)

        logger.info(
            "SSE client connected. Total clients: %d", len(self._queues)
        )

        try:
            # Send a heartbeat immediately so the browser knows we're alive
            yield "data: {\"type\":\"connected\"}\n\n"

            while True:
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=20.0)
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    # Send keep-alive comment to prevent browser timeout
                    yield ": heartbeat\n\n"

        except (GeneratorExit, asyncio.CancelledError):
            pass
        finally:
            async with self._lock:
                try:
                    self._queues.remove(q)
                except ValueError:
                    pass
            logger.info(
                "SSE client disconnected. Total clients: %d", len(self._queues)
            )


# Global singleton — import this everywhere
stream_engine = StreamEngine()
