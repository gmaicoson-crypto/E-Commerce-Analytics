"""SSE 路由:订阅 event_bus,把业务事件推给前端。

由于浏览器原生 EventSource 不支持自定义 Header,token 通过 query 参数传入。
"""
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


def _verify_token(token: Optional[str]) -> None:
    if not token:
        raise HTTPException(status_code=401, detail="token required")
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="invalid token")


async def _event_stream(entities: Optional[set] = None):
    """订阅 bus,把事件按 SSE 编码;每 15s 发一个 ping 防止连接超时。"""
    q = await bus.subscribe()
    try:
        # 连接建立时先发一个 hello
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


@router.get("/events")
async def all_events(token: str = Query(...)):
    """订阅全部事件流。前端用这个就够了。"""
    _verify_token(token)
    return StreamingResponse(_event_stream(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/orders")
async def orders_events(token: str = Query(...)):
    _verify_token(token)
    return StreamingResponse(
        _event_stream({"order", "finance"}),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.get("/finance")
async def finance_events(token: str = Query(...)):
    _verify_token(token)
    return StreamingResponse(
        _event_stream({"finance", "order"}),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.get("/dashboard")
async def dashboard_events(token: str = Query(...)):
    """旧接口保留,转发全部事件。"""
    _verify_token(token)
    return StreamingResponse(_event_stream(), media_type="text/event-stream", headers=SSE_HEADERS)
