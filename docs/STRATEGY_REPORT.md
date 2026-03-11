# Strategy Report Guide

This guide explains how to use [adaptive_rsi_strategy_harness.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi_strategy_harness.pine) with the `v7.3` production release that preserves `v7.2` behavior.

## Purpose

The production indicator is still [adaptive_rsi.pine](/Users/aaajiao/o_projects/RSI_stock/adaptive_rsi.pine).  
The strategy harness exists only to answer one question: how does the restored `v7.3` signal engine behave inside TradingView `Strategy Tester`.

## Modes

### Trade Side

- `Long Only`: only opens longs; sell signals close longs
- `Short Only`: only opens shorts; buy signals close shorts
- `Both`: allows reversals in both directions

### Backtest Mode

- `Baseline`: trades the raw `v7.2` production signals
- `Production`: trades only the same signals that the production indicator would finally allow into alerts

`Production` is the closest strategy approximation of the production script's final alert path.

## Dashboard rows

The harness adds three rows to the full dashboard:

- `Harness`: current `Trade Side` and `Backtest Mode`
- `Tester`: how to read TradingView `All`
- `Production Gate`: current signal bucket, sample count, average return, adjusted win rate

Example:

```text
Production Gate: EXT[A](12) +2.8%|67%
```

This means:

- current bucket = `EXT[A]`
- samples = `12`
- average forward return = `+2.8%`
- adjusted win rate = `67%`

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

## Important limitation

The production indicator's stats are fixed-horizon forward-return statistics.  
The strategy harness reports realized trades under `strategy()` execution rules.

So:

- indicator stats = signal-quality view
- strategy report = execution-result view

They are related, but they are not the same number.

## Common mistakes

- Treating the harness as the main product
- Reading `All` as mixed long/short data when the harness is set to one side only
- Assuming `Production` changes the production indicator logic; it only controls what the harness trades
- Comparing strategy win rate directly with the indicator's adjusted win rate
