"""Evaluate the production coverage/deduplication predicates on missing-data cases.

These checks execute extracted scalar expressions, not a separate signal model.
TradingView remains the compiler and the authority for request data availability.
"""

from __future__ import annotations

import itertools
import re
import unittest
from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[1] / "adaptive_rsi.pine").read_text()


def expression(name: str) -> str:
    match = re.search(rf"^(?:bool )?{re.escape(name)} = (.+)$", SOURCE, re.M)
    if match is None:
        raise AssertionError(f"Missing production predicate: {name}")
    value = match[1]
    # These expressions only use flat parenthesized Pine ternaries.
    value = re.sub(r"\(([^()?]+) \? ([^():?]+) : ([^():?]+)\)", r"(\2 if \1 else \3)", value)
    return value


def evaluate(name: str, state: dict) -> object:
    return eval(expression(name), {"__builtins__": {}}, state)


def mtf_state(chart: int, requested: tuple[int, int, int], statuses: tuple[int, int, int, int]) -> dict:
    state = dict(chart_tf_seconds=chart, enable_mtf=True, f_tf_seconds=lambda seconds: seconds)
    state["status_current"] = statuses[0]
    for i, (tf, status) in enumerate(zip(requested, statuses[1:]), 1):
        state[f"active_tf{i}"] = tf
        state[f"status_tf{i}"] = status
        state[f"mtf_data_ok_tf{i}"] = status is not None
        state[f"tf{i}_is_current"] = evaluate(f"tf{i}_is_current", state)
    for name in ("tf1_is_unique", "tf2_is_unique", "tf3_is_unique", "valid_tf_count", "mtf_context_ready", "oversold_count", "overbought_count", "oversold_weighted", "overbought_weighted", "max_weighted", "oversold_resonance", "overbought_resonance"):
        state[name] = evaluate(name, state)
    return state


class DataContextTest(unittest.TestCase):
    def test_daily_alias_and_auto_4h_require_all_three_contexts(self):
        for chart, requested in ((86400, (3600, 14400, 86400)), (14400, (900, 3600, 14400))):
            for first, second in itertools.product((None, -1, 0, 1), repeat=2):
                with self.subTest(chart=chart, first=first, second=second):
                    state = mtf_state(chart, requested, (1, first, second, 1))
                    self.assertEqual(state["valid_tf_count"], 3)
                    self.assertEqual(state["oversold_resonance"], first == second == 1)

    def test_manual_duplicates_have_one_vote_and_keep_highest_slot(self):
        state = mtf_state(14400, (3600, 3600, 86400), (1, 1, 1, 0))
        self.assertEqual(state["valid_tf_count"], 3)
        self.assertEqual(state["oversold_count"], 2)
        self.assertFalse(state["oversold_resonance"])
        all_same = mtf_state(14400, (3600, 3600, 3600), (1, 1, 1, 1))
        self.assertEqual(all_same["valid_tf_count"], 2)
        self.assertEqual(all_same["oversold_weighted"], 3)
        self.assertTrue(all_same["oversold_resonance"])

    def test_chart_alone_cannot_claim_multi_timeframe_resonance(self):
        state = mtf_state(14400, (14400, 14400, 14400), (1, 1, 1, 1))
        self.assertEqual(state["valid_tf_count"], 1)
        self.assertFalse(state["oversold_resonance"])

    def test_every_context_is_required_even_with_trend_filter_off(self):
        for chart, weekly, mtf in itertools.product((False, True), repeat=3):
            state = dict(chart_data_ready=chart, weekly_data_ready=weekly, mtf_context_ready=mtf, enable_trend_protection=False)
            self.assertEqual(evaluate("signal_data_ready", state), chart and weekly and mtf)

    def test_divergence_uses_directional_protection(self):
        for side in ("buy", "sell"):
            for enabled, allowed in itertools.product((False, True), repeat=2):
                state = {"enable_divergence": True, "bullish_divergence": True, "bearish_divergence": True, "was_extreme_oversold": True, "was_extreme_overbought": True, "enable_trend_protection": enabled, f"trend_allows_{side}": allowed, f"raw_sig_{side}_mtf": False}
                self.assertEqual(evaluate(f"raw_sig_{side}_div", state), not enabled or allowed)

    def test_missing_context_cannot_be_bypassed_by_a_passing_stats_gate(self):
        for side, kind in itertools.product(("buy", "sell"), ("mtf", "div", "ext", "norm")):
            state = {"signal_data_ready": False, "true": True, "false": False, f"{side}_{kind}_stats": object(), f"{side}_{kind}_stats_target": 8, "f_passes_stats_filter": lambda *args: True}
            self.assertFalse(evaluate(f"filter_{side}_{kind}", state))

    def test_samples_and_baseline_use_entry_eligibility_not_future_context(self):
        block = SOURCE.split("// STATISTICS CALCULATION", 1)[1].split("// STATISTICS-DRIVEN FILTER", 1)[0]
        guard = re.search(r"^if enable_stats[^\n]+", block, re.M)[0]
        self.assertIn("signal_data_ready[stats_forward_bars]", guard)
        self.assertNotIn("and signal_data_ready and", guard)
        self.assertIn("baseline_buy_bucket.update(true", block)
        self.assertIn("sig_buy_mtf[stats_forward_bars]", block)
        self.assertNotIn("alert_buy_mtf[stats_forward_bars]", block)

    def test_missing_requests_never_become_neutral_or_chart_fallback(self):
        self.assertIn("? int(na) : _rsi < _p10", SOURCE)
        self.assertIn("array.get(_values, _size - 1) : int(na)", SOURCE)
        self.assertIn("_available = not na(_status)", SOURCE)
        self.assertNotIn("nz(_htf_status, _current)", SOURCE)
        self.assertNotIn("WEEKLY_REQUEST_BARS", SOURCE)

    def test_intrabar_budget_supports_more_than_four_mature_mtf_samples(self):
        budget = int(re.search(r"^MAX_REQUEST_BARS = (\d+)$", SOURCE, re.M)[1])
        self.assertLessEqual(budget, 100000)
        # Default BTC 4H -> 15m: allow a conservative 1000-intrabar warmup,
        # a 20-chart-bar return horizon, and 20-bar independent sample spacing.
        theoretical_capacity = int(((budget - 1000) / 16 - 20) // 20)
        self.assertGreaterEqual(theoretical_capacity, 50)


if __name__ == "__main__":
    unittest.main()
