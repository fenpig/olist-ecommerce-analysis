# 环境与配置说明（一期）

## 1. 已确认目标环境

| 项目 | 标准 |
| --- | --- |
| Python | 当前已安装的 Python 3.13.13 |
| 虚拟环境 | 项目根目录 `.venv` |
| 依赖管理 | `requirements.in` 记录直接依赖；`requirements.txt` 仅写入已在 Python 3.13.13 环境中安装并运行验证过的固定版本 |
| 数据库 | MySQL 8.0.44，数据库名 `olist_delivery_analysis` |
| SQL 工具 | MySQL Workbench |
| Power BI 数据源 | 优先 MySQL 分析表；备用为 `data/processed/` CSV |

## 2. 当前审查状态与迁移约束

2026-08-05 的只读检查结果：

- 系统 Python 为 3.13.13，Python Launcher 仅发现 3.13；它是一期正式 Python 主版本。
- 现有 `.venv` 无法启动，仍引用不存在的 Python 3.12 解释器。
- 现有 `requirements.txt` 使用宽松版本范围，且缺少 SciPy；它尚未在目标 Python 3.13.13 环境中验证。
- MySQL CLI 为 8.0.44，满足 MySQL 8.0 的项目要求。
- 现有 SQL 使用旧数据库名 `olist_analysis`，文件结构也不符合一期目标的 `00`–`08` 顺序。
- `.env.example` 已在 T04 迁移为正式库名 `olist_delivery_analysis`，并补齐 `MYSQL_CHARSET=utf8mb4` 与非 root 占位账号；历史状态和回滚证据见 `LEGACY_MIGRATION_MANIFEST.md`。

Python 3.13.13 的 `.venv` 已在 T03 中完成直接依赖安装、基础功能与全新环境复现验证；准确版本、命令、警告和限制见 `DEPENDENCY_VERIFICATION.md`。不得删除、覆盖或静默复用失效 `.venv`、旧 SQL、旧 `.env.example` 或遗留 README 内容。旧环境已重命名为 `.venv_broken_backup_20260805` 并保留；是否删除由用户之后决定。

## 3. 正式配置变量

复制 `.env.example` 为本地 `.env` 后，目标变量应为：

```dotenv
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=olist_delivery_analysis
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_CHARSET=utf8mb4
```

`.env` 只能保留在本机，必须被 `.gitignore` 忽略；`.env.example` 是可提交的安全模板。任何脚本、Notebook、SQL、README、报告和截图均不得出现真实密码。变量含义、类型、默认值、使用组件和错误处理规则见 `CONFIGURATION_CONTRACT.md`。

## 4. 实施阶段的非破坏性迁移顺序

1. 记录现有 Python 3.13.13、失效 `.venv`、依赖文件和旧 SQL 状态。
2. 将失效 `.venv` 重命名为 `.venv_broken_backup_20260805`；不得删除，且备份目录加入 `.gitignore`。
3. 使用 Python 3.13.13 创建新的项目 `.venv`，安装 `requirements.in` 中的直接依赖。
4. 验证 pandas、numpy、scipy、matplotlib、jupyter、sqlalchemy、pymysql、python-dotenv 的导入，运行数据读取、MySQL 连接、SciPy 检验、Notebook 和关键脚本。
5. 仅在上述运行全部成功后，锁定实际已验证版本到 `requirements.txt`；T04 已将 `.env.example` 更新为 `olist_delivery_analysis`。
6. 将旧 SQL 按迁移计划映射到目标 `00`–`08` 文件，并将遗留文件移入 `legacy/` 或标记 deprecated；保留可追溯性，不得直接覆盖。
7. 在 README 中更新经验证的复现步骤和 Power BI 刷新方式。

若 Python 3.13.13 出现一期必需依赖的兼容问题，先报告问题依赖、安装或运行错误、可兼容版本、改用 Python 3.12/3.11 的必要性和对项目的影响；未经确认不得切换主版本。

## 5. MySQL 执行约束

- 在 MySQL Workbench 中依编号执行 `sql/00_create_database.sql` 至 `sql/08_validation_queries.sql`。
- CSV 导入方法、所需权限和原始表命名须在 README 中完整记录，不可依赖未说明的手动操作。
- SQL 文件不含本机绝对路径、用户名或密码；连接信息只存在于本机 `.env`，由 Python 读取。
- Power BI 连接不可用时，仪表盘须能使用处理后的 CSV 备用数据源展示。

## 6. MySQL 生命周期说明

MySQL 8.0.44 是本项目本地学习与作品集的实际验证环境，一期不将数据库升级作为阻塞条件，也不得擅自升级或卸载本机 MySQL。MySQL 8.4 LTS 兼容性验证属于后续非阻塞增强，不应把当前环境描述为推荐的生产部署版本。
