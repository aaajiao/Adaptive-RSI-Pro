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
``dashboard-rows``  readable ``Backtest`` / ``Tester View`` / ``Strategy Stats`` rows.
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
    "// Adaptive RSI Pro v7.7 Strategy Report - confirmed execution, independent exits and net closed-trade results"
)

INDICATOR_DECLARATION_RE = re.compile(
    r'^indicator\(\s*"(?P<title>[^"]+)"\s*,\s*shorttitle\s*=\s*"(?P<short>[^"]+)"\s*,\s*(?P<rest>.+)\)[ \t]*$',
    re.MULTILINE,
)
STRATEGY_TITLE_SUFFIX = " Strategy Report"
STRATEGY_SHORTTITLE_SUFFIX = " STRAT"
STRATEGY_EXTRA_ARGS = (
    "pyramiding=0, commission_type=strategy.commission.percent, "
    "commission_value=0.05, slippage=2, calc_on_every_tick=false, "
    "calc_on_order_fills=false, process_orders_on_close=false"
)


# ────────────────────────────────────────
# Harness-owned insertion blocks
# ────────────────────────────────────────

HARNESS_INPUT_BLOCK = """
grp_harness = "═══ Strategy Report / 策略回测 ═══"
harness_trade_side = input.string("Long Only", "Trade Side / 交易方向", options=["Long Only", "Short Only", "Both"], group=grp_harness, tooltip="Long Only: 仅做多，卖出信号只平多\\nShort Only: 仅做空，买入信号只平空\\nBoth: 双向切换，买卖信号会反手")
harness_backtest_mode = input.string("Production", "Backtest Mode / 回测模式", options=["Baseline", "Production"], group=grp_harness, tooltip="Baseline: raw v7.2 signals, no stats filter\\nProduction: gate-passing production alert signals; not exact intrabar alert delivery\\nBaseline: 使用 7.2 原始信号，不加统计过滤\\nProduction: 使用通过正式警报 gate/过滤的信号，不精确模拟盘中 alert 投递")
harness_exit_signal_policy = input.string("Raw", "Exit Signal Policy / 退出信号策略", options=["Raw", "Filtered (Legacy)"], group=grp_harness, tooltip="Raw: opposite exit candidates bypass entry trend/data/statistics/cooldown and weekly Smart visibility; percentile confirmation and Normal Off still apply\\nFiltered (Legacy): opposite signals use the selected Backtest Mode gate, as before\\nATR/time/date exits always remain independent of the entry gate\\nRaw：反向退出候选绕过入场趋势、数据、统计、冷却及周线Smart显示限制；仍尊重百分位确认与普通信号Off\\nFiltered (Legacy)：反向信号沿用所选回测模式的过滤结果\\nATR、时间和评估结束退出始终独立于入场门槛")
harness_use_risk_exits = input.bool(false, "Use ATR SL/TP Exits / 启用ATR止损止盈", group=grp_harness, tooltip="On: trades exit via the same ATR-based SL/TP prices the alerts advertise; prices are snapshotted at the signal bar's close (the entry order fills at the next bar's open)\\nOff: trades exit only on opposite signals (legacy harness behavior)\\n开启：按警报展示的ATR止损/止盈价格退出；价格在信号K线收盘时快照（入场单在下一根K线开盘成交）\\n关闭：仅按反向信号平仓（原有回测行为）")
harness_max_holding_bars = input.int(0, "Max Holding Bars / 最大持仓K线数", minval=0, group=grp_harness, tooltip="0 = off\\n>0: force-close the position after holding N bars (Time Exit)\\n0 = 关闭\\n大于0：持仓达到N根K线后强制平仓（时间退出）")
harness_use_date_range = input.bool(false, "Use Evaluation Dates / 启用评估日期", group=grp_harness, tooltip="Off: trade all loaded history after data warmup\\nOn: earlier bars train statistics but cannot open trades; entries need a bar opening at/after Start and closing before End\\nEnd requests liquidation at the first available bar close reaching End; market orders still fill at the next available open, including gaps\\n关闭：数据准备好后使用全部已加载历史\\n开启：开始前只积累统计；入场信号K线须在开始后开盘、结束前收盘\\n首次达到结束时间的可用K线收盘时请求平仓，仍在下一可用开盘成交，含跳空")
harness_start_time = input.time(1577836800000, "Evaluation Start / 评估开始", group=grp_harness)
harness_end_time = input.time(4102444800000, "Evaluation End / 评估结束", group=grp_harness)
"""

