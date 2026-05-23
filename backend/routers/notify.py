"""接收 simulator 推送的写入事件,转发到 SSE 总线。

Simulator(8001)写完库后调用此端点,backend(8000)再通过 event_bus 广播给 SSE 订阅者。
"""

from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel
from event_bus import bus

router = APIRouter()


class NotifyEvent(BaseModel):
    entity: str  # customer / product / order / refund / finance / notification
    action: str  # create / update / delete
    payload: Dict[str, Any] = {}


@router.post("")
def notify(event: NotifyEvent):
    bus.publish(event.entity, event.action, event.payload)
    return {"ok": True}
