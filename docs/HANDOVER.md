# 项目交接文档：Olist 配送履约与客户满意度分析（一期）

交接日期：2026-08-07
项目根目录：仓库根目录
当前分支：`main`
T10–T11 数据集恢复点：`6588167 feat: build validated clean and analysis datasets`。
当前 HEAD 不在本文档中硬编码；每次新任务接管时必须通过 `git rev-parse HEAD` 实时获取。

本交接包用于新的 Codex 任务接管。当前只允许在用户单独授权后执行 T12；不得自动开始 T12 或 T13。

## 1. 项目当前状态

- 项目名称：Olist 配送履约与客户满意度分析（一期）。
- 已完成并验收：T01–T11。
- 下一项：T12，方案已确认但尚未执行。
- 尚未开始：T13 及以后。
- 数据库：`olist_delivery_analysis`，MySQL 8.0.44。
- Python：3.13.13；项目 `.venv` 可用，`pip check` 通过，无损坏依赖。
- T10–T11 数据集恢复点：`6588167`，覆盖已验证的 T10–T11 清洗与分析数据集。

## 2. Git 状态与保护资产

- 当前分支为 `main`，HEAD 如上。
- 本地 HEAD 领先 `origin/main` 两个提交。
- `README.md` 与 `dashboard/olist_ecommerce_dashboard.pbix` 存在此前遗留的未提交修改。
- 这两个文件不属于 T12；未经用户确认，不得修改、暂存、丢弃、恢复或纳入自动提交。
- 当前 T12 正式实现文件 `sql/05_delivery_metrics.sql`、`sql/06_review_metrics.sql` 没有未提交修改；T12 尚未运行。
- `data/processed/` 下的 CSV 被 Git 忽略，可由对应脚本重建，不能把缺失或重建误判为原始数据变更。

## 3. 当前数据库状态

数据库对象总计为 7 张原始表和 8 个视图。

### 原始表

`orders_raw`、`order_items_raw`、`order_payments_raw`、`order_reviews_raw`、`customers_raw`、`products_raw`、`category_translation_raw`。

### T09 视图

- `vw_review_ranked`
- `vw_order_review_audit`
- `vw_order_review_selected`

### T10 视图

- `vw_clean_orders`

### T11 视图

- `vw_order_items_aggregated`
- `vw_order_payments_aggregated`
- `vw_order_analysis`
- `vw_order_item_analysis`

除用户单独授权外，不得重建、替换或删除上述对象。T12 不创建新的分析表或业务视图。

## 4. 已验证的关键数据

| 项目 | 已验证结果 |
| --- | ---: |
| 原始订单数 | 99,441 |
| 商品明细行数 | 112,650 |
| 评价记录数 | 99,224 |
| 有评价订单数 | 98,673 |
| 多评价订单 | 547 |
| 评分冲突订单 | 202 |
| 配送可用订单 | 96,470 |
| 评分关系可用订单 | 95,824 |
| 配送可用延迟订单 | 6,534 |
| 全量 `is_delayed = 1` 记录 | 6,535 |
| 日期异常订单 | 1,382 |
| 实际送达早于交运 | 23 |

完整的 T09、T10、T11 验收证据分别见 `docs/T09_REVIEW_SELECTION_AUDIT.md`、`docs/T10_CLEAN_ORDERS_VERIFICATION.md`、`docs/T11_ANALYSIS_DATASETS_VERIFICATION.md`，以及 `reports/validation/` 下相应 JSON。

正式 T12 延迟率使用 `6,534 / 96,470`。两项计数相差 1 个 canceled 订单：该订单具有正日历日日期差，因而在全量 `is_delayed = 1` 审计分布中保留，但不具备配送可用资格，不能计入正式配送延迟订单数或延迟率。

## 5. 已冻结的核心口径

