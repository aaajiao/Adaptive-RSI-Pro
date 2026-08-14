# AGENTS.md - Adaptive RSI Pro

> Guidelines for AI agents working on this TradingView Pine Script v6 project.

**Generated**: 2026-08-14 | **Version**: v7.5 | **Branch**: main

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
    unsatisfiable or trivially low. The dashboard stats header surfaces each
    direction as `BUY/SELL WR baseline→minimum`, and in this mode
    the `Ranking` leaderboard sorts by win-rate edge over each bucket's own
    direction baseline and labels that fact as `WR-EDGE RANK`; buckets with
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
  - **Display**: Signal Type, setup-score, and Ranking rows all use the same
    action-first readout. A mature Edge/Either row is three short cell lines:
    `BLOCK · OR (0/2)`, `WR 56.00% · edge −0.10pp ✗`, and
    `Avg +6.1% · edge +0.10% ✗`. This retains absolute bucket performance while
    translating each baseline-relative gate path directly; `Δ` is avoided
    because some TradingView fonts render it like `A`. `f_stats_gate_paths()`
    is the shared, unrounded source for filter and display booleans, while
    `f_passes_stats_filter()` remains the final action. Ranking still sorts by
    win-rate edge. A single combined `Edge Summary` row
    renders when either direction has ≥ 2 buckets that both reached
    `Min Samples` and retain effective count ≥ 5, and every qualifying bucket
    has negative win-rate edge plus non-positive payoff edge. It reports
    `no supported edge` for loaded history and does not infer a market regime.
    `full_rows` gains `+1` in Edge mode (indicator capacity 20, harness 24).
- Post-v7.5 dashboard addition (display only): a **`Stats Filter`** row
  renders after `RSI Zone` only when there is a selected current event,
  including a pure-divergence display event. It shows the
  bucket the stats gate consults and the verdict — the explanation for the
  Signal row's `✓`/`✗`/`⏳`. `f_gate_signal_kind()`
  mirrors the `signal_type_text` priority (pure divergence → not gateable);
  bucket choice and the overall verdict reuse the production `*_stats` /
  `filter_*` outputs so the row cannot drift from `f_passes_stats_filter`.
  Insufficient lifetime samples render `n=x/y⏳` plus explicit
  `ALLOW|BLOCK · UNPROVEN` (yellow/gray, never green); mature buckets show an
  explicit `PASS|BLOCK · OR|AND (k/2)`, `WR actual≥/<minimum`, and optional
  `Avg edge actual≥/<minimum` payoff path. The bucket/sample label is in the
  left cell and the three short verdict lines are in the right cell. Bars
  without an event omit
  the row instead of guessing a future type from a persistent zone;
  pure divergence says `DISPLAY ONLY / No stats bucket / Not an alert signal`.
  The row flows into the
  harness, where it coexists with the harness-owned `Strategy Stats` snapshot.
