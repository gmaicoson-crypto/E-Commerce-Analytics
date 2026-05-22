# Frontend 前端项目文档

本项目前端基于 **Vue 3 + TypeScript + Vite** 构建，使用 Pinia 做状态管理、Vue Router 做路由、ECharts 做数据可视化。

---

## 目录结构总览

```
frontend/
├── index.html                  # HTML 入口模板
├── package.json                # 依赖声明与 npm 脚本
├── vite.config.ts              # Vite 构建配置
├── tsconfig.json               # TypeScript 项目引用配置
├── tsconfig.app.json           # 应用主 TypeScript 编译配置
├── tsconfig.node.json          # Node 侧（vite.config.ts）编译配置
└── src/
    ├── main.ts                 # Vue 应用入口
    ├── App.vue                 # 根组件
    ├── env.d.ts                # 环境变量类型声明
    ├── router/                 # 路由配置
    ├── stores/                 # Pinia 全局状态
    ├── services/               # API 请求封装
    ├── types/                  # TypeScript 类型定义
    ├── composables/            # 可复用组合式函数
    ├── utils/                  # 通用工具与常量
    ├── layouts/                # 页面布局外壳
    ├── components/             # 可复用 UI 组件
    └── views/                  # 页面级视图组件
```

---

## 项目配置文件

### `package.json`

npm 包声明文件，定义项目依赖和构建脚本。

| 脚本 | 说明 |
|------|------|
| `npm run dev` | 启动 Vite 开发服务器（热更新） |
| `npm run build` | 先执行 `vue-tsc --noEmit` 类型检查，再执行 Vite 生产构建 |
| `npm run preview` | 本地预览生产构建产物 |

主要依赖：

| 包 | 版本 | 用途 |
|----|------|------|
| vue | 3.4.x | 核心框架 |
| vue-router | 4.3.x | 客户端路由 |
| pinia | 2.1.x | 全局状态管理 |
| echarts | 5.5.x | 数据可视化图表库 |

### `vite.config.ts`

Vite 构建工具配置：
- 启用 `@vitejs/plugin-vue` 插件以支持 `.vue` 单文件组件
- 配置路径别名：`@` → `src/`，所有 `import` 中的 `@/xxx` 均指向 `src/xxx`

### `tsconfig.json` / `tsconfig.app.json` / `tsconfig.node.json`

TypeScript 分层配置：
- `tsconfig.json`：顶层，通过 `references` 组合以下两份配置
- `tsconfig.app.json`：应用代码（`src/`）的编译选项，启用 `strict`、`verbatimModuleSyntax`，包含 Volar 对 Vue 模板的类型检查
- `tsconfig.node.json`：仅用于编译 `vite.config.ts`，不参与应用构建

---

## `src/` 源码目录

### 顶层文件

#### `src/main.ts`

Vue 应用程序的**入口文件**，负责：
1. 创建 Vue 应用实例（`createApp(App)`）
2. 注册 Pinia 状态管理（`createPinia()`）
3. 注册 Vue Router（`createRouter(...)`）
4. 挂载根组件到 `#app` DOM 节点

#### `src/App.vue`

**根组件**，是所有页面的最外层容器：
- 渲染 `<RouterView>`，由路由决定展示哪个页面
- 挂载全局的 `<ChartDetailModal>`（图表详情弹窗），使其在整个应用生命周期内只存在一个实例
- 不包含任何业务逻辑

#### `src/env.d.ts`

TypeScript **环境变量类型声明**：
- 为 `import.meta.env.VITE_API_BASE` 提供类型定义
- 告知 TypeScript 编译器 Vite 注入的环境变量的类型，避免 `unknown` 报错

---

### `src/router/`

#### `router/index.ts`

Vue Router 路由配置，定义所有页面路由与**导航守卫**。

**路由表：**

| 路径 | 组件 | 说明 |
|------|------|------|
| `/login` | `LoginView` | 登录页（未登录时的入口） |
| `/sales` | `SalesView` | 销售概览（默认首页） |
| `/products` | `ProductView` | 商品分析 |
| `/users` | `UserView` | 用户分析 |
| `/orders` | `OrderView` | 订单分析 |
| `/finance` | `FinanceView` | 财务汇总（仅管理员） |
| `/system` | `SystemView` | 系统管理（仅管理员） |
| `/notifications` | `NotificationsView` | 通知中心（仅管理员） |
| `/:pathMatch(.*)` | `ErrorView` | 404 页面 |