- `delay_days` 使用实际送达日期与预计送达日期的日历日期差。
- `delay_hours_raw` 使用秒差除以 3600，不使用截断式小时差。
- 低评分为 1–2 分，高评分为 4–5 分。
- 最新有效评价是订单级主口径；同订单最低有效评分仅用于敏感性分析。
- 2016-09、2016-12、2018-09、2018-10 仅从主趋势中排除，仍保留在全量数据和指标中。
- 日期异常订单保留，不静默删除、修正日期或改写 T10 样本标记。
- `is_delivered_before_carrier = 1` 的 23 条订单不进入依赖交运日期的在途时长指标；若送达和预计日期完整，仍可参与 `delay_days` 指标。
- 订单级分析严格一行一个 `order_id`；商品明细分析严格一行一个 `order_id + order_item_id`。
- 商品和支付必须先按订单聚合，再连接订单主表；不得直接把原始商品、支付与订单主表同时连接。
- 后续配送—评分关系必须保留两套口径：主口径保留全部符合条件订单，对照口径排除 `has_date_anomaly = 1`，比较主要指标与结论是否明显变化。

正式定义见 `docs/DECISIONS.md` 与 `docs/METRICS.md`。

## 6. T12 状态与已确认执行方案

T12 方案已提出，尚未执行。当前未修改 `sql/05_delivery_metrics.sql` 与 `sql/06_review_metrics.sql` 的正式指标实现。

T12 只负责配送与客户评分的核心描述性指标 SQL：有效订单、已送达订单、延迟订单、延迟率、配送时长、平均/中位延迟、评分分布、平均评分、低评分率和高评分率。每条查询必须显式说明订单粒度、筛选条件、分子与分母。

- 只消费 `vw_order_analysis`，不重新连接原始商品、支付或评价明细表。
- 延迟率分母固定为 `is_delivery_eligible = 1` 的订单；低/高评分率分母固定为 `is_review_relation_eligible = 1` 的订单。
- 对日期异常同时保留主口径与排除 `has_date_anomaly = 1` 的对照口径，但 T12 不解释关联方向或业务影响。
- 不做地区、品类或卖家排名；这些属于 T13。
- 不做统计检验；这些属于 T14。
- 不形成业务结论，不做 Power BI，不创建新的分析表或业务视图。
- 可修改的正式 SQL 为 `sql/05_delivery_metrics.sql` 和 `sql/06_review_metrics.sql`；可创建脱敏结果说明 `reports/metric_sql_outputs/README.md`。正式 SQL/Python 跨工具指标对账脚本属于 T16，不得在 T12 冒充为完成。

## 7. 新任务启动检查（只读）

在任何 T12 写入或 SQL 执行前，从仓库根目录依次执行：

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
git log -3 --oneline
git diff --check

.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip check
```

随后执行不刷新报告的数据库只读检查：确认 `DATABASE()` 为 `olist_delivery_analysis`、版本仍为 MySQL 8.0.44、原始表为 7 张、视图为上述 8 个，且 `vw_clean_orders`、`vw_order_analysis` 的粒度仍分别为一行一个 `order_id`。其中 T09 默认检查如下：

- `vw_review_ranked`、`vw_order_review_audit`、`vw_order_review_selected` 三个视图均存在；
- `vw_order_review_selected` 保持订单级一行一个 `order_id`；
- 多评价订单和评分冲突订单等关键计数仍符合 T09 已验收基线；
- 已有 `reports/validation/t09_review_selection_summary.json` 的状态为通过。

不得在只读接管检查中自动运行 `.\.venv\Scripts\python.exe src\03_validate_review_selection.py --validate-existing`。该命令不会修改数据库对象，但会刷新 `reports/validation/t09_review_selection_summary.json`。需要运行时，必须事先允许更新该报告文件；或者在运行后核对差异仅为生成时间戳变化，再恢复报告文件。

## 8. 待确认事项与风险

- T13 的 `seller_id`、商品类别、客户州最低样本量尚未最终决定；T13 前必须提出依据并取得确认。
- Power BI 后续可能需要用户在 Desktop 中手动配置、刷新和验证。
- README 与旧 PBIX 的遗留未提交修改必须持续保护。
- processed CSV 是可重建产物；原始 CSV 始终只读。
- T12 结束后必须暂停，提交实际命令、指标口径、脱敏结果、验证、风险与回滚说明，等待用户验收后才可进入 T13。
