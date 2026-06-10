#!/usr/bin/env python3
"""Unit tests for the homegrown Pine Script linter (tools/pine_linter).

Stdlib unittest only. Each rule gets:
  - known-violation fixtures asserting the issue fires on the right line
  - known-clean fixtures asserting no false positive (including the
    var/varip mutable-state declarations that NAM001 used to flag)

Plus a regression test that lints the repo's adaptive_rsi.pine with the
repo's .pine-lint.yml and asserts 0 errors, 0 warnings and 0 NAM001 issues.
"""

import sys
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.pine_linter.config import load_config  # noqa: E402
from tools.pine_linter.linter import PineLinter  # noqa: E402
from tools.pine_linter.rules import RULES_BY_ID  # noqa: E402


def fixture(source: str) -> str:
    """Dedent a triple-quoted fixture so line 1 is the first code line."""
    return textwrap.dedent(source).lstrip("\n")


def run_rule(rule_id: str, source: str):
    rule = RULES_BY_ID[rule_id]
    return rule.check(source.split("\n"), source)


class TestSEC001SafeLookahead(unittest.TestCase):
    def test_missing_lookahead_fires(self):
        src = fixture(
            """
            //@version=6
            indicator("t")
            htf = request.security(syminfo.tickerid, "W", close)
            """
        )
        issues = run_rule("SEC001", src)
        self.assertEqual(1, len(issues))
        self.assertEqual("SEC001", issues[0].rule_id)
        self.assertEqual(3, issues[0].line)
        self.assertIn("lookahead", issues[0].message)

    def test_lookahead_on_without_offset_fires(self):
        src = fixture(
            """
            htf = request.security(syminfo.tickerid, "W", close, lookahead=barmerge.lookahead_on)
            """
        )
        issues = run_rule("SEC001", src)
        self.assertEqual(1, len(issues))
        self.assertEqual(1, issues[0].line)
        self.assertIn("[1]", issues[0].message)

    def test_lookahead_off_is_clean(self):
        src = fixture(
            """
            htf = request.security(syminfo.tickerid, "D", close, lookahead=barmerge.lookahead_off)
            """
        )
        self.assertEqual([], run_rule("SEC001", src))

    def test_lookahead_on_with_confirmed_tuple_is_clean(self):
        # Mirrors the production weekly-protection request.
        src = fixture(
            """
            [weekly_rsi, weekly_sma20] = request.security(
                syminfo.tickerid, "W",
                [ta.rsi(close, 14)[1], ta.sma(close, 20)[1]],
                lookahead=barmerge.lookahead_on,
                calc_bars_count=WEEKLY_REQUEST_BARS
            )
            """
        )
        self.assertEqual([], run_rule("SEC001", src))


class TestSEC002SecurityInCondition(unittest.TestCase):
    def test_security_inside_if_fires(self):
        src = fixture(
            """
            if barstate.isconfirmed
                htf = request.security(syminfo.tickerid, "D", close)
            """
        )
        issues = run_rule("SEC002", src)
        self.assertEqual(1, len(issues))
        self.assertEqual("SEC002", issues[0].rule_id)
        self.assertEqual(2, issues[0].line)

    def test_top_level_security_after_if_block_is_clean(self):
        src = fixture(
            """
            if cond
                x = 1
            htf = request.security(syminfo.tickerid, "D", close)
            """
        )
        self.assertEqual([], run_rule("SEC002", src))

    def test_comment_inside_if_is_clean(self):
        # Regression: a commented-out call inside a conditional must not fire.
        src = fixture(
            """
            if barstate.isconfirmed
                // request.security(syminfo.tickerid, "D", close)
                x = 1
            """
        )
        self.assertEqual([], run_rule("SEC002", src))

    def test_trailing_comment_inside_if_is_clean(self):
        # Regression: a trailing-comment mention inside a conditional.
        src = fixture(
            """
            if cond
                val := 1  // request.security is resolved upstream
            """
        )
        self.assertEqual([], run_rule("SEC002", src))


