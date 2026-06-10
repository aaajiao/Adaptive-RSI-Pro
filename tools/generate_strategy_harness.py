#!/usr/bin/env python3
"""Generate the Pine strategy harness from the production indicator.

Design
------
The generator is anchor-based: ``adaptive_rsi.pine`` carries short
``// @harness: <name>`` comment lines at every point where harness-only code
is inserted. The generator never matches long verbatim copies of production
code, so cosmetic edits to tooltips, alert lines, helper bodies, etc. cannot
break generation. The only production text the generator keys on is:

* line 1 (the header comment, replaced with the harness header),
* the ``indicator(...)`` declaration line (rewritten into ``strategy(...)``
  while passing the shared parameters through),
* four single-line dashboard sizing/refresh tweaks matched with narrow
  regexes (numeric values are offset, not hardcoded, so production changes
  flow through).

Everything inserted into the harness is harness-owned text defined below.
Anchor comments flow through into the generated file unchanged.

Known anchors (each must appear exactly once in the source):

==================  =========================================================
``inputs``          ``Trade Side`` / ``Backtest Mode`` / risk-exit inputs
                    appended after the stats filter inputs.
``risk-direction``  ``strategy.risk.allow_entry_in`` wiring + production-mode
                    flag.
``stats-helpers``   harness-only stats label helpers (production stats
                    helpers flow through verbatim).
``gate-helper``     ``f_harness_gate_snapshot()`` used by the dashboard rows.
``dashboard-rows``  ``Harness`` / ``Tester`` / ``Production Gate`` rows.
==================  =========================================================
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "adaptive_rsi.pine"
DEFAULT_TARGET = ROOT / "adaptive_rsi_strategy_harness.pine"


class GenerationError(RuntimeError):
    """Raised when a required anchor/pattern is missing or ambiguous."""


# ────────────────────────────────────────
# Anchors
# ────────────────────────────────────────

ANCHOR_INPUTS = "inputs"
ANCHOR_RISK_DIRECTION = "risk-direction"
ANCHOR_STATS_HELPERS = "stats-helpers"
ANCHOR_GATE_HELPER = "gate-helper"
ANCHOR_DASHBOARD_ROWS = "dashboard-rows"

KNOWN_ANCHORS = (
    ANCHOR_INPUTS,
    ANCHOR_RISK_DIRECTION,
    ANCHOR_STATS_HELPERS,
    ANCHOR_GATE_HELPER,
    ANCHOR_DASHBOARD_ROWS,
)

ANCHOR_LINE_RE = re.compile(
    r"^[ \t]*// @harness: (?P<name>[A-Za-z0-9_-]+)[ \t]*$", re.MULTILINE
)
ANCHOR_MENTION_RE = re.compile(r"^.*@harness.*$", re.MULTILINE)


# ────────────────────────────────────────
# Header / declaration
# ────────────────────────────────────────

HARNESS_HEADER = (
    "// Adaptive RSI Pro v7.4 Strategy Report - v7.2 baseline behavior + stats engine upgrades & toolchain hardening"
)

INDICATOR_DECLARATION_RE = re.compile(
    r'^indicator\(\s*"(?P<title>[^"]+)"\s*,\s*shorttitle\s*=\s*"(?P<short>[^"]+)"\s*,\s*(?P<rest>.+)\)[ \t]*$',
    re.MULTILINE,
)
STRATEGY_TITLE_SUFFIX = " Strategy Report"
STRATEGY_SHORTTITLE_SUFFIX = " STRAT"
STRATEGY_EXTRA_ARGS = (
    "pyramiding=0, commission_type=strategy.commission.percent, "
    "commission_value=0.05, slippage=2"
)


# ────────────────────────────────────────
# Harness-owned insertion blocks
# ────────────────────────────────────────

HARNESS_INPUT_BLOCK = """
grp_harness = "═══ Strategy Report / 策略回测 ═══"
harness_trade_side = input.string("Long Only", "Trade Side / 交易方向", options=["Long Only", "Short Only", "Both"], group=grp_harness, tooltip="Long Only: 仅做多，卖出信号只平多\\nShort Only: 仅做空，买入信号只平空\\nBoth: 双向切换，买卖信号会反手")
harness_backtest_mode = input.string("Production", "Backtest Mode / 回测模式", options=["Baseline", "Production"], group=grp_harness, tooltip="Baseline: raw v7.2 signals, no stats filter\\nProduction: gate-passing production alert signals; not exact intrabar alert delivery\\nBaseline: 使用 7.2 原始信号，不加统计过滤\\nProduction: 使用通过正式警报 gate/过滤的信号，不精确模拟盘中 alert 投递")
harness_use_risk_exits = input.bool(false, "Use ATR SL/TP Exits / 启用ATR止损止盈", group=grp_harness, tooltip="On: trades exit via the same ATR-based SL/TP prices the alerts advertise, snapshotted at entry\\nOff: trades exit only on opposite signals (legacy harness behavior)\\n开启：按警报展示的ATR止损/止盈价格退出（入场时快照价格）\\n关闭：仅按反向信号平仓（原有回测行为）")
harness_max_holding_bars = input.int(0, "Max Holding Bars / 最大持仓K线数", minval=0, group=grp_harness, tooltip="0 = off\\n>0: force-close the position after holding N bars (Time Exit)\\n0 = 关闭\\n大于0：持仓达到N根K线后强制平仓（时间退出）")
"""

RISK_DIRECTION_BLOCK = """
strategy_allowed_direction = harness_trade_side == "Long Only" ? strategy.direction.long :
                             harness_trade_side == "Short Only" ? strategy.direction.short :
                             strategy.direction.all
