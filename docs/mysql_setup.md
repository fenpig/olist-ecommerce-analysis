# MySQL 导入说明

1. 在项目根目录复制 `.env.example` 为 `.env`，填写自己的 MySQL 账号和密码。
2. 安装依赖：`python -m pip install -r requirements.txt`
3. 在 MySQL Workbench 运行 `sql/00_create_database.sql`，创建 `olist_analysis` 数据库。
4. 在项目根目录运行：`python src/03_load_to_mysql.py`
5. 再次运行完整的 `sql/01_schema.sql` 创建索引。
6. 打开并执行 `sql/02_analysis_queries.sql`。

不要提交 `.env`；它包含本机连接密码。
