# Adaptive RSI Pro

[中文说明 / Chinese README](docs/README_CN.md)

[![TradingView](https://img.shields.io/badge/TradingView-Indicator-blue?logo=tradingview)](https://www.tradingview.com/scripts/)
[![Pine Script](https://img.shields.io/badge/Pine%20Script-v6-brightgreen)](https://www.tradingview.com/pine-script-reference/v6/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Pine Script Lint](https://github.com/aaajiao/Adaptive-RSI-Pro/actions/workflows/pine-lint.yml/badge.svg)](https://github.com/aaajiao/Adaptive-RSI-Pro/actions/workflows/pine-lint.yml)

**Pine Script v6** | **v7.6**

An RSI that adapts its overbought/oversold thresholds to each asset's own statistics, scores every signal, tracks how those signals performed in loaded history, and gates alerts with configurable sample and quality rules.

![Adaptive RSI Pro on a chart](images/annotated_rsi_indicator.png)

## Contents

- [What It Is](#what-it-is)
- [Quick Start](#quick-start)
- [Reading the Dashboard](#reading-the-dashboard)
  - [Reading the Ranking Leaderboard](#reading-the-ranking-leaderboard)
- [Signals & Legend](#signals--legend)
- [Alerts](#alerts)
- [The Stats Engine & Gate](#the-stats-engine--gate)
- [Backtesting with the Strategy Harness](#backtesting-with-the-strategy-harness)
- [Known Limitations](#known-limitations)
- [Development & Validation](#development--validation)
- [License](#license)

---

## What It Is

Traditional RSI uses fixed 30/70 thresholds, but different assets live in different volatility regimes — 30 on a sleepy ETF and 30 on a crypto pair mean very different things. This indicator instead measures where today's RSI sits inside the asset's **own historical RSI distribution**, using a **Z-Score**:

| Z-Score | Percentile | Meaning |
|---------|------------|---------|
| ±2σ | ≈ P2 / P98 | Extreme zone |
| ±Nσ | Dynamic | Normal overbought/oversold reference (N adapts to volatility) |

On top of the adaptive thresholds it layers multi-timeframe resonance, divergence detection, weekly trend protection, per-signal quality grading, and a statistics engine that gates alerts using the selected bucket's sample state and measured history.

The project ships two files:

- **`adaptive_rsi.pine`** — the production indicator. This is the product.
- **`adaptive_rsi_strategy_harness.pine`** — a generated `strategy()` wrapper around the same signal engine, for validating signals in TradingView's Strategy Tester. See [Backtesting with the Strategy Harness](#backtesting-with-the-strategy-harness).

---

## Quick Start

### 1. Add the indicator

1. Open TradingView and go to the Pine Editor.
2. Paste the contents of `adaptive_rsi.pine`.
3. Click **Add to chart**.

### 2. Set up the alert

1. Right-click the indicator and choose **Add Alert**.
2. Set the condition to **Any alert() function call**.
3. Optional: enable `Include Risk Hints in Alerts` to get ATR-based stop-loss/take-profit suggestions in each message.
4. Optional: enable `Alert on Bar Close` to fire alerts only on confirmed bars (no intrabar repaint, at the cost of later delivery).

### 3. Suggested presets

| Scenario | Dashboard | Normal Signals | Protection Level | Filter Mode |
|----------|-----------|----------------|------------------|-------------|
| Intraday trading | Full | Smart | Moderate | Alert Only |
| Swing trading | Full | Off | Moderate | Hard |
| Mobile monitoring | Mobile | Off | Loose | Alert Only |

### 4. Filter Mode tips

- `Alert Only` — best default: every signal stays on the chart, but only gate-passing signals reach your phone.
- `Soft` — keep full chart context, with failed signals visually de-emphasized.
- `Hard` — show only signals allowed by the current gate settings; cleanest chart.

---

## Reading the Dashboard

### Full mode (desktop)

With `Stats Mode = Ranking` and the default `Edge vs Baseline` gate, the panel looks like this:

```text
┌──────────────────────────────────────────────────────────────┐
│ ADAPTIVE RSI                                               35 │
├──────────────────────────────────────────────────────────────┤
│ RSI Position          Z -2.15σ                                │
│                       History ≤P5                              │
│ Signal                🔥 EXT BUY                              │
│                       [Score A] ✗                              │
│ RSI Zone              🟢 EXTREME OVERSOLD                    │
│ Stats Filter                 BLOCK · OR (0/2)                │
│ 🔥 EXT BUY → Type          WR edge −0.10pp ✗              │
│ n=18 · target 14             Avg edge +0.10% ✗             │
│ Market Context        Trend Moderate: Both allowed              │
│                       W-RSI 45                                  │
│                       Volume: Surge (1.8×)                    │
│ Lookback [Auto]       74 bars                                 │
│ Allowed 59–400 bars   Healthy                                 │
│ Normal Signals [Smart] Active                                  │
│                       Threshold ±1.50σ                         │
├──────────────────────────────────────────────────────────────┤
│ MTF                   1h 🟢Oversold · 4h No data            │
│                       D 🟢Oversold                             │
│                       No resonance · 2/4 incl chart             │
│ Divergence            None · Auto / Crypto                    │
│                       Pivot 10 · Max gap 120 bars              │
├──────────────────────────────────────────────────────────────┤
│ ── WR-EDGE RANK ──    Avg edge min +0.4%                   │
│ Outcome +20 bars      BUY WR 56.10→61.10%                    │
│ OR · Adaptive n 8–16  SELL WR 44.00→49.00%                   │
│ Edge Summary          SELL: no supported edge                │
│ 🌟 MTF               PASS · OR (2/2)                        │
│ BUY [Score B]         WR edge +8.60pp ✓                       │
│ n=18 · target 13      Avg edge +2.30% ✓                      │
│ 🔥 EXT               BLOCK · OR (0/2)                       │
│ BUY [Score A]         WR edge −0.10pp ✗                       │
│ n=14 · target 12      Avg edge +0.10% ✗                      │
└──────────────────────────────────────────────────────────────┘
```

The visual line breaks above are newline-separated layers inside each table cell. They do **not** add Pine table rows or consume more of the dashboard's row capacity. `Stats Filter` and `Edge Summary` are conditional table rows, so a neutral panel can still be shorter than this example.

### Row-by-row guide

| Row | What it shows |
|-----|---------------|
| **RSI Position** | One non-duplicated location readout. `Z -2.15σ` is distance from the current RSI mean; `History ≤P5` is the empirical rank interval inside the active lookback. Other intervals are `P5–P10`, `P10–P25`, `P25–P50`, `P50–P75`, `P75–P90`, `P90–P95`, and `>P95`. `History` is intentionally a range, not an exact percentile. |
| **Signal** | An event on the current bar. Full mode places icon + type + direction on the first cell line and `[Score A]` plus any gate mark on the second, for example `🔥 EXT BUY` / `[Score A] ✓`. The score is the current setup score, not the historical-edge verdict or permission to trade. Persistent overbought/oversold state no longer repeats here; with no event the row shows `—`. |
| **RSI Zone** | Persistent RSI state: `🟢 EXTREME OVERSOLD`, `🟡 OVERSOLD`, `⚪ NEUTRAL`, `🟠 OVERBOUGHT`, or `🔴 EXTREME OVERBOUGHT`. This is context, not a new signal. |
| **Stats Filter** | Appears only for a current signal event. Its left cell contains the evidence source, bucket label, and the sample label for the target actually used. A ready Edge right cell uses three short lines: `PASS|BLOCK · OR|AND (k/2)`, then `WR edge …`, then `Avg edge …`. Waiting and stale states remain two lines. With default `Sample Policy = Adaptive` and `Stats Mode = Ranking`, the left-cell layout `Stats Filter` / `🔥 EXT BUY → Type` / the parent sample label means the exact type × score × direction bucket was not ready, so the gate used its ready same-direction Signal Type parent and target; the arrow is the fallback marker. Insufficient lifetime evidence reads `ALLOW|BLOCK · WAITING / No quality verdict`; stale Adaptive evidence reads `ALLOW|BLOCK · STALE / Need fresh evidence`. The action comes from `Unproven Buckets`, not an edge estimate. Pure divergence says `DISPLAY ONLY / Not an alert signal`; with no current event the row is omitted. Ready cells stay white because one cell can contain both ✓ and ✗; policy-allowed waiting/stale evidence is yellow, policy-blocked evidence is gray, Fixed-legacy stale is yellow, and filter-off/display-only states are gray. |
| **Market Context** | Weekly trend protection in words (`Both allowed`, `BUY only`, `SELL only`, `Both blocked`, or `Trend: Off`), confirmed weekly RSI, and volume scoring state (`Surge`, `Low`, `Normal`, or `score off`). White means both directions are available or protection is off, yellow means one direction is available, and red means both are blocked. These are inputs to signal handling and grading, not an entry instruction. |
| **Lookback** | The left cell separates mode from its allowed window, for example `Lookback [Auto]` / `Allowed 59–400 bars`; `[Custom]` uses its fixed-window wording. The right cell shows the current value and health, such as `74 bars` / `Healthy`, or names the actual issue in natural language. Multiple issues can use a third cell line. |
| **Normal Signals** | `[Smart]`, `[On]`, or `[Off]`; the value cell separates the operating state from the symmetric threshold, for example `Active` / `Threshold ±1.50σ`. |
| **MTF** | One cell uses up to three lines for the configured timeframes and their plain states: `🟢Oversold`, `🔴Overbought`, `⚪Neutral`, or `No data`, followed by `Oversold resonance`, `Overbought resonance`, or `No resonance` and the agreeing/valid-slot count. `incl chart` means the chart timeframe participates in the ratio; a configured slot equal to it is not counted twice. |
| **Divergence** | Two cell lines: current result plus mode, such as `None · Auto / Crypto`, then explicit parameter meanings such as `Pivot 10 · Max gap 120 bars`. |

### Mobile mode

Three rows only:

```text
┌────────────────────────────┐
│ RSI        35.2            │
│ Signal     🔥 EXT BUY [Score A] ✓│
│ RSI Zone   🟢极卖           │
└────────────────────────────┘
```

### Reading the Ranking Leaderboard

With `Stats Mode = Ranking`, the dashboard compares **signal type × setup-score band × direction** buckets (32 in total) using the history loaded on the chart.

A typical panel in the default `Edge vs Baseline` mode:

```text
── WR-EDGE RANK ──   Avg edge min +0.4%
Outcome +20 bars        BUY WR 56.10→61.10%
OR · Adaptive n 8–16    SELL WR 44.00→49.00%
🌟 MTF                    PASS · OR (2/2)
BUY [Score B]              WR edge +8.60pp ✓
n=18 · target 13          Avg edge +2.30% ✓
🔥 EXT                    BLOCK · OR (0/2)
BUY [Score A]              WR edge −0.10pp ✗
n=14 · target 12          Avg edge +0.10% ✗
💎 DIV                    WAIT · EXACT
SELL [Score B]             Gate → Type
n=9/13⏳                  n=18 · target 12
```

#### The header

The left header cell is `WR-EDGE RANK` / `Outcome +20 bars` / `OR · Adaptive n 8–16`; the right cell is `Avg edge min +0.4%` / the BUY win-rate baseline→minimum / the SELL baseline→minimum. Those are three visual lines inside one table row. With the default `Evidence Reference = 20`, `Adaptive n 8–16` is the real dynamic target range. Turning `Independent Samples` off changes it to `Adaptive guard n 20`; `Sample Policy = Fixed (Legacy)` shows `Fixed target n 20`.

`Outcome +20 bars` means every sample measures the direction-normalized price result **20 bars** after a signal (`Forward Bars`, default 20). It is an outcome horizon, not a sample-count requirement. `BUY WR 56.10→61.10%` means a 56.10% unconditional buy-direction baseline and a 61.10% effective minimum for the win-rate path. The minimum is `baseline + (Min Adjusted WinRate − 50)`, so the default setting adds 5 percentage points and clamps the result to 25–90%. `SELL WR 44.00→49.00%` is the same calculation for sell samples. `Avg edge min +0.4%` is the separate payoff-edge threshold.

The last header line names the active rule: `OR` for `Either Edge`, `AND` for `Both Edges`, and `WR only` when payoff gating is off. When `Enable Stats Filter` is off it says `Filter off` instead, while the right header keeps the configured thresholds as reference.

Under `Absolute (Legacy)`, the title becomes `WIN-RATE RANK`, the left cell says `Absolute WR gate`, and the right cell says `Minimum WR 55.00%`. It does not show baseline-derived thresholds because that mode uses a fixed absolute win-rate rule.

#### Each row

Left cell — `🔥 EXT` / `BUY [Score A]` / `n=14 · target 12`:

- **Type and direction are written out on separate lines**: line 1 is `MTF`, `DIV`, `EXT`, or `NORMAL`; line 2 starts with `BUY` or `SELL`. The icon is only a visual shortcut; for example sell extreme uses `❄️ EXT` / `SELL [Score A]`, while sell normal uses `⬇️ NORMAL` / `SELL [Score D]`.
- **`[Score A]`** stays on the direction line and is the current setup score band A–D. It is not the bucket's historical-edge verdict and is not permission to trade.
- **`n=14 · target 12`** is a ready Adaptive label: 14 undecayed lifetime samples against this bucket's current target of 12. The target is displayed even after it is reached because different buckets can have different targets.
- **`n=9/13⏳`** means 9 lifetime samples toward this bucket's current Adaptive target of 13. `⏳` means the exact bucket cannot issue a quality verdict.
- **`n=18 · eff 3.7<5⏳`** means lifetime count reached the current target but decayed effective weight is below 5. Adaptive treats it as stale and cannot issue a verdict. Ranking hides rows with effective weight below 5, so this label appears in current `Stats Filter`, Signal Type, or Setup Score views rather than the leaderboard.
- Under `Fixed (Legacy)`, a ready bucket is simply `n=28`; an unready label has the form `n=current/B⏳`, where B is the fixed `Evidence Reference`, and `n=28 · stale` preserves the old lifetime-only verdict despite low effective weight.

Right cell, first line — `BLOCK · OR (0/2)`:

- **`PASS` / `BLOCK`** is the configured gate's final decision for verdict-ready evidence.
- **`OR (0/2)`** means the `Either Edge` rule is active and zero of the two evidence paths passed. `OR (1/2)` and `OR (2/2)` pass; `AND (2/2)` is the only passing count under `Both Edges`.
- **`WR ONLY`** means payoff gating is off. **`ABS WR`** means `Absolute (Legacy)` is using a fixed win-rate minimum.
- In an `Adaptive` Ranking row whose exact bucket is not ready, the historical row does **not** print a gate action. A ready parent uses three lines: `WAIT · EXACT` / `Gate → Type` / `n=18 · target 12`. If the parent is also unready, it says `WAIT · NO VERDICT` / `Type evidence` / `n=7/10⏳`. The parent progress is descriptive; its metrics are never presented as the exact bucket's history.

Right cell, second line — `WR edge −0.10pp ✗`:

- **`WR edge −0.10pp`** is Bayesian-adjusted win rate minus the same-direction baseline. `WR-EDGE RANK` sorts by this edge only.

Right cell, third line — `Avg edge +0.10% ✗`:

- **`Avg edge +0.10%`** is the confidence-shrunk difference between the bucket's average direction-normalized forward result and the same-direction baseline average. It is compared with `Min Payoff Edge %`.
- The `✓`/`✗` after each edge says whether that path cleared its threshold. Each path has its own short line; raw `WR` and raw `Avg` are intentionally omitted from Full mode to avoid forcing the user to recombine them.
- Displayed edge and Legacy-minimum values use enough decimals to prevent an apparent boundary contradiction. The actual decision still uses the unrounded internal value.
- With `WR ONLY`, the third line labels Avg edge as `info`. Under `ABS WR`, the right cell stays two lines and shows `WR actual ≥|< minimum ✓|✗` on its second line.

#### The direct reading rule: decision first, evidence second

For a ready Edge bucket, read the three right-cell lines from top to bottom:

1. **Action and rule:** `PASS` or `BLOCK`, then `OR`, `AND`, `WR ONLY`, or `ABS WR`.
2. **Win-frequency evidence:** `WR edge`, with its own mark.
3. **Average-payoff evidence:** `Avg edge`, with its own mark or `info` when payoff gating is off.

For example, `WR edge −0.10pp ✗` on line 2 and `Avg edge +0.10% ✗` on line 3 mean neither excess path reaches its threshold, so line 1 reports `BLOCK · OR (0/2)`.

When the selected evidence has no verdict, the gate deliberately suppresses a quality interpretation. Lifetime `n` below its current target reads `ALLOW|BLOCK · WAITING / No quality verdict`; Adaptive effective `n < 5` reads `ALLOW|BLOCK · STALE / Need fresh evidence`. `Unproven Buckets`, not either estimate, decides the action.

If statistics remain enabled but `Enable Stats Filter` is off, the row says `FILTER OFF · ALL ALLOWED`. Edge mode puts the descriptive `WR edge` and `Avg edge` estimates on separate second and third lines without ✓/✗; Legacy keeps the two-line `WR … · no gate` form. An unavailable estimate also stays two lines and says `No usable estimate`. The header says `Filter off`. When statistics themselves are off, history rows are not rendered because no statistics are collected.

The two edges still answer different questions: WR edge asks whether the signal wins more often than its direction baseline; Avg edge asks whether its average result exceeds that baseline. A bucket can clear one and miss the other. For example, WR edge −4pp plus Avg edge +1.2% gives `PASS · OR (1/2)` under `Either Edge`, but `BLOCK · AND (1/2)` under `Both Edges`. Historical estimates are not guarantees of future behavior.

#### Adaptive sample policy

`Sample Policy = Adaptive` is the default. `Evidence Reference` is denoted by **B**. For each bucket, the script looks only at lifetime counts inside four same-direction, same-scope peers:

- Signal Type: the four signal types for one direction.
- Setup Score: the four A–D bands for one direction.
- Ranking: the four A–D bands for one signal type and direction.

For bucket lifetime count `nᵢ` and the four-peer total `N`, it applies a symmetric prior with total weight B—equivalently B/4 pseudo-counts per peer:

```text
q = (nᵢ + B/4) / (N + B)
low  = min(B, max(5, round(0.4B)))
high = min(B, max(low, round(0.8B)))
target = round(low + (high − low) × sqrt(clamp(q, 0, 1)))
```

With default `Evidence Reference = 20`, the operational lifetime target therefore moves within **8–16**. Symmetric smoothing keeps empty or early-history peers from jumping to extremes. A more common bucket receives a higher target; a sparse bucket receives a lower one. The calculation uses counts only—never WR, Avg, edge, PASS/BLOCK, or the sign of performance.

Adaptive evidence is ready when lifetime `n ≥ that bucket's target` **and** effective `n ≥ 5`. `Signal Type` and `Grade` modes use their requested bucket and its own target. In `Ranking`, the exact type × score × direction bucket is preferred. If it is unready, the gate tries the same-direction Signal Type parent, whose target is calculated independently from its own four Signal Type peers. If neither is ready, the exact bucket remains unproven and `Unproven Buckets` decides. A stale bucket therefore cannot block merely because an old, strongly decayed estimate looks poor.

Turning `Independent Samples` off restores overlapping forward windows, so Adaptive's overlap guard returns every lifetime target to **B**. `Fixed (Legacy)` also uses B as a fixed lifetime threshold, always uses the bucket requested by `Stats Mode`, never falls back, and ignores effective-sample freshness for readiness.

The **8–16 rule is an operational evidence policy**, not a statistical-significance test, validation threshold, confidence interval, or guarantee. It makes the sparse-bucket trade-off explicit and conservative enough for the gate's workflow; it does not prove that a signal has a durable edge.

The two user-facing defaults of 20 do different jobs: `Outcome +20 bars` is the forward-return horizon, while `Evidence Reference = 20` sets B and therefore the default 8–16 Adaptive range. Separately, Bayesian/payoff confidence still uses the fixed `min(1, effective_n / 20)` full-confidence denominator. Lowering a bucket's lifetime target does **not** lower that shrinkage denominator or make its edge estimate reach full confidence sooner.

Historical Ranking rows always remain exact-bucket evidence. They are never replaced by parent metrics: `WAIT · EXACT / Gate → Type …` says a ready parent is available for a matching live event, while `WAIT · NO VERDICT / Type …` shows the parent's real progress. Only the current signal's gate view actually resolves to the parent.

#### Edge Summary

In `Edge vs Baseline` mode, one optional row condenses a direction-level check:

```text
Edge Summary     BUY: no supported edge
Edge Summary     SELL: no supported edge
Edge Summary     BUY + SELL: no supported edge
```

Only one summary row can appear. It may use two cell lines when both BUY and SELL qualify; that still does not add a table row. For a direction to be named, the active `Stats Mode` must contain at least two buckets that both (a) reached their own actual evidence target and (b) retain effective weight of at least 5. Every included bucket in that direction must then have WR edge < 0 and Avg edge ≤ 0. Buckets below target or too stale to retain effective weight are excluded rather than treated as negative evidence.

The summary describes only the loaded historical buckets that met those conditions. It is not a market-regime diagnosis, does not predict the next signal, and does not replace the per-signal `Stats Filter` verdict. Changing `Stats Mode`, history depth, or decay can change the summary.

#### Two honest caveats

1. **High WR edge does not imply high `Avg`.** Read the final decision and both evidence lines; frequency and magnitude capture different properties of the loaded sample.
2. **The baseline and effective weight move.** They depend on loaded history and time decay. A row can change or disappear as old weight fades, even though its displayed lifetime `n` never decreases.

#### Visibility rules

- At most **8 rows** are shown.
- Ranking includes only buckets with effective `n ≥ 5`; if none qualify, it says `No usable buckets / Need effective n ≥ 5`.
- Negative WR-edge buckets remain eligible and sort below higher WR-edge buckets.

#### Other stats modes

`Signal Type` aggregates type × direction and uses three left-cell lines such as `🔥 EXT` / `BUY` / `n=18 · target 14`. `Grade` aggregates direction × setup-score and uses `BUY` / `[Score A]` / `n=15 · target 12` under the header `SETUP SCORE STATS`. Ranking is the full type × score × direction view and uses `🔥 EXT` / `BUY [Score A]` / the sample label. Each mode computes its target from its own four-peer scope, and all three use the same decision-first, three-line ready Edge readout. Direct waiting and stale verdicts remain two lines; an exact Ranking wait uses three lines so its Type-parent source and progress remain readable. Under `Adaptive`, a stale `Signal Type` or `Grade` row shows `n=18 · eff 3.7<5⏳` and no quality verdict; under `Fixed (Legacy)` it retains the old `n=28 · stale` behavior. Ranking continues to hide rows below effective weight 5.

---

## Signals & Legend

### Buy signals (shown near the bottom of the pane)

| Icon | Name | Condition | Priority |
|------|------|-----------|----------|
| 🌟 | MTF Resonance | Multi-timeframe oversold alignment + Z < −2σ | ★★★★★ |
| 💎 | Divergence + Extreme | Bullish divergence inside the extreme oversold zone | ★★★★☆ |
| 🔥 | Extreme Oversold | Z-Score breaks below −2σ (about P2) | ★★★☆☆ |
| ⬆️ | Normal Oversold | Z-Score breaks below −Nσ (dynamic threshold) | ★★☆☆☆ |
| ↗️ | Bullish Divergence | Price makes a new low while RSI does not | ★☆☆☆☆ |

### Sell signals (shown near the top of the pane)

| Icon | Name | Condition | Priority |
|------|------|-----------|----------|
| 🌟 | MTF Resonance | Multi-timeframe overbought alignment + Z > +2σ | ★★★★★ |
| 💎 | Divergence + Extreme | Bearish divergence inside the extreme overbought zone | ★★★★☆ |
| ❄️ | Extreme Overbought | Z-Score breaks above +2σ (about P98) | ★★★☆☆ |
| ⬇️ | Normal Overbought | Z-Score breaks above +Nσ (dynamic threshold) | ★★☆☆☆ |
| ↘️ | Bearish Divergence | Price makes a new high while RSI does not | ★☆☆☆☆ |

> **Priority rule**: when multiple conditions are true on the same bar, only the highest-priority signal is shown.

### Status icons

| Icon | Status | Z-Score range |
|------|--------|---------------|
| 🟢 | Extreme oversold | Z < −2σ |
| 🟡 | Oversold | −2σ ≤ Z < −Nσ* |
| ⚪ | Neutral | −Nσ ≤ Z ≤ +Nσ |
| 🟠 | Overbought | +Nσ < Z ≤ +2σ |
| 🔴 | Extreme overbought | Z > +2σ |

> *N is the dynamic normal threshold, derived from volatility: ~1.0σ in high-volatility markets up to 1.8σ in very quiet ones (1.28σ and 1.5σ in between). In `On` mode it is the manual threshold instead.

### Setup score bands

Every signal carries a multi-factor setup score. The panel writes its band explicitly as `[Score A]` through `[Score D]` so it cannot be confused with the separate historical-edge verdict:

| Band | Score | Interpretation |
|------|-------|----------------|
| [Score A] | ≥80 | Strong current setup score |
| [Score B] | 60–79 | Supportive current setup score |
| [Score C] | 40–59 | Mixed current setup score |
| [Score D] | <40 | Weak current setup score |

The score summarizes the current signal's conditions. It is **not** a historical WR/Avg edge verdict, a `PASS`/`BLOCK` decision, or permission to trade. Read the setup score and the stats decision as separate evidence.

**How the score is built** (buy side shown; sell side mirrors it):

- Base **+50** for being in the extreme zone (|Z| > 2σ)
- Depth bonus: **+20** if |Z| > 2.5σ, else **+10** if |Z| > 2σ
- **+25** for divergence **or** MTF resonance (a single bonus — they do not stack)
- **+10** RSI pivot confirmation in the extreme zone
- **+15** weekly trend alignment
- **+10** volume surge (when volume scoring is enabled)
- **−20** opposite weekly extreme (e.g. buying into an extreme weekly downtrend)
- **−10** unusually low volume
- **−15** if any statistical health check fails (sample coverage / distribution width / validity)
- **−10** ADX counter-trend penalty (strong trend against the signal)
- Floor at 0

### Display marks

| Mark | Meaning | Notes |
|------|---------|-------|
| ✓ | Verdict-ready evidence passed its configured rule | Appears on the current Signal's final gate result, on each passing WR/Avg edge line, and in an allowed alert. It is a rule result, not statistical validation or a forecast. |
| ✗ | Verdict-ready evidence missed its configured rule | Appears on current signals in `Alert Only`/`Soft`, on failed WR/Avg edge lines, or with a `BLOCK`. A blocked signal does not alert. |
| ⏳ | No quality verdict | Lifetime `n` is below the bucket's displayed target, or `Adaptive` effective `n` is below 5 with no ready fallback. The event-level `Stats Filter` says `ALLOW|BLOCK · WAITING` or `ALLOW|BLOCK · STALE`; exact Ranking rows show `WAIT · EXACT` with a ready parent or `WAIT · NO VERDICT` with parent progress. An alert can contain `⏳` only when policy allowed it. |
| `🚫 TREND` | Hidden by weekly trend protection | Used instead of a generic hidden icon so the reason is visible. |
| `🚫 STATS` | Hidden by `Hard` stats filtering | The gate action is block; inspect `Stats Filter` for its comparisons when shown. |
| `🚫 OFF` / `🚫 SMART` | Normal signal hidden by its display mode | `OFF` means Normal Signals is disabled; `SMART` means Smart mode paused it. |
| ⚠️ | General runtime/data warning only | It is not a sample or quality verdict. The current dashboard spells out common cases as `No data` or the specific health issue. |
| — | No current event or not applicable | Persistent overbought/oversold context belongs in `RSI Zone`. |

> Alerts fire only when the filter action is allow. Their filter suffix is `✓` for verdict-ready evidence that passed or `⏳` for unproven evidence allowed by policy; blocked signals produce no alert.

---

## Alerts

One aggregated alert covers all signal types. Create it once with **Any alert() function call** and every gate-passing signal arrives in a single message stream.

### Message anatomy

```text
AAPL: 🟢 BUY → 🌟MTF共振 | RSI:25.3 Z:-2.1σ (≈P2) [Score A] ✓
AAPL: 🔴 SELL → ❄️极端 | RSI:78.5 Z:2.3σ (≈P98) [Score B] ✓
```

- **Direction**: `🟢 BUY` / `🔴 SELL`
- **Signal icon**: `🌟MTF共振` (resonance), `💎背离` (divergence), `🔥极端` / `❄️极端` (extreme), `⬆️超卖` / `⬇️超买` (normal)
- **Optional suffixes**: `✓确认` (RSI pivot confirmation), `↩反转` (Z-Score crossing back out of the extreme zone), `⚡实时背离` (realtime divergence forming)
- **Context**: RSI value, Z-Score, approximate percentile, setup score band, filter mark

With `Include Risk Hints in Alerts` enabled:

```text
AAPL: 🟢 BUY → 🔥极端 ✓确认 ⚡实时背离 | RSI:25.3 Z:-2.1σ (≈P2) [Score A] ✓ | SL:-1.5% TP:+3.0%
```

### Risk hints

Stops are based on **ATR(14)**, scaled by the signal's setup-score band:

| Setup-score band | Stop distance |
|------------------|---------------|
| A | 2.5 × ATR |
| B | 2.0 × ATR |
| C | 1.5 × ATR |
| D | 1.2 × ATR |

Take-profit = stop distance × `Risk-Reward Ratio` (default 2.0, range 1.5–3.0). For sell signals the signs flip (`SL:+x% TP:-y%`).

### Timing

`Alert on Bar Close` (default off) delays alerts to bar confirmation: no intrabar signals that flash and vanish before the close (repaint), at the cost of later delivery. Off keeps immediate intrabar behavior.

### What gets through

Alerts fire only for signals that pass the stats gate, in **every** filter mode — `Alert Only` filters nothing on the chart, but the alert stream is always gated. Same-bar deduplication only lets a higher-priority upgrade re-alert.

The dynamic evidence targets change gate behavior. TradingView alerts retain the script snapshot and settings from when they were created, so after installing this version, delete and recreate existing **Any alert() function call** alerts. Otherwise an older alert can continue running the prior fixed-target logic even while the updated panel is visible.

---

## The Stats Engine & Gate

The statistics turn each signal bucket's loaded history into a configurable filter decision. The marks report that decision; they do not certify future performance.

**What gets recorded.** Every signal occurrence is scored by its forward return — what price did `Forward Bars` later (default 20). Buy samples record the rise; sell samples record the *decline*, so positive is favorable to the sampled direction. Samples land in buckets according to `Stats Mode`: by signal type, by setup-score band, or by the full type × score × direction cross (`Ranking`). Two unconditional baseline buckets (buy/sell) record the forward result of *every* bar, giving each direction both a baseline **win rate** and a baseline **average result**.

**Bayesian adjustment.** Small raw samples are unstable. Each bucket's win rate is shrunk toward a prior: `adjusted = prior + confidence × (raw − prior)` with `confidence = min(1, effective_samples / 20)`. In `Edge vs Baseline` mode the prior is the bucket's own direction baseline; in `Absolute (Legacy)` mode it is 50%. Buckets with fewer than 5 lifetime samples report no adjusted rate. The divisor 20 is a fixed full-confidence denominator and does not fall with an 8–16 Adaptive lifetime target.

**Payoff edge.** The return-side comparison is `payoff edge = confidence × (bucket average forward result − direction baseline average result)`, with the same confidence factor and the same "no value below 5 lifetime samples" rule. Subtracting the direction baseline removes unconditional drift; shrinkage pulls small or stale estimates toward zero.

**Time decay.** `Stats Half-Life Bars` (default 1500, `0` = off) exponentially fades sample weight with age — 1500 bars is roughly 6 years on a daily chart or 9 months on 4H, covering a full cycle while letting old regimes fade. Decay affects the *effective* count and therefore confidence. Lifetime counts and targets remain undecayed; under `Adaptive`, effective `n ≥ 5` is an additional freshness requirement, so an old bucket cannot issue a verdict solely because it once accumulated enough observations.

**Independent sampling.** `Independent Samples` (default on) makes each bucket wait at least `Forward Bars` between recorded samples, so overlapping forward-return windows can't inflate the sample count. Off restores the legacy overlapping behavior and activates the Adaptive overlap guard: dynamic targets return to the full `Evidence Reference` B.

**The gate.** It first resolves a verdict-ready evidence bucket, then applies the quality rule:

1. **Evidence resolution.** With default `Sample Policy = Adaptive`, a bucket is ready only when lifetime `n ≥ its dynamic target` **and** effective `n ≥ 5`. With default `Evidence Reference = 20`, count-only peer smoothing produces targets from 8 to 16. In Ranking mode, an unready exact bucket automatically tries its same-direction Signal Type parent using the parent's independently calculated target. Bucket choice and targets depend only on sample counts/readiness, never on which result looks better. In `Fixed (Legacy)`, the configured `Stats Mode` bucket is always used and lifetime `n ≥ Evidence Reference` alone decides readiness.
2. **No ready evidence.** **`Unproven Buckets = Pass`** (default) allows the signal and marks it `⏳`; **`Block (Legacy)`** blocks it. This is a policy action, not a WR/Avg quality verdict.
3. **Ready evidence.** The quality criterion decides. `✓` means its configured logic passed and `✗` means it missed; neither mark is statistical validation or a performance guarantee.

`Evidence Reference = 20` is a configurable operating reference, not a claim that 8, 16, or 20 observations statistically validate a signal. The full formula, peer scopes, overlap guard, and the distinct fixed `effective_n / 20` shrinkage denominator are documented in [Adaptive sample policy](#adaptive-sample-policy).

The quality criterion has two possible paths:

- **Win-rate path**: adjusted win rate ≥ the required level. The required level depends on `Gate Mode`:
  - **`Edge vs Baseline`** (default): required = direction baseline + (`Min Adjusted WinRate` − 50). With the default 55 that is **baseline + 5pp**, clamped to **25–90%**. This exists because absolute thresholds systematically reject sell buckets on trending assets — a 45% sell win rate can be a genuinely strong edge when random selling wins only 38% (see [the leaderboard guide](#reading-the-ranking-leaderboard)).
  - **`Absolute (Legacy)`**: required = `Min Adjusted WinRate` as a fixed absolute threshold, prior = 50%.
- **Payoff path** (v7.5): payoff edge ≥ `Min Payoff Edge %` (default **0.4**, range 0–10, step 0.1). Because drift is already subtracted via the baseline, this threshold only has to beat estimation noise — 0.3–0.5 is the recommended band. The payoff path is **only active when `Gate Mode = Edge vs Baseline`**; under `Absolute (Legacy)` the gate is always pure win-rate.

How the two paths combine is set by **`Payoff Gate`** (options `Off` / `Either Edge` / `Both Edges`, default **`Either Edge`**):

- **`Off`** — win-rate path only: the exact v7.4 gate.
- **`Either Edge`** (default) — pass if *either* path passes. This admits "wins less often, wins bigger" buckets — the typical shape of mean-reversion signals on trending assets — and is therefore a **behavior change versus v7.4**: some buckets that v7.4 blocked will now alert. Set `Payoff Gate = Off` to revert.
- **`Both Edges`** — both paths must pass; stricter than v7.4.

**Filter modes** decide what a failed gate does:

| Mode | Chart | Alerts |
|------|-------|--------|
| `Alert Only` | All signals visible | Filtered |
| `Soft` | Failed signals downgraded visually | Filtered |
| `Hard` | Failed signals hidden | Filtered |

> **Restoring v7.4 gate behavior**: set `Sample Policy = Fixed (Legacy)`, `Payoff Gate = Off`, **and** `Unproven Buckets = Block (Legacy)`. The gate then uses the original selected bucket and lifetime-only readiness before applying the v7.4 quality expression. Ranking Avg-edge readouts and `Edge Summary` are display-only and remain available in Edge mode.
>
> **Restoring v7.3 stats behavior**: set `Sample Policy = Fixed (Legacy)`, `Stats Half-Life Bars = 0`, turn `Independent Samples` **off**, set `Unproven Buckets = Block (Legacy)`, and set `Gate Mode = Absolute (Legacy)` (which by itself deactivates the payoff path, whatever `Payoff Gate` says). This restores the legacy stats-engine arithmetic exactly. Two v7.4 signal-level changes have **no revert switch** — the lookback spread-factor hysteresis band (engages below a spread of 18, releases above 22) and the cooldown stale-level reset — so the recorded signal stream, and therefore gate decisions, may still differ slightly from v7.3.

**Cooldown & upgrades.** High-priority signals (🌟/💎/🔥/❄️) use a 1-bar cooldown. Normal signals use `Cooldown Mode`: `Smart` (the default — 2–8 bars by volatility, shortened by one when the market is active) or `Fixed` (a fixed bar count, 5 by default). A higher-priority same-side signal bypasses cooldown — `⬆️ → 🔥 → 🌟` can fire on consecutive bars. The upgrade exemption only compares against a previous signal that is *still cooling down*; expired levels count as 0, so a normal signal can never use its own stale level to bypass its own cooldown.

---

## Backtesting with the Strategy Harness

### What it is — and is not

`adaptive_rsi_strategy_harness.pine` is a `strategy()` wrapper **generated from the production indicator** (by `tools/generate_strategy_harness.py` — never hand-edited), so the signal engine is identical. It answers one question: how does the v7.6 signal engine behave inside TradingView's Strategy Tester?

It is a **gated-signal backtest**, not an exact intrabar `alert()` delivery simulation: it does not model alert scheduling or delivery counts. Use it to evaluate the signal and filter path, not alert-log parity.

Also keep the two views apart: the indicator's stats are fixed-horizon **forward-return** statistics (signal quality), while the harness reports realized trades under `strategy()` execution rules (execution results). They are related but never the same number — don't compare the strategy win rate directly with the indicator's adjusted win rate.

### Setup

1. Open a separate Pine script in the Pine Editor.
2. Paste `adaptive_rsi_strategy_harness.pine` and add it to the chart.
3. Open the **Strategy Tester** tab.

### Inputs

| Input | Default | What it does |
|-------|---------|--------------|
| `Trade Side` | `Long Only` | `Long Only`: opens longs, sell signals close them. `Short Only`: opens shorts, buy signals close them. `Both`: reverses on opposite signals. |
| `Backtest Mode` | `Production` | `Baseline`: trades the raw signals, no stats filter. `Production`: trades only gate-passing signals — the same gate the alerts use. |
| `Use ATR SL/TP Exits` | off | Exits via the same ATR-based SL/TP prices the alerts advertise. Prices are snapshotted at the signal bar's close (the entry fills at the next bar's open); the exit is issued with the entry and bound via `from_entry`, so the bracket protects the trade from the entry fill bar onward. Off = exits only on opposite signals. |
| `Max Holding Bars` | `0` (off) | Force-closes the position after exactly N held bars (time exit) — the close order is placed at the close of held bar N−1 and fills at the next bar's open. |

### Reading the results

TradingView always shows `All`, `Long`, and `Short` columns. **Read `All` according to `Trade Side`**: with `Long Only` it is your long-only result; with `Short Only` your short-only result; with `Both` the combined result. The harness's `Tester View` row repeats this rule.

The harness adds three rows to the dashboard:

- `Backtest` — side and execution path in plain language: `Long only`, `Short only`, or `Long + short`, followed by `Raw baseline` or `Production filter`.
- `Tester View` — how to read TradingView's `All` column: `All = long trades`, `All = short trades`, or `All = both sides`.
- `Strategy Stats` — three left-cell lines (`Strategy Stats` / source / sample). A ready Production Edge result uses three right-cell lines: action/rule, WR edge, and Avg edge. Waiting/stale, Legacy, and unavailable states remain two lines. A normal source can be `BUY · MTF [Score A]` / `n=14 · target 12`; an active Production Ranking fallback is `BUY · MTF [Score A] → Type`, followed by the parent sample label and parent target. Raw Edge evidence likewise uses `RAW · GATE IGNORED`, then separate WR-edge and Avg-edge lines without ✓/✗; Raw Legacy WR and `No usable estimate` remain two lines. It says `No strategy signal` when neither direction fires; simultaneous directions say `BUY + SELL conflict / No strategy action`.

The bucket and target source matrix is explicit:

| Strategy Stats state | Bucket and target shown | Right-cell meaning |
|----------------------|-------------------------|--------------------|
| `Production`, stats + filter on | Production-resolved bucket and its target; Adaptive Ranking may use the ready Signal Type parent | Ready Edge: three lines (`PASS`, WR edge, Avg edge); policy-allowed `WAITING`/`STALE`: two lines |
| `Production`, filter off | Bucket requested by `Stats Mode` and that bucket's target; no parent fallback | Edge: three lines (`FILTER OFF`, WR edge, Avg edge); Legacy/unavailable: two lines |
| `Raw baseline`, stats on | Bucket requested by `Stats Mode` and that bucket's target; no parent fallback | Edge: three lines (`RAW · GATE IGNORED`, WR edge, Avg edge); Legacy/unavailable: two lines; descriptive only |
| Statistics off, either mode | Requested source remains named, but sample line is `Stats off`; no parent fallback | `STATS OFF · ALL ALLOWED / No quality verdict` |
| `Fixed (Legacy)` | Always the requested bucket; target is fixed `Evidence Reference` B | Never falls back; lifetime-only readiness |

`Production filter` reads production-gated strategy signals and displays the production decision, resolved evidence source, and exact target that applied. `Raw baseline` reads raw strategy signals and explicitly ignores the gate; its metrics are descriptive only. Filter-off, Raw, and stats-off `Strategy Stats` cells are gray. `BUY`/`SELL` is always the signal's own direction. `Trade Side` decides what that signal does—entry, close, or reversal—but does not relabel it: for example, a `SELL` signal can close a long-only position. The inherited `Stats Filter` row remains the decision view for the current production indicator event, which need not be the same event selected by the chosen backtest mode.

### Costs

The harness declares **commission 0.05%** and **slippage 2 ticks** as defaults. Override both in **Strategy Tester → Properties** — no code edits needed.

### Recommended workflow

1. Start with `Trade Side = Long Only`.
2. Run `Backtest Mode = Baseline` — does the raw signal engine have edge on this symbol?
3. Switch to `Backtest Mode = Production` — does the alert gate improve or hurt the result?
4. Repeat on a few symbols; good starters are `GOOGL 1D`, `AAPL 1D`, and `BTCUSDT 4H`.

---

## Known Limitations

- **History-dependent statistics**: all signal statistics are computed from the chart history TradingView actually loads, so gate decisions can differ across subscription plans, symbols, and even sessions on the same symbol.
- **Sample-overlap bias**: `Independent Samples` mitigates overlapping forward-return windows but cannot fully eliminate sample-overlap bias.
- **Lower-TF MTF coverage**: lower-timeframe MTF data only covers roughly the most recent 1400 chart bars (`MAX_REQUEST_BARS`), so MTF resonance signals are sparse in deep history.
- **Intrabar repaint**: intrabar signals can appear and disappear before the bar closes unless `Alert on Bar Close` is enabled.
- **Harness scope**: the strategy harness is a gated-signal backtest, not an exact intrabar `alert()` delivery simulation.

---

## Development & Validation

Source: [github.com/aaajiao/Adaptive-RSI-Pro](https://github.com/aaajiao/Adaptive-RSI-Pro)

Local checks (a custom Pine Script static analyzer, harness-generation drift check, and a Python `unittest` suite; CI runs the same on every push/PR touching `.pine` files or tooling):

```bash
python3 tools/generate_strategy_harness.py --check
python3 tools/pine_linter/cli.py --config .pine-lint.yml adaptive_rsi.pine
python3 tools/pine_linter/cli.py --config .pine-lint.yml adaptive_rsi_strategy_harness.pine
python3 -m unittest discover -s tests -v
```

After changing production logic, regenerate the harness with `python3 tools/generate_strategy_harness.py` — never hand-edit it.

TradingView validation: paste both scripts into the Pine Editor and confirm compile/runtime behavior on at least **GOOGL 1D**, **AAPL 1D**, and **BTCUSDT 4H**.

---

## License

[MIT](LICENSE)
