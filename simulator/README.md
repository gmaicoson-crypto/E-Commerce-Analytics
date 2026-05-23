# 数据模拟器 (Simulator)

独立的 **FastAPI 服务**（默认运行在端口 8001），负责生成模拟电商数据并通过 HTTP 调用后端 Ingest API 写入数据库，同时提供一个单页管理 UI，方便手动增删改查测试数据。

---

## 整体架构

```text
浏览器打开 http://127.0.0.1:8001
         │
         ▼
┌─────────────────────┐      HTTP POST      ┌──────────────────────┐
│  Simulator          │  ───────────────►   │  Backend Ingest API  │
│  (FastAPI :8001)    │                     │  (FastAPI :8000)     │
│                     │                     │   /api/ingest/*      │
│  server/main.py     │                     └──────────┬───────────┘
│  server/automation  │                                │ 写库 + 触发 SSE
│  server/data_factory│                                ▼
│  server/backend_    │                     ┌──────────────────────┐
│    client.py        │                     │  MySQL 数据库         │
│  static/ (UI)       │                     └──────────┬───────────┘
└─────────────────────┘                                │ SSE 推送
                                                       ▼
                                            ┌──────────────────────┐
                                            │  Frontend (Vue:5173) │
                                            │  自动刷新数据         │
                                            └──────────────────────┘
```

**关键设计原则：** Simulator 与 Backend **不共享数据库连接**，所有写入操作都经过 HTTP 接口。两者可以独立启动和重启，互不影响。

---

## 目录结构

```text
simulator/
├── README.md                   # 本文档
├── server/                     # Python 后端服务
│   ├── main.py                 # FastAPI 应用入口，定义所有 API 路由
│   ├── automation.py           # 自动化事件生成引擎（异步循环）
│   ├── data_factory.py         # 模拟数据构造工厂（生成随机数据）
│   ├── backend_client.py       # 与后端 Ingest API 通信的 HTTP 客户端
│   └── requirements.txt        # Python 依赖声明
└── static/                     # 单页管理 UI（纯静态，无需构建）
    ├── index.html              # UI 页面结构（6 个功能 Tab）
    ├── app.js                  # 前端逻辑（CRUD、自动化控制、实体 Schema）
    └── style.css               # 样式（绿白主题，响应式）
```

---

## 快速启动

**前提：** MySQL 已运行，后端已启动（`:8000`），数据库已初始化。

```bash
cd simulator
pip install -r server/requirements.txt

# 基础启动
uvicorn server.main:app --port 8001 --reload

# 指定后端地址和认证 Token（与 backend/.env 中的 SIMULATOR_API_TOKEN 对应）
BACKEND_URL=http://127.0.0.1:8000 \
BACKEND_INGEST_TOKEN=your_token \
uvicorn server.main:app --port 8001 --reload
```