- Post-v7.5 gate change — **unproven-bucket pass-through** (revert switch:
  `Unproven Buckets = Block (Legacy)` restores the pre-change gate exactly):
  - New input `stats_unproven_mode` — `"Unproven Buckets"`, options
    `Pass | Block (Legacy)`, default `Pass` (a deliberate behavior change) —
    sits between `Min Samples` and `Min Adjusted WinRate` in grp_stats.
  - `f_passes_stats_filter` final expression became
    `_has_enough_samples ? _quality_ok : stats_unproven_mode == "Pass"`:
    with sufficient lifetime samples the quality paths decide as before; below
    `Min Samples` the policy decides (Pass = let through, Block = legacy).
  - Three-state marks: the selected dashboard event and each alert direction
    render `⏳` when their own bucket lacks samples (via
    `f_stats_insufficient`, on the same lifetime-count basis as the gate), and
    `✓`/`✗` only for mature-bucket verdicts. `⚠️` is reserved for general
    data/runtime warnings. Hidden signals spell out `TREND`, `STATS`, `SMART`,
    or `OFF` after `🚫`.
  - Full v7.4-gate revert = `Payoff Gate = Off` **and**
    `Unproven Buckets = Block (Legacy)` (both READMEs' revert notes updated).
- Post-v7.5 display fix: bucket rows and the harness `Strategy Stats` readout
  show undecayed lifetime sample progress directly: `n=x` when mature or
  `n=x/y⏳` below `Min Samples`; sample maturity never uses a quality
  checkmark. A mature bucket whose decayed effective weight fell below 5 is
  labeled `stale`; the right cell still reports the production decision from
  the strongly shrunk estimates and does not repeat `stale`. The
  decayed effective count is hard-capped at `1/(1-0.5^(spacing/half_life))`
  (≈ 20 only when a bucket samples at least every ~111 bars at the default
  1500-bar half-life), so effective count is not used as the `Min Samples`
  maturity basis. Ranking's visibility cut (effective ≥ 5) is unchanged.
- Post-v7.5 dashboard semantics pass (display only):
  - `Signal` is current-bar events only; ongoing zones live solely in
    `RSI Zone`, and no event displays `—` instead of a duplicate neutral dot.
    One strength-prioritized event is selected first; its direction then drives
    the grade, hidden reason, stats bucket, verdict, and color, so opposite
    candidates on the same bar cannot produce a mixed-direction explanation.
  - Z-Score and historical rank are one `RSI Position` row; empirical rank is
    an honest interval such as `P50–P75`, never an exact percentile claim;
    unavailable quantiles say `NA · need history` instead of defaulting to
    `>P95`.
  - MTF states and resonance share one row, with explicit
    `Oversold/Neutral/Overbought` labels and a plain-language resonance result.
  - Weekly trend protection and volume scoring are explicitly separated
    inside `Market Context`; adaptive-window health uses words instead of
    three unlabeled icons; normal thresholds display symmetrically as `±σ`.
  - Full-mode cells use semantic `\n` breaks (generally two or three lines)
    for position, signal, filter, context, lookback, normal state, MTF,
    divergence, stats header, and bucket readouts. These do not consume
    additional table rows. Setup grade is labeled `[Score A]`; it describes
    current pattern score, not historical edge, a gate verdict, or permission
    to trade.
  - Ranking direction stays in the left label; mature historical readout
    cells are neutral white so an OR-pass cannot paint its failed `✗` path
    green. Filter-off cells are gray and stale cells yellow.
- Post-v7.5 signal-model fix (user-approved deviation from the v7.2 baseline,
  no revert switch — it is a correctness fix, like the v7.3 ones): the MTF
  `tf*_is_current` dedupe now compares `f_tf_seconds(active_tf*)` against
  `chart_tf_seconds` instead of display strings. On daily charts
  `timeframe.period` returns `"1D"` while the auto TF3 string is `"D"`, so
  the string compare never matched — the chart's own status was counted three
  times (weight 1 as current + weight 2 as TF3), the resonance denominator
  showed 4 instead of 3, and resonance triggered on "daily extreme + any one
  lower TF" instead of the intended all-three-agree rule. Daily-chart 🌟
  signals are now stricter/rarer; intraday round TFs (1h/4h) already matched
  and are unchanged. The unused `current_tf_display` was removed.
- `Stats Mode` still selects whether the gate reads Signal Type, Grade, or
  Ranking buckets. The legacy option value `Grade` now renders as
  `Setup Score` / `[Score A]` so it cannot be mistaken for historical edge.

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
- The harness-owned `f_harness_gate_snapshot()` returns a 4-tuple (source,
  lifetime count, effective count, direct readout). The `Strategy Stats` row
  explains the actual unambiguous buy/sell strategy signal for the selected
  `Backtest Mode`, including exit/reversal signals; `Trade Side` does not
  rewrite its direction. Production mode reuses `f_stats_direct_readout()`
  and therefore shows the real filter result. Raw Baseline uses
  `f_harness_raw_stats_readout()`, explicitly says
  `RAW BASELINE · GATE IGNORED`, retains WR/Avg/edge context without quality
  marks, and allows every raw signal. When statistics are disabled, both modes
  instead prioritize `STATS OFF · ALL ALLOWED / No statistics collected / No
  quality verdict`. Stale buckets follow the production effective-count rule.
  Harness context rows are `Backtest`, `Tester View`, and `Strategy Stats`.
  These snippets live in `tools/generate_strategy_harness.py` — edit them
  there, never in the generated file.
- It is a gated-signal backtest, not an exact intrabar `alert()` delivery
  simulation.
- User-facing harness documentation lives in `README.md` § "Backtesting with
  the Strategy Harness" and `docs/README_CN.md` § "用策略报告版回测" (there are
  no separate strategy-report doc files).