RISK_DIRECTION_BLOCK = """
strategy_allowed_direction = harness_trade_side == "Long Only" ? strategy.direction.long :
                             harness_trade_side == "Short Only" ? strategy.direction.short :
                             strategy.direction.all
strategy.risk.allow_entry_in(strategy_allowed_direction)
bool harness_use_production = harness_backtest_mode == "Production"
bool harness_dates_valid = not harness_use_date_range or harness_start_time < harness_end_time
bool harness_training = harness_use_date_range and time < harness_start_time
bool harness_evaluation_ended = harness_use_date_range and time_close >= harness_end_time
bool harness_in_evaluation = harness_dates_valid and (not harness_use_date_range or (time >= harness_start_time and time_close < harness_end_time))
"""

STATS_LABEL_HELPERS = """
f_get_signal_type_label(_is_mtf, _is_div, _is_ext) =>
    _is_mtf ? "MTF" : _is_div ? "DIV" : _is_ext ? "EXT" : "NORMAL"

// Raw Baseline and disabled production filters describe the bucket requested by
// Stats Mode. Only an active Production gate may resolve to an Adaptive parent.
// Raw Baseline 与关闭过滤的 Production 始终描述 Stats Mode 请求桶；只有启用中的
// Production gate 才可解析到 Adaptive 父级证据桶。
f_harness_get_requested_stats(_is_buy, _is_mtf, _is_div, _is_ext, _grade) =>
    if stats_mode == "Signal Type"
        f_get_signal_type_stats(_is_buy, _is_mtf, _is_div, _is_ext)
    else if stats_mode == "Grade"
        f_get_grade_stats(_is_buy, _grade)
    else
        f_get_signal_stats(_is_buy, _is_mtf, _is_div, _is_ext, _grade)

f_harness_get_requested_target(_is_buy, _is_mtf, _is_div, _is_ext, _grade) =>
    if stats_mode == "Signal Type"
        f_get_signal_type_target(_is_buy, _is_mtf, _is_div, _is_ext)
    else if stats_mode == "Grade"
        f_get_grade_target(_is_buy, _grade)
    else
        f_get_signal_target(_is_buy, _is_mtf, _is_div, _is_ext, _grade)

f_get_filter_source_label(_is_mtf, _is_div, _is_ext, _grade, _is_buy, _evidence_source) =>
    _type_label = f_get_signal_type_label(_is_mtf, _is_div, _is_ext)
    _bucket_label = stats_mode == "Signal Type" ? _type_label :
                    stats_mode == "Grade" ? str.format("Score {0}", _grade) :
                    str.format("{0} [Score {1}]", _type_label, _grade)
    _display_bucket = _evidence_source == "Type fallback" ? str.format("{0} [Score {1}] → Type", _type_label, _grade) : _bucket_label
    str.format("{0} · {1}", _is_buy ? "BUY" : "SELL", _display_bucket)
"""