**导航守卫逻辑：**
1. 未登录用户访问任何需要认证的页面 → 强制跳转 `/login`
2. 已登录用户访问 `/login` → 自动跳转 `/sales`
3. 员工（非管理员）访问 `adminOnly` 路由 → 跳转 `/403`（ErrorView）

---

### `src/stores/`

使用 Pinia 管理全局状态。

#### `stores/authStore.ts`

**认证状态管理**，是整个应用权限体系的核心：

- **状态（State）：** `token`、`role`（`admin` / `employee`）、`username`、`email`、`permissions`（模块权限数组）
- **持久化：** 所有状态存入 `localStorage`，刷新页面后自动恢复登录态
- **Actions：**
  - `login(email, password, role)` — 调用登录 API，存储返回的 token 和用户信息
  - `logout()` — 清空所有状态并跳转到登录页
  - `hasPermission(moduleKey)` — 检查当前用户是否拥有特定模块权限
  - `refreshPermissions()` — 从服务器重新拉取权限列表（权限变更后同步）
  - `updateProfile(username, email)` — 更新用户资料
  - `changePassword(oldPwd, newPwd)` — 修改密码

#### `stores/realtimeStore.ts`

**实时事件状态管理**，维护 SSE（Server-Sent Events）长连接：

- 建立并维护单条 `EventSource` 连接，连接后端 `/api/sse/stream` 端点
- 监听各实体变更事件，为每类实体维护一个**递增计数器**：`orderCount`、`productCount`、`customerCount`、`notificationCount`、`financeCount`、`refundCount`、`systemCount`
- 视图层通过 `useEventStream` 订阅这些计数器，数字增加时触发数据刷新
- 连接断开时自动重连

---

### `src/services/`

#### `services/api.ts`

后端 **API 请求封装层**，所有与服务器的通信都通过此文件进行。

- 基于 `fetch` 封装了 `ApiClient` 类
- 自动在请求头中注入 `Authorization: Bearer <token>`
- 响应统一解包，只返回 `data` 字段的内容
- 请求失败时抛出含错误消息的 `Error`

提供的 API 分组：

| 分组 | 方法示例 | 说明 |
|------|---------|------|
| `auth` | `login()`, `register()`, `getProfile()` | 认证与用户信息 |
| `sales` | `getKpi()`, `getTrend()`, `getCategory()` | 销售数据 |
| `products` | `getKpi()`, `getList()`, `create()`, `update()`, `delete()` | 商品管理与分析 |
| `users` | `getKpi()`, `getTrend()`, `getGender()`, `getProvinces()` | 用户分析 |
| `orders` | `getKpi()`, `getTimeline()`, `getList()` | 订单分析 |
| `finance` | `getKpi()`, `getTrend()`, `getExpenseBreakdown()`, `getList()` | 财务汇总 |
| `notifications` | `getList()`, `markRead()`, `deleteOne()`, `deleteMany()` | 通知管理 |
| `system` | `getEmployees()`, `addEmployee()`, `getPermissions()`, `updatePermission()`, `getLogs()` | 系统管理 |

---

### `src/types/`

#### `types/index.ts`

项目全局 **TypeScript 类型定义文件**，集中声明所有共享接口：

| 类型 | 说明 |
|------|------|
| `Role` | `'admin' \| 'employee'` 枚举联合类型 |
| `NavItem` | 侧边栏导航项（key, label, icon） |
| `TableColumn<T>` | 数据表格列配置，支持自定义渲染函数 `render()` 和列头渲染 `headerRender()` |
| `BadgeColor` | 徽章颜色枚举（green / red / yellow / blue / purple / gray / orange） |
| `NotificationType` | 通知类型枚举（order / product / customer / refund / system） |
| `Notification` | 单条通知数据结构 |
| `ProductPerformance` | 商品绩效数据（销量、销售额、库存等） |
| `LowStockProduct` | 低库存商品数据 |
| `OrderListItem` | 订单列表行数据 |
| `FinanceRecord` | 财务记录行数据 |
| `Employee` | 员工信息（id、用户名、邮箱、创建时间） |
| `SystemModule` | 系统模块定义（key、名称） |
| `PermissionLog` | 权限变更审计日志 |

---

### `src/composables/`

可复用的**组合式函数**（Composition API），封装跨组件共享的响应式逻辑。

