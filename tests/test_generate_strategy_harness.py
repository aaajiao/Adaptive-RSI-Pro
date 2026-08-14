"""Tests for tools/generate_strategy_harness.py (stdlib unittest only).

Run with:
    python3 -m unittest discover -s tests -p "test_generate*" -v
"""

from __future__ import annotations

import contextlib
import io
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import generate_strategy_harness as gen  # noqa: E402


def read_source() -> str:
    return gen.DEFAULT_SOURCE.read_text(encoding="utf-8")


def read_target() -> str:
    return gen.DEFAULT_TARGET.read_text(encoding="utf-8")


class GoldenTest(unittest.TestCase):
    """generate(production source) must reproduce the committed harness."""

    def test_generated_output_matches_committed_harness(self) -> None:
        self.assertEqual(gen.generate(read_source()), read_target())


class AnchorValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = read_source()

    def remove_anchor(self, name: str) -> str:
        pattern = re.compile(rf"^[ \t]*// @harness: {re.escape(name)}[ \t]*\n", re.MULTILINE)
        mutated, count = pattern.subn("", self.source)
        self.assertEqual(count, 1, f"anchor {name!r} not found in source")
        return mutated

    def test_each_missing_anchor_raises(self) -> None:
        for name in gen.KNOWN_ANCHORS:
            with self.subTest(anchor=name):
                mutated = self.remove_anchor(name)
                with self.assertRaisesRegex(gen.GenerationError, name):
                    gen.generate(mutated)

    def test_duplicated_anchor_raises(self) -> None:
        mutated = self.source + "\n// @harness: inputs\n"
        with self.assertRaisesRegex(gen.GenerationError, "inputs"):
            gen.generate(mutated)

    def test_unknown_anchor_raises(self) -> None:
        mutated = self.source + "\n// @harness: not-a-real-anchor\n"
        with self.assertRaisesRegex(gen.GenerationError, "not-a-real-anchor"):
            gen.generate(mutated)

    def test_malformed_anchor_raises(self) -> None:
        mutated = self.source + "\n// @harness inputs (missing colon)\n"
        with self.assertRaisesRegex(gen.GenerationError, "malformed"):
            gen.generate(mutated)


class CosmeticEditRobustnessTest(unittest.TestCase):
    """Cosmetic edits to production text must not break generation."""

    def setUp(self) -> None:
        self.source = read_source()

    def mutate_line(self, line_pattern: str, replacement: str) -> str:
        pattern = re.compile(line_pattern, re.MULTILINE)
        mutated, count = pattern.subn(replacement, self.source)
        self.assertEqual(count, 1, f"expected one line matching {line_pattern!r}")
        return mutated

    def test_tooltip_edit_survives_generation(self) -> None:
        mutated = self.mutate_line(
            r"^stats_filter_mode = input\.string\(.*$",
            'stats_filter_mode = input.string("Alert Only", "Filter Mode / 过滤模式", '
            'options=["Alert Only", "Soft", "Hard"], group=grp_stats, '
            'tooltip="EDITED TOOLTIP 已编辑")',
        )
        generated = gen.generate(mutated)
        self.assertIn("EDITED TOOLTIP 已编辑", generated)

    def test_alert_level_line_edit_survives_generation(self) -> None:
        mutated = self.mutate_line(
            r"^    should_alert_buy = alert_has_buy and current_buy_level > prev_buy_level.*$",
            "    should_alert_buy = alert_has_buy and current_buy_level >= prev_buy_level  // EDITED",
        )
        generated = gen.generate(mutated)
        self.assertIn("current_buy_level >= prev_buy_level  // EDITED", generated)

    def test_stats_helper_area_edit_survives_generation(self) -> None:
        mutated = self.mutate_line(
            r"^f_get_grade_stats\(_is_buy, _grade\) =>$",
            "// edited helper comment / 已编辑\nf_get_grade_stats(_is_buy, _grade) =>",
        )
        generated = gen.generate(mutated)
        self.assertIn("// edited helper comment / 已编辑", generated)


class DashboardSemanticsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = read_source()

    def test_sample_maturity_is_not_rendered_as_a_quality_checkmark(self) -> None:
        self.assertNotIn("get_reliability", self.source)
        self.assertIn("f_stats_sample_text", self.source)
        self.assertIn('str.format("n={0}/{1}⏳"', self.source)

    def test_direction_edge_warning_is_a_single_combined_row(self) -> None:
        self.assertNotIn("No timing edge", self.source)
        self.assertEqual(self.source.count('table.cell(dashboard, 0, row, "Edge Summary"'), 1)

    def test_selected_event_drives_direction_bucket_and_hidden_state(self) -> None:
        self.assertIn("int signal_event_kind = switch", self.source)
        self.assertIn("signal_event_kind >= 1 and signal_event_kind <= 4 ? signal_event_kind : 0", self.source)
        self.assertNotIn("signal_setup_direction", self.source)
        self.assertNotIn('"Stats Filter [Setup]"', self.source)
        self.assertNotIn("current_signal_passes_filter", self.source)
        self.assertNotIn("current_signal_insufficient", self.source)

    def test_missing_quantiles_do_not_claim_top_percentile(self) -> None:
        self.assertIn('na(rsi_p5) or na(rsi_p10)', self.source)
        self.assertIn('"NA · need history"', self.source)

    def test_stats_rows_translate_metrics_into_the_actual_gate_decision(self) -> None:
        self.assertIn("f_stats_gate_paths(SignalStats _stats, bool _is_buy)", self.source)
        self.assertGreaterEqual(self.source.count("f_stats_gate_paths"), 4)
        self.assertIn('str.format("OR ({0}/2)"', self.source)
        self.assertIn('str.format("AND ({0}/2)"', self.source)
        self.assertIn('"ABS WR"', self.source)
        self.assertIn('"FILTER OFF · ALL ALLOWED', self.source)
        self.assertIn('"STATS OFF · ALL ALLOWED', self.source)
        self.assertIn("UNPROVEN POLICY", self.source)
        self.assertIn("· edge {1,number,+#.2;-#.2}pp", self.source)
        self.assertIn("· edge {1,number,+#.2;-#.2}%", self.source)
        self.assertIn("· not gated", self.source)
        self.assertNotIn("ΔWR", self.source)
        self.assertNotIn("ΔAvg", self.source)

    def test_full_dashboard_uses_semantic_multiline_cells(self) -> None:
        self.assertIn("signal_full_panel_display", self.source)
        self.assertIn('str.format("Z {0,number,+#.2;-#.2}σ\\nHistory {1}"', self.source)
        self.assertIn('trend_context + "\\n" + weekly_rsi_display + "\\n" + volume_context', self.source)
        self.assertIn('"Stats Filter\\n{0}\\nn={1}{2}"', self.source)
        self.assertIn('stats_title + str.format("\\n{0}-bar forward\\n{1}"', self.source)
        self.assertIn('"Avg edge min {0,number,+#.1;-#.1}%\\nBUY WR', self.source)
        self.assertIn('"Divergence"', self.source)
        self.assertIn("Pivot {2} · Max gap {3} bars", self.source)
        self.assertIn("Allowed {1}–{2} bars", self.source)
        self.assertIn("gate_color := gate_effective_usable ? color.white", self.source)

    def test_setup_score_is_not_presented_as_a_quality_verdict(self) -> None:
        self.assertIn('"── SETUP SCORE STATS ──"', self.source)
        self.assertIn('" [Score " + signal_grade_text + "]"', self.source)
        self.assertIn("[Score {3}]", self.source)
        self.assertNotIn('"── GRADE STATS ──"', self.source)


class GenerationContentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.generated = gen.generate(read_source())

    def test_header_is_harness_header(self) -> None:
        self.assertTrue(self.generated.startswith(gen.HARNESS_HEADER + "\n"))

    def test_declaration_is_strategy(self) -> None:
        self.assertIn('\nstrategy("Adaptive RSI Pro Strategy Report", shorttitle="ARSI Pro STRAT", ', self.generated)
        self.assertNotRegex(self.generated, r"(?m)^indicator\(")

    def test_execution_block_appended_once(self) -> None:
        self.assertEqual(self.generated.count(gen.STRATEGY_EXECUTION_SENTINEL), 1)
        self.assertTrue(self.generated.endswith("\n"))

    def test_dashboard_row_and_capacity_offsets_stay_consistent(self) -> None:
        source = read_source()

        def extract_int(text: str, pattern: str) -> int:
            match = re.search(pattern, text, re.MULTILINE)
            self.assertIsNotNone(match, pattern)
            return int(match.group(1))

        source_base = extract_int(source, r"^[ \t]*full_rows = (\d+) \+")
        generated_base = extract_int(self.generated, r"^[ \t]*full_rows = (\d+) \+")
        source_capacity = extract_int(source, r"table\.new\(position\.top_right, 2, (\d+),")
        generated_capacity = extract_int(self.generated, r"table\.new\(position\.top_right, 2, (\d+),")
        source_clear_end = extract_int(source, r"table\.clear\(dashboard, 0, 0, 1, (\d+)\)")
        generated_clear_end = extract_int(self.generated, r"table\.clear\(dashboard, 0, 0, 1, (\d+)\)")

        self.assertEqual(generated_base, source_base + gen.HARNESS_EXTRA_ROWS)
        self.assertEqual(generated_capacity, source_capacity + gen.HARNESS_TABLE_ROW_OFFSET)
        self.assertEqual(source_clear_end, source_capacity - 1)
        self.assertEqual(generated_clear_end, generated_capacity - 1)

    def test_readable_harness_dashboard_rows_are_inserted_once(self) -> None:
        for label in ('"Backtest"', '"Tester View"', '"Strategy Stats"'):
            with self.subTest(label=label):
                self.assertEqual(self.generated.count(label), 1)

        self.assertNotIn('"Trigger Stats"', self.generated)
        self.assertIn('"No strategy signal"', self.generated)
        self.assertIn('"BUY + SELL conflict\\nNo strategy action"', self.generated)

    def test_strategy_stats_follow_the_actual_signal_and_effective_weight(self) -> None:
        self.assertIn("int _direction = _has_buy and not _has_sell ? 1", self.generated)
        self.assertIn('if _has_buy and _has_sell\n        _source := "Conflict"', self.generated)
        self.assertIn("_source := f_get_filter_source_label(true, false, false, buy_quality_grade, true)", self.generated)
        self.assertIn("_source := f_get_filter_source_label(true, false, false, sell_quality_grade, false)", self.generated)
        self.assertIn("_effective := _stats.get_count()", self.generated)
        self.assertIn("harness_gate_effective >= 5", self.generated)
        self.assertIn('str.format("n={0} · stale"', self.generated)

    def test_strategy_stats_explain_production_but_ignore_gate_in_raw_baseline(self) -> None:
        self.assertIn("f_harness_raw_stats_readout", self.generated)
        self.assertIn("RAW BASELINE · GATE IGNORED", self.generated)
        self.assertIn(
            "_readout := not enable_stats or harness_use_production ? f_stats_direct_readout(_stats, _use_buy) "
            ": f_harness_raw_stats_readout(_stats, _use_buy)",
            self.generated,
        )
        self.assertIn("STATS OFF · ALL ALLOWED", self.generated)
        self.assertIn('str.format("Strategy Stats\\n{0}\\n{1}"', self.generated)
        self.assertIn("Score {0}", self.generated)
        self.assertIn('not enable_stats ? "Stats off"', self.generated)
        self.assertIn("not enable_stats or not enable_stats_filter ? color.gray", self.generated)
        self.assertNotIn("harness_gate_metrics_display", self.generated)
        self.assertNotIn("ΔAvg", self.generated)

    def test_source_with_execution_block_raises(self) -> None:
        mutated = read_source() + "\n" + gen.STRATEGY_EXECUTION_SENTINEL + "\n"
        with self.assertRaisesRegex(gen.GenerationError, "execution"):
            gen.generate(mutated)

    def test_risk_exit_brackets_each_entry_on_the_signal_bar(self) -> None:
        # Contract: strategy.exit is issued immediately after each strategy.entry
        # (bound via from_entry, guarded for na snapshots and the risk-exit toggle)
        # so SL/TP are already active on the entry fill bar itself.
        for side, sl_var, tp_var, snapshot_sl, snapshot_tp in (
            ("Long", "harness_long_sl_price", "harness_long_tp_price", "buy_sl_price", "buy_tp_price"),
            ("Short", "harness_short_sl_price", "harness_short_tp_price", "sell_sl_price", "sell_tp_price"),
        ):
            with self.subTest(side=side):
                self.assertRegex(
                    self.generated,
                    re.compile(
                        rf'strategy\.entry\("{side}", strategy\.{side.lower()}\)\n'
                        rf"[ \t]+{sl_var} := {snapshot_sl}\n"
                        rf"[ \t]+{tp_var} := {snapshot_tp}\n"
                        rf"[ \t]+if harness_use_risk_exits and \(not na\({sl_var}\) or not na\({tp_var}\)\)\n"
                        rf'[ \t]+strategy\.exit\("{side} Exit", from_entry="{side}", '
                        rf'stop={sl_var}, limit={tp_var}, comment="ATR Exit"\)'
                    ),
                )

    def test_risk_exit_is_refreshed_while_position_is_open(self) -> None:
        # Entry-time placement + open-position refresh: exactly two strategy.exit
        # calls per side, all gated behind harness_use_risk_exits (default off =
        # verified no-op).
        self.assertEqual(self.generated.count('strategy.exit("Long Exit", from_entry="Long"'), 2)
        self.assertEqual(self.generated.count('strategy.exit("Short Exit", from_entry="Short"'), 2)
        self.assertEqual(self.generated.count("strategy.exit("), 4)
        self.assertRegex(
            self.generated,
            re.compile(
                r"(?m)^if harness_use_risk_exits$\n"
                r"[ \t]+if strategy\.position_size > 0 and \(not na\(harness_long_sl_price\) or not na\(harness_long_tp_price\)\)\n"
                r'[ \t]+strategy\.exit\("Long Exit", from_entry="Long"'
            ),
        )

    def test_max_holding_bars_realizes_exactly_n_bars(self) -> None:
        # Contract: strategy.close fills at the NEXT bar's open, so the time exit
        # triggers at held bar N-1 to realize exactly N held bars. Default 0 skips
        # the block entirely via the > 0 gate.
        self.assertIn(
            "if harness_max_holding_bars > 0 and strategy.opentrades > 0",
            self.generated,
        )
        self.assertIn(
            "bar_index - strategy.opentrades.entry_bar_index(strategy.opentrades - 1) >= harness_max_holding_bars - 1",
            self.generated,
        )
        self.assertNotRegex(
            self.generated,
            re.compile(r">= harness_max_holding_bars$", re.MULTILINE),
        )


class CliCheckTest(unittest.TestCase):
    def run_main(self, argv: list[str]) -> int:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            return gen.main(argv)

    def test_check_up_to_date_exits_0(self) -> None:
        self.assertEqual(self.run_main(["--check"]), 0)

    def test_check_stale_target_exits_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stale = Path(tmp) / "stale_harness.pine"
            stale.write_text(read_target() + "// tampered\n", encoding="utf-8")
            self.assertEqual(
                self.run_main(["--check", "--source", str(gen.DEFAULT_SOURCE), "--target", str(stale)]),
                1,
            )

    def test_check_broken_source_exits_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp) / "broken_source.pine"
            broken.write_text(read_source() + "\n// @harness: inputs\n", encoding="utf-8")
            self.assertEqual(
                self.run_main(["--check", "--source", str(broken), "--target", str(gen.DEFAULT_TARGET)]),
                2,
            )

    def test_check_missing_source_exits_2(self) -> None:
        self.assertEqual(
            self.run_main(["--check", "--source", "/nonexistent/path.pine", "--target", str(gen.DEFAULT_TARGET)]),
            2,
        )


if __name__ == "__main__":
    unittest.main()