strategy.risk.allow_entry_in(strategy_allowed_direction)
bool harness_use_production = harness_backtest_mode == "Production"
"""

STATS_LABEL_HELPERS = """
f_get_signal_type_label(_is_mtf, _is_div, _is_ext) =>
    _is_mtf ? "MTF" : _is_div ? "DIV" : _is_ext ? "EXT" : "NORM"

f_get_filter_source_label(_is_mtf, _is_div, _is_ext, _grade) =>
    _type_label = f_get_signal_type_label(_is_mtf, _is_div, _is_ext)
    stats_mode == "Signal Type" ? str.format("TYPE:{0}", _type_label) :
     stats_mode == "Grade" ? str.format("GRADE[{0}]", _grade) :
     str.format("{0}[{1}]", _type_label, _grade)
"""

HARNESS_GATE_HELPER = """
f_harness_gate_snapshot() =>
    string _source = "Idle"
    int _count = 0
    float _avg = 0.0
    float _adj = 0.0
    bool _use_buy = harness_trade_side == "Long Only" ? true : harness_trade_side == "Short Only" ? false : signal_direction != -1
    SignalStats _stats = SignalStats.new()

    if _use_buy
        if sig_buy_mtf
            _stats := f_get_filter_stats(true, true, false, false, buy_quality_grade)
            _source := f_get_filter_source_label(true, false, false, buy_quality_grade)
        else if sig_buy_div
            _stats := f_get_filter_stats(true, false, true, false, buy_quality_grade)
            _source := f_get_filter_source_label(false, true, false, buy_quality_grade)
        else if sig_buy_extreme
            _stats := f_get_filter_stats(true, false, false, true, buy_quality_grade)
            _source := f_get_filter_source_label(false, false, true, buy_quality_grade)
        else if sig_buy_normal
            _stats := f_get_filter_stats(true, false, false, false, buy_quality_grade)
            _source := f_get_filter_source_label(false, false, false, buy_quality_grade)
    else
        if sig_sell_mtf
            _stats := f_get_filter_stats(false, true, false, false, sell_quality_grade)
            _source := f_get_filter_source_label(true, false, false, sell_quality_grade)
        else if sig_sell_div
            _stats := f_get_filter_stats(false, false, true, false, sell_quality_grade)
            _source := f_get_filter_source_label(false, true, false, sell_quality_grade)
        else if sig_sell_extreme
            _stats := f_get_filter_stats(false, false, false, true, sell_quality_grade)
            _source := f_get_filter_source_label(false, false, true, sell_quality_grade)
        else if sig_sell_normal
            _stats := f_get_filter_stats(false, false, false, false, sell_quality_grade)
            _source := f_get_filter_source_label(false, false, false, sell_quality_grade)

    if _source != "Idle"
        _count := math.round(_stats.get_count())
        _avg := _stats.get_avg()
        _adj := nz(_stats.get_adjusted_winrate_vs(f_stats_display_prior(_use_buy)), 0.0)

    [_source, _count, _avg, _adj]