#### `composables/useUnreadCount.ts`

**未读通知计数**全局单例：

- 在模块级别（非组件内部）创建 `unreadCount` ref，所有使用方共享同一个响应式引用
- `refreshUnread()` — 异步拉取未读通知数量并更新 ref
- 被 `Sidebar`（左侧红点）、`TopBar`（铃铛图标）、`NotificationsView`（页面标题）三处共同使用

#### `composables/useEventStream.ts`

**防抖/节流数据刷新**组合式函数：

- `useDebouncedReload(entities, reload, delayMs?)`
  - `entities`：要监听的实体名称数组（如 `['order', 'product']`）
  - `reload`：数据刷新回调函数
  - `delayMs`：节流间隔（默认 1000ms）
- 监听 `realtimeStore` 中对应实体的计数器变化
- 使用**节流**（leading + trailing）而非防抖，避免高频事件（如 2000 条/分钟）造成回调堆积或长时间不触发
- 所有使用实时数据的视图都通过此 composable 订阅更新

#### `composables/useChartDetail.ts`

**图表详情弹窗**全局状态：

- 维护一个 `current` ref，存储当前要展示的图表配置
- `open(config)` — 打开弹窗，传入包含 `title`、`load()`、`filters` 等字段的配置对象
- `close()` — 关闭弹窗，清空 `current`
- `load()` 是一个异步函数，负责拉取详情数据并返回 `{ chartOption, columns, rows }`
- 任何视图中点击图表放大按钮时调用 `open()`，全局唯一的 `ChartDetailModal` 组件响应渲染

---

### `src/utils/`

#### `utils/constants.ts`

**全局常量与格式化工具**：

- **ECharts 样式常量：** 调色盘颜色数组（`PALETTE`）、tooltip 样式、坐标轴标签样式，保证所有图表视觉风格统一
- **格式化函数：**
  - `fmtDateTime(str)` — 将 ISO 日期字符串格式化为 `YYYY-MM-DD HH:mm` 可读格式
  - `fmtMoneyCN(value)` — 金额格式化，≥10000 时自动转换为「万」单位（如 `12000` → `1.2万`）
  - `recentDayLabels(n)` — 生成最近 n 天的日期标签数组，用于图表 X 轴
- **字典映射：**
  - 订单状态中英文映射（`pending` → `待付款` 等）
  - 通知类型颜色映射（`order` → `blue` 等）
  - 商品分类中文名称映射

#### `utils/chinaMap.ts`

**中国省份地图懒加载工具**：

- 首次调用时异步 `fetch('/china.json')` 加载 GeoJSON 数据，并通过 `echarts.registerMap('china', ...)` 注册到 ECharts
- 后续调用直接返回，不重复加载（通过 `Promise` 缓存）
- 内置完整/简写省份名称双向映射（如 `北京` ↔ `北京市`），确保地图热力图数据能正确匹配到省份区域
- 被 `UserView` 的省份分布热力图使用

---

### `src/layouts/`

#### `layouts/MainLayout.vue`

登录后所有页面共用的**主布局外壳**：

- 结构：左侧 `<Sidebar>` + 右侧内容区（上方 `<TopBar>` + 下方 `<RouterView>`）
- 在 `onMounted` 时建立 SSE 连接（通过 `realtimeStore`）
- 订阅 `notification` 实体变更事件，自动调用 `refreshUnread()` 更新未读徽章
- 不含业务逻辑，仅负责整体结构排布

---

### `src/components/`

可复用 UI 组件，分为两个子目录。

---

#### `components/layout/` — 布局专用组件

这些组件仅被 `MainLayout.vue` 使用，负责页面框架的各个区域。

##### `layout/Sidebar.vue`

**左侧导航栏**（宽 60px 折叠图标式）：

- 渲染 7 个导航按钮，每个对应一个路由
- 当前激活路由的图标高亮显示
- 通知按钮右上角显示红点（`unreadCount > 0` 时）
- 鼠标悬停时显示 tooltip 文字（销售概览、商品分析等）
- 底部有退出登录按钮，调用 `authStore.logout()`

##### `layout/TopBar.vue`

**顶部工具栏**：

- 左侧：`HeadlineMarquee`（滚动公告栏）
- 中部：`HotProductsTicker`（热销商品跑马灯，仅管理员可见）
- 右侧：当前日期、通知铃铛（含未读红点）、用户头像按钮
- 点击用户头像打开**个人信息弹窗**：可修改用户名、邮箱，也可修改密码

