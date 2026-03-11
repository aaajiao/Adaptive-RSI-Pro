# AGENTS.md - Adaptive RSI Pro

> Guidelines for AI agents working on this TradingView Pine Script v6 indicator.

**Generated**: 2026-03-11 | **Version**: v7.2 | **Branch**: main

## Quick Reference

| Item | Value |
|------|-------|
| **Language** | Pine Script v6 |
| **Main File** | `adaptive_rsi.pine` (1734 lines) |
| **Platform** | TradingView (tradingview.com) |
| **Indicator** | `Adaptive RSI Pro` / `ARSI Pro` |
| **Validation** | Local lint + manual TradingView compile/runtime check |

## Project Structure

```text
RSI_stock/
├── adaptive_rsi.pine           # All Pine logic lives here (single-file requirement)
├── README.md                   # User docs + changelog (bilingual EN/CN)
├── AGENTS.md                   # This file
├── LICENSE                     # MIT
├── .pine-lint.yml              # Pine linter config
├── .github/
│   └── workflows/
│       └── pine-lint.yml       # GitHub Actions lint workflow
├── tools/
│   └── pine_linter/            # Custom Pine Script static analyzer
│       ├── cli.py
│       ├── config.py
│       ├── linter.py
│       ├── reporter.py
│       └── rules.py
└── images/
    └── annotated_rsi_indicator.png
```

## Current Architecture

```text
INPUTS
  -> RSI + LOOKBACK + PERCENTILES + Z-SCORE
  -> TREND PROTECTION + VOLUME + MTF + DIVERGENCE
  -> SIGNAL DETECTION + COOLDOWN + PRIORITY CONSOLIDATION
  -> QUALITY SCORING + ATR RISK + STATS
  -> STATS FILTER + HIDDEN STATE + DISPLAY
  -> DASHBOARD + SMART ALERT
```

### Current version focus
- **v7.2** adds tiered signal cooldown with upgrade exemption.
- High-priority signals (`MTF`, `DIV`, `EXT`) use 1-bar cooldown.
- Normal signals use adaptive/fixed cooldown bars.
- Signal escalation on the same side can bypass cooldown (`Normal -> Extreme`, `Extreme -> MTF`, etc.).

## Where to Look

| Task | Location | Notes |
|------|----------|-------|
| Input groups | Lines 15-102 | 9 groups, 50+ inputs, all EN/CN user text lives here |
| Dynamic lookback | Lines 111-162 | Auto/custom lookback, health metrics, spread feedback |
| Percentiles + Z-score | Lines 165-217 | Percentile bands and helper conversion functions |
| Trend protection | Lines 220-243 | Weekly RSI/SMA filter and Smart normal-signal gating |
| MTF analysis | Lines 258-367 | Auto/manual timeframe selection and `request.security()` calls |
| Statistics type | Lines 370-456 | `SignalStats` type and methods |
| Divergence | Lines 459-549 | Single-anchor divergence + realtime divergence |
| Signal detection | Lines 591-609 | Raw extreme/normal trigger conditions |
| Cooldown + consolidation | Lines 612-704 | v7.2 cooldown tiers, upgrade exemption, final signal priority |
| Quality scoring | Lines 707-779 | `f_buy_quality()`, `f_sell_quality()`, grade mapping |
| ATR risk hints | Lines 782-817 | Alert stop-loss/take-profit calculation |
| Statistics engine | Lines 820-1040 | Forward-return bookkeeping and stats-driven filter |
| Hidden/display state | Lines 1043-1158 | Hidden reasons, soft degrade, shared signal/status text |
| Dashboard UI | Lines 1161-1647 | Mobile/Full table rendering, stats views, ranking table |
| Smart alerts | Lines 1650-1734 | Aggregated alert messages and dedupe gating |

## Build & Validation

Pine Script still compiles only on TradingView, but this repo now has a local static-analysis step.

### Local lint

```bash
python3 tools/pine_linter/cli.py --config .pine-lint.yml adaptive_rsi.pine
```

Optional formats:

```bash
python3 tools/pine_linter/cli.py --config .pine-lint.yml --format github adaptive_rsi.pine
python3 tools/pine_linter/cli.py --config .pine-lint.yml --format markdown --output lint-report.md adaptive_rsi.pine
```

