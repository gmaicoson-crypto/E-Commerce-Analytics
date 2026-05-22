# Backend — 电商数据分析平台后端

基于 **FastAPI + SQLAlchemy + MySQL** 构建的 RESTful API 服务，提供用户认证、业务数据查询、实时推送以及模拟器数据写入等功能。

---

## 目录结构

```
backend/
├── main.py                     # 应用入口
├── database.py                 # 数据库连接 & 配置加载
├── models.py                   # SQLAlchemy ORM 数据表定义
├── schemas.py                  # Pydantic 请求/响应数据模型
├── auth.py                     # 密码哈希 & JWT 签发/验证
├── dependencies.py             # FastAPI 依赖注入（鉴权、权限检查）
├── utils.py                    # 通用工具函数（日期解析、统一响应格式）
├── event_bus.py                # 内存事件总线（SSE 实时推送核心）
├── email_service.py            # SMTP 邮件发送（管理员注册验证码）
├── setup_db.py                 # 一次性脚本：初始化数据库
├── _alter_finance_category.py  # 一次性迁移脚本：扩展财务分类 ENUM
├── requirements.txt            # Python 依赖清单
├── .env                        # 本地环境变量（不入版本库）
├── .env.example                # 环境变量模板
├── routers/                    # 各业务域路由模块
│   ├── auth.py                 # 认证：登录、注册、个人信息
│   ├── system.py               # 系统管理：员工、权限
│   ├── sales.py                # 销售分析 API
│   ├── products.py             # 商品分析 API
│   ├── users.py                # 用户（客户）分析 API
│   ├── orders.py               # 订单分析 API
│   ├── finance.py              # 财务分析 API
│   ├── notifications.py        # 通知消息 API
│   ├── sse.py                  # Server-Sent Events 实时推送
│   ├── notify.py               # 内部通知触发接口
│   └── ingest.py               # 数据模拟器写入接口
└── services/
    └── ingest_service.py       # ingest 路由的业务逻辑层
```

---

## 根目录文件详解

### `main.py` — 应用入口

创建 FastAPI 实例，注册所有路由，启用 CORS，并在启动时通过 `Base.metadata.create_all` 自动建表。所有路由按 `/api/<domain>` 前缀挂载。

### `database.py` — 数据库连接 & 配置

- `Settings`（Pydantic BaseSettings）：从 `.env` 文件加载所有环境变量，包括数据库 URL、JWT 密钥、SMTP 参数、模拟器鉴权 Token 等。
- `engine`：SQLAlchemy 连接引擎，`pool_pre_ping=True` 防止连接超时断开。
- `SessionLocal`：数据库会话工厂。
- `get_db()`：FastAPI 依赖函数，每次请求获取一个 DB Session，请求结束后自动关闭。

### `models.py` — 数据表定义

用 SQLAlchemy ORM 定义所有数据库表及枚举类型：

| 枚举 / 表 | 说明 |
|---|---|
| `CategoryEnum` | 商品品类（服装/电子/食品/家居/美妆） |
| `OrderStatusEnum` | 订单状态（pending/paid/shipped/completed/cancelled/refunded） |
| `FinanceCategoryEnum` | 财务科目（销售收入/商品成本/物流成本/广告费/退款支出） |
| `Admin` | 管理员账号表 |
| `AdminVerificationCode` | 管理员注册邮箱验证码（10 分钟有效） |
| `Employee` | 员工账号表（受权限管控） |
| `Module` | 功能模块表（对应前端页面权限） |
| `EmployeeModulePermission` | 员工-模块权限关联表 |
| `PermissionChangeLog` | 权限变更审计日志 |
| `Product` | 商品表（含库存、低库存阈值、上下架状态） |
| `Customer` | 客户表（含性别、年龄段、省份、客户类型） |
| `Order` | 订单主表（含订单号、总金额、状态时间轴） |
| `OrderItem` | 订单明细表（商品、数量、单价、小计） |
| `Refund` | 退款表（退款金额、原因、状态） |
| `FinanceRecord` | 财务流水表（类型/科目/金额/关联订单） |
| `Notification` | 系统通知表（库存/退款/订单/销售告警） |

### `schemas.py` — Pydantic 数据模型

定义所有接口的请求体和响应体结构，与 ORM 模型解耦：

- **通用**：`APIResponse[T]`（泛型统一响应）、`PaginatedData[T]`（分页响应）
- **认证**：`LoginRequest`、`AdminRegisterRequest`、`TokenResponse`、`UserInfo`
- **系统**：`EmployeeCreate/Update/Out`、`PermissionUpdate`、`PermissionLogOut`
- **销售**：`SalesKPIOut`、`TrendPoint`、`CategoryShare`、`ProvinceData`
- **商品**：`ProductRankItem`、`InventoryWarning`、`ProductListItem`
- **用户**：`UserKPIOut`、`TypeRatio`、`ProvinceUserData`、`AgeGroupData`
- **订单**：`OrderKPIOut`、`OrderStatusItem`、`OrderListItem`
- **财务**：`FinanceKPIOut`、`FinanceTrendPoint`、`ExpenseBreakdown`
- **通知**：`NotificationOut`
- **AI**：`AIChatRequest/Response`（预留 DeepSeek 接口结构）

