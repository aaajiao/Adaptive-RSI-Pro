"""Execute the harness's small scalar decision layer directly from generated Pine.

This intentionally does not emulate TradingView fills. It exercises the actual
Pine branch conditions and expressions, rather than a second action-policy
implementation. Broker fill timing, gaps and commission accounting still need
TradingView verification.
"""

from __future__ import annotations

import ast
import operator
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import generate_strategy_harness as gen  # noqa: E402


def translate_ternary(expression: str) -> str:
    """Translate the top-level, right-associative Pine ternary subset we use."""
    depth = 0
    quoted = False
    escaped = False
    question = None
    nested = 0
    for index, char in enumerate(expression):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quoted:
            escaped = True
            continue
        if char == '"':
            quoted = not quoted
        if quoted:
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif depth == 0 and char == "?":
            if question is None:
                question = index
            else:
                nested += 1
        elif depth == 0 and char == ":" and question is not None:
            if nested:
                nested -= 1
            else:
                condition = translate_ternary(expression[:question].strip())
                yes = translate_ternary(expression[question + 1:index].strip())
                no = translate_ternary(expression[index + 1:].strip())
                return f"({yes} if {condition} else {no})"
    if question is not None:
        raise AssertionError(f"Unmatched ternary: {expression}")
    return expression