class TestSYN001MultilineTernary(unittest.TestCase):
    def test_multiline_ternary_fires(self):
        src = fixture(
            """
            value = cond ?
                 1 :
                 2
            plot(value)
            """
        )
        issues = run_rule("SYN001", src)
        self.assertEqual(1, len(issues))
        self.assertEqual("SYN001", issues[0].rule_id)
        self.assertEqual(1, issues[0].line)

    def test_single_line_ternary_is_clean(self):
        src = fixture(
            """
            value = cond ? 1 : 2
            chain = a < b ? f(c) : a == b ? d : nz(e, d)
            """
        )
        self.assertEqual([], run_rule("SYN001", src))

    def test_question_mark_in_comment_is_clean(self):
        # Regression: `?` ending a comment plus a later `:` used to pair up
        # across lines and report a phantom multi-line ternary.
        src = fixture(
            """
            // did we filter?
            src = close
            // note:
            plot(src)
            """
        )
        self.assertEqual([], run_rule("SYN001", src))


class TestSYN002SwitchDefault(unittest.TestCase):
    def test_switch_without_default_fires(self):
        src = fixture(
            """
            state = switch
                x == 1 => "one"
                x == 2 => "two"

            plot(close)
            """
        )
        issues = run_rule("SYN002", src)
        self.assertEqual(1, len(issues))
        self.assertEqual("SYN002", issues[0].rule_id)
        self.assertEqual(1, issues[0].line)

    def test_switch_with_default_is_clean(self):
        src = fixture(
            """
            state = switch
                x == 1 => "one"
                => "other"

            plot(close)
            """
        )
        self.assertEqual([], run_rule("SYN002", src))

    def test_identifier_ending_in_switch_is_clean(self):
        # Regression: `mode_switch` at end of line is not the switch keyword.
        src = fixture(
            """
            toggle = mode_switch
            f_calc(x) =>
                x + 1
            """
        )
        self.assertEqual([], run_rule("SYN002", src))

    def test_switch_in_comment_is_clean(self):
        # Regression: a comment ending in "switch" must not start a match.
        src = fixture(
            """
            // legacy switch
                a => 1
            """
        )
        self.assertEqual([], run_rule("SYN002", src))


class TestSYN003TableClearParams(unittest.TestCase):
    def test_single_arg_table_clear_fires(self):
        src = fixture(
            """
            table.clear(dashboard)
            """
        )
        issues = run_rule("SYN003", src)
        self.assertEqual(1, len(issues))
        self.assertEqual("SYN003", issues[0].rule_id)
        self.assertEqual(1, issues[0].line)

    def test_ranged_table_clear_is_clean(self):
        src = fixture(
            """
            table.clear(dashboard, 0, 0, 5, 5)
            """
        )
        self.assertEqual([], run_rule("SYN003", src))

    def test_commented_table_clear_is_clean(self):
        src = fixture(
            """
            // table.clear(dashboard)
            plot(close)
            """
        )
        self.assertEqual([], run_rule("SYN003", src))


