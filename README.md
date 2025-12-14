# Adaptive RSI Pro / 自适应RSI专业版

Dynamic overbought/oversold thresholds + Multi-Timeframe analysis + Divergence detection + Signal statistics.

根据每个标的实际历史分布动态计算超买/超卖阈值，结合多时间框架分析、背离检测和信号统计。

---

## Emoji Legend / 信号图例

### Chart Signals / 图表信号

#### Buy Signals / 买入信号 (底部显示)

| Emoji | Signal Name | Condition | Priority | Action |
|-------|-------------|-----------|----------|--------|
| 🌟 | MTF + Extreme | 3+ timeframes oversold + P5 | ★★★★★ | **STRONG BUY** 强力买入 |
| 💎 | Divergence + Extreme | Bullish divergence in P5 zone | ★★★★☆ | **BUY** 买入 |
| 🔥 | Extreme Oversold | RSI crosses below P5 | ★★★☆☆ | **BUY** 买入 |
| ⬆️ | Normal Oversold | RSI crosses below P10 | ★★☆☆☆ | Consider buy 考虑买入 (默认隐藏) |
| ↗️ | Bullish Divergence | Price↓ RSI↑ (not in extreme) | ★☆☆☆☆ | Watch 观察 (潜在底部) |

#### Sell Signals / 卖出信号 (顶部显示)

| Emoji | Signal Name | Condition | Priority | Action |
|-------|-------------|-----------|----------|--------|
| 🌟 | MTF + Extreme | 3+ timeframes overbought + P95 | ★★★★★ | **STRONG SELL** 强力卖出 |
| 💎 | Divergence + Extreme | Bearish divergence in P95 zone | ★★★★☆ | **SELL** 卖出 |
| ❄️ | Extreme Overbought | RSI crosses above P95 | ★★★☆☆ | **SELL** 卖出 |
| ⬇️ | Normal Overbought | RSI crosses above P90 | ★★☆☆☆ | Consider sell 考虑卖出 (默认隐藏) |
| ↘️ | Bearish Divergence | Price↑ RSI↓ (not in extreme) | ★☆☆☆☆ | Watch 观察 (潜在顶部) |

> **Priority System / 优先级系统**: Only the highest priority signal is shown to prevent overlapping.  
> 只显示最高优先级信号，避免叠加。

---

### Dashboard Status / 仪表盘状态

| Emoji | Status | Meaning |
|-------|--------|---------|
| 🟢 | EXTREME OVERSOLD | RSI < P5, strong buy zone / 极端超卖区，强买区 |
| 🟡 | OVERSOLD | RSI < P10, oversold / 超卖 |
| ⚪ | NEUTRAL | P10 ≤ RSI ≤ P90, no signal / 中性，无信号 |
| 🟠 | OVERBOUGHT | RSI > P90, overbought / 超买 |
| 🔴 | EXTREME OVERBOUGHT | RSI > P95, strong sell zone / 极端超买区，强卖区 |

### MTF Status / 多周期状态

| Emoji | Meaning |
|-------|---------|
| 🟢 | Timeframe oversold / 该周期超卖 |
| 🔴 | Timeframe overbought / 该周期超买 |
| ⚪ | Timeframe neutral / 该周期中性 |

### Divergence Status / 背离状态

| Emoji | Meaning |
|-------|---------|
| 🟢 BULL DIV | Bullish divergence detected / 检测到看涨背离 |
| 🔴 BEAR DIV | Bearish divergence detected / 检测到看跌背离 |
| — | No divergence / 无背离 |

---

### Alert Emojis / 警报图标

| Emoji | Alert Type | Description |
|-------|------------|-------------|
| 🌟 | MTF Resonance | Multiple timeframes agree / 多周期共振 |
| 💎 | Divergence | RSI divergence detected / 检测到背离 |
| 🔥 | Extreme Oversold | RSI at P5 / RSI达到P5 |
| ❄️ | Extreme Overbought | RSI at P95 / RSI达到P95 |
| ⚡ | Any Extreme | Any extreme signal / 任意极端信号 |
| 📈 | Trend Shift Up | RSI crossed above P50 / 趋势转多 |
| 📉 | Trend Shift Down | RSI crossed below P50 / 趋势转空 |

---

## Overview / 概述

Traditional RSI uses fixed 30/70 thresholds, but different assets have different volatility characteristics.

传统RSI使用固定的30/70阈值，但不同标的有不同的波动特性。

**Solution**: Calculate thresholds using historical percentiles (P5-P95) + advanced features.

**解决方案**：使用历史百分位（P5-P95）计算阈值 + 高级功能。

---

## Features / 功能特性

