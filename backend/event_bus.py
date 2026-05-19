"""极简内存事件总线:用 asyncio.Queue 给每个 SSE 订阅者派发事件。

事件结构: {"entity": "<order|product|customer|notification|finance>",
           "action": "<create|delete|update>",
           "payload": <任意 JSON-safe dict>}
"""
from __future__ import annotations
import asyncio
import json
from typing import Any, Dict, List


class EventBus:
    def __init__(self) -> None:
        self._subscribers: List[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers.append(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue) -> None:
        async with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def publish(self, entity: str, action: str, payload: Dict[str, Any]) -> None:
        """同步发布:从 sync 路由里调用安全。失败的订阅者会被静默丢弃事件。"""
        event = {"entity": entity, "action": action, "payload": payload}
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # 慢消费者丢一帧不影响整体


bus = EventBus()


def encode_sse(event: Dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
