# AGENTS.md - Adaptive RSI Pro

> Guidelines for AI agents working on this TradingView Pine Script v6 project.

**Generated**: 2026-06-10 | **Version**: v7.4 | **Branch**: main

## Quick Reference

| Item | Value |
|------|-------|
| **Language** | Pine Script v6 |
| **Production File** | `adaptive_rsi.pine` |
| **Strategy Report File** | `adaptive_rsi_strategy_harness.pine` (generated) |
| **Platform** | TradingView |
| **Indicator** | `Adaptive RSI Pro` / `ARSI Pro` |
| **Docs** | `README.md` (English, canonical) + `docs/README_CN.md` (Chinese localization) |
| **Tooling Tests** | `tests/` (stdlib `unittest`, Python 3) |

## Project Structure

```text
RSI_stock/
├── adaptive_rsi.pine
├── adaptive_rsi_strategy_harness.pine
├── README.md
├── docs/
│   └── README_CN.md
├── AGENTS.md
├── LICENSE
├── .pine-lint.yml
├── .github/workflows/pine-lint.yml
├── tools/generate_strategy_harness.py
├── tools/pine_linter/
├── tests/
│   ├── test_generate_strategy_harness.py
│   └── test_pine_linter.py
└── images/
```

## Current Architecture

### Production indicator

- `v7.2` baseline signal model (adaptive thresholds, MTF resonance, divergence,
  tiered cooldown) plus the v7.3 correctness fixes:
  - `lookback` floor uses the statistical lower bound
  - weekly protection uses confirmed HTF data
  - lower-timeframe MTF uses `request.security_lower_tf()`
- v7.4 deliberately upgraded the **stats engine** (each upgrade keeps a legacy
  revert switch):
  - **Time decay**: `SignalStats` sample weights decay exponentially with
    half-life `stats_half_life_bars` (`0` = legacy equal-weight accumulation).
    Decay only affects win-rate confidence; sample-sufficiency checks (the
    `Min Samples` gate and the adjusted-winrate floor) use the undecayed
    `lifetime_count`, because the decayed effective count is capped at
    `1/(1-0.5^(spacing/half_life))` and would permanently lock out rare
    signal buckets.
  - **Independent sampling**: `stats_independent_samples` makes each bucket
    wait at least `Forward Bars` between recorded samples so overlapping
    forward-return windows don't inflate counts (off = legacy overlap).
  - **Edge-vs-baseline gate**: `stats_gate_mode = "Edge vs Baseline"` (default)
    records per-direction unconditional baseline buckets; the Bayesian prior
    shrinks toward the direction baseline and the required win rate becomes
    `baseline + (Min Adjusted WinRate − 50)`, clamped to `[25%, 90%]`
    (`f_stats_required_winrate`) so extreme baselines can't make the gate
    unsatisfiable or trivially low. The dashboard stats header surfaces the
    effective requirement per direction as `Base→Req`, and in this mode the
    `Ranking` leaderboard sorts by edge over each bucket's own direction
    baseline (gate-consistent) and appends the edge in `pp`; buckets with
    fewer than 5 effective samples are hidden via an explicit has-data flag,
    while negative-edge buckets stay visible and naturally rank last.
    `"Absolute (Legacy)"` restores the old fixed-threshold/50% prior behavior
    and the original sort by adjusted win rate.
- Other v7.4 behavior changes:
  - **`alert_on_close`**: optional input — alerts fire only on confirmed bars
    (anti-repaint) at the cost of delivery delay; off = legacy intrabar alerts.
  - **MTF availability surfacing**: `f_mtf_status()` returns
    `[status, available]`; unavailable TF data renders `–` plus a dashboard
    warning. Display-only — resonance math and stats recording are unchanged.
  - **Spread hysteresis**: the lookback spread-boost factor uses a hysteresis
    band on the previous bar's `P95−P5` spread (engage 1.3 below 18, release
    above 22) to stop flip-flopping near the threshold.
  - **Upgrade-level reset**: the cooldown upgrade exemption only compares
    against a still-cooling previous signal (expired levels count as 0). (The
    per-bar `barstate.isnew` reset of the `varip` alert level-sent trackers
    already existed in v7.3 and is not a v7.4 change.)
- `Stats Mode` still selects whether the gate reads Signal Type, Grade, or
  Ranking buckets.

### Strategy report harness

- Generated `strategy()` wrapper using the same signal engine.
- Source of truth is `adaptive_rsi.pine`; regenerate with
  `python3 tools/generate_strategy_harness.py` after production logic changes.
- The generator is **anchor-based**: `adaptive_rsi.pine` carries
  `// @harness: <name>` comment lines (`inputs`, `risk-direction`,
  `stats-helpers`, `gate-helper`, `dashboard-rows`) marking where harness-only
  code is inserted. Each anchor must appear exactly once and must be preserved
  verbatim — the generator no longer matches long verbatim copies of
  production code; the only production text it keys on is the header line, the
  `indicator(...)` declaration, and four narrowly-regexed dashboard sizing
  lines.
- Harness-only inputs:
  - `Trade Side`
  - `Backtest Mode = Baseline | Production`
  - Risk exits: `Use ATR SL/TP Exits` (SL/TP snapshotted at the signal bar's
    close; `strategy.exit` is issued with the entry and bound via
    `from_entry`, so the bracket protects from the entry fill bar) and
    `Max Holding Bars` (time exit realizing exactly N held bars — close order
    placed at the close of held bar N−1, fills at the next open; `0` = off)
- `Baseline` trades raw `v7.2` signals; `Production` trades signals that pass
  the production alert gate/filter.