### 🎯 Adaptive Thresholds / 自适应阈值
- P95/P5: Extreme overbought/oversold (极端超买/超卖)
- P90/P10: Normal overbought/oversold (普通超买/超卖)
- P50: Dynamic median (动态中位数)

### 📈 Trend Filter / 趋势过滤
- Filter signals by trend direction (按趋势方向过滤信号)
- 3 modes: Fixed 50, Adaptive P50, SMA(RSI)

### 🌍 Multi-Timeframe RSI / 多时间框架RSI
- View RSI status across 3 configurable timeframes
- Resonance detection: Strong signal when 3+ timeframes agree
- 共振检测：当3个以上时间框架一致时，信号更强

### 💎 Divergence Detection / 背离检测
- **Bullish Divergence**: Price lower low + RSI higher low (看涨背离)
- **Bearish Divergence**: Price higher high + RSI lower high (看跌背离)

### 📊 Signal Statistics / 信号统计
- Track historical signal performance (跟踪历史信号表现)
- Average return after N bars (N根K线后平均收益)
- Win rate percentage (胜率)

---

## Dashboard / 仪表盘

```
┌─────────────────────────────────┐
│   ADAPTIVE RSI PRO       35.2  │
├─────────────────────────────────┤
│ Status      🟢 EXTREME OVERSOLD │
│ Percentile  P10 ↓ DOWN          │
├─────────────────────────────────┤
│ Overbought P90         68.5     │
│ Median P50             52.3     │
│ Oversold P10           32.1     │
├─────────────────────────────────┤
│ ── MTF RSI ──                   │
│ 60 | 240 | D   🟢 | ⚪ | 🟢      │
│ Resonance    🟢 3/4 OVERSOLD    │
├─────────────────────────────────┤
│ Divergence   🟢 BULL DIV        │
├─────────────────────────────────┤
│ ── STATS ──   (20 bars)         │
│ 🟢 Oversold(12)  +3.2% | 75%    │
│ 🔴 Overbought(8) -2.1% | 62%    │
└─────────────────────────────────┘
```

---

## Settings / 设置

### RSI Settings / RSI设置
| Setting | Default | Description |
|---------|---------|-------------|
| RSI Length | 14 | RSI calculation period / RSI计算周期 |
| RSI Source | Close | Price source / 价格源 |
| Lookback | 252 | Historical bars for percentile / 百分位回看周期 |

### Trend Filter / 趋势过滤
| Setting | Default | Description |
|---------|---------|-------------|
| Enable | OFF | Only trigger signals in trend direction / 仅趋势方向触发 |
| Mode | Adaptive P50 | Fixed 50 / Adaptive P50 / SMA(RSI) |

### Multi-Timeframe / 多时间框架
| Setting | Default | Description |
|---------|---------|-------------|
| Enable | ON | Show MTF analysis / 显示MTF分析 |
| TF1/TF2/TF3 | 60/240/D | Timeframes / 时间框架 |

### Signal Statistics / 信号统计
| Setting | Default | Description |
|---------|---------|-------------|
| Enable | ON | Track performance / 跟踪表现 |
| Forward Bars | 20 | Bars for return calculation / 收益计算K线数 |

### Divergence / 背离设置
| Setting | Default | Description |
|---------|---------|-------------|
| Enable | ON | Detect divergences / 检测背离 |
| Pivot Lookback | 5 | Pivot detection bars / 枢轴检测周期 |
| Max Range | 60 | Max divergence range / 最大背离范围 |

---

## Alerts / 警报

| Alert | Description |
|-------|-------------|
| 🌟 MTF Resonance | Multiple timeframes agree / 多周期共振 |
| � Divergence | RSI divergence detected / 检测到背离 |
| 🔥❄️ Extreme | RSI at P5/P95 / 极端超买/超卖 |
| 📈📉 Trend Shift | RSI crossed P50 / 趋势转换 |

---

## Usage Tips / 使用建议

| Timeframe | Lookback | Use Case |
|-----------|----------|----------|
| Daily | 252 | Swing trading / 波段交易 |
| 4H | 1000 | Short-term / 短线 |
| 1H | 2000 | Day trading / 日内交易 |

**Best Practices / 最佳实践:**
1. Focus on 🌟 and 💎 signals (highest priority)
2. Use MTF resonance for high-confidence entries
3. Check win rate in stats before trading

---

## Changelog / 更新日志

### v2.1 - Signal Optimization
- ✨ Consolidated signals with priority system (no overlapping)
- ✨ Emoji-based signal display for clarity

### v2.0 - Pro Edition
- ✨ Added Trend Filter, MTF RSI, Statistics, Divergence

### v1.0 - Initial Release
- Adaptive percentile-based thresholds

---

## License

MIT License - Feel free to use, modify, and share.
