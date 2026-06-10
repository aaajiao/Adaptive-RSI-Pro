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