HARNESS_GATE_HELPER = """
// One action planner drives order placement and its explanation. Closing an
// existing position never depends on whether fresh entry evidence is available.
// 订单与说明共用同一个动作选择器；平仓不依赖新的入场证据是否已准备好。
f_harness_action(int _entry_dir, int _exit_dir, int _position_dir, bool _allow_long, bool _allow_short, bool _entry_ready, bool _date_exit, bool _time_exit) =>
    if _position_dir != 0 and _date_exit
        "Evaluation End"
    else if _position_dir != 0 and _time_exit
        "Time Exit"
    else if _entry_ready and _entry_dir == 1 and _allow_long and _position_dir <= 0
        "Long"
    else if _entry_ready and _entry_dir == -1 and _allow_short and _position_dir >= 0
        "Short"
    else if _position_dir > 0 and _exit_dir == -1
        "Close Long"
    else if _position_dir < 0 and _exit_dir == 1
        "Close Short"
    else
        "Idle"

raw_strategy_buy_signal = sig_buy_mtf or sig_buy_div or sig_buy_extreme or (show_normal_signals and sig_buy_normal)
raw_strategy_sell_signal = sig_sell_mtf or sig_sell_div or sig_sell_extreme or (show_normal_signals and sig_sell_normal)
production_strategy_buy_signal = alert_buy_mtf or alert_buy_div or alert_buy_ext or (show_normal_signals and alert_buy_norm)
production_strategy_sell_signal = alert_sell_mtf or alert_sell_div or alert_sell_ext or (show_normal_signals and alert_sell_norm)
strategy_buy_signal = harness_use_production ? production_strategy_buy_signal : raw_strategy_buy_signal
strategy_sell_signal = harness_use_production ? production_strategy_sell_signal : raw_strategy_sell_signal
strategy_signal_dir = strategy_buy_signal and not strategy_sell_signal ? 1 : strategy_sell_signal and not strategy_buy_signal ? -1 : 0

// This stream closes existing positions only. Entry candidates above retain all
// production protections; exit candidates do not inherit entry trend/data gates,
// sampling cooldown or weekly Smart hiding. Explicit user signal options remain.
// 此流仅用于已有持仓的退出；上方入场候选仍保留生产保护。退出不继承入场趋势/数据
// 门槛、采样冷却或周线Smart隐藏，但继续遵守显式百分位及普通信号Off设置。
harness_exit_buy_mtf = enable_mtf and oversold_resonance and raw_extreme_oversold and pct_allows_buy
harness_exit_buy_div = enable_divergence and bullish_divergence and was_extreme_oversold and not harness_exit_buy_mtf
harness_exit_buy_ext = raw_extreme_oversold and pct_allows_buy and not harness_exit_buy_mtf and not harness_exit_buy_div
harness_exit_buy_norm = normal_signal_mode != "Off" and raw_normal_oversold and not harness_exit_buy_mtf and not harness_exit_buy_div and not harness_exit_buy_ext
harness_exit_sell_mtf = enable_mtf and overbought_resonance and raw_extreme_overbought and pct_allows_sell
harness_exit_sell_div = enable_divergence and bearish_divergence and was_extreme_overbought and not harness_exit_sell_mtf
harness_exit_sell_ext = raw_extreme_overbought and pct_allows_sell and not harness_exit_sell_mtf and not harness_exit_sell_div
harness_exit_sell_norm = normal_signal_mode != "Off" and raw_normal_overbought and not harness_exit_sell_mtf and not harness_exit_sell_div and not harness_exit_sell_ext
harness_raw_exit_buy_signal = harness_exit_buy_mtf or harness_exit_buy_div or harness_exit_buy_ext or harness_exit_buy_norm
harness_raw_exit_sell_signal = harness_exit_sell_mtf or harness_exit_sell_div or harness_exit_sell_ext or harness_exit_sell_norm
harness_raw_exit_signal_dir = harness_raw_exit_buy_signal and not harness_raw_exit_sell_signal ? 1 : harness_raw_exit_sell_signal and not harness_raw_exit_buy_signal ? -1 : 0
harness_exit_signal_dir = harness_exit_signal_policy == "Raw" ? harness_raw_exit_signal_dir : strategy_signal_dir
allow_long_entries = harness_trade_side == "Long Only" or harness_trade_side == "Both"
allow_short_entries = harness_trade_side == "Short Only" or harness_trade_side == "Both"
harness_position_dir = strategy.position_size > 0 ? 1 : strategy.position_size < 0 ? -1 : 0
harness_entry_ready = barstate.isconfirmed and signal_data_ready and harness_in_evaluation
harness_time_exit_due = harness_max_holding_bars > 0 and strategy.opentrades > 0 and bar_index - strategy.opentrades.entry_bar_index(strategy.opentrades - 1) >= harness_max_holding_bars - 1
harness_action = f_harness_action(strategy_signal_dir, harness_exit_signal_dir, harness_position_dir, allow_long_entries, allow_short_entries, harness_entry_ready, harness_evaluation_ended, harness_time_exit_due)
harness_raw_exit = harness_exit_signal_policy == "Raw" and (harness_action == "Close Long" or harness_action == "Close Short")
harness_forced_exit = harness_action == "Evaluation End" or harness_action == "Time Exit"
harness_evaluation_state = not harness_dates_valid ? "INVALID DATES" : harness_training ? "TRAINING" : harness_evaluation_ended ? (strategy.position_size != 0 ? "ENDING · EXIT PENDING" : "ENDED") : not signal_data_ready ? "WARMUP · DATA" : harness_use_date_range ? "EVALUATION" : "ALL LOADED HISTORY"

f_harness_order_message(string _event, string _direction) =>
    str.format("ARSI_STRATEGY|v=7.7|event={0}|symbol={1}|tf={2}|order_bar={3}|order_time={4}|direction={5}|reference_close={6}|mode={7}|exit_policy={8}", _event, syminfo.tickerid, timeframe.period, bar_index, time_close, _direction, close, harness_backtest_mode, harness_exit_signal_policy)

// Raw Baseline ignores the production stats gate. Keep its requested bucket and
// target, but omit pass/fail marks so descriptive evidence cannot look like a rule.
// Edge estimates use one metric per line to keep the right cell narrow.
// Raw Baseline 不执行生产统计门槛；保留请求桶及其目标，但不显示质量勾叉。
// Edge 估计每项独占一行，避免右侧单元格横向过长。
f_harness_raw_stats_readout(SignalStats _stats, bool _is_buy, int _target) =>
    _lifetime_n = _stats.get_lifetime_count()
    if _lifetime_n < 5
        "RAW · GATE IGNORED\\nNo usable estimate"
    else
        [_has_enough, _edge_mode, _payoff_active, _wr_pass, _payoff_pass, _quality_ok, _adj_wr, _payoff_edge] = f_stats_gate_paths(_stats, _is_buy, _target)
        if _edge_mode
            _wr_edge = _adj_wr - f_stats_baseline_rate(_is_buy)
            str.format("RAW · GATE IGNORED\\nWR edge {0,number,+#.2;-#.2}pp\\nAvg edge {1,number,+#.2;-#.2}%", _wr_edge, _payoff_edge)
        else
            str.format("RAW · GATE IGNORED\\nWR {0,number,#.2}% · no gate", _adj_wr)

f_harness_gate_snapshot() =>
    string _source = "Idle"
    string _sample_display = ""
    string _readout = "No strategy signal"
    color _readout_color = color.gray
    SignalStats _stats = SignalStats.new()
    int _target = stats_min_samples

    // Rebuild the exact strategy signal for this backtest mode. Trade Side changes
    // whether the signal enters, exits or reverses; it must not rewrite its direction.
    // 按当前回测模式重建实际策略信号。Trade Side 只改变该信号是入场、
    // 平仓还是反手，不能篡改信号方向。
    bool _read_raw = not harness_use_production
    bool _buy_mtf = harness_raw_exit ? harness_exit_buy_mtf : _read_raw ? sig_buy_mtf : alert_buy_mtf
    bool _buy_div = harness_raw_exit ? harness_exit_buy_div : _read_raw ? sig_buy_div : alert_buy_div
    bool _buy_ext = harness_raw_exit ? harness_exit_buy_ext : _read_raw ? sig_buy_extreme : alert_buy_ext
    bool _buy_norm = harness_raw_exit ? harness_exit_buy_norm : _read_raw ? show_normal_signals and sig_buy_normal : show_normal_signals and alert_buy_norm
    bool _sell_mtf = harness_raw_exit ? harness_exit_sell_mtf : _read_raw ? sig_sell_mtf : alert_sell_mtf
    bool _sell_div = harness_raw_exit ? harness_exit_sell_div : _read_raw ? sig_sell_div : alert_sell_div
    bool _sell_ext = harness_raw_exit ? harness_exit_sell_ext : _read_raw ? sig_sell_extreme : alert_sell_ext
    bool _sell_norm = harness_raw_exit ? harness_exit_sell_norm : _read_raw ? show_normal_signals and sig_sell_normal : show_normal_signals and alert_sell_norm
    bool _has_buy = _buy_mtf or _buy_div or _buy_ext or _buy_norm
    bool _has_sell = _sell_mtf or _sell_div or _sell_ext or _sell_norm
    int _direction = harness_forced_exit ? 0 : _has_buy and not _has_sell ? 1 : _has_sell and not _has_buy ? -1 : 0
    bool _use_buy = _direction == 1
    bool _use_mtf = false
    bool _use_div = false
    bool _use_ext = false
    string _grade = "D"

    if _has_buy and _has_sell
        _source := "Conflict"

    if _direction == 1
        _grade := buy_quality_grade
        if _buy_mtf
            _use_mtf := true
        else if _buy_div
            _use_div := true
        else if _buy_ext
            _use_ext := true
    else if _direction == -1
        _grade := sell_quality_grade
        if _sell_mtf
            _use_mtf := true
        else if _sell_div
            _use_div := true
        else if _sell_ext
            _use_ext := true

    if _direction != 0
        // Production must explain the exact evidence bucket used by its active gate.
        // Raw Baseline (and a disabled production filter) keeps the requested bucket.
        // Production 必须解释启用中 gate 实际使用的证据桶；Raw Baseline（以及关闭的
        // Production filter）保留用户请求桶，不借用父级统计。
        bool _use_resolved = harness_use_production and not harness_raw_exit and enable_stats and enable_stats_filter
        string _evidence_source = ""
        if _use_resolved
            _stats := f_get_filter_stats(_use_buy, _use_mtf, _use_div, _use_ext, _grade)
            _target := f_get_filter_target(_use_buy, _use_mtf, _use_div, _use_ext, _grade)
            _evidence_source := f_get_filter_source(_use_buy, _use_mtf, _use_div, _use_ext, _grade)
        else
            _stats := f_harness_get_requested_stats(_use_buy, _use_mtf, _use_div, _use_ext, _grade)
            _target := f_harness_get_requested_target(_use_buy, _use_mtf, _use_div, _use_ext, _grade)
        _source := f_get_filter_source_label(_use_mtf, _use_div, _use_ext, _grade, _use_buy, _evidence_source)
        _sample_display := not enable_stats ? "Stats off" : f_stats_sample_text(_stats, _target)
        _readout := not enable_stats or (harness_use_production and not harness_raw_exit) ? f_stats_direct_readout(_stats, _use_buy, _target) : f_harness_raw_stats_readout(_stats, _use_buy, _target)
        _readout_color := harness_use_production and not harness_raw_exit ? f_stats_direct_color(_stats, _use_buy, _target) : color.gray
        if harness_raw_exit
            _readout := not enable_stats ? "RAW EXIT · GATE IGNORED\\nStats off" : str.replace_all(_readout, "RAW · GATE IGNORED", "RAW EXIT · GATE IGNORED")

    if harness_forced_exit
        _source := "Exit"
        _sample_display := "Entry gate ignored"
        _readout := str.format("CLOSE {0}\\n{1}", strategy.position_size > 0 ? "LONG" : "SHORT", harness_action)
        _readout_color := color.white
    else if not signal_data_ready and not harness_raw_exit
        _source := "Data"
        _sample_display := "Entry data unavailable"
        _readout := harness_use_production ? "BLOCK · DATA\\nNo new entry" : "RAW · DATA WAIT\\nNo new entry"
        _readout_color := color.yellow

    [_source, _sample_display, _readout, _readout_color]
"""