class TestNAM001ConstantCase(unittest.TestCase):
    def test_miscased_constant_fires(self):
        src = fixture(
            """
            Max_Lookback = 500
            plot(close)
            """
        )
        issues = run_rule("NAM001", src)
        self.assertEqual(1, len(issues))
        self.assertEqual("NAM001", issues[0].rule_id)
        self.assertEqual(1, issues[0].line)
        self.assertEqual("MAX_LOOKBACK", issues[0].suggestion)

    def test_typed_miscased_constant_fires(self):
        src = fixture(
            """
            int Buffer_Size = 8
            """
        )
        issues = run_rule("NAM001", src)
        self.assertEqual(1, len(issues))
        self.assertEqual(1, issues[0].line)
        self.assertEqual("BUFFER_SIZE", issues[0].suggestion)

    def test_string_constant_with_trailing_comment_fires(self):
        src = fixture(
            """
            Plot_Title = "ARSI Pro"  // chart title
            """
        )
        issues = run_rule("NAM001", src)
        self.assertEqual(1, len(issues))
        self.assertEqual("PLOT_TITLE", issues[0].suggestion)

    def test_var_and_varip_declarations_are_clean(self):
        # Regression: these exact production declarations are persistent
        # *mutable* state, not constants, and used to be false positives.
        src = fixture(
            """
            var float prev_spread = 30.0
            var bool bullish_divergence = false
            var bool bearish_divergence = false
            var int last_buy_level = 0
            var int last_sell_level = 0
            varip int buy_alert_level_sent = 0
            varip int sell_alert_level_sent = 0
            """
        )
        self.assertEqual([], run_rule("NAM001", src))

    def test_screaming_snake_constant_is_clean(self):
        src = fixture(
            """
            MAX_REQUEST_BARS = 1400
            WEEKLY_REQUEST_BARS = 120
            """
        )
        self.assertEqual([], run_rule("NAM001", src))

    def test_lowercase_working_variables_are_clean(self):
        # Plain lowercase bindings are ordinary variables in Pine; the repo
        # uses these idioms at top level and they must not be flagged.
        src = fixture(
            """
            grp_rsi = "═══ RSI Settings / RSI设置 ═══"
            realtime_lookback = 20
            int cooldown_mtf = 1
            """
        )
        self.assertEqual([], run_rule("NAM001", src))

    def test_reassigned_name_is_clean(self):
        src = fixture(
            """
            Total_Hits = 0
            if cond
                Total_Hits := Total_Hits + 1
            """
        )
        self.assertEqual([], run_rule("NAM001", src))

    def test_non_literal_rhs_is_clean(self):
        src = fixture(
            """
            Threshold_Mix = math.max(1, 2)
            """
        )
        self.assertEqual([], run_rule("NAM001", src))

    def test_indented_assignment_is_clean(self):
        src = fixture(
            """
            f_calc(x) =>
                Inner_Limit = 5
                x + Inner_Limit
            """
        )
        self.assertEqual([], run_rule("NAM001", src))

    def test_const_qualified_lowercase_fires(self):
        # An explicit Pine v6 `const` qualifier declares constant intent,
        # so the binding is flagged even though its plain lowercase name
        # would pass the naming-style heuristic for unqualified bindings.
        src = fixture(
            """
            const int weekly_request_bars = 120
            """
        )
        issues = run_rule("NAM001", src)
        self.assertEqual(1, len(issues))
        self.assertEqual("NAM001", issues[0].rule_id)
        self.assertEqual(1, issues[0].line)
        self.assertEqual("WEEKLY_REQUEST_BARS", issues[0].suggestion)

    def test_const_qualified_screaming_snake_is_clean(self):
        src = fixture(
            """
            const int WEEKLY_REQUEST_BARS = 120
            const string PLOT_TITLE = "ARSI Pro"
            """
        )
        self.assertEqual([], run_rule("NAM001", src))

    def test_const_bypass_keeps_unqualified_and_var_handling(self):
        # The const bypass is scoped to `const`-qualified bindings only:
        # unqualified lowercase bindings and var/varip mutable state must
        # stay clean exactly as before.
        src = fixture(
            """
            const float min_edge = 1.5
            realtime_lookback = 20
            int cooldown_mtf = 1
            var float prev_spread = 30.0
            varip int buy_alert_level_sent = 0
            """
        )
        issues = run_rule("NAM001", src)
        self.assertEqual(1, len(issues))
        self.assertEqual(1, issues[0].line)
        self.assertEqual("MIN_EDGE", issues[0].suggestion)


class TestNAM002FunctionPrefix(unittest.TestCase):
    def test_unprefixed_function_fires(self):
        src = fixture(
            """
            calcScore(x) =>
                x * 2
            """
        )
        issues = run_rule("NAM002", src)
        self.assertEqual(1, len(issues))
        self.assertEqual("NAM002", issues[0].rule_id)
        self.assertEqual(1, issues[0].line)
        self.assertEqual("f_calcScore", issues[0].suggestion)

    def test_prefixed_function_is_clean(self):
        src = fixture(
            """
            f_calc_score(x) =>
                x * 2
            """
        )
        self.assertEqual([], run_rule("NAM002", src))


class TestNAM003TypeCase(unittest.TestCase):
    def test_lowercase_type_fires(self):
        src = fixture(
            """
            type signal_stats
                int wins
            """
        )
        issues = run_rule("NAM003", src)
        self.assertEqual(1, len(issues))
        self.assertEqual("NAM003", issues[0].rule_id)
        self.assertEqual(1, issues[0].line)
        self.assertEqual("SignalStats", issues[0].suggestion)

    def test_pascal_case_type_is_clean(self):
        src = fixture(
            """
            type SignalStats
                int wins
            """
        )
        self.assertEqual([], run_rule("NAM003", src))