## Where to Look

| Task | Location | Notes |
|------|----------|-------|
| Input groups | `adaptive_rsi.pine:17-89` | All production inputs incl. stats/gate/payoff/alert toggles |
| Dynamic lookback | `adaptive_rsi.pine:124-181` | Adaptive sample-depth logic |
| Spread hysteresis | `adaptive_rsi.pine:163-195` | Boost state machine + `prev_spread` feedback update |
| Weekly protection | `adaptive_rsi.pine:228-255` | Confirmed weekly trend filter |
| MTF analysis | `adaptive_rsi.pine:268-399` | TF selection, lower-TF aggregation, availability flags, seconds-based current-TF dedupe |
| Statistics types | `adaptive_rsi.pine:400-609` | `SignalStats` with decay, indexed + baseline buckets, adjusted win rate, shrunk payoff edge, sample labels, `f_stats_required_winrate` clamp, edge summary helper |
| Signal detection | `adaptive_rsi.pine:742-762` | Raw signals and cooldown state |
| Consolidated signals | `adaptive_rsi.pine:780-876` | Priority merge, upgrade exemption with expired-level reset |
| Statistics engine | `adaptive_rsi.pine:987-1034` | Forward-return bookkeeping, baseline sampling, independent sampling |
| Stats filter | `adaptive_rsi.pine:1035-1193` | Shared `f_stats_gate_paths`, final gate, direct readout, selected-event buckets |
| Dashboard | `adaptive_rsi.pine:1301-1597` | Multiline Full cells, selected-event filter, honest rank interval, combined MTF/context rows, direct WR/Avg-edge readouts and Edge Summary |
| Alerts | `adaptive_rsi.pine:1597-1685` | Direction-specific stats suffixes, smart alert aggregation, per-bar level reset, `alert_on_close` gating |
| Harness inputs | `adaptive_rsi_strategy_harness.pine:85-89` | `Trade Side`, `Backtest Mode`, risk-exit inputs |
| Harness risk direction | `adaptive_rsi_strategy_harness.pine:101-107` | `strategy.risk.allow_entry_in` wiring |
| Harness dashboard rows | `adaptive_rsi_strategy_harness.pine:1547-1569` | `Backtest`, `Tester View`, `Strategy Stats` (Production verdict or explicit Raw gate bypass) |
| Harness strategy logic | `adaptive_rsi_strategy_harness.pine:1809-1874` | Entry/close rules, entry-bound ATR SL/TP exits, exact-N time exit |
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
- `Strategy Stats` shows the actual strategy signal's BUY/SELL bucket selected
  by `Stats Mode`. In Production mode its right cell is the production-filter
  verdict; in Raw Baseline it explicitly says the gate is ignored and shows
  descriptive metrics without marks. `No strategy signal` means neither
  direction fired; simultaneous directions display an explicit conflict and
  produce no strategy action.
- With `Use ATR SL/TP Exits` off and `Max Holding Bars = 0`, trades exit only
  on opposite signals (legacy harness behavior).

## Making Changes

1. Treat [adaptive_rsi.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi.pine) as the primary product.
2. Do not hand-edit duplicated signal logic in [adaptive_rsi_strategy_harness.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi_strategy_harness.pine); regenerate it.
3. Keep the raw signal model at the public `v7.2` baseline. The strict
   v7.2-freeze applied to v7.3 and was lifted by the user for v7.4/v7.5,
   which deliberately upgraded the stats engine (time decay, independent
   sampling, edge-vs-baseline gate, payoff-edge path, unproven-bucket
   pass-through). The post-v7.5 MTF dedupe fix (seconds-based `tf*_is_current`,
   user-requested) is a sanctioned correctness fix to the baseline, like the
   v7.3 ones — it has no revert switch. Further signal-model or stats-engine
   changes still need an explicit user request, and the legacy revert switches
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
