"""Automation engine for the simulator UI.

The simulator behaves like an external commerce platform: it generates events
and sends them to backend ingest APIs. It does not write the project database
directly.
"""
from __future__ import annotations

import asyncio
import random
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional

import data_factory as df


@dataclass
class AutoConfig:
    events_per_min: float = 60.0
    register_weight: float = 0.25
    advances_per_min: float = 30.0
    pending_to_paid: float = 0.6
    pending_to_cancel: float = 0.1
    paid_to_shipped: float = 0.6
    shipped_to_completed: float = 0.8
    backfill_enabled: bool = False
    backfill_start_date: Optional[str] = None
    backfill_end_date: Optional[str] = None


@dataclass
class AutoStats:
    started_at: Optional[str] = None
    registered: int = 0
    ordered: int = 0
    skipped_no_product: int = 0
    skipped_no_customer: int = 0
    adv_paid: int = 0
    adv_cancelled: int = 0
    adv_shipped: int = 0
    adv_completed: int = 0


class AutomationEngine:
    def __init__(self) -> None:
        self.running = False
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
        for key, value in overrides.items():
            if hasattr(self.config, key) and value is not None:
                setattr(self.config, key, value)
        self.stats = AutoStats(started_at=datetime.utcnow().isoformat())
        self.running = True
        self._gen_task = asyncio.create_task(self._run_generation())
        self._adv_task = asyncio.create_task(self._run_advancement())
        return self.status()

    async def stop(self) -> dict:
        self.running = False
        for attr in ("_gen_task", "_adv_task"):
            task = getattr(self, attr)
            if task:
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
                setattr(self, attr, None)
        return self.status()

    async def _run_generation(self) -> None:
        try:
            while self.running:
                if self.config.events_per_min <= 0:
                    await asyncio.sleep(1)
                    continue
                started = asyncio.get_event_loop().time()
                await asyncio.to_thread(self._generation_tick)
                await self._sleep_for_rate(self.config.events_per_min, started)
        except asyncio.CancelledError:
            pass

    async def _run_advancement(self) -> None:
        try:
            while self.running:
                if self.config.advances_per_min <= 0:
                    await asyncio.sleep(1)
                    continue
                started = asyncio.get_event_loop().time()
                await asyncio.to_thread(self._advancement_tick)
                await self._sleep_for_rate(self.config.advances_per_min, started)
        except asyncio.CancelledError:
            pass

    async def _sleep_for_rate(self, per_minute: float, started: float) -> None:
        target = 60.0 / per_minute
        elapsed = asyncio.get_event_loop().time() - started
        sleep_for = max(0.0, target - elapsed) * random.uniform(0.9, 1.1)
        if sleep_for > 0:
            await asyncio.sleep(sleep_for)

    def _generation_tick(self) -> None:
        if random.random() < self.config.register_weight:
            try:
                df.create_customer()
                self.stats.registered += 1
            except Exception as exc:
                print(f"[automation] customer event failed: {exc}")
            return

        try:
            df.create_order(status="pending")
            self.stats.ordered += 1
        except Exception as exc:
            print(f"[automation] order event failed: {exc}")
            counts = self._safe_counts()
            if counts.get("customers", 0) == 0:
                self.stats.skipped_no_customer += 1
            elif counts.get("products", 0) == 0:
                self.stats.skipped_no_product += 1

    def _advancement_tick(self) -> None:
        candidates = []
        for status in ("pending", "paid", "shipped"):
            try:
                data = df.list_orders(page=1, page_size=100, status=status)
                candidates.extend(data.get("data") or [])
            except Exception as exc:
                print(f"[automation] order list failed: {exc}")
                return
        if not candidates:
            return

        order = random.choice(candidates)
        next_status = self._decide_next_status(order.get("status"))
        if not next_status:
            return

        try:
            df.update_order(order["id"], status=next_status)
        except Exception as exc:
            print(f"[automation] order advance failed: {exc}")
            return

        attr = {
            "paid": "adv_paid",
            "cancelled": "adv_cancelled",
            "shipped": "adv_shipped",
            "completed": "adv_completed",
        }.get(next_status)
        if attr:
            setattr(self.stats, attr, getattr(self.stats, attr) + 1)

    def _decide_next_status(self, current: Optional[str]) -> Optional[str]:
        roll = random.random()
        if current == "pending":
            if roll < self.config.pending_to_paid:
                return "paid"
            if roll < self.config.pending_to_paid + self.config.pending_to_cancel:
                return "cancelled"
        if current == "paid":
            if roll < self.config.paid_to_shipped:
                return "shipped"
        if current == "shipped" and roll < self.config.shipped_to_completed:
            return "completed"
        return None

    def _safe_counts(self) -> dict:
        try:
            return df.get_counts()
        except Exception:
            return {}


engine = AutomationEngine()
