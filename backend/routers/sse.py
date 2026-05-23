# SSE 路由：订阅 event_bus，将业务事件实时推送给前端
# 由于浏览器原生 EventSource 不支持自定义 Header，token 通过 query 参数传入

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
from typing import Optional

from auth import decode_access_token
from event_bus import bus, encode_sse

router = APIRouter()

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


# 校验 token，无效时抛出 401
def _verify_token(token: Optional[str]) -> None:
    if not token:
        raise HTTPException(status_code=401, detail="token required")
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="invalid token")


# 订阅事件总线并以 SSE 格式逐帧输出；每 15 秒发 ping 防止连接超时
async def _event_stream(entities: Optional[set] = None):
    q = await bus.subscribe()
    try:
        yield encode_sse({"entity": "system", "action": "hello", "payload": {}})
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=15.0)
                if entities and event["entity"] not in entities:
                    continue
                yield encode_sse(event)
            except asyncio.TimeoutError:
                yield ": ping\n\n"
    except asyncio.CancelledError:
        raise
    finally:
        await bus.unsubscribe(q)


# 订阅全部事件流
@router.get("/events")
async def all_events(token: str = Query(...)):
    _verify_token(token)
    return StreamingResponse(
        _event_stream(), media_type="text/event-stream", headers=SSE_HEADERS
    )


# 仅订阅订单与财务事件
@router.get("/orders")
async def orders_events(token: str = Query(...)):
    _verify_token(token)
    return StreamingResponse(
        _event_stream({"order", "finance"}),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


# 仅订阅财务与订单事件
@router.get("/finance")
async def finance_events(token: str = Query(...)):
    _verify_token(token)
    return StreamingResponse(
        _event_stream({"finance", "order"}),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


# 仪表盘事件流（兼容旧接口，转发全部事件）
@router.get("/dashboard")
async def dashboard_events(token: str = Query(...)):
    _verify_token(token)
    return StreamingResponse(
        _event_stream(), media_type="text/event-stream", headers=SSE_HEADERS
    )
