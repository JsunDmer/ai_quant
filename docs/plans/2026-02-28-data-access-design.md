# 数据接入改造设计（多源 + 标准化 + 配置化）

## 目标

- 在不改变对外调用方式的前提下，为 K 线与实时行情引入多数据源兜底。
- 统一数据字段标准，减少上层策略对数据源差异的敏感性。
- 通过配置控制数据源优先级，默认保持现有 AKShare 行为。

## 范围

- 主要覆盖 `data/stock_data.py` 的 K 线与实时行情获取。
- 标准化字段在 `strategy/quant_strategy.py` 中作为唯一依赖。
- 新增配置项写入 `config.py`。

## 非目标

- 不改动现有 UI 与数据库结构。
- 不重构 `market_data.py` 的指数/快照逻辑（保持现状，后续可扩展）。

## 架构概览

- 在 `StockData` 内部新增轻量“数据源管理层”，对外 API 不变。
- 数据源适配器统一输出标准字段：
  - `date`, `open`, `high`, `low`, `close`, `volume`, `amount`, `pct_chg`
- 通过 `DATA_SOURCE_PRIORITY`/`REALTIME_SOURCE_PRIORITY` 控制优先级。

## 数据流

### K 线数据

1. 规范化股票代码（统一 SH/SZ 前后缀处理）。
2. 按 `DATA_SOURCE_PRIORITY=akshare,efinance,tushare` 依次尝试获取。
3. 对返回结果进行标准化与清洗：
   - 列名统一到标准字段
   - 日期格式化为 `datetime`
   - 数值列转为数值类型，缺失填 0
   - 按日期升序排序
4. 若全部失败，返回空 DataFrame（与现有行为一致）。

### 实时行情

1. 优先命中现有缓存（60 秒）。
2. 缓存失效时按 `REALTIME_SOURCE_PRIORITY` 逐源尝试。
3. 统一输出字段（price/open/high/low/volume/amount/change_percent/turnover_rate）。

## 配置项

新增 `.env` 配置（未配置时保持 AKShare 单源行为）：

```
DATA_SOURCE_PRIORITY=akshare,efinance,tushare
REALTIME_SOURCE_PRIORITY=akshare_em,akshare_sina,akshare_tencent
```

## 失败降级策略

- 单源失败不会中断，记录失败原因后继续尝试下一个。
- 全部失败时返回空结果，记录汇总日志。
- 保留现有缓存与重试机制，减少多次拉取风险。

## 测试策略

- 新增单元测试（如同意）：
  - 标准化输出列完整性测试。
  - 兜底顺序测试（模拟主源失败）。
- 若不加测试，至少跑一次 `pipeline.py` 完整流程进行验证。