启动后访问 [http://127.0.0.1:8001](http://127.0.0.1:8001) 打开管理 UI。

---

## 文件详解

### `server/main.py` — FastAPI 应用入口

所有 HTTP 路由的定义入口。

**职责：**

- 创建 FastAPI 应用实例，配置 CORS（允许所有来源，方便本地开发）
- 挂载 `/static` 目录提供 UI 静态文件服务
- 定义 21 个 REST API 端点，覆盖 5 个实体 + 自动化控制

**API 端点汇总：**

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/customers` | 获取客户列表（支持分页和关键词筛选） |
| `POST` | `/api/customers` | 创建单个客户 |
| `PUT` | `/api/customers/{id}` | 更新客户信息 |
| `DELETE` | `/api/customers/{id}` | 删除客户 |
| `GET` | `/api/products` | 获取商品列表（支持分类筛选） |
| `POST` | `/api/products` | 创建商品 |
| `PUT` | `/api/products/{id}` | 更新商品（含库存调整） |
| `DELETE` | `/api/products/{id}` | 删除商品 |
| `GET` | `/api/orders` | 获取订单列表（支持状态筛选） |
| `POST` | `/api/orders` | 创建订单 |
| `PUT` | `/api/orders/{id}` | 更新订单状态 |
| `DELETE` | `/api/orders/{id}` | 删除订单 |
| `GET` | `/api/finance` | 获取财务记录列表 |
| `POST` | `/api/finance` | 创建财务记录 |
| `PUT` | `/api/finance/{id}` | 更新财务记录 |
| `DELETE` | `/api/finance/{id}` | 删除财务记录 |
| `GET` | `/api/notifications` | 获取通知列表 |
| `POST` | `/api/notifications` | 创建通知 |
| `DELETE` | `/api/notifications/{id}` | 删除通知 |
| `GET` | `/api/automation/status` | 查询自动化引擎当前状态和统计 |
| `POST` | `/api/automation/start` | 启动自动化数据生成 |
| `POST` | `/api/automation/stop` | 停止自动化数据生成 |

**Pydantic 请求模型：** `main.py` 中为每个实体定义了 Create/Update Schema，包含字段类型和 `Optional` 默认值，FastAPI 用于请求体验证和文档生成。

**启动钩子（`@app.on_event("startup")`）：** 应用启动时自动扫描库存预警类通知，清理掉已不满足低库存条件的过期告警。

---

### `server/automation.py` — 自动化事件生成引擎

核心的**自动化数据生成模块**，模拟真实电商系统中的用户行为流。

**核心类：`AutomationEngine`**

维护两个独立的异步循环（`asyncio.create_task`）：

#### 循环一：事件生成循环（`_generation_loop`）

按设定的速率持续生成新事件：

- **概率权重（`register_weight`，默认 25%）：** 每次迭代以 25% 概率创建新客户，以 75% 概率创建新订单
- **速率控制（`events_per_min`，默认 60）：** 每分钟产生的事件总数，转换为 `sleep_sec = 60 / events_per_min` 间隔
- **Backfill 模式：** 传入 `backfill=True` 时可注入历史时间戳，用于补充历史数据而不是只产生当前时间的记录

#### 循环二：订单推进循环（`_advancement_loop`）

模拟订单生命周期状态流转：

```text
pending（待付款）
    ├─ → paid（已付款）     概率: advance_paid_rate（默认 70%）
    └─ → cancelled（取消）  概率: 1 - advance_paid_rate

paid（已付款）
    └─ → shipped（已发货）  概率: advance_ship_rate（默认 80%）

shipped（已发货）
    ├─ → completed（已完成）概率: advance_complete_rate（默认 85%）
    └─ → refunded（退款）   概率: 1 - advance_complete_rate
```

每次推进循环从数据库取一批非终态订单，按概率决定是否流转到下一状态。

**可配置参数（`start()` 方法接受）：**

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `events_per_min` | 60 | 每分钟生成事件数 |
| `register_weight` | 0.25 | 新增客户占事件比例 |
| `advance_paid_rate` | 0.70 | pending→paid 概率 |
| `advance_ship_rate` | 0.80 | paid→shipped 概率 |
| `advance_complete_rate` | 0.85 | shipped→completed 概率 |
| `advance_interval_sec` | 5 | 推进循环检查间隔（秒） |

**统计信息（`stats` 属性）：**

- `registered`：已创建客户数
- `ordered`：已创建订单数
- `advanced`：已推进状态的订单数
- `skipped`：因条件不满足跳过的次数及原因

---

### `server/data_factory.py` — 模拟数据构造工厂

负责**生成随机但合理的模拟数据**，是自动化引擎和手动 API 的数据来源。

**重要约定：** 本模块**永远不直接写数据库**，所有数据均通过 `backend_client.py` 调用后端 Ingest API 提交，后端负责持久化和业务逻辑（库存扣减、级联财务记录生成、SSE 通知推送等）。

**内置常量（模拟数据素材）：**

| 常量 | 内容 | 用途 |
| --- | --- | --- |
| `PROVINCES` | 34 个省份/直辖市 | 客户注册地 |
| `CATEGORIES` | 5 个商品分类 | 商品分类（电子产品/服装/食品/家居/运动） |
| `AGE_GROUPS` | 4 个年龄段 | 客户年龄分类 |
| `GENDERS` | 男/女 | 客户性别 |
| `CUSTOMER_TYPES` | 新客/老客 | 客户类型 |
| `ORDER_STATUSES` | 5 种状态 | 订单状态枚举 |
| `NOTIFICATION_TYPES` | 3 种类型 | 通知类型枚举 |

**核心函数：**

| 函数 | 说明 |
| --- | --- |
| `create_customer(...)` | 生成随机客户，用户名基于随机词组合，省份/性别等随机抽取；调用 `backend_client.create_customer()` |
| `create_product(...)` | 生成商品数据，价格/成本/库存在合理区间内随机；调用 `backend_client.create_product()` |
| `create_order(customer_id?, product_ids?)` | 随机挑选 1-3 个商品，关联指定或随机客户；调用 `backend_client.create_order()`。订单创建后后端自动扣库存、若已完成则级联生成财务记录 |
| `create_finance_record(...)` | 生成收入/支出财务记录，按类型限制合法 category；调用 `backend_client.create_finance_record()` |
| `create_notification(...)` | 生成 3 种类型通知（库存预警/订单提醒/客户注册），自动拼接标题和内容；调用 `backend_client.create_notification()` |
| `list_*() / update_*() / delete_*()` | 各实体的查询/更新/删除，均委托给 `backend_client` 对应函数 |

---

### `server/backend_client.py` — 后端 HTTP 客户端

Simulator 与 Backend 之间通信的**唯一桥梁**，封装了所有对后端 Ingest API 的 HTTP 调用。

**配置（读取环境变量）：**

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `BACKEND_URL` | `http://127.0.0.1:8000` | 后端服务地址 |
| `BACKEND_INGEST_TOKEN` | 空字符串 | Bearer Token，需与后端 `SIMULATOR_API_TOKEN` 一致 |

**实现方式：**

- 使用 `httpx` 库同步发送 HTTP 请求（因为 FastAPI 路由函数本身是同步的）
- 所有请求自动附带 `Authorization: Bearer <token>` Header
- 响应失败时解析后端返回的 `detail` 字段并抛出 `RuntimeError`
- 接口超时设为 10 秒

**封装的函数（共 21 个）：**

```text
客户:    create_customer, list_customers, update_customer, delete_customer
商品:    create_product,  list_products,  update_product,  delete_product
订单:    create_order,    list_orders,    update_order,    delete_order
财务:    create_finance,  list_finance,   update_finance,  delete_finance
通知:    create_notification, list_notifications, delete_notification
辅助:    get_products_for_order (给 create_order 查询可用商品列表)
```

---

### `server/requirements.txt` — Python 依赖

```text
fastapi           # Web 框架
uvicorn[standard] # ASGI 服务器（含 websockets 和 httptools 性能优化）
httpx             # 异步/同步 HTTP 客户端（用于调用后端）
pydantic>=2       # 数据验证（FastAPI 依赖）
```

---

## `static/` — 管理 UI（纯静态，无需构建）

直接由 Simulator FastAPI 服务通过 `StaticFiles` 挂载提供，浏览器访问 <http://127.0.0.1:8001> 即可使用。

### `static/index.html` — UI 页面结构

单页面应用，包含 **6 个功能 Tab**：

| Tab | 功能 |
| --- | --- |
| 客户 | 查看/新增/编辑/删除客户，支持关键词搜索 |
| 商品 | 查看/新增/编辑/删除商品，支持分类筛选，可调整库存 |
| 订单 | 查看/新增/编辑订单状态/删除，支持状态筛选 |
| 财务 | 查看/新增/编辑/删除财务记录，支持类型筛选 |
| 通知 | 查看/新增/删除通知 |
| 自动化 | 启动/停止自动化数据生成引擎，调整各项参数，实时查看生成统计 |

**页面布局：**

- 顶部：5 个实体的总数量展示（每 5 秒自动刷新）
- 中部：Tab 导航 + 数据表格（含分页）+ 操作按钮（新增/编辑/删除）
- 底部：操作日志面板（最近 50 条操作记录，含时间戳和结果）

---

### `static/app.js` — 前端交互逻辑

约 700 行的单文件前端脚本，无任何框架依赖，纯原生 JavaScript。

**核心数据结构 `ENTITIES`：**

为每个实体定义完整的 Schema，驱动 UI 自动生成：

```javascript
ENTITIES = {
  customers: {
    label: '客户',
    apiPath: '/api/customers',
    columns: [...],         // 表格列定义（key, label, formatter）
    filters: [...],         // 筛选条件（字段、类型、选项）
    createFields: [...],    // 新建表单字段
    editFields: [...]       // 编辑表单字段
  },
  // orders, products, finance, notifications...
}
```

**CRUD 流程：**

1. 切换 Tab → 调用 `/api/{entity}?page=N&...` 拉取数据
2. 渲染表格（根据 `columns` 定义自动生成 `<td>`）
3. 点击「新增」→ 根据 `createFields` 动态生成表单
4. 点击行「编辑」→ 根据 `editFields` 填入当前值
5. 提交表单 → `POST` / `PUT` API → 刷新列表 → 写日志

**订单状态机约束（在 UI 层面强制执行）：**

编辑订单时，下拉选项只显示合法的下一状态：

```text
pending  → [paid, cancelled]
paid     → [shipped]
shipped  → [completed, refunded]
completed/cancelled/refunded → 不可修改（只读）
```

**自动化面板（`AUTO` 对象）：**

- 每 2 秒轮询 `/api/automation/status` 更新状态和统计数字
- 「启动」按钮点击后发送 `POST /api/automation/start` 并携带当前配置参数
- 实时显示：已注册客户数、已创建订单数、已推进订单数、运行状态（脉冲动画指示）

---

### `static/style.css` — 样式文件

绿白主题（与前端 Vue 应用色系一致）：

| 样式块 | 说明 |
| --- | --- |
| CSS 变量 | `--green: #52b788`、`--text1: #111827` 等全局色彩 |
| 布局 | 6 列计数卡片网格、3 列自动化统计网格 |
| 组件 | 卡片、Tab 栏、数据表格（含斑马纹）、模态框、表单 |
| 动画 | `@keyframes auto-pulse` — 运行状态绿点脉冲闪烁 |
| 响应式 | `@media (max-width: 1200px)` 和 `960px` 断点 |

---

## 与后端的集成关系

Simulator 写入数据后，后端会自动执行以下业务逻辑（均在 `backend/services/ingest_service.py` 中实现）：

| Simulator 操作 | 后端自动处理 |
| --- | --- |
| 创建订单（`completed` 状态） | 生成 3 条财务记录（销售收入 + 物流成本 + 广告成本） |
| 更新订单为 `completed` | 同上，级联生成财务记录 |
| 更新订单为 `shipped` | 扣减对应商品库存 |
| 库存扣减后低于阈值 | 自动创建库存预警通知 |
| 任何写入操作 | 通过 `event_bus` 向前端推送 SSE 事件，触发实时刷新 |

**认证方式：** Simulator 通过 `Authorization: Bearer <SIMULATOR_API_TOKEN>` 访问后端 `/api/ingest/*` 路由，该 Token 在后端 `.env` 文件中配置，与普通用户 JWT 完全隔离。

---

## 环境变量

在 `simulator/` 目录下新建 `.env` 文件（或直接在启动命令中设置）：

```env
# 后端服务地址（默认已指向本地 8000 端口）
BACKEND_URL=http://127.0.0.1:8000

# 与 backend/.env 中 SIMULATOR_API_TOKEN 相同的值
BACKEND_INGEST_TOKEN=your_secret_token_here
```

---
