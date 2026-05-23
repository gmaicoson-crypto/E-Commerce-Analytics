# SQL 文件说明

这个目录用于存放项目维护的 SQL 文件，将 SQL 与 Python 代码分开管理。

## 文件列表

- `create_database.sql`
  - 供 `backend/setup_db.py` 使用。
  - 用于在数据库不存在时创建 MySQL 数据库 / schema。

- `alter_finance_category_enum.sql`
  - 供 `backend/_alter_finance_category.py` 使用。
  - 用于扩展 `finance_records.category` 的枚举值。

- `reset_business_data.sql`
  - 手动维护用 SQL。
  - 用于清空演示业务数据，同时保留账号和权限相关表。

## 约定

当需要调整 SQL 逻辑时，优先在这里新增或修改 `.sql` 文件，Python 脚本只保留为轻量执行器。
