# Adaptive RSI Pro / 自适应RSI专业版

[English README](../README.md)

[![TradingView](https://img.shields.io/badge/TradingView-Indicator-blue?logo=tradingview)](https://www.tradingview.com/scripts/)
[![Pine Script](https://img.shields.io/badge/Pine%20Script-v6-brightgreen)](https://www.tradingview.com/pine-script-reference/v6/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Pine Script v6** | **v7.4**

动态阈值 + 多周期分析 + 背离检测 + 统计过滤 + 智能警报

---

## 核心理念

传统 RSI 使用固定的 30/70 阈值，但不同资产的波动特征并不相同。本指标使用 **Z-Score 统计方法** 动态计算阈值，使其适应每个资产的历史分布。

| Z-Score | 百分位 | 含义 |
|---------|--------|------|
| ±2σ | P2 / P98 | 极端区域 |
| ±Nσ | 动态 | 普通超买超卖参考阈值 |

---

## 信号图例

### 买入信号（底部显示）

| 图标 | 名称 | 条件 | 优先级 |
|------|------|------|--------|
| 🌟 | MTF共振 | 多周期同时超卖 + Z < -2σ | ★★★★★ |
| 💎 | 背离+极端 | 看涨背离出现在极端超卖区 | ★★★★☆ |
| 🔥 | 极端超卖 | Z-Score 跌破 -2σ（约等于 P2） | ★★★☆☆ |
| ⬆️ | 普通超卖 | Z-Score 跌破 -Nσ（`normal_threshold`） | ★★☆☆☆ |
| ↗️ | 看涨背离 | 价格创新低但 RSI 未创新低 | ★☆☆☆☆ |

### 卖出信号（顶部显示）

| 图标 | 名称 | 条件 | 优先级 |
|------|------|------|--------|
| 🌟 | MTF共振 | 多周期同时超买 + Z > +2σ | ★★★★★ |
| 💎 | 背离+极端 | 看跌背离出现在极端超买区 | ★★★★☆ |
| ❄️ | 极端超买 | Z-Score 突破 +2σ（约等于 P98） | ★★★☆☆ |
| ⬇️ | 普通超买 | Z-Score 突破 +Nσ（`normal_threshold`） | ★★☆☆☆ |
| ↘️ | 看跌背离 | 价格创新高但 RSI 未创新高 | ★☆☆☆☆ |

> **优先级系统**：同一根 bar 同时满足多个条件时，只显示最高优先级信号。

### 状态指示

| 图标 | 状态 | Z-Score 范围 |
|------|------|--------------|
| 🟢 | 极端超卖 | Z < -2σ |
| 🟡 | 超卖 | -2σ ≤ Z < -Nσ* |
| ⚪ | 中性 | -Nσ ≤ Z ≤ +Nσ |
| 🟠 | 超买 | +Nσ < Z ≤ +2σ |
| 🔴 | 极端超买 | Z > +2σ |

> *N = 动态普通阈值（`normal_threshold`）。脚本会根据波动率自动计算，高波动市场可接近 1.0σ，低波动市场可提升到约 1.8σ。

### 质量等级

每个信号都带有质量评级，基于多因素综合评分：

| 等级 | 分数 | 建议 |
|------|------|------|
| [A] | ≥80 | 高质量，可交易 |
| [B] | 60-79 | 良好，可交易 |
| [C] | 40-59 | 一般，谨慎交易 |
| [D] | <40 | 低质量，通常跳过 |

**评分因素**：MTF共振（+25）| 背离（+25）| RSI拐点确认（+10）| 周线趋势一致（+15）| 成交量放大（+10）| 极端深度（+10/+20）| ADX逆势惩罚（-10）

### 标记说明

| 标记 | 含义 | 说明 |
|------|------|------|
| ✓ | 通过统计过滤 | 可显示在 Dashboard 信号行和警报消息中 |
| ⚠️ | 未通过统计过滤但仍显示 | 常见于 `Alert Only` 或 `Soft` 模式 |
| 🚫 | 信号存在但被隐藏 | 可能由 Smart 普通信号隐藏、趋势保护或 `Hard` 过滤触发 |
| 无 | 非触发状态或未启用统计过滤 | 例如持续状态文本 `🔥持续` 或 `超卖区` |

> **说明**：警报只会对通过统计过滤的信号触发，因此实际警报通常显示 `✓` 或无标记，不会发送 `⚠️`。

---

## 主要功能

### 1. 自适应阈值
- 基于统计公式 `n = (Z × σ / E)²` 自动计算回看期
- 根据资产波动率动态调整 `lookback_min` 与 `lookback_max`
- 提供 High / Normal / Low 三档精度
- 内置样本覆盖、分布宽度与统计有效性健康检查

### 2. 阈值线与视觉模式
- 提供 `Unified`、`Z-Score`、`Percentile`、`Both` 四种阈值线模式
- 支持渐变填充和多空自定义配色
- Dashboard 提供 `Mobile` 与 `Full` 两种布局，以及四档尺寸

### 3. 多周期分析（MTF）
- 自动选择分形周期，或手动设置 3 个周期
- 加权共振检测，最高周期权重翻倍
- `🌟` 共振信号拥有最高优先级
- Dashboard 数据可用性指示：无可用数据的周期在 MTF 行显示 `–`，`Resonance` 行末尾追加 `⚠️`（仅用于显示；共振计算与统计记录不受影响）

### 4. 背离检测
- 自动适配 Low Vol / Normal / High Vol / Crypto 波动环境
- 使用单锚点背离检测，并绘制在结构拐点位置
- 区分极端区背离 `💎` 与普通背离 `↗️` / `↘️`
- 存在实时背离时，警报可追加 `⚡实时背离`

### 5. 趋势保护
- 使用周线趋势过滤，减少逆势交易
- 提供 Aggressive / Moderate / Loose 三档保护级别
- `Percentile Confirm` 可要求极端信号同时满足 Z-Score 与 P5/P95
- Smart 普通信号模式会在周线极端环境下自动隐藏普通信号

### 6. 冷却与信号升级感知
- 高优先级信号（`🌟` / `💎` / `🔥` / `❄️`）使用 1 bar 冷却
- 普通信号 `⬆️` / `⬇️` 使用固定或自适应冷却期
- 同方向信号升级可绕过冷却，例如 `⬆️ -> 🔥 -> 🌟`

### 7. 信号统计与过滤
- 统计模式：`Signal Type`、`Grade`、`Ranking`
- 使用贝叶斯调整减少小样本偏差，再按样本数和调整胜率过滤
- **时间衰减**（`Stats Half-Life Bars`，默认 1500）：样本权重按 K 线间隔指数衰减，淡出旧市场环境的样本；设为 `0` 关闭衰减（旧版等权累计）。衰减只影响胜率置信度——`Min Samples` 门槛按未衰减的累计样本数判断，避免稀有信号桶永远无法达标
- **独立采样**（`Independent Samples`，默认开启）：每个统计桶记录一个样本后，至少间隔前瞻 K 线数才记录下一个，避免前瞻收益区间重叠虚增样本数；关闭 = 旧版重叠采样行为
- **门槛模式**（`Gate Mode`，默认 `Edge vs Baseline`）：胜率门槛相对每个方向的无条件基准胜率衡量——`(最小调整胜率 − 50)` 被解读为要求的超额优势（百分点），贝叶斯先验也收缩到基准胜率；可避免趋势市场中卖出桶被系统性拒绝。`Absolute (Legacy)` 保留旧版固定绝对门槛
- 三种过滤模式：
  - `Alert Only`：图表信号保留，警报过滤未通过项
  - `Soft`：未通过信号降级显示
  - `Hard`：未通过信号直接隐藏

> **升级提示（v7.4）**：以上三项统计引擎升级默认**开启**，与 v7.3 相比会改变通过 gate 的信号。设置 `Stats Half-Life Bars = 0`、关闭 `Independent Samples`、并将 `Gate Mode` 设为 `Absolute (Legacy)` 可恢复 v7.3 旧版统计引擎的计算方式。但 v7.4 在信号层面的其他改动——spread 因子滞回区间和冷却升级等级重置——没有回退开关，记录的信号流以及 gate 判定仍可能与 v7.3 不同。

### 8. 智能警报
- 一条警报聚合全部信号类型
- 包含 RSI、Z-Score、近似百分位和质量等级
- 警报图标与脚本一致：`🌟MTF共振` / `💎背离` / `🔥极端` / `❄️极端` / `⬆️超卖` / `⬇️超买`
- 条件满足时可追加 `✓确认`、`↩反转`、`⚡实时背离`
- 可选 ATR 风险提示，用于止损和止盈建议
- `Alert on Bar Close`（`alert_on_close`，默认关闭）：仅在 K 线收盘确认后触发警报，避免盘中信号闪现后消失（重绘），代价是警报延迟到收盘

### 9. Strategy Harness
- 单独提供 [adaptive_rsi_strategy_harness.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi_strategy_harness.pine)
- 由 [tools/generate_strategy_harness.py](/Users/aaajiao/o_projects/RSI_stock/tools/generate_strategy_harness.py) 从 [adaptive_rsi.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi.pine) 生成
- `Trade Side`：`Long Only / Short Only / Both`
- `Backtest Mode`
  - `Baseline`：原始正式信号
  - `Production`：通过正式警报 gate/过滤的信号
- 可选风险退出（均默认关闭）：
  - `Use ATR SL/TP Exits`（`harness_use_risk_exits`）：按警报展示的 ATR 止损/止盈价格退出（入场时快照价格）
  - `Max Holding Bars`（`harness_max_holding_bars`，`0` = 关闭）：持仓达到 N 根 K 线后强制平仓（时间退出）
- 默认成本为佣金 `0.05%`、滑点 `2` ticks；可在 TradingView `Strategy Tester` → `Properties` 中覆盖，无需修改代码
- `Production` 是过滤后信号回测，不是逐笔盘中 `alert()` 投递模拟
- 详细说明见 [docs/STRATEGY_REPORT_CN.md](/Users/aaajiao/o_projects/RSI_stock/docs/STRATEGY_REPORT_CN.md)

---

## 仪表盘

### Full 模式（桌面端）
```text
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

### Mobile 模式（手机）
```text
┌─────────────────┐
│  RSI      35.2  │
│  Signal   🔥[A]✓│  信号 + 评级 + 标记
│  Status   🟢极卖 │  纯状态
└─────────────────┘
```

---

## 快速开始

### 1. 添加指标
1. 打开 TradingView，进入 Pine Editor。
2. 粘贴 `adaptive_rsi.pine` 全部内容。
3. 点击 `Add to chart`。

### 2. 设置警报
1. 右键指标，选择 `Add Alert`。
2. 条件选择 **Any alert() function call**。
3. 如果需要 ATR 风险提示，开启 `Include Risk Hints in Alerts`。
4. 如果只想在收盘确认后收到警报（避免盘中重绘），开启 `Alert on Bar Close`。

### 3. 推荐预设

| 场景 | Dashboard | 普通信号 | 保护级别 | 过滤模式 |
|------|-----------|----------|----------|----------|
| 日内交易 | Full | Smart | Moderate | Alert Only |
| 波段交易 | Full | Off | Moderate | Hard |
| 手机查看 | Mobile | Off | Loose | Alert Only |

### 4. 过滤模式建议
- `Alert Only`：最适合多数用户，图上保留全部上下文，只过滤警报
- `Soft`：适合想保留上下文、但弱化低质量信号时使用
- `Hard`：适合只看历史表现达标信号，图表最干净

### 5. 策略回测
1. 单独新建一个 Pine 脚本。
2. 粘贴 [adaptive_rsi_strategy_harness.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi_strategy_harness.pine)。
3. 在 TradingView `Strategy Tester` 中切换 `Trade Side` 与 `Backtest Mode`。

---

## 警报消息示例

```text
AAPL: 🟢 BUY → 🌟MTF共振 | RSI:25.3 Z:-2.1σ (≈P2) [A]✓
AAPL: 🔴 SELL → ❄️极端 | RSI:78.5 Z:2.3σ (≈P98) [B]✓
```

开启风险提示后：
```text
AAPL: 🟢 BUY → 🔥极端 ✓确认 ⚡实时背离 | RSI:25.3 Z:-2.1σ (≈P2) [A]✓ | SL:-1.5% TP:+3.0%
```

> **说明**：未通过统计过滤的 `⚠️` 信号不会被发送为警报。如果关闭统计过滤，警报末尾的过滤标记也会消失。

---

## 已知局限

- **统计依赖图表历史**：所有信号统计都基于 TradingView 实际加载的图表历史计算，因此 gate 判定可能因订阅级别、品种、甚至同一品种的不同会话而不同。
- **样本重叠偏差**：`Independent Samples` 可以缓解前瞻收益区间重叠，但无法完全消除样本重叠偏差。
- **低周期 MTF 覆盖范围**：低于图表周期的 MTF 数据只覆盖最近约 `MAX_REQUEST_BARS`（1400）根图表 K 线，因此深历史区域的 MTF 共振信号会很稀疏。
- **盘中重绘**：除非开启 `Alert on Bar Close`，盘中信号可能在收盘前出现又消失。
- **百分位标签是近似值**：Z-Score 转百分位的标签（如 `≈P2`）假设正态分布，仅为显示近似，不是精确排名。
- **harness 范围**：策略壳是过滤后信号回测，不是逐笔盘中 `alert()` 投递模拟。

---

## 当前版本

### v7.4
- 保持公开 `v7.2` 的信号模型作为主基线
- 统计引擎升级（全部默认**开启**；恢复旧版行为的方法见功能 7 的升级提示）：
  - 通过 `Stats Half-Life Bars` 实现样本权重时间衰减
  - 独立采样，避免前瞻收益区间重叠
  - `Edge vs Baseline` 门槛模式，要求相对方向基准胜率的超额优势
- 新增 `Alert on Bar Close` 收盘确认警报选项
- spread 因子滞回：lookback 反馈因子改用滞回区间（低于 18 启用、高于 22 释放），避免在单一阈值附近反复跳变
- 过期升级等级重置：冷却升级豁免只比较仍在冷却期内的上一信号，冷却期已过的旧信号等级按 0 处理
- Dashboard 新增 MTF 数据可用性指示（按周期显示 `–`，并在 `Resonance` 行追加 `⚠️`）
- 策略壳：可选 ATR 止损/止盈退出和最大持仓 K 线时间退出（均默认关闭）
- 保留 `v7.3` 的正确性修复：
  - `lookback` 不低于统计下限
  - 周线保护使用已确认周线数据
  - 下级别 MTF 使用正确的 lower-TF 聚合
- [adaptive_rsi_strategy_harness.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi_strategy_harness.pine) 由正式指标生成，用于 Strategy Tester 验证

> **升级后**：请在 TradingView 重新验证——将两个脚本分别粘贴进 Pine Editor，至少在 `GOOGL 1D`、`AAPL 1D`、`BTCUSDT 4H` 上确认编译和运行行为正常。

### v7.2
- 分级冷却与升级豁免
- 高优先级信号（`🌟` / `💎` / `🔥` / `❄️`）使用 1 bar 冷却
- 同方向信号升级可绕过冷却，例如 `Normal -> Extreme -> MTF`
- 在信号质量快速恶化时响应更快
- 同时包含百分位确认、统计过滤、排行榜和 ATR 风险提示
