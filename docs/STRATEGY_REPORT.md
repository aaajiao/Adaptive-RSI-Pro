# Strategy Report Guide

This guide explains how to use [adaptive_rsi_strategy_harness.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi_strategy_harness.pine) with the `v7.4` production release that preserves `v7.2` baseline behavior.

## Purpose

The production indicator is still [adaptive_rsi.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi.pine).  
The strategy harness exists only to answer one question: how does the `v7.4` signal engine behave inside TradingView `Strategy Tester`.

The harness is generated from the production indicator by [tools/generate_strategy_harness.py](/Users/aaajiao/o_projects/RSI_stock/tools/generate_strategy_harness.py). Edit production logic in `adaptive_rsi.pine`, then regenerate the harness instead of hand-editing duplicated signal code.

## Modes

### Trade Side

- `Long Only`: only opens longs; sell signals close longs
- `Short Only`: only opens shorts; buy signals close shorts
- `Both`: allows reversals in both directions

### Backtest Mode

- `Baseline`: trades the raw `v7.2` production signals
- `Production`: trades signals that pass the production alert gate/filter

`Production` is a gated-signal execution view. It does not model intrabar `alert()` delivery, alert scheduling, or exact smart-alert delivery counts; use it to evaluate the filter path, not alert-log parity.

Since `v7.4` the production stats engine defaults to time decay, independent sampling, and the `Edge vs Baseline` gate mode, so `Production` results differ from `v7.3` with the same inputs. Setting `Stats Half-Life Bars = 0`, turning `Independent Samples` off, and setting `Gate Mode = Absolute (Legacy)` restores the legacy stats-engine arithmetic only; other `v7.4` signal-level changes (spread-factor hysteresis, cooldown upgrade-level reset) have no revert switch, so `Production` results may still differ from `v7.3`.

### Risk Exits (v7.4, both default off)

- `Use ATR SL/TP Exits` (`harness_use_risk_exits`): trades exit via the same ATR-based SL/TP prices the alerts advertise, snapshotted at entry; off = exits only on opposite signals (legacy harness behavior)
- `Max Holding Bars` (`harness_max_holding_bars`, `0` = off): force-closes the position after holding N bars (`Time Exit`)

### Costs

The harness declares commission `0.05%` and slippage `2` ticks as defaults. You can override both in TradingView `Strategy Tester` → `Properties` without editing code.

## Dashboard rows

The harness adds three rows to the full dashboard:

- `Harness`: current `Trade Side` and `Backtest Mode`
- `Tester`: how to read TradingView `All`
- `Production Gate`: actual stats bucket selected by `Stats Mode`, sample count, average return, adjusted win rate

Example in `Ranking` mode:

```text
Production Gate: EXT[A](12) +2.8%|67%
```

This means:

- current bucket = `EXT[A]`
- samples = `12`
- average forward return = `+2.8%`
- adjusted win rate = `67%`

When `Stats Mode` is `Signal Type`, the label uses `TYPE:EXT`; when it is `Grade`, it uses `GRADE[A]`. Those labels are the same buckets used by the production filter.

If there is no active signal on the current bar, the row shows `Idle`.

## How to read TradingView `All / Long / Short`

TradingView always keeps the `All`, `Long`, and `Short` columns.

Use them like this:

- `Long Only`: read `All` as the active long-only result
- `Short Only`: read `All` as the active short-only result
- `Both`: read `All` as the combined result

The `Tester` row in the harness repeats this rule.

## Recommended workflow

1. Start with `Trade Side = Long Only`
2. Run `Backtest Mode = Baseline`
3. Check whether raw `v7.2` signals still have edge on the symbol
4. Switch to `Backtest Mode = Production`
5. Check whether the final alert gate improves or reduces the result

Suggested first symbols:

- `GOOGL 1D`
- `AAPL 1D`
- `BTCUSDT 4H`

These are also the required compile-validation symbols: after any upgrade, paste both scripts into Pine Editor and confirm compile/runtime behavior on at least these three charts.

## Maintenance

After production logic changes, run:

```bash
python3 tools/generate_strategy_harness.py
python3 tools/generate_strategy_harness.py --check
```

CI also runs the `--check` path so drift between the production indicator and strategy harness fails early.

## Important limitations

The production indicator's stats are fixed-horizon forward-return statistics.  
The strategy harness reports realized trades under `strategy()` execution rules.

So:

- indicator stats = signal-quality view
- strategy report = execution-result view

They are related, but they are not the same number.

Also keep in mind:

- The harness is a gated-signal backtest, not an exact intrabar `alert()` delivery simulation.
- Statistics depend on how much chart history TradingView loads, so `Production` gate decisions (and therefore trades) can differ across subscription plans and sessions.
- Lower-timeframe MTF data only covers roughly the most recent `MAX_REQUEST_BARS` (1400) chart bars, so MTF-driven trades are sparse in deep history.

## Common mistakes

- Treating the harness as the main product
- Reading `All` as mixed long/short data when the harness is set to one side only
- Assuming `Production` changes the production indicator logic; it only controls what the harness trades
- Comparing strategy win rate directly with the indicator's adjusted win rate