### CI
- GitHub Actions runs `.github/workflows/pine-lint.yml`.
- CI installs `pyyaml` and runs the same linter.
- Lint `error` findings fail CI.
- `warning`/`info` still matter, but only `error` is blocking by default.

### TradingView validation steps
1. Copy full `adaptive_rsi.pine`.
2. TradingView -> Pine Editor -> paste -> `Add to chart`.
3. Check compile errors in editor.
4. Check runtime behavior on chart and alert preview.

### Manual test checklist
- [ ] Compiles without TradingView errors
- [ ] Works on 1m / 15m / 1H / 4H / D / W / M
- [ ] Works on stocks / crypto / forex / ETFs
- [ ] Mobile and Full dashboard render correctly
- [ ] Stats modes switch correctly: `Signal Type`, `Grade`, `Ranking`
- [ ] Smart normal-signal hiding behaves correctly under weekly extremes
- [ ] Hard/Soft/Alert Only stats filter modes behave correctly
- [ ] Cooldown upgrade exemption works on rapid deterioration/reversal bars
- [ ] Alerts fire once per bar with correct message text and optional risk hints
- [ ] No obvious performance degradation from table or ranking logic

## Code Style

### Naming conventions

| Type | Convention | Example |
|------|------------|---------|
| Constants | `SCREAMING_SNAKE` | `MAX_BARS_BACK` |
| Variables | `snake_case` | `rsi_zscore`, `lookback_min` |
| Functions | `f_prefix_snake` | `f_zscore_to_percentile()` |
| User types | `PascalCase` | `SignalStats` |
| Methods | `camelCase` | `this.get_winrate()` |
| Input groups | `grp_prefix` | `grp_rsi`, `grp_alerts` |

### File header

```pinescript
//@version=6
indicator("Adaptive RSI Pro", shorttitle="ARSI Pro", overlay=false, precision=2, max_lines_count=100, max_labels_count=100, max_bars_back=4500)
```

### Section structure

```pinescript
// ────────────────────────────────────────
// SECTION NAME
// ────────────────────────────────────────
```

### Input groups

```pinescript
grp_rsi = "═══ RSI Settings / RSI设置 ═══"
rsi_length = input.int(14, "RSI Length / RSI周期", group=grp_rsi,
    tooltip="English explanation\n中文说明")
```

### User-defined types

```pinescript
type SignalStats
    int count = 0
    float total_return = 0.0
    int wins = 0

method get_avg(SignalStats this) =>
    this.count > 0 ? this.total_return / this.count : 0.0
```

### Control-flow guidance
- Use ternary only for short single-line assignments.
- Use `switch` or helper booleans for longer multi-branch logic.
- Prefer explicit `string` / `bool` typing when Pine may infer poorly.

### String formatting

```pinescript
str.format("{0}: {1,number,#.##}%", label, value)
str.format("{0,number,+#.1;-#.1}%", return_value)
```

## Critical Patterns

### `request.security()` must disable lookahead

```pinescript
[weekly_rsi, weekly_close] = request.security(
    syminfo.tickerid, "W",
    [ta.rsi(close, 14), close],
    lookahead=barmerge.lookahead_off
)
```

### Current cooldown pattern

```pinescript
int pending_buy_level = raw_sig_buy_mtf ? 4 : raw_sig_buy_div ? 3 : raw_sig_buy_extreme ? 2 : raw_sig_buy_normal ? 1 : 0
bool buy_upgrade_exempt = pending_buy_level > last_buy_level

bool sig_buy_extreme = enable_signal_cooldown ?
    (raw_sig_buy_extreme and (buy_upgrade_exempt or na(last_ext_buy_bar) or bar_index - last_ext_buy_bar >= cooldown_ext)) :
    raw_sig_buy_extreme
```

### `table.clear()` requires a range

```pinescript
table.clear(dashboard, 0, 0, 1, 19)
```

### Weekly protection affects more than extremes
- It gates extreme buy/sell permission.
- It also controls Smart mode visibility for normal signals.
- Hidden signals still affect shared display state and alert logic in some paths, so follow the cascade before editing.

