# 接收模拟器推送的写入事件，转发到 SSE 总线
# 数据模拟器（8001）写库后调用此端点，backend（8000）再广播给 SSE 订阅者

from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel
from event_bus import bus

router = APIRouter()


# 事件数据结构
class NotifyEvent(BaseModel):
    entity: str  # customer / product / order / refund / finance / notification
    action: str  # create / update / delete
    payload: Dict[str, Any] = {}


# 接收事件并发布到总线
@router.post("")
def notify(event: NotifyEvent):
    bus.publish(event.entity, event.action, event.payload)
    return {"ok": True}