"""

HARNESS_DASHBOARD_ROWS = """            harness_side_display = harness_trade_side == "Long Only" ? "Long" : harness_trade_side == "Short Only" ? "Short" : "Both"
            harness_mode_display = harness_use_production ? "Production" : "Baseline"
            harness_tester_display = harness_trade_side == "Long Only" ? "Read All = Long" : harness_trade_side == "Short Only" ? "Read All = Short" : "Read All = Both"
            [harness_gate_source, harness_gate_count, harness_gate_avg, harness_gate_adj] = f_harness_gate_snapshot()
            harness_gate_display = harness_gate_source == "Idle" ? "Idle" : str.format("{0}({1}) {2,number,+#.1;-#.1}%|{3,number,#}%", harness_gate_source, harness_gate_count, harness_gate_avg, harness_gate_adj)

            table.cell(dashboard, 0, row, "Harness", text_color=color.gray, text_size=txt_size_body)
            table.cell(dashboard, 1, row, str.format("{0} | {1}", harness_side_display, harness_mode_display), text_color=color.white, text_size=txt_size_body)
            row += 1

            table.cell(dashboard, 0, row, "Tester", text_color=color.gray, text_size=txt_size_body)
            table.cell(dashboard, 1, row, harness_tester_display, text_color=color.white, text_size=txt_size_body)
            row += 1

            table.cell(dashboard, 0, row, "Production Gate", text_color=color.gray, text_size=txt_size_body)
            table.cell(dashboard, 1, row, harness_gate_display, text_color=color.white, text_size=txt_size_body)
            row += 1

"""

STRATEGY_EXECUTION_BLOCK = """// ────────────────────────────────────────
// STRATEGY REPORT EXECUTION
// ────────────────────────────────────────

raw_strategy_buy_signal = sig_buy_mtf or sig_buy_div or sig_buy_extreme or (show_normal_signals and sig_buy_normal)
raw_strategy_sell_signal = sig_sell_mtf or sig_sell_div or sig_sell_extreme or (show_normal_signals and sig_sell_normal)

production_strategy_buy_signal = alert_buy_mtf or alert_buy_div or alert_buy_ext or (show_normal_signals and alert_buy_norm)
production_strategy_sell_signal = alert_sell_mtf or alert_sell_div or alert_sell_ext or (show_normal_signals and alert_sell_norm)

strategy_buy_signal = harness_use_production ? production_strategy_buy_signal : raw_strategy_buy_signal
strategy_sell_signal = harness_use_production ? production_strategy_sell_signal : raw_strategy_sell_signal
strategy_signal_dir = strategy_buy_signal and not strategy_sell_signal ? 1 : strategy_sell_signal and not strategy_buy_signal ? -1 : 0

allow_long_entries = harness_trade_side == "Long Only" or harness_trade_side == "Both"
allow_short_entries = harness_trade_side == "Short Only" or harness_trade_side == "Both"

var float harness_long_sl_price = na
var float harness_long_tp_price = na
var float harness_short_sl_price = na
var float harness_short_tp_price = na

if strategy_signal_dir == 1
    if strategy.position_size < 0
        strategy.close("Short")
    if allow_long_entries and strategy.position_size <= 0
        strategy.entry("Long", strategy.long)
        harness_long_sl_price := buy_sl_price
        harness_long_tp_price := buy_tp_price

if strategy_signal_dir == -1
    if strategy.position_size > 0
        strategy.close("Long")
    if allow_short_entries and strategy.position_size >= 0
        strategy.entry("Short", strategy.short)
        harness_short_sl_price := sell_sl_price
        harness_short_tp_price := sell_tp_price