HARNESS_DASHBOARD_ROWS = """            harness_side_display = harness_trade_side == "Long Only" ? "Long only" : harness_trade_side == "Short Only" ? "Short only" : "Long + short"
            harness_mode_display = harness_use_production ? "Production filter" : "Raw baseline"
            harness_tester_display = harness_trade_side == "Long Only" ? "All = long trades" : harness_trade_side == "Short Only" ? "All = short trades" : "All = both sides"
            harness_risk_display = str.format("ATR {0} · Time {1}", harness_use_risk_exits ? "on" : "off", harness_max_holding_bars > 0 ? str.tostring(harness_max_holding_bars) + " bars" : "off")
            [harness_gate_source, harness_gate_sample_display, harness_gate_readout, harness_gate_color] = f_harness_gate_snapshot()
            // Strategy Stats 解释本回测模式的实际买/卖信号：Production 复用真实 gate 结论，Raw Baseline 明确忽略 gate。
            // Strategy Stats explains the actual signal in this backtest mode: Production reuses the real gate verdict; Raw Baseline explicitly ignores it.
            harness_stats_left = harness_gate_source == "Idle" or harness_gate_source == "Conflict" ? "Strategy Stats" : str.format("Strategy Stats\\n{0}\\n{1}", harness_gate_source, harness_gate_sample_display)
            harness_gate_display = harness_gate_source == "Idle" ? "No strategy signal" : harness_gate_source == "Conflict" ? "BUY + SELL conflict\\nNo strategy action" : harness_gate_readout

            table.cell(dashboard, 0, row, "Backtest", text_color=color.gray, text_size=txt_size_body)
            table.cell(dashboard, 1, row, str.format("{0} · {1}\\nExit signals: {2}\\n{3}", harness_side_display, harness_mode_display, harness_exit_signal_policy, harness_risk_display), text_color=color.white, text_size=txt_size_body)
            row += 1

            table.cell(dashboard, 0, row, "Tester View", text_color=color.gray, text_size=txt_size_body)
            table.cell(dashboard, 1, row, harness_tester_display + "\\nSignal close → next open", text_color=color.white, text_size=txt_size_body)
            row += 1

            table.cell(dashboard, 0, row, harness_stats_left, text_color=color.gray, text_size=txt_size_body)
            table.cell(dashboard, 1, row, harness_gate_display, text_color=harness_gate_color, text_size=txt_size_body)
            row += 1

            // TradingView's completed-trade metrics already include configured
            // commissions; never subtract fees a second time. Open P&L remains
            // visible and is excluded from the closed-trade win-rate denominator.
            // 已平仓指标已含配置佣金，不能再次扣费；未平仓盈亏另列，不充当胜率样本。
            harness_closed_n = strategy.closedtrades
            harness_wr_text = harness_closed_n > 0 ? str.format("{0,number,#.1}%", strategy.wintrades * 100.0 / harness_closed_n) : "—"
            harness_pf_text = strategy.grossloss > 0 ? str.format("{0,number,#.2}", strategy.grossprofit / strategy.grossloss) : strategy.grossprofit > 0 ? "∞" : "—"
            harness_avg_text = harness_closed_n > 0 ? str.format("{0,number,+#.2;-#.2}", strategy.netprofit / harness_closed_n) : "—"
            harness_open_bars = strategy.opentrades > 0 ? bar_index - strategy.opentrades.entry_bar_index(strategy.opentrades - 1) + 1 : 0
            harness_result_text = str.format("WR {0} · {1} closed\\nPF {2} · Avg {3} {4}\\nOpen {5,number,+#.2;-#.2} {4} · {6} bars", harness_wr_text, harness_closed_n, harness_pf_text, harness_avg_text, strategy.account_currency, strategy.openprofit, harness_open_bars)
            table.cell(dashboard, 0, row, "Trade Results\\nSIMULATED · NET\\n" + harness_evaluation_state, text_color=color.gray, text_size=txt_size_body)
            table.cell(dashboard, 1, row, harness_result_text, text_color=color.white, text_size=txt_size_body)
            row += 1

"""

