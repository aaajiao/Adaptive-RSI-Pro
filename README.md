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
- **Z-Score Based Signals**: Uses statistical Z-Score (±2σ for extreme, ±1.5σ for normal) for consistent cross-asset performance
  使用统计Z-Score（极端±2σ，普通±1.5σ）实现跨资产一致性
- **Percentile Lines**: Display P5/P10/P25/P50/P75/P90/P95 for visual reference
  百分位线（P5-P95）作为视觉参考
- **Dual Display Modes**: Show Z-Score lines, Percentile lines, or both
  双重显示模式：可选择显示Z值线、百分位线或两者

### 🔬 Auto-Adaptive Lookback / 自动自适应回看期
- **Statistical Formula**: Uses `n = (Z × σ / E)²` for optimal sample size calculation
  统计公式：使用样本量公式自动计算最优回看期
- **Dual Volatility System**: Combines short-term (4× RSI length) and long-term volatility (configurable: 6M/1Y/2Y)
  双重波动率系统：结合短期和长期波动率动态调整
- **Precision Control**: Choose High/Normal/Low precision (adjusts acceptable error margin)
  精度控制：高/普通/低精度可选（调整统计误差容忍度）
- **Health Indicators**: Real-time validation of sample coverage, distribution spread, and statistical validity
  健康度指标：实时验证样本覆盖率、分布宽度和统计有效性

### 📈 Auto-Adaptive Trend Filter / 自动自适应趋势过滤
- **Auto Mode**: Automatically selects optimal filter based on RSI volatility percentiles
  自动模式：根据RSI波动率百分位自动选择最优过滤器
- **5 Filter Modes**: Fixed 50, Adaptive P50, SMA(RSI), BB(RSI), or Auto
  5种过滤模式：固定50、自适应P50、RSI均线、布林带或自动
- **Smart Selection**: Low volatility → Fixed 50, Medium → Adaptive P50, High → BB(RSI)
  智能选择：低波动→固定50，中波动→自适应P50，高波动→布林带

### 🌍 Multi-Timeframe RSI / 多时间框架RSI
- **3 Configurable Timeframes**: View RSI status across multiple timeframes (default: 1h/4h/D)
  3个可配置时间框架：跨周期查看RSI状态（默认：1小时/4小时/日线）
- **Auto-Skip Duplicates**: Automatically detects and skips timeframes matching current chart
  自动跳过重复：自动检测并跳过与当前图表相同的时间框架
- **Resonance Detection**: Triggers when 3+ valid timeframes agree (oversold/overbought)
  共振检测：当3个以上有效时间框架一致时触发强信号

> [!NOTE]
> **MTF Signal Confirmation Timing / 信号确认时机**
> 
> - Current timeframe signals update in real-time, confirmed on bar close
> - Higher timeframe signals (e.g., Daily on 1H chart) only update after that timeframe's bar closes
> - **Best Practice**: Wait for current timeframe bar close before acting on MTF resonance signals
> 
> - 当前图表周期的信号：实时更新，K线收盘确认
> - 高周期信号（如日线）：仅在该周期K线收盘后更新
> - **最佳实践**：MTF共振信号建议在当前周期K线收盘后再做交易决策

### 💎 Auto-Adaptive Divergence Detection / 自动自适应背离检测
- **Auto Mode**: Automatically selects parameters based on asset volatility (using ATR)
  自动模式：基于资产波动率（ATR）自动选择参数
- **4 Preset Modes**: Low Vol (3/40), Normal (5/60), High Vol (7/80), Crypto (10/120)
  4种预设模式：低波动/普通/高波动/加密货币，分别对应不同的回看/范围参数
- **Extreme Zone Detection**: Distinguishes divergence in extreme zones (💎) vs normal zones (↗️↘️)
  极端区域检测：区分极端区域背离（💎）和普通背离（↗️↘️）
