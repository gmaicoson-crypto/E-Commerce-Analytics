# E-Commerce Analytics - 电商数据分析平台

<p align="center">
  <img src="https://img.shields.io/badge/Vue.js-3.4-green?logo=vuedotjs" alt="Vue.js">
  <img src="https://img.shields.io/badge/TypeScript-5.4-blue?logo=typescript" alt="TypeScript">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/MySQL-8.x-4479a1?logo=mysql" alt="MySQL">
  <img src="https://img.shields.io/badge/ECharts-5.5-aa344d" alt="ECharts">
  <img src="https://img.shields.io/badge/License-MIT-lightgrey" alt="License">
</p>

<p align="center">
  <em>一个面向电商运营场景的全栈数据分析、实时监控与权限管理系统</em>
</p>

---

## 项目简介

E-Commerce Analytics 是一个基于 **Vue 3 + TypeScript + FastAPI + MySQL** 构建的电商数据分析平台。系统围绕真实电商运营中的核心指标展开，提供销售概览、商品分析、用户画像、订单分析、财务汇总、通知中心和系统权限管理等能力。

项目内置独立的 **数据模拟器**，可以持续生成客户、商品、订单、财务和通知数据，并通过后端 Ingest API 写入数据库。后端在数据变化后通过 **Server-Sent Events** 推送事件，前端看板自动刷新，适合课程设计、毕业项目、数据可视化实践和二次开发。

## 🚀 核心特性

### 📊 多维数据看板

- **销售概览**：销售额、订单数、客单价、趋势图、品类占比
- **商品分析**：商品排行、库存预警、分类销售、商品趋势
- **用户画像**：注册趋势、性别分布、年龄段分布、省份热力图
- **订单分析**：订单状态、订单时间线、订单明细、退款联动
- **财务汇总**：收入、支出、净利润、毛利率、财务流水

### ⚡ 实时业务刷新

- **SSE 实时推送**：后端基于 EventBus 广播业务事件
- **自动刷新数据**：前端订阅订单、商品、用户、财务、通知等事件
- **节流更新机制**：避免高频事件导致页面重复请求
- **通知红点同步**：未读消息数量在侧边栏和顶部栏实时同步

### 🔐 角色与权限管理

- **双角色体系**：管理员与员工分离
- **模块级授权**：管理员可按功能模块单独给员工授权或撤权
- **JWT 鉴权**：统一登录态与接口访问保护
- **审计日志**：记录权限变更行为，方便追踪管理操作

### 🧩 数据模拟与演示

- **独立模拟器服务**：默认运行在 `8001` 端口
- **可视化管理 UI**：支持客户、商品、订单、财务、通知 CRUD
- **自动化生成引擎**：按设定频率模拟注册、下单和订单流转
- **真实业务联动**：下单、发货、退款、低库存会触发财务与通知变化

### 🛠️ 工程化设计

- **前端组件化**：通用按钮、徽章、卡片、表格、分页、图表容器
- **后端模块化**：按认证、销售、商品、用户、订单、财务等路由拆分
- **类型安全**：TypeScript + Pydantic 双端数据约束
- **SQL 集中管理**：数据库初始化和维护脚本统一放在 `database/sql`

## 🏗️ 技术栈

### 前端 (Frontend)

- **框架**：Vue 3 + TypeScript
- **构建工具**：Vite
- **状态管理**：Pinia
- **路由**：Vue Router
- **图表**：ECharts
- **地图数据**：GeoJSON 中国省份热力图

### 后端 (Backend)

- **框架**：FastAPI
- **ORM**：SQLAlchemy
- **数据校验**：Pydantic
- **认证**：JWT Token + 密码哈希
- **实时通信**：Server-Sent Events
- **数据库驱动**：PyMySQL

### 数据与工具

- **数据库**：MySQL 8.x
- **模拟器**：FastAPI + httpx + 原生 HTML/CSS/JavaScript
- **包管理**：npm、pip
- **API 文档**：Swagger / OpenAPI

## 🧭 系统架构

```mermaid
flowchart LR
  Browser[浏览器用户] --> Frontend[Vue 前端<br/>Vite :5173]
  Frontend -->|REST API| Backend[FastAPI 后端<br/>:8000]
  Frontend <-->|SSE 实时事件| Backend
  Backend --> DB[(MySQL<br/>ecommerce_db)]

  SimUI[模拟器管理 UI] --> Simulator[数据模拟器<br/>FastAPI :8001]
  Simulator -->|Ingest API| Backend

  Backend --> Auth[JWT 鉴权]
  Backend --> Permission[模块权限]
  Backend --> EventBus[事件总线]
  EventBus --> Backend
```

## 🚦 快速开始

### 环境要求

- Node.js 18+
- Python 3.10+
- MySQL 8.x
- npm 或 pnpm

### 安装步骤

1. **克隆仓库**

   ```bash
   git clone <your-repository-url>
   cd ecommerce-vue-ts
   ```

2. **初始化数据库**

   ```bash
   cd backend
   pip install -r requirements.txt
   python setup_db.py
   ```

3. **配置后端环境变量**

   在 `backend/.env` 中按需配置：

   ```env
   DATABASE_URL=mysql+pymysql://root:password@localhost:3306/ecommerce_db
   SECRET_KEY=please-change-me
   ACCESS_TOKEN_EXPIRE_HOURS=24
   SIMULATOR_API_TOKEN=your-simulator-token
   ```

