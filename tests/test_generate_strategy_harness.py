"""Tests for tools/generate_strategy_harness.py (stdlib unittest only).

Run with:
    python3 -m unittest discover -s tests -p "test_generate*" -v
"""

from __future__ import annotations

import contextlib
import io
import math
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


def reference_adaptive_targets(counts: list[int], evidence_reference: int = 20) -> list[int]:
    """Python mirror of Pine's positive-number smoothed-share target formula."""

    low = min(evidence_reference, max(5, math.floor(evidence_reference * 0.4 + 0.5)))
    high = min(evidence_reference, max(low, math.floor(evidence_reference * 0.8 + 0.5)))
    peer_total = sum(counts)
    prior_per_peer = evidence_reference / 4
    return [
        math.floor(
            low
            + (high - low)
            * math.sqrt(max(0.0, min((count + prior_per_peer) / (peer_total + evidence_reference), 1.0)))
            + 0.5
        )
        for count in counts
    ]


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
            r"^    should_alert_buy = alert_has_buy and not alert_conflict.*$",
            "    should_alert_buy = alert_has_buy and not alert_conflict and current_buy_level >= buy_alert_level_sent  // EDITED",
        )
        generated = gen.generate(mutated)
        self.assertIn("current_buy_level >= buy_alert_level_sent  // EDITED", generated)

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
        self.assertIn("f_stats_gate_paths(SignalStats _stats, bool _is_buy, int _target)", self.source)
        self.assertGreaterEqual(self.source.count("f_stats_gate_paths"), 3)
        self.assertIn('str.format("OR ({0}/2)"', self.source)
        self.assertIn('str.format("AND ({0}/2)"', self.source)
        self.assertIn('"ABS WR"', self.source)
        self.assertIn('"FILTER OFF · ALL ALLOWED', self.source)
        self.assertIn('"STATS OFF · ALL ALLOWED', self.source)
        self.assertIn('str.format("{0} · WAITING\\nNo quality verdict"', self.source)
        self.assertIn('str.format("{0} · STALE\\nNeed fresh evidence"', self.source)
        self.assertIn(
            '_headline + str.format("\\nWR edge {0,number,+#.2;-#.2}pp {1}\\n{2}"',
            self.source,
        )
        self.assertIn(
            'str.format("Avg edge {0,number,+#.2;-#.2}% {1}"',
            self.source,
        )
        self.assertIn(
            'str.format("FILTER OFF · ALL ALLOWED\\nWR edge {0,number,+#.2;-#.2}pp\\nAvg edge {1,number,+#.2;-#.2}%"',
            self.source,
        )
        self.assertNotIn("UNPROVEN POLICY", self.source)
        self.assertNotIn("ΔWR", self.source)
        self.assertNotIn("ΔAvg", self.source)

    def test_full_dashboard_uses_semantic_multiline_cells(self) -> None:
        self.assertIn("signal_full_panel_display", self.source)
        self.assertIn('str.format("Z {0,number,+#.2;-#.2}σ\\nHistory {1}"', self.source)
        self.assertIn('trend_context + "\\n" + weekly_rsi_display + "\\n" + volume_context', self.source)
        self.assertIn('gate_title + "\\n" + gate_label + "\\n" + f_stats_sample_text(gate_stats, gate_target)', self.source)
        self.assertIn('gate_display := f_stats_direct_readout(gate_stats, gate_is_buy, gate_target)', self.source)
        self.assertIn('stats_title + str.format("\\nOutcome +{0} bars\\n{1} · {2}"', self.source)
        self.assertIn('"Avg edge min {0,number,+#.1;-#.1}%\\nBUY WR', self.source)
        self.assertIn('"Divergence"', self.source)
        self.assertIn("Pivot {2} · Max gap {3} bars", self.source)
        self.assertIn("Allowed {1}–{2} bars", self.source)
        self.assertIn("gate_color := f_stats_direct_color(gate_stats, gate_is_buy, gate_target)", self.source)

    def test_full_stats_bucket_cells_use_three_semantic_lines(self) -> None:
        self.assertIn(
            'str.format("{0} {1}\\n{2}", f_signal_kind_icon(_signal_idx, _is_buy), '
            'f_signal_kind_name(_signal_idx), _is_buy ? "BUY" : "SELL")',
            self.source,
        )
        self.assertIn(
            'f_signal_type_dashboard_label(sig_idx, is_buy) + "\\n" + '
            "f_stats_sample_text(sig_stats, sig_target)",
            self.source,
        )
        self.assertIn(
            'str.format("{0}\\n[Score {1}]\\n{2}", is_buy ? "BUY" : "SELL", '
            "grade_label, f_stats_sample_text(grade_bucket, grade_target))",
            self.source,
        )
        self.assertIn(
            'str.format("{0} {1}\\n{2} [Score {3}]\\n{4}", '
            "f_signal_kind_icon(sig - 1, is_buy_rank), "
            "f_signal_kind_name(sig - 1), dir_text, grd, "
            "f_stats_sample_text(rank_stats, rank_target))",
            self.source,
        )

    def test_adaptive_ranking_wait_cells_use_three_semantic_lines(self) -> None:
        self.assertIn(
            'parent_ready ? "WAIT · EXACT\\nGate → Type\\n" + parent_progress : '
            '"WAIT · NO VERDICT\\nType evidence\\n" + parent_progress',
            self.source,
        )
        self.assertNotIn('"WAIT · EXACT\\nGate → Type " + parent_progress', self.source)
        self.assertNotIn('"WAIT · NO VERDICT\\nType " + parent_progress', self.source)

    def test_stats_filter_fallback_uses_narrow_three_line_left_cell(self) -> None:
        self.assertIn('gate_title = "Stats Filter"', self.source)
        self.assertIn(
            'gate_label = gate_source == "Type fallback" ? '
            'f_gate_type_bucket_label(gate_kind, gate_is_buy) + " → Type" : '
            "f_gate_bucket_label(gate_kind, gate_grade, gate_is_buy)",
            self.source,
        )
        self.assertIn(
            'gate_left_display := gate_title + "\\n" + gate_label + "\\n" + '
            "f_stats_sample_text(gate_stats, gate_target)",
            self.source,
        )
        self.assertNotIn("Stats Filter · Type fallback", self.source)

    def test_setup_score_is_not_presented_as_a_quality_verdict(self) -> None:
        self.assertIn('"── SETUP SCORE STATS ──"', self.source)
        self.assertIn('" [Score " + signal_grade_text + "]"', self.source)
        self.assertIn("[Score {3}]", self.source)
        self.assertNotIn('"── GRADE STATS ──"', self.source)

    def test_adaptive_sample_policy_resolves_only_ready_ranking_parents(self) -> None:
        self.assertIn('stats_sample_policy = input.string("Adaptive"', self.source)
        self.assertIn('options=["Adaptive", "Fixed (Legacy)"]', self.source)
        self.assertIn("f_stats_has_verdict_samples(SignalStats _stats, int _target)", self.source)
        self.assertIn('stats_sample_policy == "Fixed (Legacy)" or _stats.get_count() >= 5', self.source)
        self.assertIn("f_stats_uses_type_fallback", self.source)
        self.assertIn('stats_sample_policy == "Adaptive" and stats_mode == "Ranking"', self.source)
        self.assertIn("not f_stats_has_verdict_samples(_ranking, _ranking_target)", self.source)
        self.assertIn("f_stats_has_verdict_samples(_type, _type_target)", self.source)
        self.assertIn("f_get_filter_target", self.source)
        self.assertIn('? "Type fallback" : ""', self.source)

    def test_adaptive_stale_is_unproven_but_fixed_preserves_legacy_verdict(self) -> None:
        self.assertIn('str.format("n={0} · eff {1,number,#.1}<5⏳"', self.source)
        self.assertIn("else if not _has_enough_samples", self.source)
        self.assertIn('"{0} · STALE\\nNeed fresh evidence"', self.source)
        self.assertIn("not f_stats_has_verdict_samples(_stats, _target)", self.source)


class AdaptiveTargetContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = read_source()

    def test_smoothed_share_reference_values(self) -> None:
        cases = (
            ([0, 0, 0, 0], [12, 12, 12, 12]),
            ([10, 10, 10, 10], [12, 12, 12, 12]),
            ([1, 13, 13, 13], [11, 12, 12, 12]),
            ([37, 1, 1, 1], [15, 11, 11, 11]),
            ([7, 11, 14, 30], [11, 12, 12, 13]),
        )
        for counts, expected in cases:
            with self.subTest(counts=counts):
                self.assertEqual(reference_adaptive_targets(counts), expected)

    def test_pine_formula_matches_the_smoothed_share_contract(self) -> None:
        self.assertIn("STATS_EVIDENCE_PEER_COUNT = 4", self.source)
        self.assertIn("stats_min_samples * 0.4", self.source)
        self.assertIn("stats_min_samples * 0.8", self.source)
        self.assertIn(
            "_q = (float(_bucket_n) + float(stats_min_samples) / STATS_EVIDENCE_PEER_COUNT) / "
            "(float(_peer_total) + float(stats_min_samples))",
            self.source,
        )
        self.assertIn("math.sqrt(_smoothed_q)", self.source)

    def test_dynamic_target_uses_sample_structure_not_outcomes(self) -> None:
        match = re.search(
            r"f_stats_dynamic_target\(SignalStats _stats, int _peer_total\) =>\n"
            r"(?P<body>.*?)(?=\nf_stats_signal_type_peer_total)",
            self.source,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        body = match.group("body")
        for forbidden in (
            "wins",
            "total_return",
            "get_winrate",
            "get_avg",
            "get_adjusted",
            "payoff",
            "baseline",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, body)
        self.assertIn("_stats.get_lifetime_count()", body)
        self.assertIn("_peer_total", body)

    def test_fixed_and_overlapping_sample_guards_restore_reference_target(self) -> None:
        self.assertIn(
            'if stats_sample_policy == "Fixed (Legacy)" or not stats_independent_samples\n'
            "        stats_min_samples",
            self.source,
        )
        self.assertIn('stats_sample_policy == "Adaptive" and stats_mode == "Ranking"', self.source)

    def test_exact_and_parent_use_their_own_targets(self) -> None:
        self.assertIn("_ranking_target = f_get_signal_target", self.source)
        self.assertIn("_type_target = f_get_signal_type_target", self.source)
        self.assertIn("f_stats_has_verdict_samples(_ranking, _ranking_target)", self.source)
        self.assertIn("f_stats_has_verdict_samples(_type, _type_target)", self.source)
        self.assertIn("parent_target = f_stats_signal_type_target", self.source)
        self.assertIn("parent_progress = f_stats_sample_text(parent_stats, parent_target)", self.source)

    def test_production_signal_and_alert_paths_carry_targets(self) -> None:
        for event in ("mtf", "div", "ext", "norm"):
            for direction in ("buy", "sell"):
                with self.subTest(direction=direction, event=event):
                    self.assertIn(f"{direction}_{event}_stats_target = f_get_filter_target", self.source)
                    is_buy = "true" if direction == "buy" else "false"
                    self.assertIn(
                        f"filter_{direction}_{event} = signal_data_ready and f_passes_stats_filter("
                        f"{direction}_{event}_stats, {is_buy}, {direction}_{event}_stats_target)",
                        self.source,
                    )
                    self.assertIn(
                        f"f_stats_insufficient({direction}_alert_stats, {direction}_alert_target)",
                        self.source,
                    )
        self.assertIn("signal_event_stats_target", self.source)
        self.assertIn("f_stats_insufficient(signal_event_stats, signal_event_stats_target)", self.source)
        self.assertIn("f_stats_sample_text(gate_stats, gate_target)", self.source)
        self.assertIn("f_stats_direct_readout(gate_stats, gate_is_buy, gate_target)", self.source)
        self.assertIn("f_stats_direct_color(gate_stats, gate_is_buy, gate_target)", self.source)

    def test_old_three_line_unproven_vocabulary_is_gone(self) -> None:
        for old_text in (
            "UNPROVEN POLICY",
            "Policy decision only",
            "EXACT BUCKET · UNPROVEN",
            "No ready Type parent",
            "No exact-bucket verdict",
        ):
            with self.subTest(old_text=old_text):
                self.assertNotIn(old_text, self.source)


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
        self.assertIn("int _direction = harness_forced_exit ? 0 : _has_buy and not _has_sell ? 1", self.generated)
        self.assertIn('if _has_buy and _has_sell\n        _source := "Conflict"', self.generated)
        self.assertIn("_grade := buy_quality_grade", self.generated)
        self.assertIn("_grade := sell_quality_grade", self.generated)
        self.assertIn("int _target = stats_min_samples", self.generated)
        self.assertIn("_sample_display := not enable_stats ? \"Stats off\" : f_stats_sample_text(_stats, _target)", self.generated)
        self.assertIn("_readout_color := harness_use_production and not harness_raw_exit ? f_stats_direct_color(_stats, _use_buy, _target) : color.gray", self.generated)
        self.assertIn("[_source, _sample_display, _readout, _readout_color]", self.generated)
        self.assertIn("[harness_gate_source, harness_gate_sample_display, harness_gate_readout, harness_gate_color]", self.generated)
        self.assertNotIn("harness_gate_count >= stats_min_samples", self.generated)
        self.assertNotIn("harness_gate_effective >= 5", self.generated)

    def test_strategy_stats_explain_production_but_ignore_gate_in_raw_baseline(self) -> None:
        self.assertIn("f_harness_raw_stats_readout", self.generated)
        self.assertIn("RAW · GATE IGNORED", self.generated)
        self.assertIn("f_harness_get_requested_stats", self.generated)
        self.assertIn("f_harness_get_requested_target", self.generated)
        self.assertIn("bool _use_resolved = harness_use_production and not harness_raw_exit and enable_stats and enable_stats_filter", self.generated)
        self.assertIn("if _use_resolved\n            _stats := f_get_filter_stats", self.generated)
        self.assertIn("_target := f_get_filter_target", self.generated)
        self.assertIn("else\n            _stats := f_harness_get_requested_stats", self.generated)
        self.assertIn("_target := f_harness_get_requested_target", self.generated)
        self.assertIn('_evidence_source := f_get_filter_source(', self.generated)
        self.assertIn(
            "_readout := not enable_stats or (harness_use_production and not harness_raw_exit) ? f_stats_direct_readout(_stats, _use_buy, _target) "
            ": f_harness_raw_stats_readout(_stats, _use_buy, _target)",
            self.generated,
        )
        self.assertIn("STATS OFF · ALL ALLOWED", self.generated)
        self.assertIn('str.format("Strategy Stats\\n{0}\\n{1}"', self.generated)
        self.assertIn("Score {0}", self.generated)
        self.assertIn('[Score {1}] → Type', self.generated)
        self.assertIn('_evidence_source == "Type fallback"', self.generated)
        self.assertIn('not enable_stats ? "Stats off"', self.generated)
        self.assertIn("f_stats_direct_color(_stats, _use_buy, _target)", self.generated)
        self.assertNotIn("harness_gate_metrics_display", self.generated)
        self.assertNotIn("ΔAvg", self.generated)

    def test_raw_readout_is_target_aware_and_splits_edge_metrics_across_three_lines(self) -> None:
        self.assertIn(
            "f_harness_raw_stats_readout(SignalStats _stats, bool _is_buy, int _target)",
            self.generated,
        )
        self.assertIn("f_stats_gate_paths(_stats, _is_buy, _target)", self.generated)
        match = re.search(
            r"f_harness_raw_stats_readout\(SignalStats _stats, bool _is_buy, int _target\) =>\n"
            r"(?P<body>.*?)(?=\nf_harness_gate_snapshot)",
            self.generated,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        body = match.group("body")
        self.assertNotIn("All raw signals allowed", body)
        self.assertIn(
            'str.format("RAW · GATE IGNORED\\nWR edge {0,number,+#.2;-#.2}pp\\nAvg edge {1,number,+#.2;-#.2}%"',
            body,
        )
        self.assertIn('"RAW · GATE IGNORED\\nNo usable estimate"', body)
        self.assertIn(
            'str.format("RAW · GATE IGNORED\\nWR {0,number,#.2}% · no gate"',
            body,
        )
        # Only the mature Edge branch needs three lines. The no-estimate and
        # Legacy branches deliberately remain two-line cells.
        three_line_literals = re.findall(r'"[^"\n]*(?:\\n[^"\n]*){2}"', body)
        self.assertEqual(len(three_line_literals), 1)
        self.assertNotRegex(body, r'"[^"\n]*(?:\\n[^"\n]*){3}')

    def test_production_readout_line_budget_matches_cell_semantics(self) -> None:
        match = re.search(
            r"f_stats_direct_readout\(SignalStats _stats, bool _is_buy, int _target\) =>\n"
            r"(?P<body>.*?)(?=\nf_stats_direct_color)",
            self.generated,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        body = match.group("body")
        self.assertIn(
            '_headline + str.format("\\nWR edge {0,number,+#.2;-#.2}pp {1}\\n{2}"',
            body,
        )
        self.assertIn(
            'str.format("FILTER OFF · ALL ALLOWED\\nWR edge {0,number,+#.2;-#.2}pp\\nAvg edge {1,number,+#.2;-#.2}%"',
            body,
        )
        self.assertIn(
            'str.format("FILTER OFF · ALL ALLOWED\\nWR {0,number,#.2}% · no gate"',
            body,
        )
        self.assertIn(
            '_headline + str.format("\\nWR {0,number,#.2}% {1} {2,number,#.2}% {3}"',
            body,
        )
        self.assertIn('"STATS OFF · ALL ALLOWED\\nNo quality verdict"', body)
        self.assertIn('str.format("{0} · WAITING\\nNo quality verdict"', body)
        self.assertIn('str.format("{0} · STALE\\nNeed fresh evidence"', body)
        self.assertNotIn("pp · Avg edge", body)
        self.assertNotIn("WAITING\\nNo quality verdict\\n", body)
        self.assertNotIn("STALE\\nNeed fresh evidence\\n", body)
        self.assertNotRegex(body, r'"[^"\n]*(?:\\n[^"\n]*){3}')

    def test_strategy_stats_adaptive_and_fixed_source_contracts_are_explicit(self) -> None:
        # Active Production is the only harness mode that may resolve a parent.
        # Raw, stats-off, filter-off and Fixed retain the requested Stats Mode bucket;
        # Fixed is guaranteed by the production resolver's Adaptive-only condition.
        self.assertIn("harness_use_production and not harness_raw_exit and enable_stats and enable_stats_filter", self.generated)
        self.assertIn('stats_sample_policy == "Adaptive" and stats_mode == "Ranking"', self.generated)
        self.assertIn('stats_sample_policy == "Fixed (Legacy)" or _stats.get_count() >= 5', self.generated)
        self.assertIn("f_harness_get_requested_stats(_use_buy, _use_mtf, _use_div, _use_ext, _grade)", self.generated)
        self.assertIn("f_harness_get_requested_target(_use_buy, _use_mtf, _use_div, _use_ext, _grade)", self.generated)
        self.assertIn('string _evidence_source = ""', self.generated)
        self.assertIn('str.format("{0} [Score {1}] → Type"', self.generated)

    def test_every_harness_stats_render_call_carries_the_selected_target(self) -> None:
        expected = (
            "f_stats_sample_text(_stats, _target)",
            "f_stats_gate_paths(_stats, _is_buy, _target)",
            "f_stats_direct_readout(_stats, _use_buy, _target)",
            "f_stats_direct_color(_stats, _use_buy, _target)",
            "f_harness_raw_stats_readout(_stats, _use_buy, _target)",
        )
        for call in expected:
            with self.subTest(call=call):
                self.assertIn(call, self.generated)
        for legacy_call in (
            "f_stats_sample_text(_stats)",
            "f_stats_gate_paths(_stats, _is_buy)",
            "f_stats_direct_readout(_stats, _use_buy)",
            "f_stats_direct_color(_stats, _use_buy)",
            "f_harness_raw_stats_readout(_stats, _use_buy)",
        ):
            with self.subTest(legacy_call=legacy_call):
                self.assertNotIn(legacy_call, self.generated)

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
                        rf'strategy\.entry\("{side}", strategy\.{side.lower()},[^\n]+\n'
                        rf"[ \t]+{sl_var} := {snapshot_sl}\n"
                        rf"[ \t]+{tp_var} := {snapshot_tp}\n"
                        r"(?:[ \t]+//[^\n]*\n)*"
                        rf"[ \t]+if harness_use_risk_exits and \(not na\({sl_var}\) or not na\({tp_var}\)\)\n"
                        rf'[ \t]+strategy\.exit\("{side} Exit", from_entry="{side}", '
                        rf'stop={sl_var}, limit={tp_var}, comment="ATR EXIT {side.upper()}", alert_message='
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
                r'(?m)^if harness_use_risk_exits and harness_action == "Idle"$\n'
                r"[ \t]+if strategy\.position_size > 0 and \(not na\(harness_long_sl_price\) or not na\(harness_long_tp_price\)\)\n"
                r'[ \t]+strategy\.exit\("Long Exit", from_entry="Long"'
            ),
        )

    def test_max_holding_bars_realizes_exactly_n_bars(self) -> None:
        # Contract: strategy.close fills at the NEXT bar's open, so the time exit
        # triggers at held bar N-1 to realize exactly N held bars. Default 0 skips
        # the block entirely via the > 0 gate.
        self.assertIn(
            "harness_time_exit_due = harness_max_holding_bars > 0 and strategy.opentrades > 0",
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