##### `layout/HeadlineMarquee.vue`

**公告滚动栏**（水平自动滚动文字）：

- 自动获取最新通知、热销商品和销售提醒，拼接为滚动文本
- 内容越多滚动越慢（根据总字符数动态调整 `animation-duration`）
- 点击特定类型的通知条目可跳转到对应详情页
- 收到实时事件时自动刷新内容

##### `layout/HotProductsTicker.vue`

**热销商品轮播**（仅管理员可见）：

- 展示销量前 7 的商品，每 8 秒自动切换一条
- 切换时有翻转动画（CSS 3D transform）
- 鼠标悬停时暂停自动切换
- 订阅商品实体变更事件，数据有更新时重新拉取

---

#### `components/common/` — 通用 UI 组件库

这些组件是项目的基础 UI 积木，可在任意视图中复用。

##### `common/AppIcon.vue`

**SVG 图标组件**：

- 内置 30+ 个业务图标（barChart、sales、products、users、orders、finance、settings、bell、user、logout、search、trendUp、trendDown、edit、eye、refresh、checkCircle、alertCircle、package、map、maximize、close 等）
- Props：`name`（图标名）、`size`（像素尺寸，默认 20）、`color`（默认继承 `currentColor`）
- 纯 SVG 渲染，无外部依赖

##### `common/AppBtn.vue`

**通用按钮组件**：

- `variant`：`primary`（绿色实心）/ `outline`（描边）/ `ghost`（透明）/ `danger`（红色）
- `size`：`sm`（小）/ `md`（默认）
- 可在按钮内添加图标（通过 slot 插入 AppIcon）
- 点击时 emit `click` 事件

##### `common/AppBadge.vue`

**状态徽章标签**：

- 用于展示订单状态、通知类型等标签
- `color`：green / red / yellow / blue / purple / gray / orange
- `size`：sm / md（控制内边距和字号）
- 圆角胶囊形状

##### `common/AppCard.vue`

**卡片容器**：

- 带阴影和圆角的内容卡片
- 可选 `title` 和 `subtitle` 属性（显示卡片头部）
- 默认 slot 渲染卡片体内容
- 若子元素为唯一子节点，自动居中布局

##### `common/KpiCard.vue`

**KPI 指标卡片**（带数字动画）：

- 展示单个关键业务指标（如总销售额、订单数等）
- 数值从旧值到新值有 600ms 的**缓动动画**（easeOutCubic 插值）
- 可配置：`title`（指标名）、`value`（数值字符串，支持「1.2万」「¥999」等格式）、`icon`、`prefix`/`suffix`
- 可选：`change`（涨跌百分比，显示绿涨红跌箭头）或 `subValue`（次要数值）

##### `common/LegendItem.vue`

**图例条目组件**：

- 一行内显示：色块 + 标签文字 + 可选数值 + 可选百分比
- 专为饼图/环形图图例设计，与 ECharts 的内置图例互补
- 百分比右对齐

##### `common/TabBar.vue`

**标签页切换栏**：

- 水平排列的多个 Tab 按钮
- 激活 Tab 下方有绿色下划线
- 点击时 emit `change` 事件，传递选中的 Tab key

##### `common/PageHeader.vue`

**页面标题栏**：

- 大号页面标题（24px、900 字重）+ 可选副标题（灰色 13px）
- 右侧提供 `actions` 插槽，用于放置按钮等操作元素

##### `common/ThemedSelect.vue`

**主题化下拉选择框**：

- 替代原生 `<select>`，样式完全自定义（绿色主题）
- Props：`modelValue`（当前值）、`options`（`{ label, value }` 数组）、`placeholder`、`minWidth`
- 支持 `v-model` 双向绑定
- 点击外部区域自动关闭下拉

##### `common/ColumnFilter.vue`

**列多选筛选器**（用于表格列头）：

- 弹出复选框列表，支持全选/清空
- 当有筛选条件激活时，列头显示蓝色圆点指示器
- 点击外部自动关闭

##### `common/ColumnTextFilter.vue`

**列文本筛选器**（用于表格列头）：

- 弹出文本输入框，支持 Enter 确认、Esc 取消
- 确认时对输入值做 trim 处理
- 有筛选词时列头显示蓝色圆点指示器

##### `common/DataTable.vue`

