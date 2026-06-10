# Strategy Report 使用说明

这份文档说明如何使用 [adaptive_rsi_strategy_harness.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi_strategy_harness.pine) 去验证当前 `v7.4` 正式版本。这个版本在信号基线上保持接近 `v7.2`。

## 作用

正式指标仍然是 [adaptive_rsi.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi.pine)。  
策略壳的唯一作用，是把 `v7.4` 正式信号接到 TradingView `Strategy Tester`，观察它在策略执行模型下的结果。

策略壳由 [tools/generate_strategy_harness.py](/Users/aaajiao/o_projects/RSI_stock/tools/generate_strategy_harness.py) 从正式指标生成。修改信号逻辑时应改 `adaptive_rsi.pine`，然后重新生成策略壳，不要手工维护两份重复逻辑。

## 参数

### Trade Side / 交易方向

- `Long Only`：只开多，卖出信号只平多
- `Short Only`：只开空，买入信号只平空
- `Both`：允许双向反手

### Backtest Mode / 回测模式

- `Baseline`：交易原始 `v7.2` 信号
- `Production`：交易通过正式警报 gate/过滤的信号

`Production` 是过滤后信号的执行口径。它不模拟盘中 `alert()` 投递、alert 调度或 smart alert 的精确投递次数；它用于评估过滤路径，不用于和 alert 日志逐条对齐。

从 `v7.4` 起，正式统计引擎默认开启时间衰减、独立采样和 `Edge vs Baseline` 门槛模式（有效门槛 = 方向基准 + 要求优势，钳制在 25%~90% 之间，并在指标 Dashboard 的 `Base→Req` 标题行中显示），因此相同参数下 `Production` 结果会与 `v7.3` 不同。设置 `Stats Half-Life Bars = 0`、关闭 `Independent Samples`、并将 `Gate Mode` 设为 `Absolute (Legacy)` 只能恢复旧版统计引擎的计算方式；v7.4 在信号层面的其他改动（spread 因子滞回、冷却升级等级重置）没有回退开关，`Production` 结果仍可能与 `v7.3` 不同。

### 风险退出（v7.4，均默认关闭）

- `Use ATR SL/TP Exits`（`harness_use_risk_exits`）：按警报展示的 ATR 止损/止盈价格退出。价格在信号 K 线收盘时快照，入场单在下一根 K 线开盘成交；`strategy.exit` 与入场单一起下单并通过 `from_entry` 绑定，因此入场成交当根 K 线即受止损/止盈保护。持仓期间同 ID 退出单持续刷新，反手/再入场后始终挂着最新快照。关闭 = 仅按反向信号平仓（原有回测行为）
- `Max Holding Bars`（`harness_max_holding_bars`，`0` = 关闭）：持仓恰好 N 根 K 线后强制平仓（`Time Exit`）——平仓单在第 N−1 根持仓 K 线收盘时下达，下一根 K 线开盘成交

### 成本

策略壳默认声明佣金 `0.05%`、滑点 `2` ticks。两者都可以在 TradingView `Strategy Tester` → `Properties` 中覆盖，无需修改代码。

## dashboard 新增三行

harness 在完整 dashboard 里多三行：

- `Harness`：当前 `Trade Side` 和 `Backtest Mode`
- `Tester`：提示你该如何解读 TradingView 的 `All`
- `Production Gate`：`Stats Mode` 当前实际使用的统计 gate 桶、样本数、平均收益、调整胜率

`Ranking` 模式下例如：

```text
Production Gate: EXT[A](12) +2.8%|67%
```

意思是：

- 当前统计桶 = `EXT[A]`
- 样本数 = `12`
- 平均前瞻收益 = `+2.8%`
- 调整胜率 = `67%`

当 `Stats Mode` 是 `Signal Type` 时，标签会显示为 `TYPE:EXT`；当它是 `Grade` 时，会显示为 `GRADE[A]`。这些标签就是生产过滤实际使用的统计桶。

如果当前 bar 没有活动信号，会显示 `Idle`。

## 如何读 TradingView 的 `All / Long / Short`

TradingView 会始终显示 `All`、`Long`、`Short` 三列。

正确读法：

- `Long Only`：把 `All` 当成当前 long-only 的总结果
- `Short Only`：把 `All` 当成当前 short-only 的总结果
- `Both`：把 `All` 当成双向总结果

harness 的 `Tester` 行会重复提示这条规则。

## 推荐顺序

1. 先用 `Trade Side = Long Only`
2. 先跑 `Backtest Mode = Baseline`
3. 先确认原始 `v7.2` 信号本身有没有边
4. 再切到 `Backtest Mode = Production`
5. 看最终 alert 过滤后结果是变好还是变差

建议优先看：

- `GOOGL 1D`
- `AAPL 1D`
- `BTCUSDT 4H`

这三个图表也是必做的编译验证项：任何版本升级后，请把两个脚本分别粘贴进 Pine Editor，至少在这三个图表上确认编译和运行行为正常。

## 维护流程

正式指标逻辑变更后运行：

```bash
python3 tools/generate_strategy_harness.py
python3 tools/generate_strategy_harness.py --check
```

CI 也会运行 `--check`，如果正式指标和策略壳出现漂移会提前失败。

## 重要边界

正式指标里的统计，是固定前瞻窗口的信号质量统计。  
策略壳里的结果，是 `strategy()` 规则下的真实交易结果。

所以：

- 指标里的统计 = 看信号质量
- Strategy Report = 看交易执行结果

两者相关，但不是同一个数字。

另外注意：

- 策略壳是过滤后信号回测，不是逐笔盘中 `alert()` 投递模拟。
- 统计依赖 TradingView 实际加载的图表历史，因此 `Production` 的 gate 判定（以及由此产生的交易）可能因订阅级别和会话而不同。
- 低于图表周期的 MTF 数据只覆盖最近约 `MAX_REQUEST_BARS`（1400）根图表 K 线，深历史区域由 MTF 驱动的交易会很稀疏。

## 常见误区

- 把 harness 当成主产品
- 在单方向模式下仍把 `All` 理解成多空混算
- 以为 `Production` 改了正式指标逻辑；它只改变 harness 实际交易哪批信号
- 把策略胜率直接等同于正式指标里的调整胜率
