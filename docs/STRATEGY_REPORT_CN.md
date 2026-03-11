# Strategy Report 使用说明

这份文档说明如何使用 [adaptive_rsi_strategy_harness.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi_strategy_harness.pine) 去验证当前 `v7.3` 正式版本。这个版本在行为上保持接近 `v7.2`。

## 作用

正式指标仍然是 [adaptive_rsi.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi.pine)。  
策略壳的唯一作用，是把这套恢复后的正式信号接到 TradingView `Strategy Tester`，观察它在策略执行模型下的结果。

## 参数

### Trade Side / 交易方向

- `Long Only`：只开多，卖出信号只平多
- `Short Only`：只开空，买入信号只平空
- `Both`：允许双向反手

### Backtest Mode / 回测模式

- `Baseline`：交易原始 `v7.2` 信号
- `Production`：只交易正式指标最终会放进警报里的信号

`Production` 是最接近正式指标最终 alert 路径的策略回测口径。

## dashboard 新增三行

harness 在完整 dashboard 里多三行：

- `Harness`：当前 `Trade Side` 和 `Backtest Mode`
- `Tester`：提示你该如何解读 TradingView 的 `All`
- `Production Gate`：当前信号桶、样本数、平均收益、调整胜率

例如：

```text
Production Gate: EXT[A](12) +2.8%|67%
```

意思是：

- 当前统计桶 = `EXT[A]`
- 样本数 = `12`
- 平均前瞻收益 = `+2.8%`
- 调整胜率 = `67%`

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

## 一个重要边界

正式指标里的统计，是固定前瞻窗口的信号质量统计。  
策略壳里的结果，是 `strategy()` 规则下的真实交易结果。

所以：

- 指标里的统计 = 看信号质量
- Strategy Report = 看交易执行结果

两者相关，但不是同一个数字。

## 常见误区

- 把 harness 当成主产品
- 在单方向模式下仍把 `All` 理解成多空混算
- 以为 `Production` 改了正式指标逻辑；它只改变 harness 实际交易哪批信号
- 把策略胜率直接等同于正式指标里的调整胜率