- It is a gated-signal backtest, not an exact intrabar `alert()` delivery
  simulation.
- User-facing harness documentation lives in `README.md` § "Backtesting with
  the Strategy Harness" and `docs/README_CN.md` § "用策略报告版回测" (there are
  no separate strategy-report doc files).

## Where to Look

| Task | Location | Notes |
|------|----------|-------|
| Input groups | `adaptive_rsi.pine:17-86` | All production inputs incl. v7.4 stats/gate/alert toggles |
| Dynamic lookback | `adaptive_rsi.pine:120-178` | Adaptive sample-depth logic |
| Spread hysteresis | `adaptive_rsi.pine:160-192` | Boost state machine + `prev_spread` feedback update |
| Weekly protection | `adaptive_rsi.pine:234-263` | Confirmed weekly trend filter |
| MTF analysis | `adaptive_rsi.pine:276-407` | TF selection, lower-TF aggregation, availability flags (330-385) |
| Statistics types | `adaptive_rsi.pine:408-565` | `SignalStats` with decay, indexed + baseline buckets, adjusted win rate, `f_stats_required_winrate` clamp |
| Signal detection | `adaptive_rsi.pine:710-746` | Raw signals and cooldown state |
| Consolidated signals | `adaptive_rsi.pine:748-843` | Priority merge, upgrade exemption with expired-level reset |
| Statistics engine | `adaptive_rsi.pine:958-1004` | Forward-return bookkeeping, baseline sampling, independent sampling |
| Stats filter | `adaptive_rsi.pine:1006-1144` | Edge-vs-baseline / legacy gate, stats-mode-aware buckets, hidden-state detection |
| Dashboard | `adaptive_rsi.pine:1230-1458` | Main indicator UI incl. MTF availability warning, `Base→Req` header, edge-sorted ranking |
| Alerts | `adaptive_rsi.pine:1460-1543` | Smart alert aggregation, per-bar level reset, `alert_on_close` gating |
| Harness inputs | `adaptive_rsi_strategy_harness.pine:80-86` | `Trade Side`, `Backtest Mode`, risk-exit inputs |
| Harness risk direction | `adaptive_rsi_strategy_harness.pine:98-103` | `strategy.risk.allow_entry_in` wiring |
| Harness dashboard rows | `adaptive_rsi_strategy_harness.pine:1387-1405` | `Harness`, `Tester`, `Production Gate` |
| Harness strategy logic | `adaptive_rsi_strategy_harness.pine:1630-1691` | Entry/close rules, entry-bound ATR SL/TP exits, exact-N time exit |
| Generator anchors | `tools/generate_strategy_harness.py` | Anchor names, harness-owned snippets, `--check` mode |
| Tooling tests | `tests/` | Generator golden/anchor tests, linter rule tests |

## Build & Validation

### Local lint & tests

```bash
python3 tools/generate_strategy_harness.py --check
python3 tools/pine_linter/cli.py --config .pine-lint.yml adaptive_rsi.pine
python3 tools/pine_linter/cli.py --config .pine-lint.yml adaptive_rsi_strategy_harness.pine
python3 -m unittest discover -s tests -v
```

CI (`.github/workflows/pine-lint.yml`) runs the same harness check, the
unittest suite, and the linter on every push/PR that touches `.pine` files,
the lint config, `tools/`, or `tests/`.

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

### Harness anchors

```pinescript
// @harness: stats-helpers
```

Anchor comments in `adaptive_rsi.pine` are load-bearing generator markers.
They flow through into the generated harness unchanged and must each appear
exactly once.

### Strategy harness interpretation

- `All` is always present in TradingView Strategy Tester.
- Read it according to `Trade Side`.
- `Production Gate` shows the actual stats bucket selected by `Stats Mode` for the active signal.
- With `Use ATR SL/TP Exits` off and `Max Holding Bars = 0`, trades exit only
  on opposite signals (legacy harness behavior).

## Making Changes

1. Treat [adaptive_rsi.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi.pine) as the primary product.
2. Do not hand-edit duplicated signal logic in [adaptive_rsi_strategy_harness.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi_strategy_harness.pine); regenerate it.
3. Keep the raw signal model at the public `v7.2` baseline. The strict
   v7.2-freeze applied to v7.3 and was lifted by the user for v7.4, which
   deliberately upgraded the stats engine (time decay, independent sampling,
   edge-vs-baseline gate). Further signal-model or stats-engine changes still
   need an explicit user request, and the legacy revert switches
   (`stats_half_life_bars = 0`, `Independent Samples` off,
   `Absolute (Legacy)` gate) must keep restoring the old behavior.
4. Never delete or reword `// @harness: <name>` anchor comments in
   `adaptive_rsi.pine` without updating `tools/generate_strategy_harness.py`
   and `tests/test_generate_strategy_harness.py` to match; each anchor must
   appear exactly once. If `--check` fails because an anchor/marker broke, fix
   the generator — never patch the harness by hand.
5. Preserve bilingual EN/CN user-facing text where already present.
6. **Docs workflow**: the doc system is exactly two files — `README.md`
   (English, canonical) and `docs/README_CN.md` (Chinese localization with
   section parity). Doc edits land in English first, then are localized into
   the CN file. Do not recreate per-topic doc files (the old
   `docs/STRATEGY_REPORT*.md` were deleted; their content was absorbed into
   the harness/backtesting sections of the two READMEs).
7. Run harness generation check, unittest suite, and local lint after edits.
8. When touching MTF/HTF logic, verify manually on TradingView if possible.
9. Do not reintroduce later experimental concepts unless the user explicitly asks for them.
