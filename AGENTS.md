# AGENTS.md - Adaptive RSI Pro

> Guidelines for AI agents working on this TradingView Pine Script v6 project.

**Updated**: 2026-09-05 | **Version**: v7.7 | **Branch**: main

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
│   ├── test_alert_contract.py
│   ├── test_data_context.py
│   ├── test_generate_strategy_harness.py
│   ├── test_harness_execution.py
│   └── test_pine_linter.py
└── images/
```

## Current Architecture

### Production indicator

#### v7.7 execution and evidence integrity (current contract)

The user-authorized objective is the win rate of completed trades after costs,
with loss size, expectancy and drawdown checked alongside it. A forward-return
bucket, setup score, or local tooling test is not evidence of improved live
trade win rate. Do not claim a performance improvement without evaluation and
actual execution records.

- **Complete data before new decisions.** `signal_data_ready` requires ready
  current RSI/quantiles and Z-Score, confirmed weekly RSI/SMA20/SMA50, and every
  unique enabled MTF context. Weekly readiness is mandatory even with trend
  protection off because setup scoring still uses weekly features.
- **Request coverage.** The LTF budget is `MAX_REQUEST_BARS = 100000` requested
  lower-timeframe bars, never 100000 chart bars. Actual chart coverage depends
  on the timeframe ratio, feed, plan and warmup. The old artificial 120-week
  request cap is removed. Missing RSI/quantiles return `na` status; availability
  includes calculation readiness. Missing HTF status does not borrow current
  chart status. Manual TF1/TF2/TF3 duplicates are deduplicated by duration as
  well as against the chart timeframe.
- **Eligible history.** Signals and same-direction baselines are recorded only
  when their signal/start bar had `signal_data_ready`. A valid endpoint return
  is still required. Do not require data readiness throughout the future
  horizon: that would censor measurable outcomes using later context gaps.
  Do not silently classify incomplete MTF history as ordinary EXT evidence.
- **Entries versus exits.** New production decisions/alerts and all harness
  entries require complete data. Maintain separate exit-only candidates before
  entry trend/data/stats/cooldown and weekly Smart visibility restrictions; an
  entry rejection must not suppress an otherwise valid raw opposite close.
  Keep explicit normal Off, percentile and divergence conditions. A reversal opens
  a position and therefore still requires a permitted entry. DATA is an
  explicit dashboard state, distinct from WAITING/STALE evidence.
- **Trend protection includes DIV.** Confirmed divergence entries now obey the
  same configured directional weekly protection as normal/extreme entries.
  This and the data fixes are user-authorized correctness changes; do not add
  further signal factors or claim that these changes improve WR by themselves.
- **Defaults.** `alert_on_close = true`, `stats_payoff_mode = "Off"`, and
  `stats_unproven_mode = "Block (Legacy)"`. Preserve the saved option string
  `Block (Legacy)` for compatibility. `Ranking`, Adaptive targets and their
  parent fallback remain. Win-rate gate arithmetic and the optional payoff
  paths remain available; selecting `Either Edge` can still admit a bucket
  whose WR path fails.
- **Shrinkage terminology.** `min(1, effective_n / 20)` is a heuristic weight,
  not calibrated confidence, a Bayesian posterior, a significance test or a
  probability of success. The weight denominator stays 20, independently of
  Adaptive lifetime targets. Legacy toggles restore formulas, not the old
  incomplete data history, pre-fix signal stream, or alert delivery.
- **Alert delivery.** Per-direction `varip` sent levels reset by `bar_index`,
  including close-only strategy execution. `alert.freq_all` permits distinct
  intrabar upgrades while level checks deduplicate repeated evaluations.
  Message construction runs only when `barstate.isrealtime`; historical
  execution still supplies the strategy signal outputs. No
  previous-bar level comparison suppresses a fresh eligible bar event. If
  both directions are actionable in one evaluation, neither is sent; an
  already-delivered earlier-tick alert cannot be withdrawn.
- **Decision snapshots.** `Alert Format = Text | JSON` defaults to Text. JSON
  schema `arsi.alert.v1` records only delivered signal decisions, including
  version/symbol/timeframe/bar/observed times, direction/level/type/grade,
  decision reference price, resolved evidence and target, gate settings,
  unrounded metrics and risk hints. Missing estimates use `null`. Event IDs
  include symbol, timeframe, bar opening time, direction and level. These
  snapshots are not broker fills or a complete blocked-candidate log.
- **Upgrade validation.** Recreate TradingView alerts after upgrading and
  explicitly check saved inputs. Validate common history coverage, warmup,
  repeated manual TFs, DIV protection, close-only new-bar reset, intrabar
  upgrades/conflicts and actual entry/exit behavior. Do not replace the
  user-approved raw model with a new entry hypothesis without a separate
  request and measured evaluation.

#### Historical implementation notes

The following v7.2–v7.6 notes explain the retained engine and its original
behavior. v7.7 requirements and defaults above supersede historical defaults,
display-only availability handling, and claims of full legacy stream parity.

- `v7.2` baseline signal model (adaptive thresholds, MTF resonance, divergence,
  tiered cooldown) plus the v7.3 correctness fixes:
  - `lookback` floor uses the statistical lower bound
  - weekly protection uses confirmed HTF data
  - lower-timeframe MTF uses `request.security_lower_tf()`
- v7.4 deliberately upgraded the **stats engine** (each upgrade keeps a legacy
  revert switch):
  - **Time decay**: `SignalStats` sample weights decay exponentially with
    half-life `stats_half_life_bars` (`0` = legacy equal-weight accumulation).
    Lifetime evidence targets use undecayed `lifetime_count`; confidence uses
    decayed effective count. The v7.6 default Adaptive sample policy
    additionally requires effective count ≥ 5 before evidence can issue a
    verdict, and Ranking may fall back to a ready parent rather than treating
    a sparse or stale exact bucket as proven.
  - **Independent sampling**: `stats_independent_samples` makes each bucket
    wait at least `Forward Bars` between recorded samples so overlapping
    forward-return windows don't inflate counts. Off restores legacy overlap
    and activates the Adaptive overlap guard, returning every lifetime target
    to `Evidence Reference` B.
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
  - **MTF availability surfacing** (original v7.4, superseded by v7.7 readiness): `f_mtf_status()` returns
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
    `Off | Either Edge | Both Edges`, originally default `Either Edge` (a deliberate
    behavior change vs v7.4) — and `stats_min_payoff_edge` —
    `"Min Payoff Edge %"`, default `0.4`, range 0–10, step 0.1.
  - **Gate wiring** (`f_passes_stats_filter`): the payoff path is active only
    when `stats_gate_mode == "Edge vs Baseline"` and `Payoff Gate != Off`;
    `Either Edge` ORs the win-rate and payoff paths, `Both Edges` ANDs them.
    Payoff is an alternative quality criterion, never an alternative to
    evidence readiness: `f_stats_has_verdict_samples(_stats, _target)` gates
    both quality paths. Adaptive requires lifetime count ≥ the bucket's dynamic
    target plus effective count ≥ 5; Fixed (Legacy) uses B as a fixed
    lifetime-only rule. Legacy gate mode forces the payoff path off. The
    confidence shrinkage remains fixed at `min(1, effective/20)` and never
    adopts the lower Adaptive lifetime target.
  - **Display**: Signal Type, setup-score, and Ranking rows all use the same
    action-first readout. A ready Edge/Either right cell is three short lines:
    `BLOCK · OR (0/2)`, `WR edge −0.10pp ✗`, and
    `Avg edge +0.10% ✗`; Full mode no longer repeats raw WR/Avg. The left
    cell uses the same height: Signal Type = type / direction / sample,
    setup score = direction / `[Score X]` / sample, and Ranking = type /
    direction + `[Score X]` / sample. `f_stats_gate_paths()` is the shared,
    unrounded source for filter
    and display booleans, while `f_passes_stats_filter()` remains the final
    action. Ranking still sorts by win-rate edge. A single combined
    `Edge Summary` row renders when either direction has ≥ 2 buckets that both
    reached their own actual targets and retain effective count ≥ 5, and every
    qualifying bucket has negative win-rate edge plus non-positive payoff edge.
    It reports `no supported edge` for loaded history and does not infer a
    market regime. `full_rows` gains `+1` in Edge mode (indicator capacity 20,
    harness 24).
- Later v7.5 dashboard addition (display only): a **`Stats Filter`** row
  renders after `RSI Zone` only when there is a selected current event,
  including a pure-divergence display event. It shows the
  bucket the stats gate consults and the verdict — the explanation for the
  Signal row's `✓`/`✗`/`⏳`. `f_gate_signal_kind()`
  mirrors the `signal_type_text` priority (pure divergence → not gateable);
  resolved bucket choice and the overall verdict reuse the production
  `*_stats` / `filter_*` outputs so the row cannot drift from
  `f_passes_stats_filter`. Under Adaptive Ranking, a parent resolution renders
  the left cell as `Stats Filter` / `<TYPE DIR> → Type` / the parent's real
  `f_stats_sample_text(parent, parent_target)`; the arrow is the fallback mark.
  Insufficient lifetime evidence
  renders `ALLOW|BLOCK · WAITING / No quality verdict`; Adaptive stale evidence
  renders `ALLOW|BLOCK · STALE / Need fresh evidence`. Ready Edge buckets show
  three right-cell lines: `PASS|BLOCK · OR|AND (k/2)`, WR edge, and Avg
  edge. Their left cells also use three semantic lines; direct waiting/stale
  states remain two-line readouts. Bars
  without an event omit
  the row instead of guessing a future type from a persistent zone;
  pure divergence says `DISPLAY ONLY / Not an alert signal`.
  The row flows into the
  harness, where it coexists with the harness-owned `Strategy Stats` snapshot.
- Later v7.5 gate change — **unproven-bucket pass-through** (revert switch:
  `Unproven Buckets = Block (Legacy)` restores the pre-change gate exactly):
  - New input `stats_unproven_mode` — `"Unproven Buckets"`, options
    `Pass | Block (Legacy)`, default `Pass` (a deliberate behavior change) —
    sits between `Sample Policy` and `Min Adjusted WinRate` in grp_stats.
    v7.7 retains the option names but changes the default to `Block (Legacy)`.
  - `f_passes_stats_filter` final expression is
    `_has_enough_samples ? _quality_ok : stats_unproven_mode == "Pass"`:
    verdict-ready evidence uses the quality paths; evidence without a verdict
    uses the policy (Pass = let through, Block = legacy).
  - Three-state marks: the selected dashboard event and each alert direction
    render `⏳` when their own bucket lacks samples (via
    `f_stats_insufficient`, using the same resolved-bucket readiness as the
    gate), and `✓`/`✗` only for verdict-ready evidence. `⚠️` is reserved for general
    data/runtime warnings. Hidden signals spell out `TREND`, `STATS`, `SMART`,
    or `OFF` after `🚫`.
  - Full v7.4-gate revert now also requires
    `Sample Policy = Fixed (Legacy)`, in addition to `Payoff Gate = Off` and
    `Unproven Buckets = Block (Legacy)`.
- v7.6 **adaptive evidence resolution** (revert switch:
  `Sample Policy = Fixed (Legacy)` restores fixed-bucket, lifetime-only
  readiness):
  - `stats_min_samples` is user-facing **`Evidence Reference`**, denoted B;
    default B=20. `stats_sample_policy` options are
    `Adaptive | Fixed (Legacy)`, default `Adaptive`.
  - Adaptive computes a target from lifetime counts only. For bucket count
    `n_i` and the total `N` of four same-direction, same-scope peers:
    `q=(n_i+B/4)/(N+B)`,
    `low=min(B,max(5,round(.4B)))`,
    `high=min(B,max(low,round(.8B)))`, and
    `target=round(low+(high-low)*sqrt(clamp(q,0,1)))`. The B/4 terms are a
    symmetric prior with total weight B. Default B=20 yields 8–16. Signal Type
    peers are the four types per direction; Grade peers are A–D per direction;
    Ranking peers are A–D within one signal type and direction. Target
    selection never reads WR, Avg, edge, or gate outcome.
  - `f_stats_dynamic_target()` returns B when `Fixed (Legacy)` is active or
    when `Independent Samples` is off; the latter is an overlap guard.
    `f_stats_has_verdict_samples(_stats, _target)` is the shared readiness
    predicate. Adaptive requires lifetime ≥ its target and effective ≥ 5;
    Fixed requires lifetime ≥ B only.
  - With `Stats Mode = Ranking`, an unready exact type × score × direction
    bucket resolves to its same-direction Signal Type parent only when that
    parent is ready by the same predicate using the parent's independently
    computed Signal Type target. If neither is ready, the exact bucket remains
    selected but unproven. Signal Type and Grade modes do not have a broader
    fallback.
  - All production filter decisions, signal marks, Soft/Hard display and
    alerts use the resolved bucket. The `Stats Filter` left cell identifies a
    parent as `Stats Filter` / `<TYPE DIR> → Type` / parent sample text.
    Historical Ranking rows remain exact-bucket evidence: an unready visible
    row says `WAIT · EXACT` / `Gate → Type` / parent progress when the
    parent is ready, or `WAIT · NO VERDICT` / `Type evidence` / parent
    progress otherwise. It never displays parent metrics as the exact
    bucket's own.
  - Adaptive sample labels are `n=x/y⏳` below target,
    `n=x · target y` when ready, and `n=x · eff z<5⏳` when lifetime-ready but
    stale. Fixed uses `n=x/y⏳`, ready `n=x`, and legacy `n=x · stale` while
    retaining a lifetime-only verdict. Ranking visibility still requires
    effective count ≥ 5.
  - The stats header is `Outcome +<Forward Bars> bars` plus
    `Adaptive n low–high`; overlap guard and Fixed render
    `Adaptive guard n B` and `Fixed target n B`. `Outcome +20 bars` is the
    return horizon, B=20 is the Evidence Reference, and the separate
    `effective/20` confidence denominator stays fixed.
  - The 8–16 policy is an operational evidence rule, not statistical
    significance, validation, certification, or a future-performance guarantee.
  - This changes signal eligibility. TradingView alerts snapshot the script and
    inputs at creation time, so existing `Any alert() function call` alerts must
    be deleted and recreated after upgrading.
- v7.6 dashboard semantics pass (display only):
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
- Later v7.5 signal-model fix (user-approved deviation from the v7.2 baseline,
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
- `Stats Mode` selects the requested Signal Type, Grade, or Ranking bucket.
  Adaptive may resolve an unready Ranking request to its Signal Type parent;
  Fixed always reads the requested bucket. The legacy option value `Grade`
  renders as `Setup Score` / `[Score A]` so it cannot be mistaken for
  historical edge.

### Strategy report harness

#### v7.7 execution contract

- `Exit Signal Policy = Raw | Filtered (Legacy)` defaults to Raw. Separate
  `harness_exit_*` candidates close existing positions before entry weekly
  trend protection, data/stats guards, cross-bar signal cooldown, and Smart
  weekly visibility restrictions. They retain raw Z-Score crossing thresholds,
  configured percentile confirmation, confirmed divergence, type priority and
  explicit `Normal Signal Mode = Off`. The opposite exit direction must be
  unambiguous. Filtered uses the selected Backtest Mode output. Baseline entry
  candidates still use protected `sig_*` and skip only the stats gate; Production
  entry rules are unchanged. A reversal must pass new-entry requirements.
- `Use Evaluation Dates` defaults off. `Evaluation Start` defaults to
  2020-01-01 UTC and `Evaluation End` to 2100-01-01 UTC. An active interval
  requires start < end, signal-bar open >= start and close < end for entries.
  Earlier eligible history trains statistics without entries; statistics
  continue updating causally during evaluation. This is not a frozen model
  or automatic out-of-sample validation.
- At the first close reaching the evaluation end, request liquidation for the
  next available open. Gaps can extend the trade past the configured date;
  do not invent a boundary fill. Time/ATR/raw exits remain operational.
- Explicit close-only engine settings are `calc_on_every_tick=false`,
  `calc_on_order_fills=false`, `process_orders_on_close=false`. Default
  commission remains 0.05% and slippage 2 ticks; risk exits remain opt-in.
- The additional `Trade Results` row is `SIMULATED · NET`: closed trade WR and
  count, PF, average net trade in account currency, open P&L and holding bars.
  WR is `strategy.wintrades / strategy.closedtrades`; open trades are excluded
  and breakevens stay in the denominator. Commission is already accounted
  for by TradingView: do not subtract it again. States distinguish training,
  data warmup, evaluation, ending/exit pending, ended, all history, invalid dates.
- Raw exits use `RAW EXIT · GATE IGNORED` and the requested bucket/target in
  `Strategy Stats`. Time/date exits name the real exit action. Entry snapshots
  retain the requested-versus-resolved evidence contracts described below.
- Order comments distinguish ENTRY, REVERSE, RAW EXIT, FILTERED EXIT, ATR EXIT,
  Time Exit, Evaluation End. Order `alert_message` begins `ARSI_STRATEGY|v=7.7` and
  includes event/symbol/TF/order bar/time/direction/reference close/mode/exit
  policy. This is an order reference, not a fill; actual fill price/time must
  come from order-fill placeholders, exported emulator trades or broker data.
- The inherited production `alert()` stream (Text/JSON) ignores harness
  Backtest Mode, Trade Side, evaluation dates and exit planning. It is a
  production signal decision, not a strategy order/action. Actual strategy
  action evidence comes from order-fill alerts using
  `{{strategy.order.alert_message}}` plus fill placeholders, or trade exports.
  Keep the two logs separate when reconciling results.
- The harness has four context/results rows: Backtest, Tester View,
  Strategy Stats, Trade Results. Full indicator capacity is 21 rows; generated
  harness capacity is 26 rows (four inserted rows plus one spare). Update the
  generator and regenerate the Pine
  file; never hand-edit generated logic or rows.

#### Retained generator and evidence behavior

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
  - `Exit Signal Policy = Raw | Filtered (Legacy)`
  - `Use Evaluation Dates`, `Evaluation Start`, `Evaluation End`
  - Risk exits: `Use ATR SL/TP Exits` (SL/TP snapshotted at the signal bar's
    close; `strategy.exit` is issued with the entry and bound via
    `from_entry`, so the bracket protects from the entry fill bar) and
    `Max Holding Bars` (time exit realizing exactly N held bars — close order
    placed at the close of held bar N−1, fills at the next open; `0` = off)
- `Baseline` entries use raw candidates with v7.7 data readiness; `Production`
  entries also require the production stats gate. Both reject direction
  conflicts. The independent exit policy determines opposite-signal closes.
- The harness-owned `f_harness_gate_snapshot()` returns a 4-tuple (source,
  sample text, direct readout, color). The `Strategy Stats` row
  explains the actual unambiguous buy/sell strategy signal for the selected
  `Backtest Mode`, including exit/reversal signals; `Trade Side` does not
  rewrite its direction. An active Production gate uses the resolved evidence
  bucket and target and therefore shows the real filter result; an Adaptive
  Ranking fallback renders for example `BUY · EXT [Score A] → Type`, with the
  parent's `f_stats_sample_text(parent, parent_target)`. Raw Baseline,
  stats-off and Production filter-off views retain both the bucket requested by
  `Stats Mode` and that requested bucket's target; they never borrow parent
  statistics. Fixed never falls back and uses B. Production reuses
  `f_stats_direct_readout()`: ready Edge results use action / WR edge / Avg
  edge as three lines, while waiting/stale and Legacy results stay two lines.
  Raw Baseline uses `f_harness_raw_stats_readout()`: Edge results are
  `RAW · GATE IGNORED` / WR edge / Avg edge, while Legacy WR and
  `No usable estimate` stay two lines; none carry quality marks. When statistics
  are disabled, both modes use `Stats off` plus
  `STATS OFF · ALL ALLOWED / No quality verdict`. Sample labels and colors come
  from the same production helpers as the readout.
  Harness context rows are `Backtest`, `Tester View`, `Strategy Stats`, and
  `Trade Results` (added in v7.7).
  These snippets live in `tools/generate_strategy_harness.py` — edit them
  there, never in the generated file.
- It is a gated-signal backtest, not an exact intrabar `alert()` delivery
  simulation.
- User-facing harness documentation lives in `README.md` § "Backtesting with
  the Strategy Harness" and `docs/README_CN.md` § "用策略报告版回测" (there are
  no separate strategy-report doc files).

## Where to Look

Line starts are navigation hints; search the named function or section after edits.

| Task | Location | Notes |
|------|----------|-------|
| Input groups | `adaptive_rsi.pine:23` | Evidence, defaults, alert format, and signal settings |
| Dynamic lookback | `adaptive_rsi.pine:128` | RSI sample-depth logic, separate from evidence targets |
| Spread hysteresis | `adaptive_rsi.pine:171` | Previous-spread feedback state |
| Weekly protection | `adaptive_rsi.pine:236` | Confirmed weekly features, readiness and protection |
| MTF analysis | `adaptive_rsi.pine:273` | 100000 LTF bars, indicator availability, unique TFs |
| Common data eligibility | `adaptive_rsi.pine:396` | Entry/sample readiness and first eligible time |
| Statistics types + targets | `adaptive_rsi.pine:421` | Decay, count-only targets, fixed weight denominator |
| Signal detection | `adaptive_rsi.pine:823` | Raw candidates and protected DIV eligibility |
| Consolidated signals | `adaptive_rsi.pine:861` | Priority/cooldown and data-ready cooldown updates |
| Statistics engine | `adaptive_rsi.pine:1068` | Signal-time eligible samples and matched baselines |
| Stats filter | `adaptive_rsi.pine:1119` | Requested/resolved evidence, data-gated outputs and conflict |
| Dashboard | `adaptive_rsi.pine:1438` | Data Context, action readout and exact ranking evidence |
| Alerts | `adaptive_rsi.pine:1736` | JSON snapshots, bar-identity reset, upgrade dedupe/conflicts |
| Harness inputs | `adaptive_rsi_strategy_harness.pine:89` | Side/mode/exit policy/risk and dates |
| Harness dates and side | `adaptive_rsi_strategy_harness.pine:114` | Direction wiring and evaluation interval |
| Harness requested evidence | `adaptive_rsi_strategy_harness.pine:1201` | Requested bucket and target helpers |
| Harness action planner | `adaptive_rsi_strategy_harness.pine:1518` | Independent entries, exits, reversals, date/time actions |
| Harness evidence snapshot | `adaptive_rsi_strategy_harness.pine:1589` | Entry/exit-specific source/sample/readout/color |
| Harness dashboard rows | `adaptive_rsi_strategy_harness.pine:1787` | Backtest, Tester View, Strategy Stats, Trade Results |
| Harness strategy logic | `adaptive_rsi_strategy_harness.pine:2194` | Exclusive market action and entry-bound ATR brackets |
| Generator anchors | `tools/generate_strategy_harness.py` | Anchor names, harness-owned snippets, `--check` mode |
| Tooling tests | `tests/` | Generator/anchor, signal integrity, alert and linter checks |

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
    lookahead=barmerge.lookahead_on
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
  by `Stats Mode`, or its resolved Signal Type parent when an active Production
  Adaptive Ranking gate falls back (`[Score A] → Type`). Active Production uses
  the resolved bucket's target; Raw Baseline, stats-off and Production
  filter-off views keep the requested bucket **and requested target**. Fixed
  always uses requested bucket + B. Production's right cell is the compact
  production-filter verdict; Raw Baseline says `RAW · GATE IGNORED` and shows
  descriptive evidence without marks. `No strategy signal` means neither
  direction fired; simultaneous directions display an explicit conflict and
  produce no new entry; independent time/date liquidation remains available.
- Raw exits read the separate `harness_exit_*` candidate's requested bucket/target
  and ignore entry trend/data/stats/cooldown and Smart weekly visibility guards,
  retaining explicit signal conditions and Normal Off.
  Time/date exits report their actual action instead of an entry gate verdict.
- With `Use ATR SL/TP Exits` off, `Max Holding Bars = 0`, and evaluation dates
  off, trades exit only on opposite signals, using the chosen exit policy.

## Making Changes

1. Treat [adaptive_rsi.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi.pine) as the primary product.
2. Do not hand-edit duplicated signal logic in [adaptive_rsi_strategy_harness.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi_strategy_harness.pine); regenerate it.
3. Keep the raw signal model at the public `v7.2` baseline. The strict
   v7.2-freeze applied to v7.3 and was lifted by the user for v7.4/v7.5,
   which deliberately upgraded the stats engine (time decay, independent
   sampling, edge-vs-baseline gate, payoff-edge path, unproven-bucket
   pass-through). The later-v7.5 MTF dedupe fix (seconds-based `tf*_is_current`,
   user-requested) is a sanctioned correctness fix to the baseline, like the
   v7.3 ones — it has no revert switch. The user also authorized the v7.7 data,
   DIV protection, default-policy, alert and execution repairs described above.
   Further signal-model or stats-engine changes still need an explicit user request, and the legacy revert switches
   (`stats_half_life_bars = 0`, `Independent Samples` off,
   `Sample Policy = Fixed (Legacy)`, `Absolute (Legacy)` gate,
   `Payoff Gate = Off` plus
   `Unproven Buckets = Block (Legacy)` for the v7.4 gate) must keep restoring
   the old formulas. They do not restore pre-fix data coverage, signal streams,
   or alert delivery.
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
