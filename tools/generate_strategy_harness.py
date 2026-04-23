#!/usr/bin/env python3
"""Generate the Pine strategy harness from the production indicator."""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "adaptive_rsi.pine"
DEFAULT_TARGET = ROOT / "adaptive_rsi_strategy_harness.pine"

HEADER_LINE = (
    "// Adaptive RSI Pro v7.3 - Restored v7.2 baseline + minimal correctness fixes\n"
)
HARNESS_HEADER_LINE = (
    "// Adaptive RSI Pro v7.3 Strategy Report - v7.2 baseline behavior + minimal correctness fixes\n"
)

INDICATOR_DECLARATION = (
    'indicator("Adaptive RSI Pro", shorttitle="ARSI Pro", overlay=false, precision=2, '
    "max_lines_count=100, max_labels_count=100, max_bars_back=4500)\n"
)
STRATEGY_DECLARATION = (
    'strategy("Adaptive RSI Pro Strategy Report", shorttitle="ARSI Pro STRAT", overlay=false, precision=2, '
    "max_lines_count=100, max_labels_count=100, max_bars_back=4500, pyramiding=0, "
    "commission_type=strategy.commission.percent, commission_value=0.05, slippage=2)\n"
)

STATS_INPUT_MARKER = (
    'stats_filter_mode = input.string("Alert Only", "Filter Mode / 过滤模式", '
    'options=["Alert Only", "Soft", "Hard"], group=grp_stats, tooltip="Alert Only: 仅过滤警报，图表显示所有信号\\n'
    'Soft: 低质量信号降级显示\\nHard: 完全隐藏低质量信号")\n'
)
HARNESS_INPUT_BLOCK = """
grp_harness = "═══ Strategy Report / 策略回测 ═══"
harness_trade_side = input.string("Long Only", "Trade Side / 交易方向", options=["Long Only", "Short Only", "Both"], group=grp_harness, tooltip="Long Only: 仅做多，卖出信号只平多\\nShort Only: 仅做空，买入信号只平空\\nBoth: 双向切换，买卖信号会反手")
harness_backtest_mode = input.string("Production", "Backtest Mode / 回测模式", options=["Baseline", "Production"], group=grp_harness, tooltip="Baseline: raw v7.2 signals, no stats filter\\nProduction: gate-passing production alert signals; not exact intrabar alert delivery\\nBaseline: 使用 7.2 原始信号，不加统计过滤\\nProduction: 使用通过正式警报 gate/过滤的信号，不精确模拟盘中 alert 投递")
"""

AUTO_VOL_MARKER = (
    'auto_vol_type = avg_volatility > 6 ? "Crypto" : avg_volatility > 3 ? "High Vol" : '
    'avg_volatility > 1 ? "Normal" : "Low Vol"\n'
)
RISK_DIRECTION_BLOCK = """
strategy_allowed_direction = harness_trade_side == "Long Only" ? strategy.direction.long :
                             harness_trade_side == "Short Only" ? strategy.direction.short :
                             strategy.direction.all
strategy.risk.allow_entry_in(strategy_allowed_direction)
bool harness_use_production = harness_backtest_mode == "Production"
"""

PRODUCTION_STATS_HELPERS = """f_get_signal_type_stats(_is_buy, _is_mtf, _is_div, _is_ext) =>
    SignalStats result = SignalStats.new()
    if _is_mtf
        result := _is_buy ? mtf_buy_stats : mtf_sell_stats
    else if _is_div
        result := _is_buy ? div_buy_stats : div_sell_stats
    else if _is_ext
        result := _is_buy ? ext_buy_stats : ext_sell_stats
    else
        result := _is_buy ? norm_buy_stats : norm_sell_stats
    result

f_get_grade_stats(_is_buy, _grade) =>
    SignalStats result = SignalStats.new()
    result := _is_buy ? (_grade == "A" ? grade_a_buy_stats : _grade == "B" ? grade_b_buy_stats : _grade == "C" ? grade_c_buy_stats : grade_d_buy_stats) :
                       (_grade == "A" ? grade_a_sell_stats : _grade == "B" ? grade_b_sell_stats : _grade == "C" ? grade_c_sell_stats : grade_d_sell_stats)
    result

f_get_filter_stats(_is_buy, _is_mtf, _is_div, _is_ext, _grade) =>
    SignalStats result = SignalStats.new()
    if stats_mode == "Signal Type"
        result := f_get_signal_type_stats(_is_buy, _is_mtf, _is_div, _is_ext)
    else if stats_mode == "Grade"
        result := f_get_grade_stats(_is_buy, _grade)
    else
        result := f_get_signal_stats(_is_buy, _is_mtf, _is_div, _is_ext, _grade)
    result
"""