### Stats filter modes
- `Alert Only`: chart keeps signals, alerts are filtered.
- `Soft`: failed signals still render but degraded.
- `Hard`: failed signals can be fully hidden.

## Signal Model

### Priority order

| Priority | Signal | Condition |
|----------|--------|-----------|
| 4 | `🌟` MTF resonance | MTF alignment + extreme trigger |
| 3 | `💎` Divergence + extreme | Divergence in extreme zone |
| 2 | `🔥` / `❄️` Extreme | Z-score crosses `±2σ` |
| 1 | `⬆️` / `⬇️` Normal | Z-score crosses `±normal_threshold` |
| 0 | `↗️` / `↘️` Divergence only | Divergence outside extreme zone |

### Quality score factors
- Base: 50 points in extreme zone
- Bonuses: divergence/MTF, RSI pivot confirmation, weekly trend alignment, volume surge, deeper extremes
- Penalties: weekly extreme counter-trend, low volume, unhealthy sample/distribution, ADX strong-trend opposition

## Common Gotchas

| Issue | Guidance |
|------|----------|
| Future-data leak | Every `request.security()` must use `lookahead=barmerge.lookahead_off` |
| Pine multiline syntax | Avoid multi-line ternary chains and fragile boolean wraps |
| Table clearing | `table.clear()` needs start/end coordinates |
| Dashboard row drift | Keep row math aligned with `enable_mtf`, `enable_divergence`, `enable_stats`, and stats mode |
| Hidden vs displayed signal | A signal may exist logically but be hidden/degraded visually |
| Stats filter regressions | Alert behavior, plot behavior, and dashboard markers are not the same path |
| Cooldown regressions | Side-specific `last_*_bar` and `last_*_level` updates affect future exemption logic |
| Percentile confirm | Extreme checks may be dual-gated by Z-score and P5/P95 |
| `na` propagation | Guard MTF and percentile values before using them |

## Common Syntax Errors (Pine Script v6)

### 1. Multi-line expressions

```pinescript
// WRONG
status_text = rsi_zscore < -2 ? "EXTREME" :
              rsi_zscore < -1.5 ? "OVERSOLD" :
              "NEUTRAL"

// BETTER
string status_text = switch
    rsi_zscore < -2 => "EXTREME"
    rsi_zscore < -1.5 => "OVERSOLD"
    => "NEUTRAL"
```

### 2. `table.clear()` without coordinates

```pinescript
// WRONG
table.clear(dashboard)

// CORRECT
table.clear(dashboard, 0, 0, 1, 19)
```

### 3. Type inference around `switch`

```pinescript
// SAFER
string alert_buy_icon = switch
    alert_buy_mtf => "🌟MTF共振"
    alert_buy_div => "💎背离"
    => ""
```

### 4. Missing default case in `switch`

```pinescript
string result = switch
    condition1 => "A"
    condition2 => "B"
    => "default"
```

## Making Changes

1. Read the full `adaptive_rsi.pine` flow before editing. It is a single-file script with coupled behavior.
2. Preserve bilingual EN/CN user-facing text in inputs, dashboard labels, alerts, and docs.
3. Run local lint after edits. Treat lint `error` as blocking, and inspect new `warning`/`info`.
4. Re-check the full cascade when touching signals: detection -> cooldown -> stats -> hidden state -> display -> alerts.
5. Re-test both dashboard modes and at least one stats mode after UI or row-count changes.
6. If you touch `request.security()`, percentile logic, or alert gating, assume regressions are easy and verify manually.
7. Avoid multi-line ternary/boolean expressions when a helper variable or `switch` is clearer.

### README changelog format

```markdown
### vX.Y - Feature Name / 功能名称
- **New / 新功能**: Description / 描述
- **Improvement / 改进**: Description / 描述
- **Fix / 修复**: Description / 描述
```

## External Resources

- [Pine Script v6 Reference](https://www.tradingview.com/pine-script-reference/v6/)
- [Pine Script v6 Manual](https://www.tradingview.com/pine-script-docs/en/v6/)
- [TradingView Pine Editor](https://www.tradingview.com/chart/)
