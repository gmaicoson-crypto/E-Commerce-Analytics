# 数据模拟生成器

独立 FastAPI 服务,**写入** ecommerce-vue-ts 数据库 + 提供单页 UI。

## 架构

```
数据模拟生成器  →  数据库  →  后端只获取并处理数据  →  前端请求后端拿到数据进行渲染
(simulator:8001)    MySQL          (backend:8000 read-only)        (frontend:5173)

写入路径:浏览器 → simulator:8001 → MySQL
                           ↓
                        POST backend:8000 /api/notify
                           ↓
                        backend event_bus → SSE → frontend refetch
```

backend(8000)只读 / 转发 SSE,**不接受任何写入**。所有 create / update / delete 都走 simulator(8001)。

## 启动

```powershell
# 1. 先确保 MySQL 跑着,且 ecommerce_db 已建库(没建可跑 backend/setup_db.py)
# 2. 灌初始数据
python "D:\Study\Project5\data-simulator\data_generator\seed.py"

# 3. 启 backend(8000,read-only)
cd "d:\Study\Project5\ecommerce-vue-ts\backend"
uvicorn main:app --host 127.0.0.1 --port 8000

# 4. 装 simulator 依赖 + 启 simulator(8001)
cd "d:\Study\Project5\ecommerce-vue-ts\simulator"
pip install -r server/requirements.txt
uvicorn server.main:app --host 127.0.0.1 --port 8001 --app-dir server
```

> `--app-dir server` 让 server/ 下的 `database.py / models.py / data_factory.py / notify_client.py` 同包互相 import。

打开浏览器:**http://127.0.0.1:8001/**

## 6 个 Tab(完整 CRUD)

| Tab | List 过滤 | 新增字段(空=随机/默认) | 编辑字段 |
|------|------------|--------------------------|-----------|
| 客户 | 性别 / 年龄段 / 省份 / 类型 | 性别、年龄段、省份、类型 | 用户名 + 上面 4 项 |
| 商品 | 品类 / 状态 | 品类、状态、价格、成本、库存 | 名称 + 品类 + 状态 + 价格 + 成本 + 库存 + 阈值 |
| 订单 | 状态 | 状态、客户 ID | 状态(跨 completed → 自动同步 finance) |
| 退款 | 状态 | 订单 ID、金额 | 状态、原因、退款金额 |
| 财务 | 类型 / 分类 | 类型、分类、金额 | 类型、分类、金额 |
| 通知 | 类型 / 已读 | 类型、标题、内容 | 已读、标题、内容 |

## 级联规则(全在 server/data_factory.py)

| 触发 | 自动级联 |
|------|---------|
| `create_order(status=completed)` | 落 3 条 finance:sales_income + logistics_cost + ad_cost |
| `update_order(status)` 进入 completed | 补 3 条 finance |
| `update_order(status)` 离开 completed | 删该订单相关 finance |
| `update_product(stock < threshold)` | 推 stock_alert 通知 |
| `create_refund(amount ≥ 500)` | 推 refund_alert 通知 |
| `delete_customer` 客户有订单 | HTTP 400 拒绝 |
| `delete_product` 商品在 order_items 中 | HTTP 400 拒绝 |
| `delete_order` | cascade order_items + refunds + finance |

## 接口表

25 个端点(6 实体 × 4 + `/api/counts`):

```
GET    /api/counts

GET    /api/customer/list?page&page_size&gender&age_group&province&customer_type
POST   /api/customer
PATCH  /api/customer/{id}
DELETE /api/customer/{id}

GET    /api/product/list?page&page_size&category&status
POST   /api/product
PATCH  /api/product/{id}
DELETE /api/product/{id}

GET    /api/order/list?page&page_size&status
POST   /api/order
PATCH  /api/order/{id}
DELETE /api/order/{id}

GET    /api/refund/list?page&page_size&status
POST   /api/refund
PATCH  /api/refund/{id}
DELETE /api/refund/{id}

GET    /api/finance/list?page&page_size&type&category
POST   /api/finance
PATCH  /api/finance/{id}
DELETE /api/finance/{id}

GET    /api/notification/list?page&page_size&ntype&is_read
POST   /api/notification
PATCH  /api/notification/{id}
DELETE /api/notification/{id}
```

## 与 backend 的耦合点

| 文件 | 作用 |
|------|------|
| [backend/routers/notify.py](../backend/routers/notify.py) | 接收 simulator 推送的事件,转发到 `event_bus.bus` → SSE |
| [backend/event_bus.py](../backend/event_bus.py) | 全局 SSE 总线 |
| [backend/routers/sse.py](../backend/routers/sse.py) | SSE 订阅端点 `/api/sse/subscribe`,主前端连接此处 |

simulator 与 backend 是 HTTP 通信(不共享内存),所以两边可以独立启动 / 重启。simulator 推 notify 失败时静默忽略(不阻塞写入)。

## 环境变量

| 变量 | 默认 | 作用 |
|------|------|------|
| `DATABASE_URL` | `mysql+pymysql://root:20041122@127.0.0.1:3306/ecommerce_db` | DB 连接 |
| `BACKEND_URL`  | `http://127.0.0.1:8000` | notify 推送目标 |