HARNESS_STATS_HELPERS = """f_get_type_stats(_is_buy, _is_mtf, _is_div, _is_ext) =>
    SignalStats result = SignalStats.new()
    if _is_mtf
        result := _is_buy ? mtf_buy_stats : mtf_sell_stats
    else if _is_div
        result := _is_buy ? div_buy_stats : div_sell_stats
    else if _is_ext
        result := _is_buy ? ext_buy_stats : ext_sell_stats
    else
        result := _is_buy ? norm_buy_stats : norm_sell_stats
    result

f_get_grade_stats(_is_buy, _grade) =>
    SignalStats result = SignalStats.new()
    if _grade == "A"
        result := _is_buy ? grade_a_buy_stats : grade_a_sell_stats
    else if _grade == "B"
        result := _is_buy ? grade_b_buy_stats : grade_b_sell_stats
    else if _grade == "C"
        result := _is_buy ? grade_c_buy_stats : grade_c_sell_stats
    else
        result := _is_buy ? grade_d_buy_stats : grade_d_sell_stats
    result

f_get_filter_stats(_is_buy, _is_mtf, _is_div, _is_ext, _grade) =>
    SignalStats result = SignalStats.new()
    if stats_mode == "Signal Type"
        result := f_get_type_stats(_is_buy, _is_mtf, _is_div, _is_ext)
    else if stats_mode == "Grade"
        result := f_get_grade_stats(_is_buy, _grade)
    else
        result := f_get_signal_stats(_is_buy, _is_mtf, _is_div, _is_ext, _grade)
    result

f_get_signal_type_label(_is_mtf, _is_div, _is_ext) =>
    _is_mtf ? "MTF" : _is_div ? "DIV" : _is_ext ? "EXT" : "NORM"

f_get_filter_source_label(_is_mtf, _is_div, _is_ext, _grade) =>
    _type_label = f_get_signal_type_label(_is_mtf, _is_div, _is_ext)
    stats_mode == "Signal Type" ? str.format("TYPE:{0}", _type_label) :
     stats_mode == "Grade" ? str.format("GRADE[{0}]", _grade) :
     str.format("{0}[{1}]", _type_label, _grade)
"""

PRODUCTION_ARRAY_STATS_HELPERS = """f_get_signal_stats(_is_buy, _is_mtf, _is_div, _is_ext, _grade) =>
    array.get(ranking_stats, f_ranking_bucket_index(_is_buy, f_signal_kind_index(_is_mtf, _is_div, _is_ext), _grade))

f_get_signal_type_stats(_is_buy, _is_mtf, _is_div, _is_ext) =>
    array.get(signal_type_stats, f_signal_type_bucket_index(_is_buy, f_signal_kind_index(_is_mtf, _is_div, _is_ext)))

f_get_grade_stats(_is_buy, _grade) =>
    array.get(grade_stats, f_grade_bucket_index(_is_buy, _grade))

f_get_filter_stats(_is_buy, _is_mtf, _is_div, _is_ext, _grade) =>
    if stats_mode == "Signal Type"
        f_get_signal_type_stats(_is_buy, _is_mtf, _is_div, _is_ext)
    else if stats_mode == "Grade"
        f_get_grade_stats(_is_buy, _grade)
    else
        f_get_signal_stats(_is_buy, _is_mtf, _is_div, _is_ext, _grade)
"""

