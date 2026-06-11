# AGENTS.md - Adaptive RSI Pro

> Guidelines for AI agents working on this TradingView Pine Script v6 project.

**Generated**: 2026-06-10 | **Version**: v7.5 | **Branch**: main

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
- v7.5 added a **payoff-edge path** to the stats gate (revert switch:
  `Payoff Gate = Off` restores the exact v7.4 gate expression):
  - **Shrunk payoff edge**: `SignalStats.get_shrunk_payoff_edge_vs(baseline_avg)`
    returns `confidence × (bucket avg forward return − direction baseline avg)`
    with the same `confidence = min(1, effective/20)` and the same
    `lifetime_count < 5 → na` rule as `get_adjusted_winrate_vs`. Helpers:
    `f_stats_baseline_avg(_is_buy)` (unconditional drift baseline per
    direction) and `f_stats_payoff_edge(_stats, _is_buy)`.
  - **New inputs** (grp_stats, between Gate Mode and Filter Mode):
    `stats_payoff_mode` — `"Payoff Gate"`, options
    `Off | Either Edge | Both Edges`, default `Either Edge` (a deliberate
    behavior change vs v7.4) — and `stats_min_payoff_edge` —
    `"Min Payoff Edge %"`, default `0.4`, range 0–10, step 0.1.
  - **Gate wiring** (`f_passes_stats_filter`): the payoff path is active only
    when `stats_gate_mode == "Edge vs Baseline"` and `Payoff Gate != Off`;
    `Either Edge` ORs the win-rate and payoff paths, `Both Edges` ANDs them.
    Payoff is an alternative quality criterion, never an alternative to
    sample sufficiency: the `Min Samples` lifetime-count check gates the
    quality paths in **all** modes (as released in v7.5 an insufficient
    bucket always failed; post-v7.5 the `Unproven Buckets` policy decides
    that case — see below). Legacy gate mode forces the payoff path off.
  - **Display** (Edge gate mode only): the `Ranking` second line is
    `(+8.6pp|+2.3%)` (win-rate edge pp | shrunk payoff edge %; sort key is
    still the win-rate edge); a per-direction "No timing edge" regime-hint
    row (`f_stats_no_timing_edge`) renders after the stats header when ≥ 2
    has-data buckets (effective count ≥ 5) in that direction all have
    negative win-rate edge and non-positive payoff edge; `full_rows` gains
    `+2` in Edge gate mode (indicator table capacity 23, harness 27).
- Post-v7.5 dashboard addition (display only): a **`Gate` row** renders after
  `Status` whenever `enable_stats and enable_stats_filter`, showing the bucket
  the stats gate consults for the current (prospective) signal and the verdict
  — the explanation for the Signal row's `✓`/`⚠️`. `f_gate_signal_kind()`
  mirrors the `signal_type_text` priority (pure divergence → not gateable);
  bucket choice and the overall verdict reuse the production `*_stats` /
  `filter_*` outputs so the row cannot drift from `f_passes_stats_filter`.
  Insufficient lifetime samples render `n=x/y⏳` plus the `Unproven Buckets`
  verdict (`⏳✓` green / `⏳✗` gray); otherwise each quality path shows
  `actual→required` plus `✓`/`✗` (payoff segment only when the payoff path
  is active). `full_rows` gains `+1` when the stats filter is
  on; the row flows into the harness, where it coexists with the
  harness-owned `Production Gate` row (per-bar prospective vs trigger-only).
