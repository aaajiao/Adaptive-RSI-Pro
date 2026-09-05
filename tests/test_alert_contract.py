"""Regression fixtures for alert delivery and the emitted decision JSON.

The fixtures execute the production reset/eligibility expressions and JSON
concatenation statements. They do not execute Pine or model broker fills; live
TradingView compilation and delivery still need separate verification.
"""

from __future__ import annotations

import json
import re
import textwrap
import unittest
from pathlib import Path
from types import SimpleNamespace


SOURCE = (Path(__file__).resolve().parents[1] / "adaptive_rsi.pine").read_text()


def assignment(name: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(name)} = (.+)$", SOURCE)
    if match is None:
        raise AssertionError(f"Missing production assignment: {name}")
    return match.group(1)


def function_body(name: str) -> str:
    match = re.search(rf"(?m)^{re.escape(name)}\([^\n]+\) =>\n((?:    [^\n]*\n|\n)+)", SOURCE)
    if match is None:
        raise AssertionError(f"Missing production function: {name}")
    return textwrap.dedent(match.group(1)).strip()


class PineStrings:
    """The small string API surface used by the production JSON serializer."""

    replace_all = staticmethod(lambda value, target, replacement: value.replace(target, replacement))
    substring = staticmethod(lambda value, start, end: value[start:end])
    length = staticmethod(len)

    @staticmethod
    def match(value: str, pattern: str) -> str:
        result = re.search(pattern, value)
        return result.group(0) if result else ""

    @staticmethod
    def tostring(value: int | float, number_format: str | None = None) -> str:
        if number_format is None:
            return str(value)
        if number_format != "0.################":
            raise AssertionError(f"Review changed numeric format: {number_format}")
        return format(value, ".16f").rstrip("0").rstrip(".")


def source_json_string(value: str) -> str:
    """Run the actual escape statements, including their control-code loop."""
    lines = function_body("f_alert_json_string").splitlines()
    translated = []
    for line in lines[:-1]:
        line = line.replace(" := ", " = ")
        loop = re.fullmatch(r"(\s*)for (\w+) = (\d+) to (\d+)", line)
        if loop:
            indent, variable, start, end = loop.groups()
            line = f"{indent}for {variable} in range({start}, {int(end) + 1}):"
        elif line.lstrip().startswith("if "):
            line += ":"
        translated.append(line)
    translated.append("result = " + lines[-1])
    namespace = {"_value": value, "str": PineStrings, "int": int, "range": range}
    exec("\n".join(translated), {"__builtins__": {}}, namespace)
    return namespace["result"]


def source_scalar(name: str, value: object) -> str:
    condition, _, choices = function_body(name).partition(" ? ")
    true_value, _, false_value = choices.partition(" : ")
    namespace = {"_value": value, "na": lambda item: item is None, "str": PineStrings}
    chosen = true_value if eval(condition, {"__builtins__": {}}, namespace) else false_value
    return eval(chosen, {"__builtins__": {}}, namespace)


def source_event_id(namespace: dict) -> str:
    expression = function_body("f_alert_event_id").replace(
        '(_is_buy ? "BUY" : "SELL")', '("BUY" if _is_buy else "SELL")'
    )
    return eval(expression, {"__builtins__": {}}, {**namespace, "str": PineStrings})


