"""自动化模拟引擎 —— 单例后台 asyncio.Task。

挂在 simulator FastAPI app 上,由 /api/automation/start|stop|status 控制。

新规则:
- 「生成循环」按 events_per_min 创建客户 / pending 订单
- 「推进循环」按 advances_per_min 随机挑非终态订单,按转移概率沿状态机推进
- 两个循环各自独立 asyncio.Task,各有自己的速率
"""
import asyncio
import random
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict

from sqlalchemy import func as sa_func

from database import SessionLocal
import data_factory as df
from models import Order, OrderStatusEnum
from notify_client import notify


@dataclass
class AutoConfig:
    # ─── 生成循环 ───────────────────────────────────────────────────────
    events_per_min: float = 60.0       # 默认 1 事件/秒
    register_weight: float = 0.25      # 25% 注册 / 75% 下单
    # 字段保留向后兼容,但新规则下 _tick_order 强制 status=pending,不再读此权重
    order_status_weights: Dict[str, int] = field(default_factory=lambda: {
        "pending": 100,
    })

    # ─── 推进循环(新)──────────────────────────────────────────────────
    advances_per_min: float = 30.0     # 0 = 禁用推进
    # 每个状态被本 tick 选中后的"出口概率",余下概率 = 保持不变
    pending_to_paid:      float = 0.6
    pending_to_cancel:    float = 0.1
    paid_to_shipped:      float = 0.6
    paid_to_refunded:     float = 0.05
    shipped_to_completed: float = 0.8


@dataclass
class AutoStats:
    started_at: Optional[str] = None
    # 生成
    registered: int = 0
    ordered: int = 0
    skipped_no_product: int = 0    # create_order 因无 on_sale 商品被跳过
    skipped_no_customer: int = 0   # create_order 因无客户被跳过
    # 推进(新)
    adv_paid:      int = 0
    adv_cancelled: int = 0
    adv_shipped:   int = 0
    adv_refunded:  int = 0
    adv_completed: int = 0


class AutomationEngine:
    def __init__(self) -> None:
        self.running: bool = False
        self.config = AutoConfig()
        self.stats = AutoStats()
        self._gen_task: Optional[asyncio.Task] = None
        self._adv_task: Optional[asyncio.Task] = None

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
        self._gen_task = asyncio.create_task(self._run_gen())
        self._adv_task = asyncio.create_task(self._run_adv())
        return self.status()

    async def stop(self) -> dict:
        self.running = False
        for attr in ("_gen_task", "_adv_task"):
            t = getattr(self, attr)
            if t:
                t.cancel()
                try:
                    await t
                except (asyncio.CancelledError, Exception):
                    pass
                setattr(self, attr, None)
        return self.status()

    # ─── 异步循环 ───────────────────────────────────────────────────────

    async def _run_gen(self) -> None:
        try:
            while self.running:
                await asyncio.to_thread(self._tick)
                base = 60.0 / max(self.config.events_per_min, 1)
                await asyncio.sleep(base * random.uniform(0.5, 1.5))
        except asyncio.CancelledError:
            pass

    async def _run_adv(self) -> None:
        try:
            while self.running:
                if self.config.advances_per_min <= 0:
                    # 禁用推进:轻量轮询配置变化,避免 CPU 空转
                    await asyncio.sleep(1.0)
                    continue
                await asyncio.to_thread(self._advance_tick)
                base = 60.0 / self.config.advances_per_min
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
        # 新规则:自动化只生成 pending 订单,后续状态由「推进循环」沿状态机演进
        try:
            result = df.create_order(db, status="pending")
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

    # ─── 推进 tick ──────────────────────────────────────────────────────

    def _advance_tick(self) -> None:
        with SessionLocal() as db:
            # ORDER BY RAND() LIMIT 1 — 比 .all() + random.choice 高效
            order = (
                db.query(Order)
                .filter(Order.status.in_([
                    OrderStatusEnum.pending,
                    OrderStatusEnum.paid,
                    OrderStatusEnum.shipped,
                ]))
                .order_by(sa_func.rand())
                .first()
            )
            if not order:
                return
            next_status = self._decide_next_status(order.status)
            if next_status is None:
                return  # 本 tick 保持
            try:
                result = df.update_order(db, order.id, status=next_status.value)
            except Exception as e:
                print(f"[automation] advance error: {e}")
                return
            if not isinstance(result, dict):
                return  # invalid_transition / None — 状态机防御

            # 计数
            attr_map = {
                OrderStatusEnum.paid:      "adv_paid",
                OrderStatusEnum.cancelled: "adv_cancelled",
                OrderStatusEnum.shipped:   "adv_shipped",
                OrderStatusEnum.refunded:  "adv_refunded",
                OrderStatusEnum.completed: "adv_completed",
            }
            attr = attr_map[next_status]
            setattr(self.stats, attr, getattr(self.stats, attr) + 1)

            # SSE 通知 — 与 PATCH /api/order/{id} 同结构
            notify("order", "update", result["row"])
            for f in result.get("finance_added") or []:
                notify("finance", "create", f)
            if result.get("finance_removed"):
                notify("finance", "delete", {
                    "order_id": order.id,
                    "removed": result["finance_removed"],
                })

    def _decide_next_status(self, current) -> Optional[OrderStatusEnum]:
        cfg = self.config
        r = random.random()
        if current == OrderStatusEnum.pending:
            if r < cfg.pending_to_paid:
                return OrderStatusEnum.paid
            if r < cfg.pending_to_paid + cfg.pending_to_cancel:
                return OrderStatusEnum.cancelled
        elif current == OrderStatusEnum.paid:
            if r < cfg.paid_to_shipped:
                return OrderStatusEnum.shipped
            if r < cfg.paid_to_shipped + cfg.paid_to_refunded:
                return OrderStatusEnum.refunded
        elif current == OrderStatusEnum.shipped:
            if r < cfg.shipped_to_completed:
                return OrderStatusEnum.completed
        return None


engine = AutomationEngine()