- **Bullish/Bearish Divergence**: Price lower low + RSI higher low / Price higher high + RSI lower high
  看涨/看跌背离：价格新低+RSI未新低 / 价格新高+RSI未新高

### 📊 Layered Signal Statistics / 分层信号统计
- **4-Tier Classification**: MTF Resonance (🌟) > Divergence+Extreme (💎) > Extreme Only (🔥❄️) > Normal (⬆️⬇️)
  四层分级：多周期共振 > 背离+极端 > 仅极端 > 普通信号
- **Independent Tracking**: Each signal tier has separate count, average return, and win rate
  独立跟踪：每层信号独立统计次数、平均收益、胜率
- **Signal Cooldown**: Optional cooldown period (default 5 bars) to prevent duplicate counting
  信号冷却：可选冷却期（默认5根K线）防止重复计数
- **Real Forward Testing**: Calculates actual returns N bars after signal (configurable 5-100 bars)
  真实前瞻测试：计算信号后N根K线的实际收益（可配置5-100）

---

## Z-Score vs Percentile Reference / Z值与百分位对照表

This indicator uses **Z-Score** for signal triggering and **Percentiles** for visual reference.

本指标使用 **Z-Score** 触发信号，**百分位** 作为视觉参考。

| Z-Score | Approx. Percentile | 含义 / Meaning |
|---------|-------------------|-------------------|
| +2.0σ | P97.7 | Extreme Overbought / 极端超买 |
| +1.5σ | P93.3 | Normal Overbought / 普通超买 |
| +1.0σ | P84.1 | Mild Overbought / 偏强 |
| 0σ (mean) | P50 | Neutral / 中性 |
| -1.0σ | P15.9 | Mild Oversold / 偏弱 |
| -1.5σ | P6.7 | Normal Oversold / 普通超卖 |
| -2.0σ | P2.3 | Extreme Oversold / 极端超卖 |

> **Why Z-Score? / 为什么用 Z-Score？**
> 
> Z-Score provides a **statistically consistent threshold** across different assets, while percentiles vary by asset volatility.
> 
> Z-Score 提供了跨资产的**统计一致性阈值**，而百分位会因资产波动率而异。

---

## Dashboard / 仪表盘

```
┌─────────────────────────────────┐
│   ADAPTIVE RSI PRO       35.2  │
├─────────────────────────────────┤
│ Status      🟢 EXTREME OVERSOLD │
│ Percentile  P10 ↓ DOWN          │
│ Lookback[Auto] 456 ✅✅✅     │
├─────────────────────────────────├ (Full Mode Only)
│ ── MTF ──                   │
│ 1h | 4h | D   🟢 | ⚪ | 🟢      │
│ Resonance    🟢 3/4 OVERSOLD    │
├─────────────────────────────────┤
│ Divergence[Normal] 🟢 BULL (5/60) │
├─────────────────────────────────┤
│ ── STATS ──   (20 bars)         │
│ 🌟 MTF Buy(12)  +4.2% | 83%    │
│ 🌟 MTF Sell(8)  +3.8% | 75%    │
│ 💎 Div Buy(15)  +3.5% | 80%    │
│ 💎 Div Sell(11) +2.9% | 73%    │
│ 🔥 Ext Buy(45)  +2.1% | 67%    │
│ ❄️ Ext Sell(38) +1.8% | 63%    │
└─────────────────────────────────┘
```

**Health Indicators / 健康度指标**:
- ✅✅✅ = All healthy (所有健康): Sample coverage ≥ 80%, Distribution spread ≥ 15, Statistical validity ≥ 90%
- ⚠️ present = Warning (警告): One or more health checks failed, consider using Custom mode with larger lookback

---

## Settings / 设置

### RSI Settings / RSI设置
| Setting | Default | Description |
|---------|---------|-------------|
| RSI Length | 14 | RSI calculation period / RSI计算周期 |
| RSI Source | Close | Price source / 价格源 |