STRATEGY_EXECUTION_BLOCK = """// ────────────────────────────────────────
// STRATEGY REPORT EXECUTION
// ────────────────────────────────────────

var float harness_long_sl_price = na
var float harness_long_tp_price = na
var float harness_short_sl_price = na
var float harness_short_tp_price = na

// Orders use confirmed signal closes and fill at the next available open. A
// reversal needs only strategy.entry: it closes the old side automatically.
// Date/time liquidation takes precedence; a single branch issues market orders.
// 收盘确定动作、下一可用开盘成交；反手只发 strategy.entry，自动平掉原方向。
// 日期/持仓期限退出优先；互斥分支避免平仓单与反手单重复提交。
if barstate.isconfirmed
    if harness_action == "Evaluation End" or harness_action == "Time Exit"
        strategy.cancel("Long Exit")
        strategy.cancel("Short Exit")
        strategy.close(strategy.position_size > 0 ? "Long" : "Short", comment=harness_action, alert_message=f_harness_order_message(harness_action == "Evaluation End" ? "EVALUATION_END" : "TIME_EXIT", strategy.position_size > 0 ? "LONG" : "SHORT"))
    else if harness_action == "Long"
        strategy.cancel("Short Exit")
        strategy.entry("Long", strategy.long, comment=strategy.position_size < 0 ? "REVERSE LONG" : "ENTRY LONG", alert_message=f_harness_order_message(strategy.position_size < 0 ? "REVERSE_LONG" : "ENTRY_LONG", "LONG"))
        harness_long_sl_price := buy_sl_price
        harness_long_tp_price := buy_tp_price
        // Entry-bound bracket protects the fill bar; prices remain signal-close
        // snapshots, so opening gaps can change the actual risk/reward ratio.
        // 入场同时挂止损止盈，覆盖成交当根；价格仍是信号收盘快照，跳空会改变实际盈亏比。
        if harness_use_risk_exits and (not na(harness_long_sl_price) or not na(harness_long_tp_price))
            strategy.exit("Long Exit", from_entry="Long", stop=harness_long_sl_price, limit=harness_long_tp_price, comment="ATR EXIT LONG", alert_message=f_harness_order_message("ATR_EXIT", "LONG"))
    else if harness_action == "Short"
        strategy.cancel("Long Exit")
        strategy.entry("Short", strategy.short, comment=strategy.position_size > 0 ? "REVERSE SHORT" : "ENTRY SHORT", alert_message=f_harness_order_message(strategy.position_size > 0 ? "REVERSE_SHORT" : "ENTRY_SHORT", "SHORT"))
        harness_short_sl_price := sell_sl_price
        harness_short_tp_price := sell_tp_price
        if harness_use_risk_exits and (not na(harness_short_sl_price) or not na(harness_short_tp_price))
            strategy.exit("Short Exit", from_entry="Short", stop=harness_short_sl_price, limit=harness_short_tp_price, comment="ATR EXIT SHORT", alert_message=f_harness_order_message("ATR_EXIT", "SHORT"))
    else if harness_action == "Close Long"
        strategy.cancel("Long Exit")
        strategy.close("Long", comment=harness_raw_exit ? "RAW EXIT LONG" : "FILTERED EXIT LONG", alert_message=f_harness_order_message(harness_raw_exit ? "RAW_EXIT" : "FILTERED_EXIT", "LONG"))
    else if harness_action == "Close Short"
        strategy.cancel("Short Exit")
        strategy.close("Short", comment=harness_raw_exit ? "RAW EXIT SHORT" : "FILTERED EXIT SHORT", alert_message=f_harness_order_message(harness_raw_exit ? "RAW_EXIT" : "FILTERED_EXIT", "SHORT"))

// Refresh unchanged brackets only when no market action replaces them. Risk
// protection remains active outside the date/data/evidence entry conditions.
// 无市场动作替代时刷新原止损止盈；退出保护不受入场日期、数据、证据门槛限制。
if harness_use_risk_exits and harness_action == "Idle"
    if strategy.position_size > 0 and (not na(harness_long_sl_price) or not na(harness_long_tp_price))
        strategy.exit("Long Exit", from_entry="Long", stop=harness_long_sl_price, limit=harness_long_tp_price, comment="ATR EXIT LONG", alert_message=f_harness_order_message("ATR_EXIT", "LONG"))
    if strategy.position_size < 0 and (not na(harness_short_sl_price) or not na(harness_short_tp_price))
        strategy.exit("Short Exit", from_entry="Short", stop=harness_short_sl_price, limit=harness_short_tp_price, comment="ATR EXIT SHORT", alert_message=f_harness_order_message("ATR_EXIT", "SHORT"))

// The planner triggers time exit at the close of held bar N-1, giving exactly N
// open-to-open held bars with the declared calculation settings (0 disables it).
// 选择器在第 N-1 根持仓K线收盘提交时间退出，默认计算设置下持有 N 根开盘到开盘K线。
"""

STRATEGY_EXECUTION_SENTINEL = "// STRATEGY REPORT EXECUTION"


# ────────────────────────────────────────
# Dashboard sizing/refresh tweaks (narrow single-line regexes)
# ────────────────────────────────────────

# The harness adds four dashboard rows; table capacity gets one extra row of
# headroom on top of that (production: 20-row table cleared as 0..19).
HARNESS_EXTRA_ROWS = 4
HARNESS_TABLE_ROW_OFFSET = 5

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
