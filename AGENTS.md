# AGENTS.md - Adaptive RSI Pro

> Guidelines for AI agents working on this TradingView Pine Script v6 indicator.

## Quick Reference

| Item | Value |
|------|-------|
| **Language** | Pine Script v6 |
| **Main File** | `adaptive_rsi.pine` (~1660 lines) |
| **Platform** | TradingView (tradingview.com) |
| **Build/Test** | Manual via TradingView Pine Editor |

## Build & Validation

**No local build system.** Pine Script compiles only on TradingView.

### Validation Steps
1. Copy full `adaptive_rsi.pine` content
2. TradingView → Pine Editor → paste → "Add to chart"
3. Compiler shows errors inline; runtime errors appear on chart

### Testing Checklist
- [ ] Compiles without errors
- [ ] Works on multiple timeframes (1m, 1H, 4H, D, W, M)
- [ ] Works on different assets (stocks, crypto, forex, ETFs)
- [ ] All 3 dashboard modes render (Mobile/Lite/Full)
- [ ] Alerts fire with correct message format
- [ ] No performance lag

## Code Style

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Constants | SCREAMING_SNAKE | `MAX_BARS_BACK = 4500` |
| Variables | snake_case | `rsi_zscore`, `lookback_min` |
| Functions | f_prefix_snake | `f_zscore_to_percentile()` |
| User Types | PascalCase | `SignalStats`, `RankEntry` |
| Methods | camelCase | `this.get_winrate()` |
| Input groups | grp_prefix | `grp_rsi`, `grp_alerts` |

### File Header
```pinescript
//@version=6
indicator("Title", shorttitle="SHORT", overlay=false, precision=2, max_bars_back=4500)
```

### Section Structure
```pinescript
// ────────────────────────────────────────
// SECTION NAME
// ────────────────────────────────────────
```

### Input Groups (Bilingual EN/CN)
```pinescript
grp_rsi = "═══ RSI Settings / RSI设置 ═══"
rsi_length = input.int(14, "RSI Length / RSI周期", group=grp_rsi,
    tooltip="English explanation\n中文说明")
```

### User-Defined Types
```pinescript
type SignalStats
    int count = 0
    float total_return = 0.0
    int wins = 0

method get_avg(SignalStats this) =>
    this.count > 0 ? this.total_return / this.count : 0.0
```

### Conditional Logic
- **Ternary** for simple assignments:
  ```pinescript
  status = zscore > 2 ? "overbought" : zscore < -2 ? "oversold" : "neutral"
  ```
- **if/else** for side effects or multi-line logic

### String Formatting
```pinescript
str.format("{0}: {1,number,#.##}%", label, value)
str.format("{0,number,+#.1;-#.1}%", return_value)  // +/- sign
```

## Critical Patterns

### request.security() - ALWAYS prevent lookahead bias
```pinescript
[weekly_rsi, weekly_close] = request.security(
    syminfo.tickerid, "W",
    [ta.rsi(close, 14), close],
    lookahead=barmerge.lookahead_off  // REQUIRED
)
```

### var vs varip
```pinescript
var int persistent_across_bars = 0      // Recalculates each tick
varip int persistent_across_ticks = 0   // Truly persistent within bar
```

### Signal Cooldown (prevent duplicates)
```pinescript
varip int last_alert_bar = -1
varip int last_alert_level = 0

new_signal = bar_index != last_alert_bar or current_level > last_alert_level
if new_signal
    last_alert_bar := bar_index
    last_alert_level := current_level
```

### Timeframe Detection
```pinescript
tf_minutes = timeframe.in_seconds(timeframe.period) / 60
bars_per_day = timeframe.ismonthly ? 1.0/21 : timeframe.isweekly ? 1.0/5 : 
               timeframe.isdaily ? 1 : math.ceil(1440 / tf_minutes)
```

## Architecture Overview

```
INPUT GROUPS → RSI CALC → Z-SCORE → SIGNAL DETECTION → QUALITY SCORING → DASHBOARD
                  ↓              ↓           ↓
              PERCENTILES    MTF DATA    DIVERGENCE
```

### Signal Flow
1. **RSI Calculation**: Standard RSI from `ta.rsi()`
2. **Z-Score**: `(rsi - mean) / stdev` over dynamic lookback
3. **Percentile Mapping**: Z-Score → approximate percentile
4. **MTF Analysis**: `request.security()` for higher timeframes
5. **Signal Detection**: Crossover/crossunder of Z-Score thresholds
6. **Quality Grading**: A/B/C/D based on multi-factor scoring
7. **Statistics Tracking**: Win rate, returns per signal type
8. **Dashboard Rendering**: Table-based UI

### Signal Priority (highest wins)
| Priority | Signal | Condition |
|----------|--------|-----------|
| 4 | MTF Resonance 🌟 | Multiple TFs aligned + extreme |
| 3 | Divergence+Extreme 💎 | Divergence in extreme zone |
| 2 | Extreme 🔥/❄️ | Z-Score crosses ±2σ |
| 1 | Normal ⬆️/⬇️ | Z-Score crosses ±1.5σ |

### Quality Score Factors
- **Base**: 50 pts if in extreme zone
- **Bonuses**: MTF/Divergence (+25), RSI pivot (+10), Weekly trend (+15), Volume surge (+10), Extreme depth (+10/20)
- **Penalties**: Weekly extreme bearish (-20), Low volume (-10), Poor health (-15), ADX counter-trend (-10)

## Common Gotchas

| Issue | Solution |
|-------|----------|
| Array/lookback limit | Max ~4500 bars; use `max_bars_back=4500` |
| Future data leak | Always `lookahead=barmerge.lookahead_off` |
| Plot limits | Use tables for dashboards, not plots |
| String in switch | Pine v6 requires exact string matches |
| na propagation | Always check `not na()` before using values |

## Making Changes

1. **Read entire file** - Single ~1660 line file; understand signal flow
2. **Preserve bilingual** - All user-facing text needs EN/CN
3. **Test all modes** - Mobile/Lite/Full dashboard, all timeframes
4. **Check signal cascade** - Changes to scoring affect multiple signals

### Changelog Format (in README.md)
```markdown
### vX.Y - Feature Name / 功能名称
- **New / 新功能**: Description / 描述
- **Fix / 修复**: Description / 描述
```

## External Resources

- [Pine Script v6 Reference](https://www.tradingview.com/pine-script-reference/v6/)
- [Pine Script v6 Manual](https://www.tradingview.com/pine-script-docs/en/v6/)
- [TradingView Pine Editor](https://www.tradingview.com/chart/) → Pine Editor tab