### `auth.py` — 认证工具

- `hash_password` / `verify_password`：基于 `pbkdf2_sha256` 的密码哈希。
- `create_access_token`：生成 JWT，payload 含 `sub`（用户 ID）、`role`（admin/employee）、`table`（所在数据库表名）。
- `decode_access_token`：验证并解码 JWT，失败返回 `None`。

### `dependencies.py` — 依赖注入

提供三个核心 FastAPI 依赖：

- `get_current_user`：从 Bearer Token 解析用户身份，同时查询 Admin 或 Employee 表确认账号存在且启用。
- `require_admin`：在 `get_current_user` 基础上强制要求管理员角色，用于系统管理类接口。
- `check_module_permission(module_key)`：工厂函数，生成检查员工是否有某功能模块访问权限的依赖（管理员自动放行）。

### `utils.py` — 工具函数

- `parse_date_range`：将前端传入的日期范围参数（`"7"`/`"30"`/`"90"`/`"today"`/`"custom"`）解析为 `(start_date, end_date)` 元组。
- `get_prev_period`：计算同等时长的上一周期，用于同比（YoY）计算。
- `is_returning_customer` / `customer_type_label` / `new_customer_threshold`：基于注册时间（15 天阈值）动态判定新老客户类型。
- `success_response` / `error_response`：生成统一格式的 JSON 响应体 `{code, message, data}`。

### `event_bus.py` — 内存事件总线

实现基于 `asyncio.Queue` 的发布-订阅机制，驱动 SSE 实时推送：

- `EventBus.subscribe()`：为每个 SSE 客户端创建独立的消息队列并注册。
- `EventBus.publish(entity, action, payload)`：同步广播事件给所有订阅者，队列满时丢弃（防慢消费者阻塞）。
- `bus`：全局单例，所有路由通过它发布事件。
- `encode_sse(event)`：将事件 dict 序列化为 `data: {...}\n\n` 格式的 SSE 文本帧。

### `email_service.py` — SMTP 邮件服务

封装标准库 `smtplib`，从 `database.Settings` 读取 SMTP 配置，支持 SSL（465 端口）和 STARTTLS（587 端口）两种连接方式。目前用于管理员注册时发送 6 位验证码邮件。

### `setup_db.py` — 数据库初始化脚本（一次性运行）

读取 `database/sql/create_database.sql`，通过 `pymysql` 直连 MySQL 执行建库 SQL。在项目首次部署时运行一次：

```bash
cd backend
python setup_db.py
```

### `_alter_finance_category.py` — 数据库迁移脚本（一次性运行）

执行 `database/sql/alter_finance_category_enum.sql`，用于扩展 `finance_records.category` 字段的 ENUM 枚举值。属于一次性变更脚本，命名以 `_` 开头以示区别：

```bash
cd backend
python _alter_finance_category.py
```

### `requirements.txt` — 依赖清单

| 包 | 用途 |
|---|---|
| `fastapi` | Web 框架 |
| `uvicorn[standard]` | ASGI 服务器 |
| `sqlalchemy` | ORM |
| `pymysql` | MySQL 驱动 |
| `python-jose[cryptography]` | JWT 签发/验证 |
| `passlib[bcrypt]` | 密码哈希 |
| `pydantic` / `pydantic-settings` | 数据校验 & 配置管理 |
| `python-dotenv` | `.env` 文件加载 |
| `httpx` | 异步 HTTP 客户端（预留外部调用） |

---

## routers/ — 路由模块详解

### `auth.py` — 认证路由 `/api/auth`

| 接口 | 说明 |
|---|---|
| `POST /login` | 用邮箱或用户名登录，同时查管理员/员工表，返回 JWT 及权限列表 |
| `POST /admin/send-code` | 向指定邮箱发送 6 位注册验证码（60 秒限频） |
| `POST /admin/register` | 校验验证码后创建管理员账号 |
| `POST /logout` | 登出（JWT 无状态，仅返回成功） |
| `GET /me` | 获取当前登录用户信息及权限列表 |
| `PATCH /me` | 修改当前用户的用户名/邮箱 |
| `POST /me/password` | 修改当前用户密码（需验证旧密码） |

### `system.py` — 系统管理路由 `/api/system`

管理员专用接口，负责员工账号和模块权限的 CRUD：

- 员工管理：创建员工、查询员工列表（含当前权限）、启用/禁用员工、重置员工密码。
- 权限管理：为员工授权/撤销功能模块权限，写入审计日志。
- 日志查询：分页查看权限变更历史记录。

### `sales.py` — 销售分析路由 `/api/sales`

