# AGENTS.md - Adaptive RSI Pro

> Guidelines for AI agents working on this TradingView Pine Script v6 project.

**Generated**: 2026-03-11 | **Version**: v7.3 | **Branch**: main

## Quick Reference

| Item | Value |
|------|-------|
| **Language** | Pine Script v6 |
| **Production File** | `adaptive_rsi.pine` |
| **Strategy Report File** | `adaptive_rsi_strategy_harness.pine` |
| **Platform** | TradingView |
| **Indicator** | `Adaptive RSI Pro` / `ARSI Pro` |

## Project Structure

```text
RSI_stock/
├── adaptive_rsi.pine
├── adaptive_rsi_strategy_harness.pine
├── README.md
├── docs/
│   ├── README_CN.md
│   ├── STRATEGY_REPORT.md
│   └── STRATEGY_REPORT_CN.md
├── AGENTS.md
├── LICENSE
├── .pine-lint.yml
├── .github/workflows/pine-lint.yml
├── tools/generate_strategy_harness.py
├── tools/pine_linter/
└── images/
```

## Current Architecture

### Production indicator

- Public `v7.2` baseline behavior.
- Keeps adaptive thresholds, MTF resonance, divergence, stats filtering, and tiered cooldown.
- Only obvious correctness fixes are retained:
  - `lookback` floor uses the statistical lower bound
  - weekly protection uses confirmed HTF data
  - lower-timeframe MTF uses `request.security_lower_tf()`
- Stats filtering still uses the original adjusted-win-rate gate, but the active
  `Stats Mode` now selects whether the gate reads Signal Type, Grade, or Ranking
  buckets.

### Strategy report harness

- Generated `strategy()` wrapper using the same signal engine.
- Source of truth is `adaptive_rsi.pine`; regenerate the harness with
  `python3 tools/generate_strategy_harness.py` after production logic changes.
- Adds:
  - `Trade Side`
  - `Backtest Mode = Baseline | Production`
- `Baseline` trades raw `v7.2` signals.
- `Production` trades signals that pass the production alert gate/filter.
- It is a gated-signal backtest, not an exact intrabar `alert()` delivery simulation.

## Where to Look

| Task | Location | Notes |
|------|----------|-------|
| Input groups | `adaptive_rsi.pine:17-85` | Main production inputs |
| Dynamic lookback | `adaptive_rsi.pine:114-167` | Adaptive sample-depth logic |
| Weekly protection | `adaptive_rsi.pine:226-248` | Confirmed weekly trend filter |
| MTF analysis | `adaptive_rsi.pine:260-385` | Auto/manual TF selection and lower-TF aggregation |
| Statistics type | `adaptive_rsi.pine:386-501` | `SignalStats`, indexed buckets, adjusted win rate |
| Signal detection | `adaptive_rsi.pine:637-684` | Raw signals and cooldown inputs |
| Statistics engine | `adaptive_rsi.pine:866-905` | Forward-return bookkeeping |
| Stats filter | `adaptive_rsi.pine:908-1124` | Stats-mode-aware adjusted win-rate gate |
| Dashboard | `adaptive_rsi.pine:1127-1331` | Main indicator UI |
| Alerts | `adaptive_rsi.pine:1334-1417` | Smart alert aggregation |
| Harness inputs | `adaptive_rsi_strategy_harness.pine:67-79` | `Trade Side` and `Backtest Mode` |
| Harness dashboard rows | `adaptive_rsi_strategy_harness.pine:1279-1295` | `Harness`, `Tester`, `Production Gate` |
| Harness strategy logic | `adaptive_rsi_strategy_harness.pine:1499-1522` | Entry/close rules |

## Build & Validation

### Local lint

```bash
python3 tools/generate_strategy_harness.py --check
python3 tools/pine_linter/cli.py --config .pine-lint.yml adaptive_rsi.pine
python3 tools/pine_linter/cli.py --config .pine-lint.yml adaptive_rsi_strategy_harness.pine
```

### TradingView validation

1. Paste [adaptive_rsi.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi.pine) into Pine Editor and add to chart.
2. Paste [adaptive_rsi_strategy_harness.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi_strategy_harness.pine) separately if strategy validation is needed.
3. Check compile/runtime behavior on at least:
   - `GOOGL 1D`
   - `AAPL 1D`
   - `BTCUSDT 4H`

## Critical Patterns

### Confirmed weekly data

```pinescript
[weekly_rsi, weekly_sma20, weekly_sma50] = request.security(
    syminfo.tickerid, "W",
    [ta.rsi(close, 14)[1], ta.sma(close, 20)[1], ta.sma(close, 50)[1]],
    lookahead=barmerge.lookahead_on,
    calc_bars_count=WEEKLY_REQUEST_BARS
)
```

### Lower-timeframe aggregation

```pinescript
array<int> statuses = request.security_lower_tf(
    syminfo.tickerid,
    _tf,
    f_mtf_status_expr(lookback),
    ignore_invalid_timeframe=true,
    calc_bars_count=MAX_REQUEST_BARS
)
```

### Strategy harness interpretation

- `All` is always present in TradingView Strategy Tester.
- Read it according to `Trade Side`.
- `Production Gate` shows the actual stats bucket selected by `Stats Mode` for the active signal.

## Making Changes

1. Treat [adaptive_rsi.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi.pine) as the primary product.
2. Do not hand-edit duplicated signal logic in [adaptive_rsi_strategy_harness.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi_strategy_harness.pine); regenerate it.
3. Keep the signal model close to public `v7.2` unless the user explicitly requests a new product direction.
4. Preserve bilingual EN/CN user-facing text where already present.
5. Run harness generation check and local lint after edits.
6. When touching MTF/HTF logic, verify manually on TradingView if possible.
7. Do not reintroduce later experimental concepts unless the user explicitly asks for them.