if harness_use_risk_exits
    if strategy.position_size > 0 and (not na(harness_long_sl_price) or not na(harness_long_tp_price))
        strategy.exit("Long Exit", from_entry="Long", stop=harness_long_sl_price, limit=harness_long_tp_price, comment="ATR Exit")
    if strategy.position_size < 0 and (not na(harness_short_sl_price) or not na(harness_short_tp_price))
        strategy.exit("Short Exit", from_entry="Short", stop=harness_short_sl_price, limit=harness_short_tp_price, comment="ATR Exit")

if harness_max_holding_bars > 0 and strategy.opentrades > 0
    if bar_index - strategy.opentrades.entry_bar_index(strategy.opentrades - 1) >= harness_max_holding_bars
        strategy.close(strategy.position_size > 0 ? "Long" : "Short", comment="Time Exit")
"""

STRATEGY_EXECUTION_SENTINEL = "// STRATEGY REPORT EXECUTION"


# ────────────────────────────────────────
# Dashboard sizing/refresh tweaks (narrow single-line regexes)
# ────────────────────────────────────────

# The harness adds three dashboard rows; table capacity gets one extra row of
# headroom on top of that (production: 20-row table cleared as 0..19).
HARNESS_EXTRA_ROWS = 3
HARNESS_TABLE_ROW_OFFSET = 4

FULL_ROWS_RE = re.compile(
    r"^(?P<prefix>[ \t]*full_rows = )(?P<base>\d+)(?P<rest> \+ .*)$", re.MULTILINE
)
DASHBOARD_TABLE_RE = re.compile(
    r"^(?P<prefix>[ \t]*var table dashboard = table\.new\(position\.top_right, 2, )(?P<rows>\d+)(?P<rest>,.*)$",
    re.MULTILINE,
)
DASHBOARD_CLEAR_RE = re.compile(
    r"^(?P<prefix>[ \t]*table\.clear\(dashboard, 0, 0, 1, )(?P<rows>\d+)(?P<rest>\).*)$",
    re.MULTILINE,
)
DASHBOARD_REFRESH_RE = re.compile(
    r"^(?P<indent>[ \t]*)if barstate\.islast$", re.MULTILINE
)
DASHBOARD_REFRESH_REPLACEMENT = "if barstate.islastconfirmedhistory or barstate.isrealtime"


# ────────────────────────────────────────
# Engine
# ────────────────────────────────────────


def substitute_once(
    text: str, pattern: re.Pattern[str], repl: Callable[[re.Match[str]], str], label: str
) -> str:
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise GenerationError(
            f"{label}: expected exactly one match, found {len(matches)}"
        )
    match = matches[0]
    return text[: match.start()] + repl(match) + text[match.end() :]


def validate_anchors(text: str) -> None:
    found: dict[str, int] = {}
    for mention in ANCHOR_MENTION_RE.finditer(text):
        line = mention.group(0)
        anchor = ANCHOR_LINE_RE.match(line)
        if anchor is None:
            raise GenerationError(f"malformed @harness anchor line: {line.strip()!r}")
        name = anchor.group("name")
        if name not in KNOWN_ANCHORS:
            raise GenerationError(f"unknown @harness anchor: {name!r}")
        found[name] = found.get(name, 0) + 1

    for name in KNOWN_ANCHORS:
        count = found.get(name, 0)
        if count != 1:
            raise GenerationError(
                f"anchor {name!r}: expected exactly once, found {count}"
            )


def insert_after_anchor(text: str, name: str, insertion: str) -> str:
    pattern = re.compile(
        rf"^[ \t]*// @harness: {re.escape(name)}[ \t]*\n", re.MULTILINE
    )
    return substitute_once(
        text, pattern, lambda m: m.group(0) + insertion, f"anchor {name!r}"
    )


def replace_header(text: str) -> str:
    newline_index = text.find("\n")
    first_line = text[:newline_index] if newline_index != -1 else text
    if not first_line.startswith("//"):
        raise GenerationError("header: line 1 must be a // comment")
    if newline_index == -1:
        raise GenerationError("header: source has a single line")
    return HARNESS_HEADER + text[newline_index:]


def replace_declaration(text: str) -> str:
    def build(match: re.Match[str]) -> str:
        return (
            f'strategy("{match.group("title")}{STRATEGY_TITLE_SUFFIX}", '
            f'shorttitle="{match.group("short")}{STRATEGY_SHORTTITLE_SUFFIX}", '
            f'{match.group("rest")}, {STRATEGY_EXTRA_ARGS})'
        )

    return substitute_once(text, INDICATOR_DECLARATION_RE, build, "indicator declaration")


def apply_dashboard_tweaks(text: str) -> str:
    text = substitute_once(
        text,
        FULL_ROWS_RE,
        lambda m: f"{m.group('prefix')}{int(m.group('base')) + HARNESS_EXTRA_ROWS}{m.group('rest')}",
        "dashboard row count",
    )
    text = substitute_once(
        text,
        DASHBOARD_TABLE_RE,
        lambda m: f"{m.group('prefix')}{int(m.group('rows')) + HARNESS_TABLE_ROW_OFFSET}{m.group('rest')}",
        "dashboard table height",
    )
    text = substitute_once(
        text,
        DASHBOARD_REFRESH_RE,
        lambda m: f"{m.group('indent')}{DASHBOARD_REFRESH_REPLACEMENT}",
        "dashboard refresh condition",
    )
    text = substitute_once(
        text,
        DASHBOARD_CLEAR_RE,
        lambda m: f"{m.group('prefix')}{int(m.group('rows')) + HARNESS_TABLE_ROW_OFFSET}{m.group('rest')}",
        "dashboard clear range",
    )
    return text


def append_execution_block(text: str) -> str:
    if STRATEGY_EXECUTION_SENTINEL in text:
        raise GenerationError(
            "strategy execution append: source already contains an execution block"
        )
    return text.rstrip("\n") + "\n\n" + STRATEGY_EXECUTION_BLOCK


def generate(source_text: str) -> str:
    text = source_text.replace("\r\n", "\n").replace("\r", "\n")

    validate_anchors(text)

    text = replace_header(text)
    text = replace_declaration(text)

    text = insert_after_anchor(text, ANCHOR_INPUTS, HARNESS_INPUT_BLOCK)
    text = insert_after_anchor(text, ANCHOR_RISK_DIRECTION, RISK_DIRECTION_BLOCK)
    text = insert_after_anchor(text, ANCHOR_STATS_HELPERS, STATS_LABEL_HELPERS)
    text = insert_after_anchor(text, ANCHOR_GATE_HELPER, HARNESS_GATE_HELPER)
    text = insert_after_anchor(text, ANCHOR_DASHBOARD_ROWS, HARNESS_DASHBOARD_ROWS)

    text = apply_dashboard_tweaks(text)
    text = append_execution_block(text)

    if not text.endswith("\n"):
        text += "\n"
    return text


# ────────────────────────────────────────
# CLI
# ────────────────────────────────────────


def unified_diff(expected: str, actual: str, source_path: Path, target_path: Path) -> str:
    return "".join(
        difflib.unified_diff(
            actual.splitlines(keepends=True),
            expected.splitlines(keepends=True),
            fromfile=str(target_path),
            tofile=f"generated from {source_path}",
        )
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate adaptive_rsi_strategy_harness.pine from adaptive_rsi.pine."
    )
    parser.add_argument("--check", action="store_true", help="exit nonzero if the generated harness differs")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="production Pine source path")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET, help="strategy harness path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        source_text = args.source.read_text(encoding="utf-8")
        generated = generate(source_text)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except GenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.check:
        try:
            target_text = args.target.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

        if target_text != generated:
            print(unified_diff(generated, target_text, args.source, args.target), end="")
            return 1
        print(f"{args.target} is up to date")
        return 0

    current = args.target.read_text(encoding="utf-8") if args.target.exists() else None
    if current == generated:
        print(f"{args.target} is already up to date")
    else:
        args.target.write_text(generated, encoding="utf-8")
        print(f"wrote {args.target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
