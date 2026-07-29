# Power BI 仪表板制作说明

## 1. 导入数据

在 Power BI Desktop 选择“获取数据 → 文本/CSV”，依次导入以下文件：

- `data/processed/order_fact.csv`
- `data/processed/order_item_fact.csv`
- `data/processed/rfm_customers.csv`

在 Power Query 中确认：

- `order_purchase_timestamp`、`order_delivered_customer_date`、`order_estimated_delivery_date` 是“日期/时间”类型。
- `gmv`、`item_price`、`freight_value`、`review_score`、`delivery_days` 是小数类型。
- `is_delivered`、`is_late_delivery` 是 True/False 类型。
- 将 `purchase_month` 转为日期，或保留其文本并按月份升序排序。

## 2. 数据模型

创建下列关系，均使用单向筛选：

```text
order_fact[order_id] (1) ──── (*) order_item_fact[order_id]
rfm_customers[customer_unique_id] (1) ──── (*) order_fact[customer_unique_id]
```

不要把 `order_fact` 的 `gmv` 和 `order_item_fact` 的金额字段放进同一个视觉对象后直接求和；前者是订单粒度，后者是商品明细粒度。

## 3. 日期表

在“建模 → 新建表”创建 `Date` 表：

```DAX
Date =
ADDCOLUMNS(
    CALENDAR(DATE(2016, 9, 1), DATE(2018, 10, 31)),
    "Year", YEAR([Date]),
    "Month Number", MONTH([Date]),
    "Year Month", FORMAT([Date], "YYYY-MM")
)
```

再建立 `Date[Date] (1) → order_fact[Purchase Date] (*)` 的单向关系。若没有 `Purchase Date` 字段，在 `order_fact` 上建计算列：

```DAX
Purchase Date = DATE(YEAR(order_fact[order_purchase_timestamp]), MONTH(order_fact[order_purchase_timestamp]), DAY(order_fact[order_purchase_timestamp]))
```

将 `Date[Year Month]` 按 `Date[Date]` 排序，并把日期表标记为日期表。

## 4. 两页仪表板布局

### 页面 1：经营总览

- 顶部 KPI 卡片：已交付 GMV、已交付订单、客单价、复购客户占比、平均评分。
- 左侧折线图：月份 × 已交付 GMV。
- 中部柱状图：月份 × 已交付订单。
- 右侧条形图：客户州 × 已交付 GMV（前 10）。
- 底部左侧：品类 × 明细 GMV（前 10，使用 `order_item_fact` 和 `[Item GMV]`）。
- 底部右侧：订单状态分布、支付方式 GMV（可在数据库查询结果中补充）。
- 切片器：年份、客户州、订单状态。

### 页面 2：履约与客户价值

- KPI 卡片：延迟交付率、平均配送天数、延迟订单平均评分、准时订单平均评分。
- 簇状柱状图：准时/延迟 × 平均评分。
- 条形图：客户州 × 延迟交付率（至少 30 笔已交付订单再展示）。
- 散点图：配送天数 × 评分，大小为订单数。
- 表格：RFM 高价值客户，列出 `frequency`、`monetary`、`recency_days`。
- 切片器：年份、客户州。

## 5. 讲故事顺序

演示时依次回答：整体经营是否增长 → 增长来自哪里 → 客户是否有复购价值 → 履约问题是否伤害体验 → 应优先采取什么行动。