HARNESS_ARRAY_STATS_HELPERS = """f_get_signal_stats(_is_buy, _is_mtf, _is_div, _is_ext, _grade) =>
    array.get(ranking_stats, f_ranking_bucket_index(_is_buy, f_signal_kind_index(_is_mtf, _is_div, _is_ext), _grade))

f_get_type_stats(_is_buy, _is_mtf, _is_div, _is_ext) =>
    array.get(signal_type_stats, f_signal_type_bucket_index(_is_buy, f_signal_kind_index(_is_mtf, _is_div, _is_ext)))

f_get_grade_stats(_is_buy, _grade) =>
    array.get(grade_stats, f_grade_bucket_index(_is_buy, _grade))

f_get_filter_stats(_is_buy, _is_mtf, _is_div, _is_ext, _grade) =>
    if stats_mode == "Signal Type"
        f_get_type_stats(_is_buy, _is_mtf, _is_div, _is_ext)
    else if stats_mode == "Grade"
        f_get_grade_stats(_is_buy, _grade)
    else
        f_get_signal_stats(_is_buy, _is_mtf, _is_div, _is_ext, _grade)

f_get_signal_type_label(_is_mtf, _is_div, _is_ext) =>
    _is_mtf ? "MTF" : _is_div ? "DIV" : _is_ext ? "EXT" : "NORM"

f_get_filter_source_label(_is_mtf, _is_div, _is_ext, _grade) =>
    _type_label = f_get_signal_type_label(_is_mtf, _is_div, _is_ext)
    stats_mode == "Signal Type" ? str.format("TYPE:{0}", _type_label) :
     stats_mode == "Grade" ? str.format("GRADE[{0}]", _grade) :
     str.format("{0}[{1}]", _type_label, _grade)
"""

STATUS_TEXT_MARKER = """f_status_text(_status) =>
    _status == 1 ? "🟢" : _status == -1 ? "🔴" : "⚪"

"""
HARNESS_GATE_HELPER = """f_harness_gate_snapshot() =>
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
        _count := _stats.count
        _avg := _stats.get_avg()
        _adj := nz(_stats.get_adjusted_winrate(), 0.0)

    [_source, _count, _avg, _adj]

"""

FULL_DASHBOARD_STATUS_MARKER = """            weekly_rsi_display = na(weekly_rsi) ? "W.RSI:--" : str.format("W.RSI:{0,number,#}", weekly_rsi)
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

BUY_ALERT_LEVEL_BLOCK = """    prev_buy_level = f_signal_level(alert_buy_mtf[1], alert_buy_div[1], alert_buy_ext[1], show_normal_signals[1] and alert_buy_norm[1])
    should_alert_buy = alert_has_buy and current_buy_level > prev_buy_level and current_buy_level > buy_alert_level_sent
"""
HARNESS_BUY_ALERT_LEVEL_BLOCK = """    previous_buy_level = f_signal_level(alert_buy_mtf[1], alert_buy_div[1], alert_buy_ext[1], show_normal_signals[1] and alert_buy_norm[1])
    should_alert_buy = alert_has_buy and current_buy_level > previous_buy_level and current_buy_level > buy_alert_level_sent
"""

SELL_ALERT_LEVEL_BLOCK = """    prev_sell_level = f_signal_level(alert_sell_mtf[1], alert_sell_div[1], alert_sell_ext[1], show_normal_signals[1] and alert_sell_norm[1])
    should_alert_sell = alert_has_sell and current_sell_level > prev_sell_level and current_sell_level > sell_alert_level_sent
"""
HARNESS_SELL_ALERT_LEVEL_BLOCK = """    previous_sell_level = f_signal_level(alert_sell_mtf[1], alert_sell_div[1], alert_sell_ext[1], show_normal_signals[1] and alert_sell_norm[1])
    should_alert_sell = alert_has_sell and current_sell_level > previous_sell_level and current_sell_level > sell_alert_level_sent
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

if strategy_signal_dir == 1
    if strategy.position_size < 0
        strategy.close("Short")
    if allow_long_entries and strategy.position_size <= 0
        strategy.entry("Long", strategy.long)

if strategy_signal_dir == -1
    if strategy.position_size > 0
        strategy.close("Long")
    if allow_short_entries and strategy.position_size >= 0
        strategy.entry("Short", strategy.short)
