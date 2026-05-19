"""自动化模拟引擎 —— 单例后台 asyncio.Task。

挂在 simulator FastAPI app 上,由 /api/automation/start|stop|status 控制。
每 tick 在线程池里跑一次写库 + notify,把 event loop 让出去。
"""
import asyncio
import random
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict

from database import SessionLocal
import data_factory as df
from notify_client import notify


@dataclass
class AutoConfig:
    events_per_min: float = 60.0       # 默认 1 事件/秒
    register_weight: float = 0.25      # 25% 注册 / 75% 下单
    order_status_weights: Dict[str, int] = field(default_factory=lambda: {
        "pending": 10, "paid": 25, "shipped": 25, "completed": 40,
    })


@dataclass
class AutoStats:
    started_at: Optional[str] = None
    registered: int = 0
    ordered: int = 0
    skipped_no_product: int = 0    # create_order 因无 on_sale 商品被跳过
    skipped_no_customer: int = 0   # create_order 因无客户被跳过


class AutomationEngine:
    def __init__(self) -> None:
        self.running: bool = False
        self.config = AutoConfig()
        self.stats = AutoStats()
        self._task: Optional[asyncio.Task] = None

    def status(self) -> dict:
        return {
            "running": self.running,
            "config": asdict(self.config),
            "stats": asdict(self.stats),
        }

    def start(self, **overrides) -> dict:
        if self.running:
            return self.status()
        for k, v in overrides.items():
            if hasattr(self.config, k) and v is not None:
                setattr(self.config, k, v)
        self.stats = AutoStats(started_at=datetime.utcnow().isoformat())
        self.running = True
        self._task = asyncio.create_task(self._run())
        return self.status()

    async def stop(self) -> dict:
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        return self.status()

    async def _run(self) -> None:
        try:
            while self.running:
                await asyncio.to_thread(self._tick)
                # 速率 → 平均 sleep,uniform 抖动 0.5-1.5x 避免节拍齐刷
                base = 60.0 / max(self.config.events_per_min, 1)
                await asyncio.sleep(base * random.uniform(0.5, 1.5))
        except asyncio.CancelledError:
            pass

    # ─── 同步 tick(运行在 worker 线程) ─────────────────────────────────

    def _tick(self) -> None:
        with SessionLocal() as db:
            if random.random() < self.config.register_weight:
                self._tick_register(db)
            else:
                self._tick_order(db)

    def _tick_register(self, db) -> None:
        try:
            info = df.create_customer(db)  # 全字段空 → 随机分布
            self.stats.registered += 1
            notify("customer", "create", info)
        except Exception as e:
            print(f"[automation] register error: {e}")

    def _tick_order(self, db) -> None:
        statuses = list(self.config.order_status_weights.keys())
        weights = list(self.config.order_status_weights.values())
        status = random.choices(statuses, weights=weights)[0]
        try:
            result = df.create_order(db, status=status)
        except Exception as e:
            print(f"[automation] order error: {e}")
            return

        if result is None:
            # 区分一下跳过原因 — 引导用户去面板补数据
            from models import Customer, Product, ProductStatusEnum
            if db.query(Customer).count() == 0:
                self.stats.skipped_no_customer += 1
            elif db.query(Product).filter(Product.status == ProductStatusEnum.on_sale).count() == 0:
                self.stats.skipped_no_product += 1
            return

        self.stats.ordered += 1
        notify("order", "create", result["row"])
        if result.get("finance"):
            for f in result["finance"]:
                notify("finance", "create", f)
        for n in result.get("notifs") or []:
            notify("notification", "create", n)


engine = AutomationEngine()
