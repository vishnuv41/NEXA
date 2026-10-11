import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional, List
from datetime import datetime
import uuid

import redis.asyncio as redis
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EventStreamManager:
    """Manages Redis Streams for real-time event streaming."""

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.stream_key = settings.stream_key
        self.max_len = settings.stream_max_len
        self._connected = False

    async def connect(self) -> bool:
        """Connect to Redis."""
        try:
            self.redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.redis_max_connections,
            )
            await self.redis.ping()
            self._connected = True
            logger.info("Connected to Redis for event streaming")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    async def publish_event(self, event: Dict[str, Any]) -> bool:
        """Publish event to Redis Stream."""
        if not self._connected:
            return False

        try:
            # Add timestamp and ID if not present
            if "timestamp" not in event:
                event["timestamp"] = datetime.utcnow().isoformat()
            if "event_id" not in event:
                event["event_id"] = str(uuid.uuid4())

            # Serialize to JSON
            event_data = {
                "data": json.dumps(event, default=str),
            }

            # Add to stream with max length trimming
            await self.redis.xadd(
                self.stream_key,
                event_data,
                maxlen=self.max_len,
                approximate=True,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return False

    async def publish_batch(self, events: List[Dict[str, Any]]) -> int:
        """Publish multiple events efficiently."""
        if not self._connected or not events:
            return 0

        try:
            pipe = self.redis.pipeline()
            for event in events:
                if "timestamp" not in event:
                    event["timestamp"] = datetime.utcnow().isoformat()
                if "event_id" not in event:
                    event["event_id"] = str(uuid.uuid4())

                pipe.xadd(
                    self.stream_key,
                    {"data": json.dumps(event, default=str)},
                    maxlen=self.max_len,
                    approximate=True,
                )
            await pipe.execute()
            return len(events)
        except Exception as e:
            logger.error(f"Failed to publish batch: {e}")
            return 0

    async def get_recent_events(self, count: int = 100) -> List[Dict[str, Any]]:
        """Get recent events from stream."""
        if not self._connected:
            return []

        try:
            # Get last N events
            entries = await self.redis.xrevrange(self.stream_key, count=count)
            events = []
            for entry_id, data in entries:
                try:
                    event = json.loads(data.get("data", "{}"))
                    event["_stream_id"] = entry_id
                    events.append(event)
                except json.JSONDecodeError:
                    continue
            return list(reversed(events))  # Oldest first
        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            return []


class SSEManager:
    """Manages Server-Sent Events connections."""

    def __init__(self, stream_manager: EventStreamManager):
        self.stream_manager = stream_manager
        self.subscribers: Dict[str, asyncio.Queue] = {}
        self._listener_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start listening to Redis stream."""
        if self._running:
            return

        self._running = True
        self._listener_task = asyncio.create_task(self._listen_loop())
        logger.info("SSE manager started")

    async def stop(self) -> None:
        """Stop listening."""
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        logger.info("SSE manager stopped")

    async def _listen_loop(self) -> None:
        """Listen to Redis stream and broadcast to subscribers."""
        last_id = "0"
        while self._running:
            try:
                if not self.stream_manager.is_connected():
                    await asyncio.sleep(5)
                    continue

                # Blocking read with timeout
                entries = await self.stream_manager.redis.xread(
                    {self.stream_manager.stream_key: last_id},
                    count=100,
                    block=5000,  # 5 second block
                )

                for stream_name, stream_entries in entries:
                    for entry_id, data in stream_entries:
                        last_id = entry_id
                        try:
                            event = json.loads(data.get("data", "{}"))
                            event["_stream_id"] = entry_id
                            await self._broadcast(event)
                        except json.JSONDecodeError:
                            continue

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"SSE listen error: {e}")
                await asyncio.sleep(1)

    async def _broadcast(self, event: Dict[str, Any]) -> None:
        """Broadcast event to all subscribers."""
        dead_queues = []
        for queue in self.subscribers.values():
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead_queues.append(queue)

        # Clean up full queues
        for queue in dead_queues:
            for sub_id, q in list(self.subscribers.items()):
                if q is queue:
                    del self.subscribers[sub_id]
                    break

    def subscribe(self) -> asyncio.Queue:
        """Create new subscription."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        sub_id = str(uuid.uuid4())
        self.subscribers[sub_id] = queue
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove subscription."""
        for sub_id, q in list(self.subscribers.items()):
            if q is queue:
                del self.subscribers[sub_id]
                break

    async def event_generator(self, queue: asyncio.Queue) -> AsyncGenerator[str, None]:
        """Generate SSE events for a subscriber."""
        try:
            # Send initial heartbeat
            yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=settings.sse_heartbeat_interval)
                    yield f"data: {json.dumps(event, default=str)}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            self.unsubscribe(queue)


# Global instances
_stream_manager: Optional[EventStreamManager] = None
_sse_manager: Optional[SSEManager] = None


async def get_stream_manager() -> EventStreamManager:
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = EventStreamManager()
        await _stream_manager.connect()
    return _stream_manager


async def get_sse_manager() -> SSEManager:
    global _sse_manager
    if _sse_manager is None:
        stream_mgr = await get_stream_manager()
        _sse_manager = SSEManager(stream_mgr)
        await _sse_manager.start()
    return _sse_manager


async def close_streaming() -> None:
    global _stream_manager, _sse_manager
    if _sse_manager:
        await _sse_manager.stop()
        _sse_manager = None
    if _stream_manager:
        await _stream_manager.disconnect()
        _stream_manager = None