- Post-v7.5 gate change — **unproven-bucket pass-through** (revert switch:
  `Unproven Buckets = Block (Legacy)` restores the pre-change gate exactly):
  - New input `stats_unproven_mode` — `"Unproven Buckets"`, options
    `Pass | Block (Legacy)`, default `Pass` (a deliberate behavior change) —
    sits between `Min Samples` and `Min Adjusted WinRate` in grp_stats.
  - `f_passes_stats_filter` final expression became
    `_has_enough_samples ? _quality_ok : stats_unproven_mode == "Pass"`:
    with sufficient lifetime samples the quality paths decide as before; below
    `Min Samples` the policy decides (Pass = let through, Block = legacy), so
    `⚠️` now always means "proven bad", never "no data".
  - Three-state marks: `signal_mark_text` and the alert `alert_filter_status`
    render `⏳` when the bucket lacks samples (via
    `current_signal_insufficient` / `f_stats_insufficient`, same
    lifetime-count basis as the gate), `✓`/`⚠️` only with sufficient samples.
    The Gate row's insufficient branch shows `n=x/y⏳✓` (green, passed under
    Pass) or `⏳✗` (gray, blocked under Block), reusing the production
    `gate_pass`. The harness `Production Gate` count gains a `⏳` suffix below
    `Min Samples` (harness-owned snippet in the generator).
  - Full v7.4-gate revert = `Payoff Gate = Off` **and**
    `Unproven Buckets = Block (Legacy)` (both READMEs' revert notes updated).
- Post-v7.5 display fix: `get_reliability()` and the bucket-row sample counts
  (Signal Type / Grade / Ranking rows, plus the harness `Production Gate`
  snapshot count in `f_harness_gate_snapshot()`) now use the undecayed
  `lifetime_count` — `✓ ≥ stats_min_samples`, `⏳ ≥ 5`, `❌ < 5` — the same
  basis as the `Min Samples` gate and the Gate row's `n=`. The middle tier is
  `⏳` (unproven), keeping `⚠️` exclusively for "proven bad" panel-wide. The
  decayed effective count is hard-capped at `1/(1-0.5^(spacing/half_life))`
  (≈ 20 only when a bucket samples at least every ~111 bars at the default
  1500-bar half-life), so keying the mark on it left every sparse bucket
  permanently below `✓`. Ranking's has-data visibility cut (effective ≥ 5) is
  unchanged.
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
- The harness-owned `f_harness_gate_snapshot()` returns a 5-tuple (source,
  count, avg, adjusted win rate, payoff edge); the `Production Gate` row
  appends `|+x.x%` (shrunk payoff edge) in Edge gate mode only. This snippet
  lives in `tools/generate_strategy_harness.py` — edit it there, never in the
  generated file.
- It is a gated-signal backtest, not an exact intrabar `alert()` delivery
  simulation.
- User-facing harness documentation lives in `README.md` § "Backtesting with
  the Strategy Harness" and `docs/README_CN.md` § "用策略报告版回测" (there are
  no separate strategy-report doc files).

## Where to Look

| Task | Location | Notes |
|------|----------|-------|
| Input groups | `adaptive_rsi.pine:17-89` | All production inputs incl. stats/gate/payoff/alert toggles |
| Dynamic lookback | `adaptive_rsi.pine:123-181` | Adaptive sample-depth logic |
| Spread hysteresis | `adaptive_rsi.pine:163-195` | Boost state machine + `prev_spread` feedback update |
| Weekly protection | `adaptive_rsi.pine:237-266` | Confirmed weekly trend filter |
| MTF analysis | `adaptive_rsi.pine:279-410` | TF selection, lower-TF aggregation, availability flags (333-388) |
| Statistics types | `adaptive_rsi.pine:411-591` | `SignalStats` with decay, indexed + baseline buckets, adjusted win rate, shrunk payoff edge, `f_stats_required_winrate` clamp, `f_stats_no_timing_edge` |
| Signal detection | `adaptive_rsi.pine:758-794` | Raw signals and cooldown state |
| Consolidated signals | `adaptive_rsi.pine:796-891` | Priority merge, upgrade exemption with expired-level reset |
| Statistics engine | `adaptive_rsi.pine:1006-1052` | Forward-return bookkeeping, baseline sampling, independent sampling |
| Stats filter | `adaptive_rsi.pine:1053-1217` | Edge-vs-baseline / legacy gate, payoff-edge path, stats-mode-aware buckets, hidden-state detection |
| Dashboard | `adaptive_rsi.pine:1303-1603` | Main indicator UI incl. Gate row (helpers 1314-1329, render 1420-1455), MTF availability warning, `Base→Req` header, regime-hint rows, edge-sorted ranking with payoff column |
| Alerts | `adaptive_rsi.pine:1604-1690` | Smart alert aggregation, per-bar level reset, `alert_on_close` gating |
| Harness inputs | `adaptive_rsi_strategy_harness.pine:85-89` | `Trade Side`, `Backtest Mode`, risk-exit inputs |
| Harness risk direction | `adaptive_rsi_strategy_harness.pine:101-107` | `strategy.risk.allow_entry_in` wiring |
| Harness dashboard rows | `adaptive_rsi_strategy_harness.pine:1522-1544` | `Harness`, `Tester`, `Production Gate` (payoff suffix in Edge mode) |
| Harness strategy logic | `adaptive_rsi_strategy_harness.pine:1779-1844` | Entry/close rules, entry-bound ATR SL/TP exits, exact-N time exit |
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
   v7.2-freeze applied to v7.3 and was lifted by the user for v7.4/v7.5,
   which deliberately upgraded the stats engine (time decay, independent
   sampling, edge-vs-baseline gate, payoff-edge path, unproven-bucket
   pass-through). Further signal-model or stats-engine changes still need an
   explicit user request, and the legacy revert switches
   (`stats_half_life_bars = 0`, `Independent Samples` off,
   `Absolute (Legacy)` gate, `Payoff Gate = Off` plus
   `Unproven Buckets = Block (Legacy)` for the v7.4 gate) must keep restoring
   the old behavior.
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
