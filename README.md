# Adaptive RSI Pro / 自适应RSI专业版

[![TradingView](https://img.shields.io/badge/TradingView-Indicator-blue?logo=tradingview)](https://www.tradingview.com/scripts/)
[![Pine Script](https://img.shields.io/badge/Pine%20Script-v6-brightgreen)](https://www.tradingview.com/pine-script-reference/v6/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Pine Script v6** | **v7.3**

动态阈值 + 多周期分析 + 背离检测 + 统计过滤 + 智能警报

Dynamic thresholds + Multi-timeframe analysis + Divergence detection + stats filtering + smart alerts

> **Current repo state / 当前仓库状态**
>
> `v7.3` now stays close to the public `v7.2` baseline. Only obvious correctness fixes are applied to the production indicator:
> - safer `lookback` lower-bound handling
> - confirmed weekly trend data
> - proper lower-timeframe MTF aggregation
>
> 当前仓库的 `v7.3` 版本以公开 `v7.2` 为行为基线。正式指标只保留三类明显正确性修复：
> - 更稳的 `lookback` 下限处理
> - 使用已确认周线数据的趋势保护
> - 正确的下级别多周期聚合

## 文件说明 / Files

- [adaptive_rsi.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi.pine): 正式指标 / production indicator
- [adaptive_rsi_strategy_harness.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi_strategy_harness.pine): Strategy Tester 验证脚本 / strategy report harness
- [docs/STRATEGY_REPORT.md](/Users/aaajiao/o_projects/RSI_stock/docs/STRATEGY_REPORT.md): strategy report guide
- [docs/STRATEGY_REPORT_CN.md](/Users/aaajiao/o_projects/RSI_stock/docs/STRATEGY_REPORT_CN.md): 中文 strategy report 说明

---

## 核心理念 / Core Concept

传统RSI使用固定的30/70阈值，但不同资产波动特性不同。本指标使用**Z-Score统计方法**动态计算阈值，自适应每个资产的历史分布。

Traditional RSI uses fixed 30/70 thresholds, but different assets have different volatility. This indicator uses **Z-Score statistics** to dynamically calculate thresholds, adapting to each asset's historical distribution.

| Z-Score | 百分位 Percentile | 含义 Meaning |
|---------|------------------|--------------|
| ±2σ | P2 / P98 | 极端区域 Extreme Zone |
| ±Nσ | 动态 / Dynamic | 普通超买超卖参考 Dynamic normal threshold |

---

## 信号图例 / Signal Legend

### 买入信号 Buy Signals (底部显示)

| 图标 | 名称 | 条件 | 优先级 |
|------|------|------|--------|
| 🌟 | MTF共振 | 多周期同时超卖 + Z<−2σ | ★★★★★ |
| 💎 | 背离+极端 | 看涨背离 + 极端超卖区 | ★★★★☆ |
| 🔥 | 极端超卖 | Z-Score 跌破 −2σ (≈P2) | ★★★☆☆ |
| ⬆️ | 普通超卖 | Z-Score 跌破 −Nσ (`normal_threshold`) | ★★☆☆☆ |
| ↗️ | 看涨背离 | 价格新低 + RSI未新低 | ★☆☆☆☆ |

### 卖出信号 Sell Signals (顶部显示)

| 图标 | 名称 | 条件 | 优先级 |
|------|------|------|--------|
| 🌟 | MTF共振 | 多周期同时超买 + Z>+2σ | ★★★★★ |
| 💎 | 背离+极端 | 看跌背离 + 极端超买区 | ★★★★☆ |
| ❄️ | 极端超买 | Z-Score 突破 +2σ (≈P98) | ★★★☆☆ |
| ⬇️ | 普通超买 | Z-Score 突破 +Nσ (`normal_threshold`) | ★★☆☆☆ |
| ↘️ | 看跌背离 | 价格新高 + RSI未新高 | ★☆☆☆☆ |

> **优先级系统**: 同时满足多个条件时，只显示最高优先级信号，避免叠加。
> 
> **Priority System**: When multiple conditions are met, only the highest priority signal is shown.

### 状态指示 Status Indicators

| 图标 | 状态 | Z-Score范围 |
|------|------|-------------|
| 🟢 | 极端超卖 | Z < −2σ |
| 🟡 | 超卖 | −2σ ≤ Z < −Nσ* |
| ⚪ | 中性 | −Nσ ≤ Z ≤ +Nσ |
| 🟠 | 超买 | +Nσ < Z ≤ +2σ |
| 🔴 | 极端超买 | Z > +2σ |

> *N = 动态普通阈值 (`normal_threshold`)，由脚本按波动率自动计算；高波动市场可接近 1.0σ，低波动市场可提升到 1.8σ 左右

### 质量等级 Quality Grades

每个信号附带质量评级，基于多因素评分：

| 等级 | 分数 | 建议 |
|------|------|------|
| [A] | ≥80 | 高质量，可交易 |
| [B] | 60-79 | 良好，可交易 |
| [C] | 40-59 | 一般，谨慎交易 |
| [D] | <40 | 低质量，建议观望 |

**评分因素**: MTF共振(+25) | 背离(+25) | RSI拐点确认(+10) | 周线趋势一致(+15) | 成交量放大(+10) | 极端深度(+10/+20) | ADX逆势惩罚(-10)

### 标记说明 / Display Marks

| 标记 | 含义 | 说明 |
|------|------|------|
| ✓ | 通过统计过滤 | Dashboard 信号行和警报消息可显示 |
| ⚠️ | 未通过统计过滤但仍显示 | 常见于 `Alert Only` 或 `Soft` 模式下的图表/面板显示 |
| 🚫 | 信号存在但被隐藏 | 可能由 Smart 普通信号隐藏、趋势保护或 `Hard` 过滤触发 |
| 无 | 非触发状态或未启用统计过滤 | 例如持续区域状态 `🔥持续` / `超卖区` |

> **注意 / Note**: 当前脚本的警报只会对通过统计过滤的信号触发，因此警报消息通常显示 `✓` 或无标记，不会发送 `⚠️`。

---

## 主要功能 / Key Features

### 1. 自适应阈值 Adaptive Thresholds
- 自动计算回看期，基于统计公式 `n = (Z × σ / E)²`
- 根据资产波动率自动调整 `lookback_min` / `lookback_max`
- 三级精度可选: High / Normal / Low
- 内置健康度检查: 样本覆盖、分布宽度、统计有效性

### 2. 阈值线与视觉模式 Visual Line Modes
- `Unified` / `Z-Score` / `Percentile` / `Both` 四种阈值线模式
- 可选渐变填充与自定义多空配色
- Dashboard 支持 `Mobile` / `Full` 两种模式与四档尺寸

### 3. 多周期分析 Multi-Timeframe (MTF)
- 自动选择分形周期或手动设置3个周期
- 加权共振检测 (最高周期权重×2)
- 共振信号 `🌟` 为最高优先级

### 4. 背离检测 Divergence Detection
- 自动适应波动率 (Low Vol / Normal / High Vol / Crypto)
- 单锚点检测，信号绘制在结构转折点
- 极端区背离 `💎` vs 普通背离 `↗️` / `↘️`
- 警报可附加 `⚡实时背离`

### 5. 趋势保护 Trend Protection
- 周线趋势过滤，避免逆势交易
- 三档保护级别: Aggressive / Moderate / Loose
- `Percentile Confirm` 可要求极端信号同时满足 Z-Score 与 P5/P95
- Smart 普通信号模式会在周线极端环境下自动隐藏普通信号

### 6. 冷却与信号升级 Cooldown Upgrade Awareness
- 高优先级信号 (`🌟` / `💎` / `🔥` / `❄️`) 使用 1 bar 冷却
- 普通信号 `⬆️` / `⬇️` 使用固定或智能冷却期
- 同方向信号升级可绕过冷却，例如 `⬆️ -> 🔥 -> 🌟`

### 7. 信号统计与过滤 Signal Statistics & Filtering
- 统计模式: `Signal Type` / `Grade` / `Ranking`
- 贝叶斯调整小样本偏差，按样本数与调整胜率过滤
- 三种过滤模式:
  - `Alert Only`: 图表照常显示，警报过滤未通过信号
  - `Soft`: 未通过信号降级显示
  - `Hard`: 未通过信号直接隐藏

### 8. 智能警报 Smart Alert
- 一条警报聚合所有信号
- 包含完整上下文: RSI值、Z-Score、近似百分位、质量等级
- 警报图标与脚本保持一致: `🌟MTF共振` / `💎背离` / `🔥极端` / `❄️极端` / `⬆️超卖` / `⬇️超买`
- 条件满足时可附加 `✓确认` / `↩反转` / `⚡实时背离`
- 可选ATR风险提示 (止损/止盈建议)

### 9. Strategy Report Harness
- 单独提供 [adaptive_rsi_strategy_harness.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi_strategy_harness.pine)
- `Trade Side`: `Long Only` / `Short Only` / `Both`
- `Backtest Mode`
  - `Baseline`: 原始 7.2 信号
  - `Production`: 正式指标最终进入警报的信号
- dashboard 额外提示 `Harness`、`Tester`、`Production Gate`
- 详细说明见 [docs/STRATEGY_REPORT.md](/Users/aaajiao/o_projects/RSI_stock/docs/STRATEGY_REPORT.md)

---

## 仪表盘 / Dashboard

### Full 模式 (PC)
```
┌────────────────────────────────────────┐
│ ADAPTIVE RSI                    35.2   │
├────────────────────────────────────────┤
│ Z-Score     -2.15σ (≈P2)               │
│ Percentile  P5 (−1.5σ ~ −2σ)           │
│ Signal      🔥[A]✓                     │
│ Status      🟢 EXTREME OVERSOLD        │
│ Protection  ✓ W.RSI:45 📊↑             │
│ Lookback    456(150-800) ✅✅✅         │
│ Normal      ⬆️1.50σ ✓                  │
├────────────────────────────────────────┤
│ MTF 1m|5m|15m  🟢|⚪|🟢                │
│ Resonance    🟢 3/4                    │
│ Divergence Auto  🟢 BULL (5/60)        │
├────────────────────────────────────────┤
│ Ranking      (20b)                     │
│ 🌟[A]📈(12)✓  +4.5%|85%                │
│ 💎[A]📈(8)✓   +4.2%|82%                │
└────────────────────────────────────────┘
```

### Mobile 模式 (手机)
```
┌─────────────────┐
│  RSI      35.2  │
│  Signal   🔥[A]✓│  信号+评级+标记
│  Status   🟢极卖 │  纯状态
└─────────────────┘
```

---

## 快速开始 / Quick Start

### 1. 添加指标
1. TradingView → Pine Editor
2. 粘贴 `adaptive_rsi.pine` 代码
3. 点击 `Add to chart`

### 2. 设置警报
1. 右键指标 → "Add Alert"
2. 条件选择 **"Any alert() function call"**
3. 如需风险提示，开启 `Include Risk Hints in Alerts`

### 3. 推荐设置

| 场景 | Dashboard | 普通信号 | 保护级别 | 过滤模式 |
|------|-----------|----------|----------|----------|
| 日内交易 | Full | Smart | Moderate | Alert Only |
| 波段交易 | Full | Off | Moderate | Hard |
| 手机查看 | Mobile | Off | Loose | Alert Only |

### 4. 过滤模式建议 / Filter Mode Tips
- `Alert Only`: 最适合多数用户，图上保留全部信号，警报只发统计通过的信号
- `Soft`: 想保留上下文，但弱化低质量信号时使用
- `Hard`: 只看历史表现达标的信号，图表最干净

---

## 警报消息示例 / Alert Examples

```
AAPL: 🟢 BUY → 🌟MTF共振 | RSI:25.3 Z:-2.1σ (≈P2) [A]✓
AAPL: 🔴 SELL → ❄️极端 | RSI:78.5 Z:2.3σ (≈P98) [B]✓
```

开启风险提示后:
```
AAPL: 🟢 BUY → 🔥极端 ✓确认 ⚡实时背离 | RSI:25.3 Z:-2.1σ (≈P2) [A]✓ | SL:-1.5% TP:+3.0%
```

> **说明 / Note**: 警报不会发送未通过统计过滤的 `⚠️` 信号；如果关闭统计过滤，警报末尾的过滤标记会消失。

---

## 版本历史 / Changelog

### v7.3 - Restored Baseline / 回归基线版
- **Change / 变更**: Keep public `v7.2` behavior as the product baseline / 以公开 `v7.2` 行为作为产品基线
- **Fix / 修复**: Keep `lookback` above statistical floor / 保证 `lookback` 不低于统计下限
- **Fix / 修复**: Weekly protection uses confirmed weekly bars / 周线保护使用已确认周线
- **Fix / 修复**: Lower-timeframe MTF uses proper lower-TF aggregation / 下级别 MTF 改为正确聚合
- **New / 新功能**: Added [adaptive_rsi_strategy_harness.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi_strategy_harness.pine) for Strategy Tester validation

### v7.2 - Cooldown Upgrade Awareness / 冷却升级感知
- **New / 新功能**: Tiered cooldown with upgrade exemption / 分级冷却与升级豁免
  - High-priority signals (Extreme/Div/MTF) use 1-bar cooldown / 高优先级信号使用 1 bar 冷却
  - Signal upgrade bypasses cooldown (e.g., Normal → Extreme) / 信号升级可跳过冷却
- **Improvement / 改进**: Faster response to rapid market deterioration / 急跌行情中更快响应
- **Note / 说明**: 升级豁免仅在信号级别提升时生效，同级别信号仍受冷却约束

### v7.1 - Percentile Confirm / 百分位确认
- **New / 新功能**: 可选的百分位双重确认模式 (Trend Protection 组)
- **Improvement / 改进**: 极端信号需同时满足 Z-Score(-2σ) 和 Percentile(P5/P95)
- **Benefit / 优势**: 减少波动率变化时的假信号，提升胜率
- **Note / 说明**: 默认关闭，适用于波动率变化较大的市场

### v7.0 - Dashboard 重构 / Dashboard Refactor
- **移除 Lite 模式** - 仅保留 Mobile 和 Full 两种模式
- **Signal/Status 职责分离** - Signal 行显示信号+评级+标记，Status 行只显示纯区域状态
- **统一动态阈值** - Status 状态使用动态 `normal_threshold` 而非固定 ±1.5σ
- **修复表格残留** - 切换模式时自动清除旧行内容
- **Alert 重构** - 使用 switch 语句简化图标选择，过滤标记仅在启用时显示
- **代码优化** - 删除冗余变量，统一信号显示逻辑

### v6.9
- ADX趋势惩罚 (ADX>25时逆势信号-10分，避免强趋势中逆势交易)
- RSI拐点确认加分 (极端区形成RSI拐点+10分，提升反转信号可信度)

### v6.8
- 统计驱动过滤器 (基于历史胜率过滤信号)
- 背离检测重构 (单锚点 + offset绘制)
- MTF加权共振 (高周期权重×2)
- ATR风险提示 (可选止损止盈)
- Bug修复: 成交量开关、周月线计算

### v6.7
- 智能回看期 (基于波动率动态范围)
- 分布宽度反馈环
- 双层背景显示

### v6.6
- 智能普通信号模式 (Off/On/Smart)
- 自动阈值 (基于波动率)

### v6.5
- 重构评分系统 (Base + Bonuses - Penalties)
- 智能冷却期 (双重波动率检测)
- 排行榜统计模式

---

## 代码质量 / Code Quality

本项目使用自定义的 **Pine Script 静态分析器** 进行代码质量检查。

This project uses a custom **Pine Script Static Analyzer** for code quality checks.

### GitHub CI

每次推送或提交涉及 `.pine`、`.pine-lint.yml`、`tools/pine_linter/**` 的变更时，GitHub Actions 会自动运行 lint 检查。

Lint checks run automatically via GitHub Actions when changes touch `.pine`, `.pine-lint.yml`, or `tools/pine_linter/**`.

[![Pine Script Lint](https://github.com/aaajiao/Adaptive-RSI-Pro/actions/workflows/pine-lint.yml/badge.svg)](https://github.com/aaajiao/Adaptive-RSI-Pro/actions/workflows/pine-lint.yml)

### 本地检查 / Local Check

```bash
python3 tools/pine_linter/cli.py --config .pine-lint.yml adaptive_rsi.pine
python3 tools/pine_linter/cli.py --config .pine-lint.yml --format markdown --output lint-report.md adaptive_rsi.pine
```

### 检查规则 / Lint Rules

| 规则 Rule | 严重性 Severity | 描述 Description |
|-----------|----------------|------------------|
| SEC001 | error | `request.security()` 需要 `lookahead=barmerge.lookahead_off` |
| SEC002 | warning | `request.security()` 在条件语句内可能导致重绘 |
| SYN001 | warning | 多行三元表达式 (v6 语法陷阱) |
| SYN002 | info | `switch` 语句应包含默认分支 |
| SYN003 | warning | `table.clear()` 需要传入清理范围参数 |
| NAM001-003 | info | 命名规范检查 (常量/函数/类型) |
| QUA001 | info | Tooltip 应包含双语文本 |
| QUA002 | warning | `request.security()` 结果应检查 na |

配置文件: `.pine-lint.yml`

---

## License

MIT License - Feel free to use, modify, and share.
