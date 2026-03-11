# Adaptive RSI Pro / 自适应RSI专业版

[English README](../README.md)

[![TradingView](https://img.shields.io/badge/TradingView-Indicator-blue?logo=tradingview)](https://www.tradingview.com/scripts/)
[![Pine Script](https://img.shields.io/badge/Pine%20Script-v6-brightgreen)](https://www.tradingview.com/pine-script-reference/v6/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Pine Script v6** | **v7.2**

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
- 三种过滤模式：
  - `Alert Only`：图表信号保留，警报过滤未通过项
  - `Soft`：未通过信号降级显示
  - `Hard`：未通过信号直接隐藏

### 8. 智能警报
- 一条警报聚合全部信号类型
- 包含 RSI、Z-Score、近似百分位和质量等级
- 警报图标与脚本一致：`🌟MTF共振` / `💎背离` / `🔥极端` / `❄️极端` / `⬆️超卖` / `⬇️超买`
- 条件满足时可追加 `✓确认`、`↩反转`、`⚡实时背离`
- 可选 ATR 风险提示，用于止损和止盈建议

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

## 版本历史

### v7.2（当前）- 冷却升级感知
- **新功能**：分级冷却与升级豁免
- **新功能**：高优先级信号（Extreme / Div / MTF）使用 1 bar 冷却
- **新功能**：信号升级可跳过冷却，例如 `Normal -> Extreme`
- **改进**：在市场快速恶化时响应更快
- **说明**：升级豁免仅在信号级别提高时生效，同级别信号仍受冷却约束

### v7.1 - 百分位确认
- **新功能**：在 Trend Protection 分组中提供可选的百分位双重确认模式
- **改进**：极端信号可同时要求满足 Z-Score（-2σ）与 Percentile（P5 / P95）
- **优势**：减少波动率切换阶段的假信号，提高胜率
- **说明**：默认关闭，更适合波动率变化较大的市场

### v7.0 - Dashboard 重构
- 移除 Lite 模式，仅保留 Mobile 和 Full
- 拆分 Signal 行与 Status 行职责
- Status 统一使用动态 `normal_threshold`，不再使用固定 ±1.5σ
- 修复切换模式时表格残留问题
- 用 `switch` 重构警报图标选择逻辑
- 删除冗余变量，简化共享显示逻辑

### v6.9
- 添加 ADX 趋势惩罚，在 ADX > 25 时降低逆势交易评分
- 添加 RSI 拐点确认加分，提升反转信号质量评分

### v6.8
- 添加统计驱动过滤
- 将背离检测重构为单锚点 + offset 模型
- 添加加权 MTF 共振
- 添加可选 ATR 风险提示
- 修复成交量开关与周/月线计算

### v6.7
- 添加基于波动率的智能回看期
- 添加分布宽度反馈
- 添加双层背景显示

### v6.6
- 添加智能普通信号模式（`Off` / `On` / `Smart`）
- 添加基于波动率的自动阈值

### v6.5
- 重构评分模型（Base + Bonuses - Penalties）
- 添加双重波动率检测的自适应冷却逻辑
- 添加排行榜统计模式

---

## 代码质量

本项目使用自定义的 **Pine Script 静态分析器** 进行本地和 CI 检查。

### GitHub CI

当变更涉及 `.pine`、`.pine-lint.yml` 或 `tools/pine_linter/**` 时，GitHub Actions 会自动运行 lint。

[![Pine Script Lint](https://github.com/aaajiao/Adaptive-RSI-Pro/actions/workflows/pine-lint.yml/badge.svg)](https://github.com/aaajiao/Adaptive-RSI-Pro/actions/workflows/pine-lint.yml)

### 本地检查

```bash
python3 tools/pine_linter/cli.py --config .pine-lint.yml adaptive_rsi.pine
python3 tools/pine_linter/cli.py --config .pine-lint.yml --format markdown --output lint-report.md adaptive_rsi.pine
```

### 检查规则

| 规则 | 严重性 | 描述 |
|------|--------|------|
| SEC001 | error | `request.security()` 必须使用 `lookahead=barmerge.lookahead_off` |
| SEC002 | warning | `request.security()` 放在条件分支中可能导致重绘 |
| SYN001 | warning | Pine v6 中多行三元表达式较脆弱 |
| SYN002 | info | `switch` 语句应包含默认分支 |
| SYN003 | warning | `table.clear()` 必须传入明确范围 |
| NAM001-003 | info | 常量、函数、类型的命名规范检查 |
| QUA001 | info | Tooltip 应包含双语文本 |
| QUA002 | warning | `request.security()` 输出应检查 `na` |

配置文件：`.pine-lint.yml`

---

## License

MIT License。允许自由使用、修改和分享。