### Adaptive Settings / 自适应设置
| Setting | Default | Description |
|---------|---------|-------------|
| Lookback Mode | Auto | Auto (statistical formula) / Custom / 自动/自定义 |
| Custom Lookback | 252 | Only used in Custom mode / 仅自定义模式使用 |
| Precision | Normal | High/Normal/Low: Adjusts error tolerance / 精度等级 |
| History Depth | 1 Year | 6 Months / 1 Year / 2 Years for volatility calculation / 波动率历史深度 |

### Visual Settings / 视觉设置
| Setting | Default | Description |
|---------|---------|-------------|
| Threshold Line Mode | Z-Score | Z-Score / Percentile / Both / 阈值线模式 |
| Show Gradient Fill | ON | Display background gradients / 显示背景渐变 |
| Dashboard Mode | Full | Full (all stats) / Lite (core only) / 面板模式 |
| Dashboard Size | Normal | Tiny/Small/Normal/Large / 面板大小 |
| Dashboard Transparency | 30 | 0-100% transparency level / 透明度 |

### Trend Filter / 趋势过滤
| Setting | Default | Description |
|---------|---------|-------------|
| Enable Trend Filter | OFF | Only trigger signals in trend direction / 趋势方向过滤 |
| Filter Mode | Auto | Auto/Fixed 50/Adaptive P50/SMA(RSI)/BB(RSI) / 过滤模式 |

### Alert Settings / 警报设置
| Setting | Default | Description |
|---------|---------|-------------|
| Enable Extreme Alerts | ON | Alerts for ±2σ signals / 极端信号警报 |
| Enable Normal Alerts | OFF | Alerts for normal threshold / 普通信号警报 |
| Show Normal Signals | OFF | Display ⬆️⬇️ on chart / 图表显示普通信号 |
| Normal Signal Threshold | 1.5σ | Z-Score threshold (1.0-2.0σ) / 普通信号阈值 |
| Enable Signal Cooldown | ON | Prevent duplicate signal counting / 防止重复信号 |
| Cooldown Period | 5 bars | Bars between same signal type / 冷却K线数 |

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

### Divergence Detection / 背离检测
| Setting | Default | Description |
|---------|---------|-------------|
| Enable Detection | ON | Detect divergences / 检测背离 |
| Divergence Mode | Auto | Auto/Low Vol/Normal/High Vol/Crypto/Custom / 背离模式 |
| Custom Lookback | 5 | Only in Custom mode / 仅自定义模式使用 |
| Custom Range | 60 | Only in Custom mode / 仅自定义模式使用 |

**Auto Mode Presets / 自动模式预设**:
- Low Vol (蓝筹/ETF): Lookback 3, Range 40
- Normal (一般股票): Lookback 5, Range 60  
- High Vol (成长股): Lookback 7, Range 80
- Crypto (加密货币): Lookback 10, Range 120

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

### v3.0 - Auto-Adaptive Systems (Current)
- ✨ Auto-adaptive lookback calculation using statistical formula `n = (Z × σ / E)²`
- ✨ Auto-adaptive trend filter with 5 modes and volatility-based selection
- ✨ Auto-adaptive divergence detection with 4 volatility presets
- ✨ Layered statistics system (MTF/Divergence/Extreme/Normal tiers)
- ✨ Signal cooldown mechanism to prevent duplicate counting
- ✨ Health indicators for lookback validation
- ✨ Dashboard modes (Lite/Full) with customizable size and transparency
- ✨ Dual volatility system (short-term + long-term) for robust calculations

### v2.1 - Signal Optimization
- ✨ Consolidated signals with priority system (no overlapping)
- ✨ Emoji-based signal display for clarity
- ✨ MTF timeframe auto-skip for duplicates

### v2.0 - Pro Edition
- ✨ Added Trend Filter, MTF RSI, Statistics, Divergence
- ✨ Z-Score based signal triggering

### v1.0 - Initial Release
- ✨ Adaptive percentile-based thresholds

---

## License

MIT License - Feel free to use, modify, and share.