class TestQUA001BilingualTooltip(unittest.TestCase):
    def test_english_only_tooltip_fires(self):
        src = fixture(
            """
            opt = input.bool(true, "Opt", tooltip="English only tooltip")
            """
        )
        issues = run_rule("QUA001", src)
        self.assertEqual(1, len(issues))
        self.assertEqual("QUA001", issues[0].rule_id)
        self.assertEqual(1, issues[0].line)
        self.assertIn("Chinese", issues[0].message)

    def test_chinese_only_tooltip_fires(self):
        src = fixture(
            """
            opt = input.bool(true, "Opt", tooltip="只有中文提示")
            """
        )
        issues = run_rule("QUA001", src)
        self.assertEqual(1, len(issues))
        self.assertIn("English", issues[0].message)

    def test_bilingual_tooltip_is_clean(self):
        src = fixture(
            """
            opt = input.bool(true, "Opt", tooltip="Enable filter / 启用过滤")
            """
        )
        self.assertEqual([], run_rule("QUA001", src))

    def test_bilingual_tooltip_with_escaped_quotes_is_clean(self):
        # Regression: \" inside the tooltip used to truncate the capture and
        # misreport the Chinese half as missing.
        src = fixture(
            """
            opt = input.bool(true, "Opt", tooltip="Set \\"auto\\" mode 自动模式")
            """
        )
        self.assertEqual([], run_rule("QUA001", src))


class TestQUA002NaCheck(unittest.TestCase):
    def test_unchecked_security_result_fires(self):
        src = fixture(
            """
            w_rsi = request.security(syminfo.tickerid, "W", close, lookahead=barmerge.lookahead_off)
            plot(w_rsi)
            """
        )
        issues = run_rule("QUA002", src)
        self.assertEqual(1, len(issues))
        self.assertEqual("QUA002", issues[0].rule_id)
        self.assertEqual(2, issues[0].line)
        self.assertIn("w_rsi", issues[0].message)

    def test_nz_checked_security_result_is_clean(self):
        src = fixture(
            """
            w_rsi = request.security(syminfo.tickerid, "W", close, lookahead=barmerge.lookahead_off)
            plot(nz(w_rsi, 50))
            """
        )
        self.assertEqual([], run_rule("QUA002", src))

    def test_not_na_checked_security_result_is_clean(self):
        src = fixture(
            """
            w_rsi = request.security(syminfo.tickerid, "W", close, lookahead=barmerge.lookahead_off)
            ok = not na(w_rsi)
            plot(w_rsi)
            """
        )
        self.assertEqual([], run_rule("QUA002", src))

    def test_comment_mention_is_not_a_usage(self):
        # Regression: the only non-declaration mention is in a comment, which
        # used to be reported as an unchecked usage.
        src = fixture(
            """
            w_rsi = request.security(syminfo.tickerid, "W", close, lookahead=barmerge.lookahead_off)
            // w_rsi may be na on the first bars
            plot(close)
            """
        )
        self.assertEqual([], run_rule("QUA002", src))


class TestAdaptiveRsiRegression(unittest.TestCase):
    """Lint the real production file with the repo config."""

    @classmethod
    def setUpClass(cls):
        config = load_config(REPO_ROOT / ".pine-lint.yml")
        linter = PineLinter(config)
        cls.issues = linter.lint_file(REPO_ROOT / "adaptive_rsi.pine")

    def test_no_errors(self):
        errors = [i for i in self.issues if i.severity == "error"]
        self.assertEqual([], errors)

    def test_no_warnings(self):
        warnings = [i for i in self.issues if i.severity == "warning"]
        self.assertEqual([], warnings)

    def test_no_nam001_false_positives(self):
        # prev_spread / bullish_divergence / bearish_divergence /
        # last_buy_level / last_sell_level are var (mutable) declarations and
        # must not be reported as constants.
        nam001 = [i for i in self.issues if i.rule_id == "NAM001"]
        self.assertEqual([], nam001)


if __name__ == "__main__":
    unittest.main()