4. **启动后端服务**

   ```bash
   cd backend
   uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

5. **启动前端应用**

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

6. **启动数据模拟器**

   ```bash
   cd simulator
   pip install -r server/requirements.txt
   uvicorn server.main:app --port 8001 --reload
   ```

7. **访问应用**

   - 前端应用：http://127.0.0.1:5173
   - 后端文档：http://127.0.0.1:8000/docs
   - 模拟器 UI：http://127.0.0.1:8001
   - 健康检查：http://127.0.0.1:8000/health

### 前端环境变量

如需指定后端 API 地址，可在 `frontend/.env.local` 中配置：

```env
VITE_API_BASE=http://127.0.0.1:8000/api
```

### 模拟器环境变量

如后端启用了 `SIMULATOR_API_TOKEN`，请在 `simulator/.env` 中配置同样的 Token：

```env
BACKEND_URL=http://127.0.0.1:8000
BACKEND_INGEST_TOKEN=your-simulator-token
```

## 🧪 功能演示

### 实时数据刷新流程

```text
模拟器创建订单
   ↓
后端写入 orders / order_items / finance_records
   ↓
EventBus 发布 order、finance、notification 事件
   ↓
前端 SSE 连接收到事件
   ↓
相关看板自动重新拉取数据并刷新图表
```

### 订单状态流转

```text
pending（待付款）
  ├── paid（已付款）
  │     └── shipped（已发货）
  │            ├── completed（已完成）
  │            └── refunded（已退款）
  └── cancelled（已取消）
```

### 权限控制示例

- 管理员：默认拥有所有模块访问权限，可管理员工和授权
- 员工：只能访问管理员授予的模块
- 未登录用户：访问业务页面会自动跳转登录页
- 无权限用户：访问受限页面会进入错误提示页

## 📁 项目结构

```text
ecommerce-vue-ts/
├── backend/                     # FastAPI 后端服务
│   ├── routers/                 # API 路由模块
│   │   ├── auth.py              # 登录、注册、个人信息
│   │   ├── system.py            # 员工与权限管理
│   │   ├── sales.py             # 销售分析
│   │   ├── products.py          # 商品分析与管理
│   │   ├── users.py             # 用户画像
│   │   ├── orders.py            # 订单分析
│   │   ├── finance.py           # 财务汇总
│   │   ├── notifications.py     # 通知中心
│   │   ├── sse.py               # 实时事件流
│   │   └── ingest.py            # 模拟器写入接口
│   ├── services/                # 业务服务层
│   ├── models.py                # SQLAlchemy 数据模型
│   ├── schemas.py               # Pydantic 请求/响应模型
│   ├── event_bus.py             # SSE 事件总线
│   ├── database.py              # 数据库连接配置
│   └── main.py                  # 应用入口
│
├── frontend/                    # Vue 3 前端应用
│   ├── src/
│   │   ├── components/          # 通用组件与布局组件
│   │   ├── views/               # 页面视图
│   │   ├── stores/              # Pinia 状态管理
│   │   ├── services/            # API 请求封装
│   │   ├── composables/         # 组合式函数
│   │   ├── router/              # 路由与导航守卫
│   │   ├── types/               # TypeScript 类型定义
│   │   └── utils/               # 工具函数与图表配置
│   └── public/china.json        # 中国地图 GeoJSON
│
├── simulator/                   # 数据模拟器
│   ├── server/                  # 模拟器 FastAPI 服务
│   │   ├── main.py              # 模拟器 API 入口
│   │   ├── automation.py        # 自动化生成引擎
│   │   ├── data_factory.py      # 随机数据工厂
│   │   └── backend_client.py    # 后端 Ingest API 客户端
│   └── static/                  # 模拟器管理 UI
│
├── database/sql/                # 数据库 SQL 脚本
│   ├── create_database.sql      # 初始化数据库
│   ├── reset_business_data.sql  # 清理演示业务数据
│   └── alter_finance_category_enum.sql
│
└── README.md                    # 项目说明文档
```

## 📡 API 模块

| 前缀 | 功能 |
| --- | --- |
| `/api/auth` | 登录、注册、个人信息、修改密码 |
| `/api/system` | 员工管理、模块权限、审计日志 |
| `/api/sales` | 销售 KPI、趋势、品类分析 |
| `/api/products` | 商品分析、库存预警、商品管理 |
| `/api/users` | 用户增长、用户画像、地域分布 |
| `/api/orders` | 订单 KPI、订单状态、订单明细 |
| `/api/finance` | 财务 KPI、收支趋势、财务流水 |
| `/api/notifications` | 通知列表、未读数、批量操作 |
| `/api/sse` | SSE 实时事件推送 |
| `/api/ingest` | 数据模拟器写入接口 |

## 🧑‍💻 开发命令

```bash
# 前端开发
cd frontend
npm run dev
npm run build
npm run preview

# 后端开发
cd backend
uvicorn main:app --reload --port 8000
python setup_db.py

# 数据模拟器
cd simulator
uvicorn server.main:app --port 8001 --reload
```

## 📜 许可证

本项目建议采用 [MIT License](LICENSE) 开源许可

## 🙏 致谢

- 感谢 [Vue.js](https://vuejs.org/) 社区提供优秀的前端框架
- 感谢 [FastAPI](https://fastapi.tiangolo.com/) 带来的高效 Python Web 开发体验
- 感谢 [ECharts](https://echarts.apache.org/) 提供强大的数据可视化能力
- 感谢所有开源项目和学习资料对本项目的启发



2026 © [gmaicoson-crypto](https://github.com/gmaicoson-crypto)