提供销售大盘数据，均支持日期范围过滤：

- KPI 看板：总销售额、订单数、客单价、退款率（含同比变化率）。
- 趋势图：按天/周的销售额与订单数折线数据。
- 品类分析：各品类销售占比。
- 地域分析：各省份销售额分布。
- 明细接口：支持下钻的销售趋势明细表（日期×金额×订单数）、品类销售明细。

### `products.py` — 商品分析路由 `/api/products`

- 销量排行：TOP N 商品榜单（销售数量/金额排序）。
- 库存预警：低于阈值的商品列表。
- 商品列表：支持按品类、状态过滤，含销量统计。
- 商品管理：修改单个商品的价格/库存/状态/低库存阈值。
- 趋势分析：指定商品的近期销售趋势。

### `users.py` — 用户分析路由 `/api/users`

- KPI：总客户数、新客数、老客数（含同比）。
- 新老客比例：饼图数据。
- 注册趋势：按天的新增客户曲线。
- 地域分布：各省客户数及占比。
- 年龄段分布、性别分布。

### `orders.py` — 订单分析路由 `/api/orders`

- KPI：总订单数、已完成数、退款数、平均订单金额（含同比）。
- 状态分布：各状态订单数及占比。
- 订单趋势：按天的订单量折线。
- 订单列表：分页查询，支持按状态过滤，含客户名/金额/状态。
- 退款列表：退款明细分页查询。
- 订单明细：单个订单的商品明细。

### `finance.py` — 财务分析路由 `/api/finance`

- KPI：总收入、总支出、净利润、利润率（含同比）。
- 收支趋势：按天的收入/支出曲线。
- 支出结构：各费用科目（物流/广告/退款/成本）金额及占比。
- 财务流水：分页列表，支持按类型/科目过滤。

### `notifications.py` — 通知路由 `/api/notifications`

- 分页查询通知列表，支持按类型和已读状态过滤。
- 标记单条/全部通知为已读。
- 查询未读通知数量（前端徽标用）。

### `sse.py` — SSE 实时推送路由 `/api/sse`

基于 `event_bus` 实现 Server-Sent Events，将后端业务事件实时推送到前端：

- `GET /events`：订阅全量事件流（推荐前端使用）。
- `GET /orders`：仅接收订单和财务相关事件。
- `GET /finance`：仅接收财务和订单相关事件。
- `GET /dashboard`：兼容旧接口，等同于全量事件流。

> Token 通过 Query 参数传入（`?token=...`），因为浏览器 `EventSource` API 不支持自定义请求头。连接建立后每 15 秒发送 `: ping` 心跳防止超时断开。

### `notify.py` — 内部通知触发路由 `/api/notify`

提供给内部逻辑或管理员手动触发通知的接口，写入 `notifications` 表并通过 `event_bus` 广播给 SSE 订阅者。

### `ingest.py` — 模拟器数据写入路由 `/api/ingest`

专为数据模拟器设计的写入接口，所有接口以 `SIMULATOR_API_TOKEN` 做 Bearer Token 鉴权：

- 提供客户、商品、订单、财务记录、通知的完整 **增删改查**（CRUD）接口。
- 每次写入操作执行后，通过 `event_bus.publish()` 广播事件，触发前端实时刷新。
- 订单状态变更时自动处理联动副作用（生成/删除财务流水、触发低库存或大额订单通知）。

---

## services/ — 服务层

### `services/ingest_service.py` — Ingest 业务逻辑

将 `ingest.py` 路由中的所有数据库操作提取为独立函数，保持路由层简洁：

- `IngestError`：业务异常类，携带 HTTP 状态码，由路由层统一转换为 HTTPException。
- 各实体的 `create_*` / `update_*` / `delete_*` / `list_*` 函数。
- 订单状态机逻辑：`create_order` 自动生成财务流水（销售收入/商品成本），`update_order_status` 处理支付/完成/取消/退款各状态的库存扣减、财务记录增删及通知生成。
- `delete_many`：批量删除的通用包装函数。

---

## 环境变量配置

复制 `.env.example` 为 `.env` 并填写实际值：

```env
# 数据库
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/ecommerce_db

# JWT（生产环境务必更换为随机长字符串）
SECRET_KEY=your-256-bit-secret-key
ACCESS_TOKEN_EXPIRE_HOURS=24

# SMTP（管理员注册验证码邮件，不配置则注册功能不可用）
SMTP_HOST=smtp.163.com
SMTP_PORT=465
SMTP_USER=yourname@163.com
SMTP_PASS=your-auth-code

# 模拟器鉴权 Token（不设置则 /api/ingest/* 接口无需鉴权）
SIMULATOR_API_TOKEN=your-simulator-token

# DeepSeek AI（预留，暂未启用）
DEEPSEEK_API_KEY=sk-xxx
```

---

## 快速启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 初始化数据库（仅首次）
python setup_db.py

# 启动开发服务器
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API 文档自动生成，访问 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)。