def scalar(expression: str, values: dict):
    """Evaluate only explicitly supported scalar AST nodes; reject all others."""
    operations = {
        ast.Add: operator.add, ast.Sub: operator.sub,
        ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Eq: operator.eq, ast.NotEq: operator.ne,
        ast.Lt: operator.lt, ast.LtE: operator.le,
        ast.Gt: operator.gt, ast.GtE: operator.ge,
    }

    def dotted(node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return dotted(node.value) + "." + node.attr
        raise AssertionError(f"Unsupported name: {ast.dump(node)}")

    def evaluate(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, (ast.Name, ast.Attribute)):
            name = dotted(node)
            if name in ("true", "false"):
                return name == "true"
            return values[name]
        if isinstance(node, ast.IfExp):
            return evaluate(node.body if evaluate(node.test) else node.orelse)
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(evaluate(value) for value in node.values)
            if isinstance(node.op, ast.Or):
                return any(evaluate(value) for value in node.values)
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return not evaluate(node.operand)
            if isinstance(node.op, ast.USub):
                return -evaluate(node.operand)
        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            return operations[type(node.op)](evaluate(node.left), evaluate(node.right))
        if isinstance(node, ast.Compare):
            left = evaluate(node.left)
            for op, right_node in zip(node.ops, node.comparators):
                right = evaluate(right_node)
                if not operations[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.Call) and dotted(node.func) == "str.format":
            # Metric tests inspect the numeric value passed to formatting.
            args = [evaluate(arg) for arg in node.args]
            if len(args) != 2:
                raise AssertionError("Only single-value metric formatting is supported")
            return args[1]
        raise AssertionError(f"Unsupported scalar Pine expression: {ast.dump(node)}")

    return evaluate(ast.parse(translate_ternary(expression), mode="eval").body)


def assignment(source: str, name: str) -> str:
    matches = re.findall(rf"(?m)^\s*(?:bool |int |float |string )?{re.escape(name)} = (.+)$", source)
    if len(matches) != 1:
        raise AssertionError(f"Expected one assignment for {name}, found {len(matches)}")
    return matches[0]


class HarnessExecutionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = gen.generate(gen.DEFAULT_SOURCE.read_text(encoding="utf-8"))
        cls.planner = re.search(
            r"(?m)^f_harness_action\([^\n]+\) =>\n((?:[ ]+[^\n]*\n|\n)+)",
            cls.source,
        ).group(1)
        cls.branches = re.findall(
            r'^    (?:if (.+)|else if (.+)|(else))\n        ("[^"\n]+")$',
            cls.planner,
            re.MULTILINE,
        )
        # Fail closed if the function grows beyond this intentionally tiny subset.
        consumed = re.sub(
            r'^    (?:if .+|else if .+|else)\n        "[^"\n]+"\n?',
            "", cls.planner, flags=re.MULTILINE,
        )
        if consumed.strip() or not cls.branches:
            raise AssertionError("Planner changed beyond supported scalar branch syntax")

    def action(self, *, entry=0, exit=0, position=0, long=True,
               short=False, ready=True, date=False, time=False):
        values = dict(_entry_dir=entry, _exit_dir=exit,
                      _position_dir=position, _allow_long=long,
                      _allow_short=short, _entry_ready=ready,
                      _date_exit=date, _time_exit=time)
        for first, later, otherwise, result in self.branches:
            if otherwise or scalar(first or later, values):
                return ast.literal_eval(result)
        self.fail("Planner has no matching return")

    def signal_direction(self, buy, sell):
        return scalar(assignment(self.source, "strategy_signal_dir"),
                      {"strategy_buy_signal": buy, "strategy_sell_signal": sell})

    def exit_candidates(self, **overrides):
        values = dict(enable_mtf=True, oversold_resonance=False,
                      overbought_resonance=False, raw_extreme_oversold=False,
                      raw_extreme_overbought=False, pct_allows_buy=True,
                      pct_allows_sell=True, enable_divergence=True,
                      bullish_divergence=False, bearish_divergence=False,
                      was_extreme_oversold=False, was_extreme_overbought=False,
                      raw_normal_oversold=False, raw_normal_overbought=False,
                      normal_signal_mode="Smart", show_normal_signals=False,
                      weekly_data_ready=False, signal_data_ready=False,
                      trend_allows_buy=False, trend_allows_sell=False,
                      harness_exit_signal_policy="Raw", strategy_signal_dir=0)
        values.update(overrides)
        names = [f"harness_exit_{side}_{kind}"
                 for side in ("buy", "sell")
                 for kind in ("mtf", "div", "ext", "norm")]
        names += ["harness_raw_exit_buy_signal", "harness_raw_exit_sell_signal",
                  "harness_raw_exit_signal_dir", "harness_exit_signal_dir"]
        for name in names:
            values[name] = scalar(assignment(self.source, name), values)
        return values

    def test_date_then_time_exit_precedes_an_eligible_reversal(self):
        for position in (-1, 1):
            with self.subTest(position=position):
                values = dict(entry=-position, exit=-position, position=position,
                              long=True, short=True)
                self.assertEqual(self.action(**values, date=True, time=True), "Evaluation End")
                self.assertEqual(self.action(**values, time=True), "Time Exit")
                self.assertEqual(self.action(**values), "Short" if position == 1 else "Long")

    def test_raw_sell_closes_long_when_entry_gate_or_data_blocks_entry(self):
        values = self.exit_candidates(raw_extreme_overbought=True)
        self.assertFalse(values["weekly_data_ready"])
        self.assertFalse(values["trend_allows_sell"])
        self.assertEqual(self.action(entry=values["strategy_signal_dir"], exit=values["harness_exit_signal_dir"],
                                     position=1, ready=False), "Close Long")
        values["harness_exit_signal_policy"] = "Filtered (Legacy)"
        filtered_exit = scalar(assignment(self.source, "harness_exit_signal_dir"), values)
        self.assertEqual(self.action(entry=0, exit=filtered_exit, position=1, ready=False), "Idle")

    def test_raw_exit_priority_and_explicit_options_are_preserved(self):
        values = self.exit_candidates(raw_extreme_overbought=True,
                                      overbought_resonance=True,
                                      bearish_divergence=True,
                                      was_extreme_overbought=True,
                                      raw_normal_overbought=True)
        self.assertEqual([values[f"harness_exit_sell_{kind}"]
                          for kind in ("mtf", "div", "ext", "norm")],
                         [True, False, False, False])
        values = self.exit_candidates(raw_extreme_overbought=True,
                                      bearish_divergence=True,
                                      was_extreme_overbought=True)
        self.assertTrue(values["harness_exit_sell_div"])
        self.assertFalse(values["harness_exit_sell_ext"])
        self.assertFalse(self.exit_candidates(raw_extreme_overbought=True,
                                              pct_allows_sell=False)["harness_raw_exit_sell_signal"])
        self.assertFalse(self.exit_candidates(bearish_divergence=True,
                                              was_extreme_overbought=False)["harness_raw_exit_sell_signal"])

    def test_raw_normal_exit_ignores_weekly_smart_hiding_but_respects_off(self):
        values = self.exit_candidates(raw_normal_overbought=True)
        self.assertFalse(values["show_normal_signals"])
        self.assertTrue(values["harness_exit_sell_norm"])
        self.assertEqual(self.action(exit=values["harness_exit_signal_dir"],
                                     position=1, ready=False), "Close Long")
        disabled = self.exit_candidates(raw_normal_overbought=True, normal_signal_mode="Off")
        self.assertFalse(disabled["harness_raw_exit_sell_signal"])

    def test_unprotected_exit_stream_does_not_change_baseline_entry_stream(self):
        values = self.exit_candidates(raw_extreme_overbought=True)
        values.update(sig_sell_mtf=False, sig_sell_div=False,
                      sig_sell_extreme=False, sig_sell_normal=False)
        self.assertTrue(values["harness_raw_exit_sell_signal"])
        self.assertFalse(scalar(assignment(self.source, "raw_strategy_sell_signal"), values))
        self.assertEqual(self.action(entry=0, exit=values["harness_exit_signal_dir"],
                                     position=0, ready=False), "Idle")

    def test_raw_exit_snapshot_uses_exit_candidate_type_and_ignores_data_overlay(self):
        values = self.exit_candidates(bearish_divergence=True, was_extreme_overbought=True)
        values.update(harness_raw_exit=True, harness_use_production=True,
                      harness_forced_exit=False, enable_stats=True, enable_stats_filter=True)
        snapshot = re.search(r"(?m)^f_harness_gate_snapshot\(\) =>\n((?:[ ]+[^\n]*\n|\n)+)",
                             self.source).group(1)
        for name in ("_read_raw", "_buy_mtf", "_buy_div", "_buy_ext", "_buy_norm",
                     "_sell_mtf", "_sell_div", "_sell_ext", "_sell_norm",
                     "_has_buy", "_has_sell", "_direction", "_use_buy", "_use_resolved"):
            values[name] = scalar(assignment(snapshot, name), values)
        self.assertEqual(values["_direction"], -1)
        self.assertFalse(values["_use_buy"])
        self.assertTrue(values["_sell_div"])
        self.assertFalse(values["_sell_mtf"])
        self.assertFalse(values["_sell_ext"])
        self.assertFalse(values["_use_resolved"])
        type_expression = re.search(r"(?m)^f_get_signal_type_label\([^\n]+\) =>\n    (.+)$",
                                    self.source).group(1)
        self.assertEqual(scalar(type_expression, {"_is_mtf": values["_sell_mtf"],
                                                 "_is_div": values["_sell_div"],
                                                 "_is_ext": values["_sell_ext"]}), "DIV")
        data_override = re.search(r'else if (.+)\n        _source := "Data"', snapshot).group(1)
        self.assertFalse(scalar(data_override, values))

    def test_long_only_and_short_only_exit_without_reversing(self):
        self.assertEqual(self.action(entry=-1, exit=-1, position=1), "Close Long")
        self.assertEqual(self.action(entry=1, exit=1, position=-1, long=False, short=True), "Close Short")
        self.assertEqual(self.action(entry=-1, position=0), "Idle")
        self.assertEqual(self.action(entry=1, position=0, long=False, short=True), "Idle")

    def test_both_sides_reverse_once_and_same_side_never_pyramids(self):
        for position in (-1, 1):
            with self.subTest(position=position):
                self.assertEqual(self.action(entry=-position, position=position, short=True),
                                 "Short" if position == 1 else "Long")
                self.assertEqual(self.action(entry=position, position=position, short=True), "Idle")

    def test_simultaneous_directions_are_conflicts_and_do_not_trade(self):
        self.assertEqual(self.signal_direction(True, True), 0)
        self.assertEqual(self.signal_direction(False, False), 0)
        self.assertEqual(self.signal_direction(True, False), 1)
        self.assertEqual(self.signal_direction(False, True), -1)
        for position in (-1, 0, 1):
            self.assertEqual(self.action(entry=self.signal_direction(True, True),
                                         exit=0, position=position, short=True), "Idle")

    def dates(self, *, enabled=True, start=100, end=200, opened=100, closed=110):
        values = dict(harness_use_date_range=enabled, harness_start_time=start,
                      harness_end_time=end, time=opened, time_close=closed)
        for name in ("harness_dates_valid", "harness_training", "harness_evaluation_ended", "harness_in_evaluation"):
            values[name] = scalar(assignment(self.source, name), values)
        return values

    def test_evaluation_boundaries_and_invalid_dates(self):
        self.assertTrue(self.dates(opened=100)["harness_in_evaluation"])
        self.assertFalse(self.dates(opened=99)["harness_in_evaluation"])
        self.assertTrue(self.dates(closed=199)["harness_in_evaluation"])
        at_end = self.dates(closed=200)
        self.assertFalse(at_end["harness_in_evaluation"])
        self.assertTrue(at_end["harness_evaluation_ended"])
        for start in (200, 201):
            result = self.dates(start=start)
            self.assertFalse(result["harness_dates_valid"])
            self.assertFalse(result["harness_in_evaluation"])
        self.assertTrue(self.dates(enabled=False, start=500, end=10)["harness_in_evaluation"])

    def test_new_entries_require_confirmed_ready_data_and_evaluation(self):
        for confirmed, data, window in ((True, True, True), (False, True, True),
                                        (True, False, True), (True, True, False)):
            values = {"barstate.isconfirmed": confirmed, "signal_data_ready": data,
                      "harness_in_evaluation": window}
            ready = scalar(assignment(self.source, "harness_entry_ready"), values)
            self.assertEqual(self.action(entry=1, ready=ready),
                             "Long" if confirmed and data and window else "Idle")
            self.assertEqual(self.action(exit=-1, position=1, ready=ready), "Close Long")

    def test_closed_trade_metrics_reuse_net_results_without_double_fees(self):
        # Profitable, losing and break-even trades all count in the denominator;
        # a large open loss must neither become a closed loss nor disappear.
        values = {"harness_closed_n": 4, "strategy.wintrades": 2,
                  "strategy.netprofit": -20.0, "strategy.grossprofit": 60.0,
                  "strategy.grossloss": 80.0, "strategy.openprofit": -500.0}
        self.assertEqual(scalar(assignment(self.source, "harness_wr_text"), values), 50.0)
        self.assertEqual(scalar(assignment(self.source, "harness_avg_text"), values), -5.0)
        self.assertEqual(scalar(assignment(self.source, "harness_pf_text"), values), 0.75)
        self.assertIn("strategy.openprofit, harness_open_bars", self.source)
        metric_region = self.source[self.source.index("harness_closed_n ="):self.source.index('"Trade Results\\n')]
        self.assertNotIn("commission", metric_region)
        values["harness_closed_n"] = 0
        self.assertEqual(scalar(assignment(self.source, "harness_wr_text"), values), "—")
        self.assertEqual(scalar(assignment(self.source, "harness_avg_text"), values), "—")

    def test_each_action_dispatches_only_one_market_order(self):
        block = gen.STRATEGY_EXECUTION_BLOCK
        self.assertIn("if barstate.isconfirmed\n", block)
        branches = re.findall(
            r"(?m)^    (?:if|else if) (harness_action[^\n]+)\n((?:[ ]{8}[^\n]*\n|\n)+)",
            block,
        )
        self.assertEqual(len(branches), 5)
        self.assertEqual(
            len(re.findall(r"strategy\.(?:entry|close)\(", block)),
            sum(len(re.findall(r"strategy\.(?:entry|close)\(", body))
                for _, body in branches),
            "Every market order must belong to one selected action branch",
        )
        for action in ("Evaluation End", "Time Exit", "Long", "Short", "Close Long", "Close Short", "Idle"):
            matching = [body for condition, body in branches
                        if scalar(condition, {"harness_action": action})]
            commands = [command for body in matching
                        for command in re.findall(r"strategy\.(entry|close)\(", body)]
            self.assertEqual(len(commands), 0 if action == "Idle" else 1, action)
            if action in ("Long", "Short"):
                self.assertEqual(commands, ["entry"])
        self.assertIn('if harness_use_risk_exits and harness_action == "Idle"', block)


if __name__ == "__main__":
    unittest.main()
