# T05 MySQL 8.0.44 最小连通性与空库验证

验证日期：2026-08-06  
任务范围：仅使用本地 `.env` 在内存读取配置，执行只读 `SELECT`、`SHOW TABLES` 与 `SHOW GRANTS`。未输出密码或完整连接 URL，未执行 DDL/DML，未运行项目 SQL。

## 验证结果

| 检查项 | 结果 |
| --- | --- |
| Python 环境 | Python 3.13.13；`pip check` 通过。 |
| 配置安全 | `.env` 存在、被 Git 忽略且未被 Git 跟踪；真实内容未输出。 |
| 连接 | 成功。 |
| MySQL 版本 | 8.0.44。 |
| 当前数据库 | `olist_delivery_analysis`。 |
| 数据库字符集 | `utf8mb4`。 |
| 数据库排序规则 | `utf8mb4_unicode_ci`。 |
| 基础只读查询 | `SELECT 1` 返回 1。 |
| 空库检查 | `SHOW TABLES` 返回 0 张表。 |
| 当前连接账号 | `olist_project@localhost`，非 root。 |
| 授权 | `USAGE ON *.*`，以及 `ALL PRIVILEGES ON olist_delivery_analysis.*`。 |

## 执行的只读 SQL

```sql
SELECT VERSION(), DATABASE(), @@character_set_database, @@collation_database;
SELECT 1;
SHOW TABLES;
SHOW GRANTS FOR CURRENT_USER();
SELECT CURRENT_USER();
```

本次权限结论基于 `SHOW GRANTS`；没有通过创建对象来测试写权限，因此未修改空数据库。

## 限制与下一步

- 这只验证 MySQL 服务、账号、正式数据库、字符集、空库和授权，不代表原始 CSV 导入、正式 SQL、数据模型或分析逻辑已经验证。
- 真实 `.env` 仍仅保留在本机；不要在任何文档、代码、Notebook 或 Git 中写入凭据。
- 下一项 T06 才会建立正式 SQL 目录结构与遗留 SQL 隔离；未经用户确认不得开始。
