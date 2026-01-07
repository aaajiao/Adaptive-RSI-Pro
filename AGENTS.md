# AGENTS.md - Adaptive RSI Pro

> Guidelines for AI coding agents working on this TradingView Pine Script indicator.

## Project Overview

**Type**: TradingView Pine Script v6 Indicator  
**Main File**: `adaptive_rsi.pine` (~2500 lines)  
**Language**: Pine Script v6  
**Purpose**: Adaptive RSI with dynamic thresholds, multi-timeframe analysis, divergence detection, and signal statistics

## Build/Lint/Test Commands

### No Local Build System

Pine Script runs exclusively on TradingView's platform. There is no local build, lint, or test system.

**Validation Process**:
1. Copy `adaptive_rsi.pine` content
2. Paste into TradingView Pine Editor (tradingview.com → Pine Editor)
3. Click "Add to chart" to compile and validate
4. TradingView compiler will show any syntax errors

**Testing**:
- Visual verification on chart
- Test on different assets (stocks, crypto, ETFs)
- Test on different timeframes (1m, 1H, 4H, D, W)
- Verify all settings combinations work

## Code Style Guidelines

### Pine Script v6 Syntax

```pinescript
//@version=6
indicator("Title", shorttitle="SHORT", overlay=false)
```

### Variable Naming

| Type | Convention | Example |
|------|------------|---------|
| Constants | SCREAMING_SNAKE | `MAX_BARS_BACK = 4500` |
| Variables | snake_case | `rsi_zscore`, `lookback_min` |
| Parameters | snake_case | `rsi_length`, `rsi_source` |
| Functions | f_prefix_snake | `f_zscore_to_percentile()` |
| User Types | PascalCase | `SignalStats`, `RankEntry` |
| Methods | camelCase | `this.get_winrate()` |

### Input Groups

Organize inputs with clear group headers using box-drawing characters:

```pinescript
grp_rsi = "--- RSI Settings / RSI设置 ---"
rsi_length = input.int(14, "RSI Length / RSI周期", group=grp_rsi)
```

### Bilingual Comments/Labels

This indicator serves English and Chinese users. Use bilingual format:

```pinescript
// English description / 中文说明
tooltip="Auto: Calculate automatically\nCustom: Use custom value / 自动/自定义"
```

### Section Headers

Use decorated section headers for major code blocks:

```pinescript
// ====================================================================
// SECTION NAME
// ====================================================================
```

### Type Declarations (UDT)

```pinescript
type SignalStats
    int count = 0
    float total_return = 0.0
    int wins = 0

method update(SignalStats this, bool triggered, float ret) =>
    if triggered
        this.count += 1
        // ...
```

### Conditional Logic

- Prefer ternary for simple assignments:
  ```pinescript
  color_status = zscore > 2 ? color_bear : zscore < -2 ? color_bull : color.gray
  ```
- Use if/else for complex logic with side effects

### Request.Security Calls

Minimize `request.security` calls - use tuple returns for efficiency:

```pinescript
[weekly_rsi, weekly_close, weekly_sma20, weekly_sma50] = request.security(
    syminfo.tickerid, "W",
    [ta.rsi(close, 14), close, ta.sma(close, 20), ta.sma(close, 50)],
    lookahead=barmerge.lookahead_off
)
```

### String Formatting

Use `str.format()` for cleaner string construction:

```pinescript
text = str.format("{0}: {1,number,#.##}%", label, value)
```

## Critical Patterns

### Signal Cooldown

Prevent duplicate signals using `varip` for bar-persistent state:

```pinescript
varip int last_buy_alert_bar = -1
varip int last_buy_alert_level = 0

// Check if new signal or upgrade
new_signal = bar_index != last_buy_alert_bar or current_level > last_buy_alert_level
```

### Health Indicators

Always validate data quality before generating signals:
- Sample coverage: `bar_index >= lookback * 0.8`
- Distribution spread: `rsi_p95 - rsi_p5 >= 15`
- Statistical validity: `lookback >= stat_required * 0.9`

### Signal Priority System

Higher priority signals override lower ones:
1. MTF Resonance (4)
2. Divergence + Extreme (3)
3. Extreme (2)
4. Normal (1)

## Common Gotchas

### Lookback Limits

- Maximum array size / lookback: ~4500 bars
- Use `max_bars_back=4500` in indicator declaration if needed

### Lookahead Bias

Always use `lookahead=barmerge.lookahead_off` in `request.security()` to prevent future data leakage.

### Timeframe Detection

```pinescript
tf_minutes = timeframe.in_seconds(timeframe.period) / 60
bars_per_day = timeframe.isdaily ? 1 : math.ceil(1440 / tf_minutes)
```

### Plot Limits

TradingView limits plots per indicator. Use tables for dashboards instead of multiple plots.

### varip vs var

- `var`: persists across bars, recalculates on each tick of current bar
- `varip`: persists across bars AND ticks (truly persistent within bar)

## File Structure

```
/workspace
--- adaptive_rsi.pine    # Main indicator source (ONLY source file)
--- README.md            # Comprehensive documentation
--- LICENSE              # MIT License
--- images/              # Chart screenshots for documentation
--- .gitignore          # Standard ignores
```

## Making Changes

1. **Read the full file first** - It's a single 2500-line file, understand the structure
2. **Understand the signal flow**:
   - RSI Calculation -> Z-Score -> Percentile conversion
   - Multi-timeframe data fetch
   - Signal detection (extreme, divergence, MTF resonance)
   - Quality grading (A/B/C/D based on multiple factors)
   - Statistics tracking
   - Dashboard rendering
3. **Test thoroughly** - Changes can have cascading effects
4. **Maintain bilingual support** - All user-facing strings need EN/CN

## Version Changelog Pattern

When making updates, follow the changelog format in README.md:

```markdown
### vX.Y - Feature Name / Chinese Name
- **New Feature / 新功能**: Description / 描述
- **Fix / 修复**: Description / 描述
```

## Dashboard Structure

The indicator uses a table-based dashboard with these rows:
1. Title + RSI value
2. Z-Score + approximate percentile
3. Percentile range + Z-Score range
4. Status + Quality grade
5. Protection status + Volume
6. Lookback + Health indicators
7. MTF timeframes + status (Full mode)
8. Resonance status (Full mode)
9. Divergence status (Full mode)
10-18. Statistics ranking (Full mode)

## Testing Checklist

Before finalizing changes:
- [ ] Compiles without errors in TradingView
- [ ] No runtime errors on chart load
- [ ] Works on all timeframes (1m to Monthly)
- [ ] Works on different asset types (stocks, crypto, forex)
- [ ] All dashboard modes render correctly (Mobile/Lite/Full)
- [ ] Alerts trigger correctly with proper message format
- [ ] Statistics update correctly
- [ ] Performance is acceptable (no lag)

## External Resources

- [Pine Script v6 Reference](https://www.tradingview.com/pine-script-reference/v6/)
- [Pine Script User Manual](https://www.tradingview.com/pine-script-docs/en/v6/)