**客户端分页数据表格**：

- 接受 `columns`（列配置）和 `data`（数据数组）
- 支持 `TableColumn.render()` 自定义单元格渲染（返回 VNode 或字符串）
- 支持 `TableColumn.headerRender()` 自定义列头（用于嵌入 ColumnFilter）
- 分页：`pageSize`（默认 20）、显示「第 N 页 / 共 M 页」
- 分页按钮带省略号（只显示当前页附近 5 个按钮）

##### `common/Pagination.vue`

**独立分页控件**：

- 可单独使用的分页 UI 组件（非绑定表格）
- 显示总条数、上一页/下一页按钮、页码按钮（带省略号）
- emit `update:page` 事件

##### `common/InfiniteTable.vue`

**无限滚动数据表格**：

- 使用 **Intersection Observer** 监听列表底部的哨兵元素
- 当哨兵进入视口时自动调用 `loader(page)` 回调加载下一页
- 显示「已加载 N / 共 M 条」底部提示
- `resetKey` prop 变化时重置到第一页（用于筛选条件改变后重新加载）
- 当 KPI 区域滚动出视口时显示「回到顶部」按钮

##### `common/EChartBox.vue`

**ECharts 图表容器组件**：

- 接受任意 ECharts `option` 配置对象（prop 类型为 `unknown` 以绕过 ECharts 内部类型复杂度）
- 初始化 `echarts.ECharts` 实例，绑定到 DOM
- 监听 `option` prop 变化，调用 `chart.setOption()` 刷新图表
- 通过 `ResizeObserver` + `window resize` 事件监听容器尺寸变化，自动调用 `chart.resize()`
- 组件销毁时自动 `chart.dispose()` 释放资源

##### `common/ChartDetailModal.vue`

**图表详情全屏弹窗**：

- 全局只有一个实例（挂载在 `App.vue` 根节点），通过 `useChartDetail()` composable 控制显隐
- 布局：左侧大图（占 1.8fr）+ 右侧明细表格（占 1fr）
- 支持筛选条件下拉（如选择时间维度、商品分类等），筛选条件变更时自动重新加载
- 数据通过外部传入的 `load()` 异步函数获取，内部处理 loading/error 状态
- 按 Esc 键或点击背景遮罩关闭弹窗
- 使用 `Teleport to="body"` 渲染，不受父组件 `z-index` 影响

---

### `src/views/`

**页面级视图组件**，每个对应一个路由，包含完整的业务逻辑和数据获取。

#### `views/LoginView.vue`

**登录页面**：

- 支持**管理员**和**员工**两个角色的登录（Tab 切换）
- 管理员 Tab 下额外提供注册新管理员账号的入口（展开注册表单）
- 表单校验：邮箱格式、密码非空
- 登录成功后调用 `authStore.login()`，自动跳转到 `/sales`
- 错误信息行内展示

#### `views/ErrorView.vue`

**错误页面**（403 / 404）：

- 根据路由 meta 或 query 参数判断错误类型
- 显示大号错误码 + 说明文字
- 提供「返回销售概览」按钮

#### `views/SalesView.vue`

**销售概览仪表板**（所有角色可访问）：

- **KPI 区域：** 4 张 KpiCard（总销售额、订单总数、平均客单价、已完成订单数）
- **销售趋势：** 折线图（最近 30 天每日销售额），点击放大按钮打开详情弹窗（可筛选 7/30/90/365 天）
- **品类占比：** 饼图（各商品品类销售额占比）+ 图例，点击放大打开详情弹窗
- **品类柱状图：** 各品类对比条形图
- 通过 `useEventStream(['order'])` 订阅订单变更，实时刷新数据

#### `views/ProductView.vue`

**商品分析页**（所有角色可访问）：

- **KPI 区域：** 4 张 KpiCard（在售商品数、总销量、低库存商品数、滞销商品数）
- **商品管理表格：** 支持搜索、分类筛选、状态筛选；管理员可新增/编辑/删除商品
- **品类销售饼图：** 各品类销售额占比，可放大查看详情
- **每日品类 Top5：** 折线图，展示最近 N 天各品类每日销量前 5
- **商品趋势：** 可选择特定商品查看其销量趋势折线图
- 通过 `useEventStream(['product', 'order'])` 订阅变更

#### `views/UserView.vue`

**用户分析页**（所有角色可访问）：

