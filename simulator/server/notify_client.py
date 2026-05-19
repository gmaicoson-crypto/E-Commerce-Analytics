"""同步推一条事件给 backend /api/notify。失败静默,不影响写入主流程。

注意:用 `trust_env=False` 禁用 httpx 读取系统 HTTP_PROXY/HTTPS_PROXY 环境变量。
Windows 上若装了 v2ray/Clash 之类代理(7897 等),httpx 默认会把 localhost:8000
也通过代理转发 → ReadTimeout,从而 SSE 链路彻底断掉(simulator 写库成功但
backend 收不到 notify 事件,前端永远不刷新)。
"""
import os
import httpx

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")

# 复用连接池,顺便禁代理
_client = httpx.Client(timeout=2.0, trust_env=False)


def notify(entity: str, action: str, payload: dict) -> None:
    try:
        _client.post(
            f"{BACKEND_URL}/api/notify",
            json={"entity": entity, "action": action, "payload": payload},
        )
    except Exception as e:
        # 静默 —— 但开发环境第一次失败时打一行,便于排查
        print(f"[notify_client] post failed: {type(e).__name__}: {e}")