class AlertRuntime:
    """Feed bar/tick fixtures through the source's delivery predicates."""

    def __init__(self, on_close: bool):
        self.state = {"alert_state_bar": None, "buy_alert_level_sent": 0, "sell_alert_level_sent": 0}
        self.on_close = on_close
        reset = re.search(r"(?m)^if (na\(alert_state_bar\)[^\n]+)\n((?:    [^\n]+\n)+)", SOURCE)
        if reset is None:
            raise AssertionError("Missing bar-index reset")
        self.reset_condition, self.reset_body = reset.groups()

    def step(self, bar: int, buy: int = 0, sell: int = 0, confirmed: bool = True) -> list[str]:
        namespace = {
            **self.state,
            "na": lambda item: item is None,
            "bar_index": bar,
            # Close-only strategies need not observe barstate.isnew == true.
            "barstate": SimpleNamespace(isnew=False, isconfirmed=confirmed),
            "alert_on_close": self.on_close,
            "alert_has_buy": buy > 0,
            "alert_has_sell": sell > 0,
            "current_buy_level": buy,
            "current_sell_level": sell,
        }
        if eval(self.reset_condition, {"__builtins__": {}}, namespace):
            exec(textwrap.dedent(self.reset_body).replace(" := ", " = "), {"__builtins__": {}}, namespace)
        namespace["alert_conflict"] = eval(assignment("alert_conflict"), {"__builtins__": {}}, namespace)
        sent = []
        for direction in ("buy", "sell"):
            if eval(assignment(f"should_alert_{direction}"), {"__builtins__": {}}, namespace):
                sent.append(direction)
                namespace[f"{direction}_alert_level_sent"] = namespace[f"current_{direction}_level"]
        self.state = {name: namespace[name] for name in self.state}
        return sent


class AlertDeliveryTests(unittest.TestCase):
    def test_new_bar_resets_even_when_strategy_never_observes_opening_tick(self):
        runtime = AlertRuntime(on_close=True)
        self.assertEqual(runtime.step(100, buy=2), ["buy"])
        self.assertEqual(runtime.step(101, buy=2), ["buy"])
        self.assertEqual(runtime.step(102, sell=2), ["sell"])

    def test_default_close_delivery_ignores_transient_and_duplicate_ticks(self):
        runtime = AlertRuntime(on_close=True)
        self.assertEqual(runtime.step(100, buy=1, confirmed=False), [])
        self.assertEqual(runtime.step(100, buy=4, confirmed=False), [])
        self.assertEqual(runtime.step(100, buy=2), ["buy"])
        self.assertEqual(runtime.step(100, buy=2), [])

    def test_intrabar_opt_in_sends_upgrades_once_without_sending_downgrades(self):
        runtime = AlertRuntime(on_close=False)
        results = [runtime.step(100, buy=level, confirmed=False) for level in (1, 1, 2, 1, 4, 4)]
        self.assertEqual(results, [["buy"], [], ["buy"], [], ["buy"], []])
        self.assertEqual(SOURCE.count("alert(msg, alert.freq_all)"), 2)
        self.assertNotIn("alert(msg, alert.freq_once_per_bar)", SOURCE)

    def test_simultaneous_directions_emit_neither_then_next_bar_can_send(self):
        runtime = AlertRuntime(on_close=True)
        self.assertEqual(runtime.step(100, buy=4, sell=2), [])
        self.assertEqual(runtime.step(101, buy=4), ["buy"])

    def test_later_intrabar_conflict_does_not_emit_second_action(self):
        runtime = AlertRuntime(on_close=False)
        self.assertEqual(runtime.step(100, buy=2, confirmed=False), ["buy"])
        self.assertEqual(runtime.step(100, buy=4, sell=3, confirmed=False), [])


class AlertSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.context = {
            "SCRIPT_VERSION": "7.7", "syminfo": SimpleNamespace(tickerid='TEST:A"\\B'),
            "timeframe": SimpleNamespace(period="240"), "time": 1788566400000,
            "time_close": 1788580800000, "timenow": 1788580800123, "close": 123.25,
            "barstate": SimpleNamespace(isconfirmed=True), "signal_data_ready": True,
            "_is_buy": True, "_level": 2, "_direction": "BUY", "_kind": "EXT", "_grade": "A",
            "stats_forward_bars": 20, "_requested_source": "Ranking:EXT BUY [Score A]",
            "_resolved_source": "Signal Type:EXT BUY", "_uses_parent": True,
            "_lifetime_n": 15, "_effective_n": 12.5, "_target": 12,
            "_readiness": "READY", "_quality_verdict": "PASS", "_gate_active": True, "_allowed": True,
            "stats_sample_policy": "Adaptive", "stats_unproven_mode": "Block (Legacy)",
            "stats_gate_mode": "Edge vs Baseline", "stats_payoff_mode": "Off",
            "_shrinkage_weight": 0.625, "_raw_wr": 75.0, "_prior_wr": 50.0,
            "_reported_wr": 65.625, "_baseline_wr": 50.0, "_required_wr": 55.0, "_wr_edge": 15.625,
            "_wr_pass_json": "true", "_bucket_avg": 1.5, "_baseline_avg": 0.5,
            "_reported_payoff": 0.625, "stats_min_payoff_edge": 0.4,
            "_payoff_active": False, "_payoff_pass_json": "true", "_sl_price": 119.0, "_tp_price": 131.75,
        }

    def emit(self) -> dict:
        namespace = {
            **self.context,
            "f_alert_json_string": source_json_string,
            "f_alert_json_number": lambda value: source_scalar("f_alert_json_number", value),
            "f_alert_json_int": lambda value: source_scalar("f_alert_json_int", value),
            "f_alert_json_bool": lambda value: source_scalar("f_alert_json_bool", value),
            "f_alert_event_id": lambda is_buy, level: source_event_id({**self.context, "_is_buy": is_buy, "_level": level}),
        }
        # Execute the actual payload assembly, not a separately maintained dict.
        statements = [line for line in function_body("f_alert_snapshot_json").splitlines() if line.startswith("_json ")]
        for statement in statements:
            exec(statement.replace(" := ", " = "), {"__builtins__": {}}, namespace)
        return json.loads(namespace["_json"])

    def test_snapshot_is_parseable_and_keeps_decision_provenance_and_numeric_types(self):
        payload = self.emit()
        self.assertEqual(payload["schema"], "arsi.alert.v1")
        self.assertEqual(payload["tickerid"], self.context["syminfo"].tickerid)
        self.assertEqual(payload["bar_time"], 1788566400000)
        self.assertTrue(payload["confirmed"])
        evidence = payload["evidence"]
        self.assertEqual(evidence["requested_source"], "Ranking:EXT BUY [Score A]")
        self.assertEqual(evidence["resolved_source"], "Signal Type:EXT BUY")
        self.assertEqual(evidence["effective_n"], 12.5)
        self.assertEqual(evidence["adjusted_wr_pct"], 65.625)
        self.assertIs(evidence["wr_pass"], True)
        self.assertIs(evidence["payoff_active"], False)
        self.assertEqual(payload["risk"]["sl_price"], 119.0)
        self.assertIs(payload["risk"]["hints_only"], True)

    def test_missing_estimates_and_unknown_close_time_are_json_null(self):
        self.context.update(time_close=None, _reported_wr=None, _reported_payoff=None,
                            _wr_pass_json="null", _payoff_pass_json="null", _readiness="WAITING",
                            _quality_verdict="NO_VERDICT")
        payload = self.emit()
        self.assertIsNone(payload["bar_time_close"])
        self.assertIsNone(payload["evidence"]["adjusted_wr_pct"])
        self.assertIsNone(payload["evidence"]["payoff_pass"])
        self.assertEqual(payload["evidence"]["quality_verdict"], "NO_VERDICT")

    def test_every_ascii_control_character_and_backslash_quote_round_trip(self):
        value = 'prefix"\\' + "".join(chr(code) for code in range(32)) + "标的"
        self.assertEqual(json.loads(source_json_string(value)), value)
        self.context["syminfo"] = SimpleNamespace(tickerid=value)
        self.assertEqual(self.emit()["tickerid"], value)

    def test_event_id_is_stable_across_ticks_and_changes_for_direction_or_upgrade(self):
        first = source_event_id(self.context)
        self.context.update(timenow=1788580800999, close=130.0)
        self.assertEqual(source_event_id(self.context), first)
        self.assertNotEqual(source_event_id({**self.context, "_level": 4}), first)
        self.assertNotEqual(source_event_id({**self.context, "_is_buy": False}), first)
        self.assertNotEqual(source_event_id({**self.context, "time": 1788580800000}), first)


if __name__ == "__main__":
    unittest.main()
