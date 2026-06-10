# Adaptive RSI Pro

[中文说明 / Chinese README](docs/README_CN.md)

[![TradingView](https://img.shields.io/badge/TradingView-Indicator-blue?logo=tradingview)](https://www.tradingview.com/scripts/)
[![Pine Script](https://img.shields.io/badge/Pine%20Script-v6-brightgreen)](https://www.tradingview.com/pine-script-reference/v6/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Pine Script Lint](https://github.com/aaajiao/Adaptive-RSI-Pro/actions/workflows/pine-lint.yml/badge.svg)](https://github.com/aaajiao/Adaptive-RSI-Pro/actions/workflows/pine-lint.yml)

**Pine Script v6** | **v7.5**

An RSI that adapts its overbought/oversold thresholds to each asset's own statistics, scores every signal, tracks how those signals actually performed, and only alerts you when a signal type has a proven historical edge.

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

On top of the adaptive thresholds it layers multi-timeframe resonance, divergence detection, weekly trend protection, per-signal quality grading, and a statistics engine that gates alerts on each signal type's measured historical edge.

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
- `Hard` — show only historically qualified signals; cleanest chart.

---

## Reading the Dashboard

### Full mode (desktop)

With `Stats Mode = Ranking` and the default `Edge vs Baseline` gate, the panel looks like this:

```text
┌────────────────────────────────────────────┐
│ ADAPTIVE RSI                          35.2 │
├────────────────────────────────────────────┤
│ Z-Score              -2.15σ (≈P2)          │
│ Percentile           P5 (−1.5σ ~ −2σ)      │
│ Signal               🔥[A]✓                │
│ Status               🟢 EXTREME OVERSOLD   │
│ Protection [Moderate] ✓ W.RSI:45 📊↑       │
│ Lookback [Auto]      456↑(150-800) ✅✅✅   │
│ Normal [Smart]       ⬆️1.50σ ✓             │
├────────────────────────────────────────────┤
│ MTF 60|240|D         🟢|⚪|–               │
│ Resonance            🟢 3/4 ⚠️             │
│ Divergence [Normal]  🟢 BULL (5/60)        │
├────────────────────────────────────────────┤
│ ── RANKING ──        (20b) Base→Req        │
│                      ⬆62→67%|⬇38→43%       │
│ 🌟[A]📈(28)✓         +3.2%|71%             │
│                      (+8.6pp|+2.3%)        │
│ 💎[B]📉(21)✓         +1.8%|46%             │
│                      (+7.9pp|+2.7%)        │
└────────────────────────────────────────────┘
```

### Row-by-row guide

| Row | What it shows |
|-----|---------------|
| **Z-Score** | Current RSI Z-Score and its approximate percentile (`≈P2`). The percentile label assumes a normal distribution — a display approximation, not an exact rank. |
| **Percentile** | The actual bucketed percentile of RSI in the lookback window (P5/P10/P25/P50/P75/P90/P95/P99), with the matching σ range. |
| **Signal** | Active signal icon + quality grade + filter mark, e.g. `🔥[A]✓`. Between signals it shows persistent state text such as `🔥持续` (extreme zone continues) or `超卖区` (in the normal oversold zone). |
| **Status** | Current zone: `🟢 EXTREME OVERSOLD`, `🟡 OVERSOLD`, `⚪ NEUTRAL`, `🟠 OVERBOUGHT`, `🔴 EXTREME OVERBOUGHT`. |
| **Protection** | Weekly trend filter state — `✓` both directions allowed, `BUY✓` / `SELL✓` one direction allowed, `⚠️` both blocked, `OFF` disabled — plus the weekly RSI value and a volume icon (`📊↑` surge, `📊↓` low, `📊` normal). |
| **Lookback** | `[Auto]` or `[Custom]` mode; the current adaptive sample window and its allowed range, e.g. `456(150-800)`. A trailing `↑` after the number means the spread-feedback boost is engaged (narrow RSI distribution → longer window). The three icons are health checks — sample coverage, distribution width, statistical validity — each `✅` (ok) or `⚠️` (degraded). |
| **Normal** | Normal-signal mode `[Smart]`/`[On]`/`[Off]` and the current dynamic threshold, e.g. `⬆️1.50σ ✓` (active) or `1.50σ ✗` (suppressed by Smart mode), `—` when off. |
| **MTF** | Per-timeframe RSI status: `🟢` oversold, `🔴` overbought, `⚪` neutral, `–` no usable data for that timeframe. |
| **Resonance** | How many timeframes agree out of those with valid data, e.g. `🟢 3/4`. A trailing `⚠️` means at least one timeframe has no data (display-only warning; resonance math is unchanged). |
| **Divergence** | Active divergence mode (auto-selected or custom), `🟢 BULL` / `🔴 BEAR` / `—`, and the (lookback/range) parameters in use. |

### Mobile mode

Three rows only:

```text
┌─────────────────┐
│  RSI      35.2  │
│  Signal   🔥[A]✓│   signal + grade + mark
│  Status   🟢极卖 │   zone only
└─────────────────┘
```

### Reading the Ranking Leaderboard

With `Stats Mode = Ranking` the dashboard becomes a leaderboard of **signal type × quality grade × direction** buckets (32 in total), showing which combinations have actually worked on this chart. This is the most information-dense part of the panel, so here is how to read it, element by element.

A typical panel in the default `Edge vs Baseline` mode:

```text
── RANKING ──      (20b) Base→Req
                   ⬆62→67%|⬇38→43%
🌟[A]📈(28)✓       +3.2%|71%
                   (+8.6pp|+2.3%)
💎[B]📉(21)✓       +1.8%|46%
                   (+7.9pp|+2.7%)
🔥[B]📈(35)✓       +1.6%|68%
                   (+5.7pp|+0.7%)
⬆️[C]📉(9)⚠️       +0.6%|39%
                   (+1.2pp|+0.7%)
🔥[D]📈(12)⚠️      -0.8%|60%
                   (-2.4pp|-1.0%)
```

#### The header

`(20b)` is the forward window: every sample measures what price did **20 bars** after a signal (`Forward Bars`, default 20).

`⬆62→67%` reads as: the **buy-direction baseline** win rate is 62% — the probability that buying on *any* bar of this chart shows a gain 20 bars later — and a buy bucket needs an **adjusted win rate of 67%** to pass the win-rate path of the alert gate (since v7.5, under the default `Payoff Gate = Either Edge`, a bucket can alternatively qualify through the payoff path — see [the stats engine](#the-stats-engine--gate)). The requirement is `baseline + (Min Adjusted WinRate − 50)`, so with the default `Min Adjusted WinRate = 55` that is baseline + 5 percentage points, clamped to 25–90% so extreme baselines can never make the gate unsatisfiable or trivially easy. `⬇38→43%` is the same thing for the sell direction.

The `Base→Req` header appears in both gate modes; under `Absolute (Legacy)` the `Req` value is simply the fixed absolute threshold.

#### Each row

Left cell — `🌟[A]📈(28)✓`:

- **Signal type emoji**: `🌟` MTF resonance, `💎` divergence + extreme, `🔥` extreme, `⬆️` normal. In this column the type emoji is *not* directional — direction comes only from the next element.
- **`[A]`** — quality grade A–D.
- **`📈`/`📉`** — buy or sell bucket.
- **`(28)`** — effective sample count, after time decay.
- **Reliability mark**: `✓` ≥ 20 effective samples, `⚠️` ≥ 5.

Right cell, first line — `+3.2%|71%`:

- **Average forward return**. For `📉` (sell) rows the convention flips: the number measures how far price *fell* after the signal, so positive = the sell call was right.
- **Adjusted win rate** — the raw win rate shrunk toward the bucket's own direction baseline (see [the stats engine](#the-stats-engine--gate)).

Right cell, second line — `(+8.6pp|+2.3%)`:

- **Win-rate edge**: adjusted win rate − its own direction's baseline, in percentage points. This is the sort key.
- **Payoff edge**: the bucket's average forward return minus the direction baseline's average forward return, shrunk by the same confidence factor as the win rate (see [the stats engine](#the-stats-engine--gate)). Positive = this bucket's signals not only happen, they *pay* better than random entries.
- The second line only appears in `Edge vs Baseline` mode; under `Absolute (Legacy)` the cell is a single line and rows are sorted by absolute adjusted win rate instead.

#### The core reading rule: compare pp, not win rates

Think of the win rate as an exam score and the baseline as the class average for that exam. Only the amount **above the average** was earned by the signal itself.

On a rising asset, randomly buying might win 62% of the time (tailwind), while randomly selling is right only 38% of the time (headwind). A 68% buy win rate and a 46% sell win rate are therefore **not directly comparable**. Run the numbers: out of 100 random buys you'd win 62; the `🔥[B]📈` bucket at 68% wins only 6 more (+5.7pp). Out of 100 random sells you'd be right 38 times; the `💎[B]📉` bucket at 46% is right 8 more times (+7.9pp). The "worse-looking" sell bucket actually carries more information.

If the leaderboard ranked by absolute win rate, every buy bucket on an uptrending asset would crowd the top and every sell bucket would sink to the bottom — the board would be measuring "this stock is going up", not "which signal works". (This was a real flaw in v7.3, and the same accounting issue caused sell alerts to be systematically filtered out.) Edge sorting uses the same yardstick as the alert gate: the gate requires a lifetime sample count ≥ `Min Samples` (default 20) **and** a quality edge — a win-rate edge of at least +5pp (by default) or, since v7.5 under the default `Payoff Gate = Either Edge`, a payoff edge ≥ `Min Payoff Edge %` instead.

#### Win-rate edge vs payoff edge

The two numbers on the second line answer different questions. **Win-rate edge** (`pp`) asks: does this signal win *more often* than a random entry? **Payoff edge** (`%`) asks: does it win *more money* per trade than a random entry? A bucket can fail one and pass the other.

Worked example, on a chart with a 62% buy baseline whose random 20-bar entry averages +0.9%: a bucket sits at a 58% win rate — that is **−4pp**, it fails the win-rate path — but its average forward return is **+2.1%** against the baseline's +0.9%, a **+1.2% shrunk payoff edge** (at full confidence), which clears the default `Min Payoff Edge % = 0.4`. The bucket **wins less often, but wins bigger** — typical of mean-reversion entries on a trending asset, where the few deep-pullback fills capture outsized rebounds. With the default `Payoff Gate = Either Edge`, this bucket passes the gate.

The converse is the caution: when **both** edges are negative — wins less often *and* pays worse than random — the bucket is truly dead. No reading of the numbers rescues it.

#### What a negative pp means

A negative edge means following that signal wins *less often than buying at random* — the signal systematically picks worse-than-average moments. This is easy to misread: in the mock panel, `🔥[D]📈` shows a 60% win rate, which looks fine against the naive 50% mark — but with a 62% baseline it is 2.4pp **worse than blind buying** (the win rate is shown rounded; the panel's `(-2.4pp)` is the exact edge). Mechanically this happens, for example, when extreme-oversold signals tend to fire mid-collapse (catching a falling knife). Since v7.5 a negative pp is no longer a single-metric death sentence — check the payoff figure on the same line before discarding the bucket, because a wins-less-often-wins-bigger bucket can still carry a real payoff edge (here `🔥[D]📈` shows `-1.0%`, so both edges are negative and the bucket really is dead).

This is also why bucketing matters: the same signal type at different grades can have opposite signs — `🔥[A]📈` might be +6pp while `🔥[D]📈` sits at −2.4pp.

How to act on a negative-edge bucket:

- The win-rate path of the gate blocks it, so under the default `Either Edge` it only alerts if its payoff edge clears `Min Payoff Edge %` — i.e. a negative-pp alert is always a "wins less often, wins bigger" bucket. With `Payoff Gate = Off` or `Both Edges` it never alerts.
- If it appears on the chart anyway (e.g. `Alert Only` mode), treat it as noise.
- Don't trade it in reverse: the inverse trade is measured against the *opposite* direction's baseline, and after costs there is usually no edge left.
- Because shrinkage pulls small samples toward the baseline, the true negative edge may be deeper than displayed.
- Only when a bucket reaches `✓` reliability and stays negative is it a dependable "this path doesn't work" verdict.

#### The "No timing edge" row

When an entire *direction* goes dead, the panel says so explicitly. Right under the stats header, a row like

```text
⬆️ No timing edge  无择时优势·趋势市?
```

appears (in orange, one row per direction at most, `Edge vs Baseline` mode only) when that direction has at least **2 buckets with data** (effective count ≥ 5) and **all** of them show a negative win-rate edge **and** a non-positive payoff edge. In other words: nothing in that direction wins more often than random, and nothing wins bigger either.

That pattern is the signature of a trending regime — on a strong uptrend, mean-reversion buy timing adds nothing over just being long (and vice versa for downtrends). How to act on it: don't counter-trend time entries in that direction on this symbol/timeframe; the alert gate will already be blocking those signals, so treat any that still appear on the chart as noise. The hint reads the same buckets the gate reads (the active `Stats Mode`), so switching `Stats Mode` can change whether it fires. Like everything in the stats panel, it describes loaded history — after a regime change it fades only as new samples accumulate.

#### Two honest caveats

1. **High edge ≠ high expected return.** A 46% win rate still means a 54% chance of being wrong — counter-trend remains counter-trend. The average-return column already amortizes the losing trades, so read both: win rate tells you whether the signal *reads the market* well; average return tells you whether it *makes money*.
2. **The baseline itself moves.** It depends on how much chart history is loaded and shifts with time decay, so after a regime change the meaning of every edge value refreshes. Small-sample buckets have their adjusted win rate shrunk toward the baseline, squeezing their edge toward 0 — by design, so small samples can't brag.

#### Visibility rules

- At most **8 rows** are shown.
- Buckets with fewer than 5 effective samples are hidden; if nothing qualifies, the panel shows `No data yet / Need ≥5 signals`.
- Negative-edge buckets stay visible and naturally sink to the bottom.

#### Other stats modes

`Stats Mode = Signal Type` aggregates by signal type only (labels like the alert icons, 8 buckets); `Grade` aggregates by quality grade only (`[A]📈`-style labels, 8 buckets). Both use the same header and the same gate; `Ranking` is the cross product and the recommended default.

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

### Quality grades

Every signal carries a grade from a multi-factor score:

| Grade | Score | Interpretation |
|-------|-------|----------------|
| [A] | ≥80 | High quality, tradable |
| [B] | 60–79 | Good, tradable |
| [C] | 40–59 | Mixed, trade cautiously |
| [D] | <40 | Low quality, usually skip |

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
| ✓ | Passed the stats filter | Appears in dashboard signal rows and alert messages |
| ⚠️ | Failed the stats filter but still shown | Common in `Alert Only` or `Soft` mode |
| 🚫 | Signal exists but is hidden | Caused by Smart normal-signal hiding, trend protection, or `Hard` filtering |
| (none) | Not a trigger bar, or stats filtering disabled | E.g. persistent state text such as `🔥持续` |

> Alerts fire only for signals that pass the stats filter — alert text shows `✓` or no mark, never `⚠️`.

---

## Alerts

One aggregated alert covers all signal types. Create it once with **Any alert() function call** and every gate-passing signal arrives in a single message stream.

### Message anatomy

```text
AAPL: 🟢 BUY → 🌟MTF共振 | RSI:25.3 Z:-2.1σ (≈P2) [A]✓
AAPL: 🔴 SELL → ❄️极端 | RSI:78.5 Z:2.3σ (≈P98) [B]✓
```

- **Direction**: `🟢 BUY` / `🔴 SELL`
- **Signal icon**: `🌟MTF共振` (resonance), `💎背离` (divergence), `🔥极端` / `❄️极端` (extreme), `⬆️超卖` / `⬇️超买` (normal)
- **Optional suffixes**: `✓确认` (RSI pivot confirmation), `↩反转` (Z-Score crossing back out of the extreme zone), `⚡实时背离` (realtime divergence forming)
- **Context**: RSI value, Z-Score, approximate percentile, quality grade, filter mark

With `Include Risk Hints in Alerts` enabled:

```text
AAPL: 🟢 BUY → 🔥极端 ✓确认 ⚡实时背离 | RSI:25.3 Z:-2.1σ (≈P2) [A]✓ | SL:-1.5% TP:+3.0%
```

### Risk hints

Stops are based on **ATR(14)**, scaled by signal grade:

| Grade | Stop distance |
|-------|---------------|
| A | 2.5 × ATR |
| B | 2.0 × ATR |
| C | 1.5 × ATR |
| D | 1.2 × ATR |

Take-profit = stop distance × `Risk-Reward Ratio` (default 2.0, range 1.5–3.0). For sell signals the signs flip (`SL:+x% TP:-y%`).

### Timing

`Alert on Bar Close` (default off) delays alerts to bar confirmation: no intrabar signals that flash and vanish before the close (repaint), at the cost of later delivery. Off keeps immediate intrabar behavior.

### What gets through

Alerts fire only for signals that pass the stats gate, in **every** filter mode — `Alert Only` filters nothing on the chart, but the alert stream is always gated. Same-bar deduplication only lets a higher-priority upgrade re-alert.

---

## The Stats Engine & Gate

This is what makes the `✓` mark mean something. In plain terms:

**What gets recorded.** Every signal occurrence is scored by its forward return — what price did `Forward Bars` later (default 20). Buy samples record the rise; sell samples record the *decline*, so positive always means "the signal was right". Samples land in buckets according to `Stats Mode`: by signal type, by grade, or by the full type × grade × direction cross (`Ranking`). Two unconditional baseline buckets (buy/sell) record the forward return of *every* bar, giving each direction its "random entry" benchmark — both a baseline **win rate** and a baseline **average return** (the drift).

**Bayesian adjustment.** Raw win rates from a handful of samples lie. Each bucket's win rate is shrunk toward a prior: `adjusted = prior + confidence × (raw − prior)` with `confidence = min(1, effective_samples / 20)`. In `Edge vs Baseline` mode the prior is the bucket's own direction baseline; in `Absolute (Legacy)` mode it is 50%. Buckets with fewer than 5 lifetime samples report no adjusted rate at all.

**Payoff edge.** The same anti-overclaim treatment applied to returns instead of win rates: `payoff edge = confidence × (bucket average forward return − direction baseline average return)`, with the same confidence factor and the same "no value below 5 lifetime samples" rule as the adjusted win rate. Subtracting the direction baseline removes the asset's drift, so what remains is the **timing contribution** of the signal in forward-window % terms; the shrinkage drags small or stale buckets toward zero edge so they can't brag.

**Time decay.** `Stats Half-Life Bars` (default 1500, `0` = off) exponentially fades sample weight with age — 1500 bars is roughly 6 years on a daily chart or 9 months on 4H, covering a full cycle while letting old regimes fade. Decay only affects the *effective* count (and therefore confidence); the `Min Samples` gate always uses the undecayed lifetime count, so rare signal buckets are not permanently locked out.

**Independent sampling.** `Independent Samples` (default on) makes each bucket wait at least `Forward Bars` between recorded samples, so overlapping forward-return windows can't inflate the sample count. Off restores the legacy overlapping behavior.

**The gate.** A signal passes when both hold:

1. Lifetime samples ≥ `Min Samples` (default 20) — required in **every** mode and combination; nothing below substitutes for sample sufficiency — and
2. The quality criterion.

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

> **Restoring v7.4 gate behavior**: set `Payoff Gate = Off`. The gate decision is then bit-identical to v7.4 (the ranking panel's payoff numbers and the "No timing edge" hint are display-only and remain visible in Edge mode).
>
> **Restoring v7.3 stats behavior**: set `Stats Half-Life Bars = 0`, turn `Independent Samples` **off**, and set `Gate Mode = Absolute (Legacy)` (which by itself deactivates the payoff path, whatever `Payoff Gate` says). This restores the legacy stats-engine arithmetic exactly. Two v7.4 signal-level changes have **no revert switch** — the lookback spread-factor hysteresis band (engages below a spread of 18, releases above 22) and the cooldown stale-level reset — so the recorded signal stream, and therefore gate decisions, may still differ slightly from v7.3.

**Cooldown & upgrades.** High-priority signals (🌟/💎/🔥/❄️) use a 1-bar cooldown. Normal signals use `Cooldown Mode`: `Smart` (the default — 2–8 bars by volatility, shortened by one when the market is active) or `Fixed` (a fixed bar count, 5 by default). A higher-priority same-side signal bypasses cooldown — `⬆️ → 🔥 → 🌟` can fire on consecutive bars. The upgrade exemption only compares against a previous signal that is *still cooling down*; expired levels count as 0, so a normal signal can never use its own stale level to bypass its own cooldown.

---

## Backtesting with the Strategy Harness

### What it is — and is not

`adaptive_rsi_strategy_harness.pine` is a `strategy()` wrapper **generated from the production indicator** (by `tools/generate_strategy_harness.py` — never hand-edited), so the signal engine is identical. It answers one question: how does the v7.5 signal engine behave inside TradingView's Strategy Tester?

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

TradingView always shows `All`, `Long`, and `Short` columns. **Read `All` according to `Trade Side`**: with `Long Only` it is your long-only result; with `Short Only` your short-only result; with `Both` the combined result. The harness's `Tester` dashboard row repeats this rule.

The harness adds three rows to the dashboard:

- `Harness` — current `Trade Side` and `Backtest Mode`
- `Tester` — how to read `All`
- `Production Gate` — the actual stats bucket selected by `Stats Mode` for the active signal, with its sample count, average return, adjusted win rate and — in `Edge vs Baseline` mode — its shrunk payoff edge, e.g. `EXT[A](12) +2.8%|67%|+1.2%` in `Ranking` mode (`TYPE:EXT` in `Signal Type` mode, `GRADE[A]` in `Grade` mode; `Idle` when no signal is active; under `Absolute (Legacy)` the payoff suffix is omitted).

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
- **Percentile labels are approximations**: the Z-Score-to-percentile labels (such as `≈P2`) assume a normal distribution and are display approximations, not exact ranks.
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
