# 第三方电商平台接入 API 后续开发设计

## 目标

第三方电商平台接入属于后续独立功能。本设计只记录方向,不改变当前项目运行状态。

当前项目中的 `/api/ingest/*` 继续只服务 simulator 演示流程。正式第三方平台接入后续应单独新增 API,避免与 simulator 的演示接口混用。

## 不影响当前项目的边界

本阶段不修改以下内容:

- 不修改 `backend/routers/ingest.py`
- 不修改现有 `/api/ingest/*` 行为
- 不修改 simulator
- 不修改 frontend
- 不修改数据库 schema
- 不修改现有 README

## 推荐 API 路径

后续新增正式外部接入路由,建议使用版本化路径:

```text
POST  /api/external/v1/customers
POST  /api/external/v1/products
POST  /api/external/v1/orders
PATCH /api/external/v1/orders/{external_order_id}/status
```

这些接口只面向第三方电商平台。前端可视化后台仍然调用当前 backend 的分析接口,例如 `/api/sales/*`、`/api/products/*`、`/api/orders/*`。

## 后续设计要点

- 独立 token 鉴权,不复用管理员/员工 JWT。
- 独立外部平台 ID 映射,例如:
  - `external_customer_id`
  - `external_product_id`
  - `external_order_id`
- 独立 payload 文档,明确字段、枚举、时间格式和必填规则。
- 独立错误码策略,区分认证失败、字段错误、状态流转错误和重复数据。
- 独立幂等策略,避免第三方平台重试造成重复订单或重复商品。

## 推荐数据流

```text
第三方电商平台
    |
    | 业务事件 HTTP 请求
    v
backend external API
    |
    | 鉴权 / 校验 / 幂等判断
    v
backend service
    |
    | 写库 / 处理库存 / 财务 / 通知
    v
MySQL
    |
    | SSE 事件
    v
frontend 可视化后台刷新
```

## 后续测试方向

真正开发该功能时需要验证:

- simulator 原有流程不受影响。
- 外部 API token 校验正确。
- 第三方提交客户、商品、订单后能进入 backend 数据库。
- 前端分析页面能正常展示第三方数据。
- 重复提交同一外部订单不会产生重复数据。
- 非法枚举、非法状态流转、缺失必填字段能返回明确错误。

## 当前结论

第三方平台接入应作为后续独立模块开发。当前阶段只保留本设计文档,不改变项目现有代码行为。
