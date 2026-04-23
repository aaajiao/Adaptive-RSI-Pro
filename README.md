# Adaptive RSI Pro

[中文说明 / Chinese README](docs/README_CN.md)

[![TradingView](https://img.shields.io/badge/TradingView-Indicator-blue?logo=tradingview)](https://www.tradingview.com/scripts/)
[![Pine Script](https://img.shields.io/badge/Pine%20Script-v6-brightgreen)](https://www.tradingview.com/pine-script-reference/v6/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Pine Script v6** | **v7.3**

Dynamic thresholds + multi-timeframe analysis + divergence detection + stats filtering + smart alerts

---

## Core Concept

Traditional RSI uses fixed 30/70 thresholds, but different assets have different volatility regimes. This indicator uses **Z-Score statistics** to calculate adaptive thresholds based on each asset's historical distribution.

| Z-Score | Percentile | Meaning |
|---------|------------|---------|
| ±2σ | P2 / P98 | Extreme zone |
| ±Nσ | Dynamic | Dynamic normal overbought/oversold reference |

---

## Signal Legend

### Buy Signals (shown near the bottom)

| Icon | Name | Condition | Priority |
|------|------|-----------|----------|
| 🌟 | MTF Resonance | Multi-timeframe oversold alignment + Z < -2σ | ★★★★★ |
| 💎 | Divergence + Extreme | Bullish divergence inside the extreme oversold zone | ★★★★☆ |
| 🔥 | Extreme Oversold | Z-Score breaks below -2σ (about P2) | ★★★☆☆ |
| ⬆️ | Normal Oversold | Z-Score breaks below -Nσ (`normal_threshold`) | ★★☆☆☆ |
| ↗️ | Bullish Divergence | Price makes a new low while RSI does not | ★☆☆☆☆ |

### Sell Signals (shown near the top)

| Icon | Name | Condition | Priority |
|------|------|-----------|----------|
| 🌟 | MTF Resonance | Multi-timeframe overbought alignment + Z > +2σ | ★★★★★ |
| 💎 | Divergence + Extreme | Bearish divergence inside the extreme overbought zone | ★★★★☆ |
| ❄️ | Extreme Overbought | Z-Score breaks above +2σ (about P98) | ★★★☆☆ |
| ⬇️ | Normal Overbought | Z-Score breaks above +Nσ (`normal_threshold`) | ★★☆☆☆ |
| ↘️ | Bearish Divergence | Price makes a new high while RSI does not | ★☆☆☆☆ |

> **Priority system**: When multiple conditions are true on the same bar, only the highest-priority signal is shown.

### Status Indicators

| Icon | Status | Z-Score Range |
|------|--------|---------------|
| 🟢 | Extreme oversold | Z < -2σ |
| 🟡 | Oversold | -2σ ≤ Z < -Nσ* |
| ⚪ | Neutral | -Nσ ≤ Z ≤ +Nσ |
| 🟠 | Overbought | +Nσ < Z ≤ +2σ |
| 🔴 | Extreme overbought | Z > +2σ |

> *N = the dynamic normal threshold (`normal_threshold`). The script calculates it from volatility, so it can be near 1.0σ in high-volatility markets and around 1.8σ in lower-volatility markets.

### Quality Grades

Each signal carries a quality grade based on multi-factor scoring:

| Grade | Score | Interpretation |
|-------|-------|----------------|
| [A] | ≥80 | High quality, tradable |
| [B] | 60-79 | Good, tradable |
| [C] | 40-59 | Mixed, trade cautiously |
| [D] | <40 | Low quality, usually skip |

**Scoring factors**: MTF resonance (+25) | divergence (+25) | RSI pivot confirmation (+10) | weekly trend alignment (+15) | volume surge (+10) | deeper extremes (+10/+20) | ADX counter-trend penalty (-10)

### Display Marks

| Mark | Meaning | Notes |
|------|---------|-------|
| ✓ | Passed the stats filter | Can appear in dashboard signal rows and alert messages |
| ⚠️ | Failed the stats filter but still shown | Common in `Alert Only` or `Soft` mode |
| 🚫 | Signal exists but is hidden | Can be caused by Smart normal-signal hiding, trend protection, or `Hard` filtering |
| None | Not triggered or stats filter disabled | For example persistent state text such as `🔥持续` or `超卖区` |

> **Note**: Alerts fire only for signals that pass the stats filter. In practice, alert text usually shows `✓` or no mark at all, and does not send `⚠️`.

---

## Key Features

### 1. Adaptive Thresholds
- Automatically calculates the lookback window from the statistical formula `n = (Z × σ / E)²`
- Adjusts `lookback_min` and `lookback_max` from asset volatility
- Three precision presets: High / Normal / Low
- Includes health checks for sample coverage, distribution width, and statistical validity

### 2. Threshold Lines and Visual Modes
- Four line modes: `Unified`, `Z-Score`, `Percentile`, and `Both`
- Optional gradient fills and custom bull/bear colors
- Dashboard supports both `Mobile` and `Full` layouts with four size presets

### 3. Multi-Timeframe (MTF) Analysis
- Automatic fractal timeframe selection or manual selection of three timeframes
- Weighted resonance detection, with the highest timeframe counting double
- `🌟` resonance signals are the top-priority signals

### 4. Divergence Detection
- Volatility-adaptive behavior for Low Vol / Normal / High Vol / Crypto
- Single-anchor divergence detection, plotted at the structure pivot
- Extreme-zone divergence `💎` versus regular divergence `↗️` / `↘️`
- Alerts can append `⚡实时背离` when realtime divergence is present

### 5. Trend Protection
- Weekly trend filter to reduce counter-trend trades
- Three protection levels: Aggressive / Moderate / Loose
- `Percentile Confirm` can require extreme signals to satisfy both Z-Score and P5/P95 conditions
- Smart normal-signal mode automatically hides normal signals during weekly extreme conditions

### 6. Cooldown Upgrade Awareness
- High-priority signals (`🌟` / `💎` / `🔥` / `❄️`) use a 1-bar cooldown
- Normal signals `⬆️` / `⬇️` use fixed or adaptive cooldown bars
- Same-side signal upgrades can bypass cooldown, such as `⬆️ -> 🔥 -> 🌟`

### 7. Signal Statistics and Filtering
- Stats modes: `Signal Type`, `Grade`, and `Ranking`
- Uses Bayesian adjustment to reduce small-sample bias before filtering by sample count and adjusted win rate
- Three filter modes:
  - `Alert Only`: chart signals stay visible, alerts are filtered
  - `Soft`: failed signals are downgraded visually
  - `Hard`: failed signals are hidden

### 8. Smart Alert
- A single alert aggregates all signal types
- Includes RSI, Z-Score, approximate percentile, and quality grade
- Alert icons match the script output: `🌟MTF共振` / `💎背离` / `🔥极端` / `❄️极端` / `⬆️超卖` / `⬇️超买`
- Can append `✓确认`, `↩反转`, and `⚡实时背离` when conditions apply
- Optional ATR-based risk hints for stop-loss and take-profit suggestions

### 9. Strategy Harness
- Separate file: [adaptive_rsi_strategy_harness.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi_strategy_harness.pine)
- Generated from [adaptive_rsi.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi.pine) by [tools/generate_strategy_harness.py](/Users/aaajiao/o_projects/RSI_stock/tools/generate_strategy_harness.py)
- `Trade Side`: `Long Only / Short Only / Both`
- `Backtest Mode`
  - `Baseline`: raw production signals
  - `Production`: signals that pass the production alert gate/filter
- `Production` is a gated-signal backtest, not an exact intrabar `alert()` delivery simulation
- Full guide: [docs/STRATEGY_REPORT.md](/Users/aaajiao/o_projects/RSI_stock/docs/STRATEGY_REPORT.md)

---

## Dashboard

### Full Mode (Desktop)
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

### Mobile Mode
```text
┌─────────────────┐
│  RSI      35.2  │
│  Signal   🔥[A]✓│  Signal + grade + mark
│  Status   🟢EXT │  Pure status
└─────────────────┘
```

---

## Quick Start

### 1. Add the Indicator
1. Open TradingView and go to Pine Editor.
2. Paste the contents of `adaptive_rsi.pine`.
3. Click `Add to chart`.

### 2. Configure Alerts
1. Right-click the indicator and choose `Add Alert`.
2. Set the condition to **Any alert() function call**.
3. If you want ATR hints in alerts, enable `Include Risk Hints in Alerts`.

### 3. Suggested Presets

| Scenario | Dashboard | Normal Signals | Protection Level | Filter Mode |
|----------|-----------|----------------|------------------|-------------|
| Intraday trading | Full | Smart | Moderate | Alert Only |
| Swing trading | Full | Off | Moderate | Hard |
| Mobile monitoring | Mobile | Off | Loose | Alert Only |

### 4. Filter Mode Tips
- `Alert Only`: best default for most users; keep all chart context while filtering alerts
- `Soft`: useful when you want context but lower-quality signals de-emphasized
- `Hard`: use when you only want historically qualified signals and a cleaner chart

### 5. Strategy Validation
1. Open a separate Pine script.
2. Paste [adaptive_rsi_strategy_harness.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi_strategy_harness.pine).
3. Use TradingView `Strategy Tester` with `Trade Side` and `Backtest Mode`.

---

## Alert Examples

```text
AAPL: 🟢 BUY → 🌟MTF共振 | RSI:25.3 Z:-2.1σ (≈P2) [A]✓
AAPL: 🔴 SELL → ❄️极端 | RSI:78.5 Z:2.3σ (≈P98) [B]✓
```

With risk hints enabled:
```text
AAPL: 🟢 BUY → 🔥极端 ✓确认 ⚡实时背离 | RSI:25.3 Z:-2.1σ (≈P2) [A]✓ | SL:-1.5% TP:+3.0%
```

> **Note**: Alerts do not send `⚠️` signals that fail the stats filter. If stats filtering is disabled, the filter mark at the end of the alert also disappears.

---

## Current Version

### v7.3
- Keeps the public `v7.2` signal model as the main baseline
- Retains only minimal correctness fixes:
  - `lookback` floor stays above the statistical lower bound
  - weekly protection uses confirmed weekly data
  - lower-timeframe MTF uses proper lower-TF aggregation
- Keeps [adaptive_rsi_strategy_harness.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi_strategy_harness.pine) generated from the production indicator for Strategy Tester validation
- Stores signal statistics in indexed buckets instead of duplicated per-bucket variables

### v7.2
- Tiered cooldown with upgrade exemption
- High-priority signals (`🌟` / `💎` / `🔥` / `❄️`) use a 1-bar cooldown
- Same-side upgrades can bypass cooldown, such as `Normal -> Extreme -> MTF`
- Faster response when signal quality deteriorates quickly
- Includes percentile confirm, stats filtering, ranking, and ATR risk hints

---

## Code Quality

This project uses a custom **Pine Script Static Analyzer** and a generated strategy harness check for local and CI validation.

### GitHub CI

GitHub Actions runs lint and harness-generation checks automatically when changes touch `.pine`, `.pine-lint.yml`, or project tooling.

[![Pine Script Lint](https://github.com/aaajiao/Adaptive-RSI-Pro/actions/workflows/pine-lint.yml/badge.svg)](https://github.com/aaajiao/Adaptive-RSI-Pro/actions/workflows/pine-lint.yml)

### Local Check

```bash
python3 tools/generate_strategy_harness.py --check
python3 tools/pine_linter/cli.py --config .pine-lint.yml adaptive_rsi.pine
python3 tools/pine_linter/cli.py --config .pine-lint.yml adaptive_rsi_strategy_harness.pine
python3 tools/pine_linter/cli.py --config .pine-lint.yml --format markdown --output lint-report.md adaptive_rsi.pine adaptive_rsi_strategy_harness.pine
```

When production logic changes, regenerate the harness with:

```bash
python3 tools/generate_strategy_harness.py
```

### Lint Rules

| Rule | Severity | Description |
|------|----------|-------------|
| SEC001 | error | `request.security()` must declare `lookahead`; `lookahead_off` is safe, while `lookahead_on` requires a `[1]` confirmed historical expression |
| SEC002 | warning | `request.security()` inside conditional branches may repaint |
| SYN001 | warning | Multi-line ternary expressions are fragile in Pine v6 |
| SYN002 | info | `switch` statements should include a default branch |
| SYN003 | warning | `table.clear()` must receive an explicit range |
| NAM001-003 | info | Naming convention checks for constants, functions, and types |
| QUA001 | info | Tooltips should include bilingual text |
| QUA002 | warning | `request.security()` outputs should be checked for `na` |

Config file: `.pine-lint.yml`