- **KPI 区域：** 3 张 KpiCard（注册用户总数、新增用户、活跃用户）
- **新老用户比：** 饼图（新用户 vs. 复购用户），可放大查看按时间段分布
- **注册趋势：** 折线图（最近 30 天每日新注册用户数），可放大筛选时间范围
- **性别分布：** 饼图，可放大查看详情
- **省份热力图：** 中国地图（choropleth），颜色深浅表示用户数量；右侧显示 Top10 省份排名表
- 通过 `useEventStream(['customer'])` 订阅变更
- 地图首次展示时懒加载 `chinaMap.ts`

#### `views/OrderView.vue`

**订单分析页**（所有角色可访问）：

- **KPI 区域：** 8 张 KpiCard（按状态细分：待付款、已付款、已发货、已完成、已取消、已退款，以及平均客单价）
- **状态分布：** 饼图（各状态订单数占比），可放大查看
- **订单时间线：** 折线图（按小时/日粒度展示订单量），可放大筛选时间范围
- **订单明细表：** 无限滚动表格，支持按状态筛选、按日期范围筛选
- 通过 `useEventStream(['order', 'refund'])` 订阅变更

#### `views/FinanceView.vue`

**财务汇总页**（**仅管理员可访问**）：

- **KPI 区域：** 4 张 KpiCard（总收入、总支出、净利润、毛利率）
- **收支趋势：** 双折线图（收入 vs. 支出趋势对比），可放大筛选时间范围
- **支出结构：** 饼图（支出按类别分解：商品成本、运营成本、退款等），可放大查看
- **财务流水：** 无限滚动表格，支持按日期范围筛选，展示每条收支记录
- 通过 `useEventStream(['finance', 'order', 'refund'])` 订阅变更

#### `views/SystemView.vue`

**系统管理页**（**仅管理员可访问**）：

- **Tab 1 — 员工管理：** 员工列表（用户名、邮箱、注册时间）+ 添加新员工表单
- **Tab 2 — 权限管理：** 选择员工（分页选择器）→ 显示 7 个模块的权限开关矩阵，逐项切换并实时保存
- **Tab 3 — 审计日志：** 分页展示所有权限变更记录（谁、何时、将谁的何模块权限从什么改为什么）
- 通过 `useEventStream(['system'])` 订阅系统事件

#### `views/NotificationsView.vue`

**通知中心**（**仅管理员可访问**）：

- 展示所有系统通知（订单提醒、库存预警、用户注册、退款申请等）
- 支持按通知类型筛选
- 支持批量选择 + 批量删除
- 单条通知可标记为已读
- 未读通知数量同步更新到侧边栏和顶部铃铛图标
- 通过 `useEventStream(['notification'])` 订阅新通知

---

## 架构设计要点

### 1. 实时数据流
```
后端 SSE → realtimeStore（计数器递增）→ useEventStream（节流）→ 各 View 刷新数据
```
单条 `EventSource` 连接，所有视图共享；计数器递增而非布尔翻转，防止高频事件漏触发。

### 2. 全局图表弹窗
```
任意 View 调用 useChartDetail().open(config) → ChartDetailModal 响应渲染
```
`ChartDetailModal` 挂载在根 `App.vue`，全局只存一个，通过 composable 共享状态，避免每个视图单独挂载导致的内存泄漏。

### 3. 类型安全的表格
`TableColumn<T>` 的 `render(value: unknown, row: T, index: number) => unknown` 设计允许在运行时返回任意 VNode，同时 `DataTable` 负责调用 `h()` 渲染结果，保持列配置与渲染逻辑解耦。

### 4. ECharts 类型兼容
ECharts 的 `EChartsOption` 类型因 `graphic` 组件链路中存在 `ZRText` 私有字段而无法被普通对象字面量满足。解决方案：`EChartBox.vue` 的 `option` prop 类型声明为 `unknown`，内部调用 `setOption` 时强制转型为 `ECBasicOption`，运行时由 ECharts 自行验证。

### 5. 无限滚动
`InfiniteTable` 使用 **Intersection Observer API** 监听底部哨兵元素进入视口，触发下一页加载，无需轮询或监听 scroll 事件，性能更优。

### 6. 懒加载地图
中国地图 GeoJSON（`/china.json`）约 500KB，通过 `chinaMap.ts` 在首次渲染省份热力图时异步加载，并缓存 `Promise` 防止重复请求。