"""


class GenerationError(RuntimeError):
    """Raised when a required source marker is missing or ambiguous."""


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise GenerationError(f"{label}: expected marker exactly once, found {count}")
    return text.replace(old, new, 1)


def insert_after(text: str, marker: str, insertion: str, label: str) -> str:
    return replace_once(text, marker, marker + insertion, label)


def insert_before(text: str, marker: str, insertion: str, label: str) -> str:
    return replace_once(text, marker, insertion + marker, label)


def generate(source_text: str) -> str:
    text = source_text.replace("\r\n", "\n").replace("\r", "\n")

    text = replace_once(text, HEADER_LINE, HARNESS_HEADER_LINE, "header")
    text = replace_once(text, INDICATOR_DECLARATION, STRATEGY_DECLARATION, "declaration")
    text = insert_after(text, STATS_INPUT_MARKER, HARNESS_INPUT_BLOCK, "strategy report inputs")
    text = insert_after(text, AUTO_VOL_MARKER, RISK_DIRECTION_BLOCK, "strategy risk direction")

    old_helper_count = text.count(PRODUCTION_STATS_HELPERS)
    array_helper_count = text.count(PRODUCTION_ARRAY_STATS_HELPERS)
    if old_helper_count == 1 and array_helper_count == 0:
        text = replace_once(text, PRODUCTION_STATS_HELPERS, HARNESS_STATS_HELPERS, "stats helper block")
    elif old_helper_count == 0 and array_helper_count == 1:
        text = replace_once(
            text,
            PRODUCTION_ARRAY_STATS_HELPERS,
            HARNESS_ARRAY_STATS_HELPERS,
            "array stats helper block",
        )
    else:
        raise GenerationError(
            "stats helper block: expected exactly one supported helper variant "
            f"(old={old_helper_count}, array={array_helper_count})"
        )
    text = replace_once(
        text,
        "// 计算各信号的过滤状态\n",
        "// 根据 stats_mode 选择实际用于生产过滤的统计桶\n",
        "stats filter comment",
    )

    text = insert_after(text, STATUS_TEXT_MARKER, HARNESS_GATE_HELPER, "harness gate helper")
    text = replace_once(
        text,
        "    full_rows = 8 + (enable_mtf ? 2 : 0) + (enable_divergence ? 1 : 0) + (enable_stats ? 9 : 0)\n",
        "    full_rows = 11 + (enable_mtf ? 2 : 0) + (enable_divergence ? 1 : 0) + (enable_stats ? 9 : 0)\n",
        "dashboard row count",
    )
    text = replace_once(
        text,
        "    var table dashboard = table.new(position.top_right, 2, 20,\n",
        "    var table dashboard = table.new(position.top_right, 2, 24,\n",
        "dashboard table height",
    )
    text = replace_once(
        text,
        "    if barstate.islast\n",
        "    if barstate.islastconfirmedhistory or barstate.isrealtime\n",
        "dashboard refresh condition",
    )
    text = replace_once(
        text,
        "        table.clear(dashboard, 0, 0, 1, 19)\n",
        "        table.clear(dashboard, 0, 0, 1, 23)\n",
        "dashboard clear range",
    )
    text = insert_before(
        text,
        FULL_DASHBOARD_STATUS_MARKER,
        HARNESS_DASHBOARD_ROWS,
        "strategy report dashboard rows",
    )

    text = replace_once(text, BUY_ALERT_LEVEL_BLOCK, HARNESS_BUY_ALERT_LEVEL_BLOCK, "buy alert level variable")
    text = replace_once(text, SELL_ALERT_LEVEL_BLOCK, HARNESS_SELL_ALERT_LEVEL_BLOCK, "sell alert level variable")

    strategy_marker_count = text.count("// STRATEGY REPORT EXECUTION")
    if strategy_marker_count != 0:
        raise GenerationError(
            f"strategy execution append: expected generated source to have no execution block, found {strategy_marker_count}"
        )

    text = text.rstrip("\n") + "\n\n" + STRATEGY_EXECUTION_BLOCK
    if not text.endswith("\n"):
        text += "\n"
    return text


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
