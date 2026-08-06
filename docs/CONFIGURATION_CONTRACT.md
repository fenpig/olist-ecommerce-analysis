# MySQL 配置契约（一期）

本契约只定义本地配置接口，不创建连接、不读取项目根目录的真实 `.env`，也不在 SQL、Python、Power BI 或文档中存储密码。

## 1. 使用方式与安全边界

1. 将 `.env.example` 复制为项目根目录的 `.env`，仅在本机填写真实值。
2. `.env`、`.env.local` 和 `.env.*.local` 必须被 Git 忽略；`.env.example` 必须可被 Git 跟踪。
3. 后续 Python 组件以独立环境变量构造连接参数，不拼接含密码的完整连接 URL。
4. 不建议使用 MySQL `root` 账号；应使用权限最小化的本地项目账号。
5. 配置缺失或格式错误时，后续代码必须报告变量名和安全的错误原因并停止，不能静默回退到不安全默认值。

## 2. 变量定义

| 变量 | 必填 | 类型 | 示例 / 默认值 | 敏感性 | 后续使用组件 | 缺失或格式错误处理 |
| --- | --- | --- | --- | --- | --- | --- |
| `MYSQL_HOST` | 是 | 字符串 | `localhost` | 非敏感 | Python 导入、MySQL 连接说明、Power BI 连接说明 | 缺失时停止并提示设置主机名。 |
| `MYSQL_PORT` | 是 | 整数 | 默认 `3306` | 非敏感 | Python 导入、MySQL/Power BI 连接说明 | 必须可转换为 1–65535 整数；否则停止。 |
| `MYSQL_DATABASE` | 是 | 字符串 | `olist_delivery_analysis` | 非敏感 | 正式 SQL、Python 配置、Power BI 连接说明、验证脚本 | 必须等于一期正式名称；否则停止并提示历史名称不可用于正式流程。 |
| `MYSQL_USER` | 是 | 字符串 | `your_username` | 账号信息 | Python 导入、MySQL/Power BI 连接说明 | 缺失、为空或为 `root` 时停止并提示配置项目账号。 |
| `MYSQL_PASSWORD` | 是 | 字符串 | `your_password`（仅模板占位） | 敏感 | 仅本地 Python/客户端连接配置 | 缺失、为空或仍为模板占位值时停止；不得输出值。 |
| `MYSQL_CHARSET` | 否 | 字符串 | 默认 `utf8mb4` | 非敏感 | 建库、Python 连接和文本处理说明 | 缺失时使用 `utf8mb4`；非 `utf8mb4` 时记录并要求明确确认。 |

## 3. 名称一致性

一期唯一正式数据库名称是 `olist_delivery_analysis`。`olist_analysis` 是遗留/历史名称，仅可在迁移清单、旧 SQL、旧 README 或 deprecated 说明中出现，不能用于一期正式执行流程。

后续正式 SQL、Python 配置、Power BI 连接说明和验证脚本均使用本契约的变量名。T04 只建立接口；实际 Python 连接代码、SQL 和 Power BI 配置分别在后续经确认任务中实现和验证。

## 4. 模板安全检查

`.env.example` 只能包含安全占位值：主机为 `localhost`、端口为 `3306`、数据库为 `olist_delivery_analysis`、用户不是 `root`、密码为非真实的 `your_password` 占位值、字符集为 `utf8mb4`。模板不得包含完整数据库 URL、绝对路径、私人服务器地址、令牌或真实秘密信息。
