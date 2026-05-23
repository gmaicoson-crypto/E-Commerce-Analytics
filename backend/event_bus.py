# 基于 asyncio.Queue 的内存事件总线，用于向 SSE 订阅者广播业务事件
# 事件结构：{"entity": "order|product|...", "action": "create|update|delete", "payload": {...}}

from __future__ import annotations
import asyncio
import json
from typing import Any, Dict, List


class EventBus:
    def __init__(self) -> None:
        self._subscribers: List[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    # 新增订阅者，返回其专属队列
    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers.append(q)
        return q

    # 移除订阅者
    async def unsubscribe(self, q: asyncio.Queue) -> None:
        async with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    # 同步发布事件到所有订阅者；队列满时静默丢弃
    def publish(self, entity: str, action: str, payload: Dict[str, Any]) -> None:
        event = {"entity": entity, "action": action, "payload": payload}
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


# 全局事件总线单例
bus = EventBus()


# 将事件编码为 SSE 数据帧格式
def encode_sse(event: Dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
