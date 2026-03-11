# Adaptive RSI Pro 中文说明

当前仓库当前发布版本为 `v7.3`，但行为基线保持接近 GitHub 公开 `v7.2`。

正式指标是 [adaptive_rsi.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi.pine)。  
这次没有继续沿用后续实验版，而是回到原版 `v7.2`，只保留三类明显正确性修复：

- `lookback` 不再低于统计下限
- 周线趋势保护使用已确认周线数据
- 下级别多周期读取改为正确的 lower-TF 聚合

另外新增了一个单独的策略验证脚本：

- [adaptive_rsi_strategy_harness.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi_strategy_harness.pine)

它不是正式指标，只是为了在 TradingView `Strategy Tester` 里验证 `v7.2` 的信号表现。

主要用法：

- 看图、看信号、设警报：用 [adaptive_rsi.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi.pine)
- 看策略回测：用 [adaptive_rsi_strategy_harness.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi_strategy_harness.pine)

harness 只保留两组核心开关：

- `Trade Side`: `Long Only` / `Short Only` / `Both`
- `Backtest Mode`
  - `Baseline`: 原始 `v7.2` 信号
  - `Production`: 正式指标最终进入 alert 的信号

详细说明请看：

- [README.md](/Users/aaajiao/o_projects/RSI_stock/README.md)
- [docs/STRATEGY_REPORT_CN.md](/Users/aaajiao/o_projects/RSI_stock/docs/STRATEGY_REPORT_CN.md)
