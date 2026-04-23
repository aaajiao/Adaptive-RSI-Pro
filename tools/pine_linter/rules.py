#!/usr/bin/env python3
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from abc import ABC, abstractmethod


@dataclass
class Issue:
    rule_id: str
    severity: str
    line: int
    column: int
    message: str
    suggestion: Optional[str] = None


class BaseRule(ABC):
    rule_id: str = ""
    severity: str = "warning"
    message: str = ""

    @abstractmethod
    def check(self, lines: List[str], content: str) -> List[Issue]:
        pass

    def _get_line_number(self, content: str, pos: int) -> int:
        return content[:pos].count("\n") + 1

    def _get_column(self, content: str, pos: int) -> int:
        last_newline = content.rfind("\n", 0, pos)
        return pos - last_newline if last_newline >= 0 else pos + 1


class SEC001_SafeLookahead(BaseRule):
    rule_id = "SEC001"
    severity = "error"
    message = "request.security() must declare safe lookahead behavior"

    SECURITY_START_PATTERN = re.compile(r"request\.security\s*\(", re.DOTALL)
    LOOKAHEAD_OFF = "barmerge.lookahead_off"
    LOOKAHEAD_ON = "barmerge.lookahead_on"

    def _find_matching_paren(self, content: str, start: int) -> int:
        depth = 1
        i = start
        in_string = False
        string_quote = ""
        in_line_comment = False

        while i < len(content) and depth > 0:
            char = content[i]
            next_char = content[i + 1] if i + 1 < len(content) else ""

            if in_line_comment:
                if char == "\n":
                    in_line_comment = False
                i += 1
                continue

            if in_string:
                if char == "\\":
                    i += 2
                    continue
                if char == string_quote:
                    in_string = False
                    string_quote = ""
                i += 1
                continue

            if char == "/" and next_char == "/":
                in_line_comment = True
                i += 2
                continue

            if char in ("'", '"'):
                in_string = True
                string_quote = char
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            i += 1
        return i

    def _strip_comments_and_strings(self, text: str) -> str:
        result = []
        i = 0
        in_string = False
        string_quote = ""
        in_line_comment = False

        while i < len(text):
            char = text[i]
            next_char = text[i + 1] if i + 1 < len(text) else ""

            if in_line_comment:
                result.append("\n" if char == "\n" else " ")
                if char == "\n":
                    in_line_comment = False
                i += 1
                continue

            if in_string:
                result.append(" ")
                if char == "\\":
                    if i + 1 < len(text):
                        result.append(" ")
                    i += 2
                    continue
                if char == string_quote:
                    in_string = False
                    string_quote = ""
                i += 1
                continue

            if char == "/" and next_char == "/":
                result.extend("  ")
                in_line_comment = True
                i += 2
                continue

            if char in ("'", '"'):
                result.append(" ")
                in_string = True
                string_quote = char
                i += 1
                continue

            result.append(char)
            i += 1

        return "".join(result)

    def _split_top_level_args(self, text: str) -> List[str]:
        args = []
        start = 0
        paren_depth = 0
        bracket_depth = 0
        brace_depth = 0
        i = 0
        in_string = False
        string_quote = ""
        in_line_comment = False

        while i < len(text):
            char = text[i]
            next_char = text[i + 1] if i + 1 < len(text) else ""

            if in_line_comment:
                if char == "\n":
                    in_line_comment = False
                i += 1
                continue

            if in_string:
                if char == "\\":
                    i += 2
                    continue
                if char == string_quote:
                    in_string = False
                    string_quote = ""
                i += 1
                continue

            if char == "/" and next_char == "/":
                in_line_comment = True
                i += 2
                continue

            if char in ("'", '"'):
                in_string = True
                string_quote = char
            elif char == "(":
                paren_depth += 1
            elif char == ")":
                paren_depth -= 1
            elif char == "[":
                bracket_depth += 1
            elif char == "]":
                bracket_depth -= 1
            elif char == "{":
                brace_depth += 1
            elif char == "}":
                brace_depth -= 1
            elif (
                char == ","
                and paren_depth == 0
                and bracket_depth == 0
                and brace_depth == 0
            ):
                args.append(text[start:i].strip())
                start = i + 1
            i += 1

        trailing = text[start:].strip()
        if trailing:
            args.append(trailing)

        return args

    def _parse_named_arg(self, arg: str) -> Tuple[Optional[str], str]:
        match = re.match(r"\s*([A-Za-z_]\w*)\s*=\s*(.*)\s*$", arg, re.DOTALL)
        if not match:
            return None, arg.strip()
        return match.group(1), match.group(2).strip()

    def _normalize_value(self, value: str) -> str:
        value_without_comments = self._strip_comments_and_strings(value)
        return re.sub(r"\s+", "", value_without_comments)

    def _get_security_expression(self, args: List[str]) -> Optional[str]:
        for arg in args:
            name, value = self._parse_named_arg(arg)
            if name == "expression":
                return value

        if len(args) >= 3:
            return self._parse_named_arg(args[2])[1]

        return None

    def _get_lookahead_value(self, args: List[str]) -> Optional[str]:
        for arg in args:
            name, value = self._parse_named_arg(arg)
            if name == "lookahead":
                return value

        if len(args) >= 5:
            name, value = self._parse_named_arg(args[4])
            if name is None:
                return value

        return None

    def _matching_outer_bracket(self, text: str) -> bool:
        stripped = text.strip()
        if not stripped.startswith("[") or not stripped.endswith("]"):
            return False

        depth = 0
        in_string = False
        string_quote = ""
        in_line_comment = False

        for i, char in enumerate(stripped):
            next_char = stripped[i + 1] if i + 1 < len(stripped) else ""

            if in_line_comment:
                if char == "\n":
                    in_line_comment = False
                continue

            if in_string:
                if char == "\\":
                    continue
                if char == string_quote:
                    in_string = False
                    string_quote = ""
                continue

            if char == "/" and next_char == "/":
                in_line_comment = True
                continue

            if char in ("'", '"'):
                in_string = True
                string_quote = char
            elif char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0 and i != len(stripped) - 1:
                    return False

        return depth == 0

    def _uses_confirmed_historical_offset(self, expression: str) -> bool:
        if self._matching_outer_bracket(expression):
            inner = expression.strip()[1:-1]
            items = self._split_top_level_args(inner)
            return bool(items) and all(
                self._uses_confirmed_historical_offset(item) for item in items
            )

        expression_without_comments = self._strip_comments_and_strings(expression)
        normalized_expression = re.sub(r"\s+", "", expression_without_comments)
        return normalized_expression.endswith("[1]")

    def check(self, lines: List[str], content: str) -> List[Issue]:
        issues = []

        for match in self.SECURITY_START_PATTERN.finditer(content):
            start_pos = match.end()
            end_pos = self._find_matching_paren(content, start_pos)
            call_text = content[match.start() : end_pos]

            if "lookahead" not in call_text.lower():
                line_num = self._get_line_number(content, match.start())

                line_content = lines[line_num - 1] if line_num <= len(lines) else ""
                if line_content.strip().startswith("//"):
                    continue

                issues.append(
                    Issue(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        line=line_num,
                        column=self._get_column(content, match.start()),
                        message="request.security() must explicitly set lookahead",
                        suggestion=(
                            "Add lookahead=barmerge.lookahead_off, or use "
                            "lookahead=barmerge.lookahead_on only with a [1] "
                            "confirmed historical expression."
                        ),
                    )
                )
                continue

            args = self._split_top_level_args(call_text[call_text.find("(") + 1 : -1])
            lookahead_value = self._get_lookahead_value(args)
            expression = self._get_security_expression(args)

            line_num = self._get_line_number(content, match.start())
            line_content = lines[line_num - 1] if line_num <= len(lines) else ""
            if line_content.strip().startswith("//"):
                continue

            if lookahead_value is None:
                issues.append(
                    Issue(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        line=line_num,
                        column=self._get_column(content, match.start()),
                        message="request.security() must explicitly set lookahead",
                        suggestion=(
                            "Add lookahead=barmerge.lookahead_off, or use "
                            "lookahead=barmerge.lookahead_on only with a [1] "
                            "confirmed historical expression."
                        ),
                    )
                )
                continue

            normalized_lookahead = self._normalize_value(lookahead_value)
            if normalized_lookahead == self.LOOKAHEAD_OFF:
                continue

            if normalized_lookahead == self.LOOKAHEAD_ON:
                if expression and self._uses_confirmed_historical_offset(expression):
                    continue

                issues.append(
                    Issue(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        line=line_num,
                        column=self._get_column(content, match.start()),
                        message=(
                            "request.security() with lookahead_on must use a [1] "
                            "confirmed historical expression"
                        ),
                        suggestion=(
                            "Offset the requested expression, for example "
                            "close[1] or [expr1[1], expr2[1]], or switch to "
                            "lookahead=barmerge.lookahead_off."
                        ),
                    )
                )
                continue

            issues.append(
                Issue(
                    rule_id=self.rule_id,
                    severity=self.severity,
                    line=line_num,
                    column=self._get_column(content, match.start()),
                    message=(
                        "request.security() lookahead must be "
                        "barmerge.lookahead_off or safe barmerge.lookahead_on"
                    ),
                    suggestion=(
                        "Use lookahead=barmerge.lookahead_off, or "
                        "lookahead=barmerge.lookahead_on with a [1] confirmed "
                        "historical expression."
                    ),
                )
            )

        return issues


class SEC002_SecurityInCondition(BaseRule):
    rule_id = "SEC002"
    severity = "warning"
    message = "request.security() inside conditional may cause repainting issues"

    def check(self, lines: List[str], content: str) -> List[Issue]:
        issues = []
        in_conditional = False
        conditional_indent = 0
        conditional_line = 0

        for i, line in enumerate(lines):
            stripped = line.lstrip()
            current_indent = len(line) - len(stripped)

            if stripped.startswith(("if ", "if(", "else if ", "switch ")):
                in_conditional = True
                conditional_indent = current_indent
                conditional_line = i + 1
            elif in_conditional:
                if (
                    current_indent <= conditional_indent
                    and stripped
                    and not stripped.startswith(("else", "//"))
                ):
                    in_conditional = False
                elif "request.security" in line and current_indent > conditional_indent:
                    issues.append(
                        Issue(
                            rule_id=self.rule_id,
                            severity=self.severity,
                            line=i + 1,
                            column=1,
                            message=self.message,
                            suggestion="Move request.security() outside conditional scope",
                        )
                    )

        return issues


class SYN001_MultilineTernary(BaseRule):
    rule_id = "SYN001"
    severity = "warning"
    message = "Multi-line ternary expression may cause 'end of line without line continuation' error in v6"

    MULTILINE_TERNARY_PATTERN = re.compile(r"\?\s*\n\s*[^:]+:\s*\n", re.MULTILINE)

    def check(self, lines: List[str], content: str) -> List[Issue]:
        issues = []

        for match in self.MULTILINE_TERNARY_PATTERN.finditer(content):
            line_num = self._get_line_number(content, match.start())
            issues.append(
                Issue(
                    rule_id=self.rule_id,
                    severity=self.severity,
                    line=line_num,
                    column=1,
                    message=self.message,
                    suggestion="Use single-line ternary or switch statement instead",
                )
            )

        return issues


class SYN002_SwitchDefault(BaseRule):
    rule_id = "SYN002"
    severity = "info"
    message = "switch statement may be missing default case (=> without condition)"

    SWITCH_PATTERN = re.compile(r"switch\s*\n((?:.*\n)*?)(?=\n\S|\Z)", re.MULTILINE)

    def check(self, lines: List[str], content: str) -> List[Issue]:
        issues = []

        for match in self.SWITCH_PATTERN.finditer(content):
            switch_body = match.group(1)

            if "=>" in switch_body and not re.search(
                r"^\s*=>", switch_body, re.MULTILINE
            ):
                line_num = self._get_line_number(content, match.start())
                issues.append(
                    Issue(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        line=line_num,
                        column=1,
                        message=self.message,
                        suggestion='Add default case: => "default_value"',
                    )
                )

        return issues


class SYN003_TableClearParams(BaseRule):
    rule_id = "SYN003"
    severity = "warning"
    message = "table.clear() in v6 requires range parameters"

    TABLE_CLEAR_PATTERN = re.compile(r"table\.clear\s*\(\s*\w+\s*\)", re.MULTILINE)

    def check(self, lines: List[str], content: str) -> List[Issue]:
        issues = []

        for match in self.TABLE_CLEAR_PATTERN.finditer(content):
            line_num = self._get_line_number(content, match.start())
            issues.append(
                Issue(
                    rule_id=self.rule_id,
                    severity=self.severity,
                    line=line_num,
                    column=self._get_column(content, match.start()),
                    message=self.message,
                    suggestion="Use: table.clear(table_id, start_col, start_row, end_col, end_row)",
                )
            )

        return issues


class NAM001_ConstantCase(BaseRule):
    rule_id = "NAM001"
    severity = "info"
    message = "Constant should use SCREAMING_SNAKE_CASE"

    CONSTANT_PATTERN = re.compile(
        r'^var\s+(?:int|float|string|bool)\s+([a-z][a-z0-9_]*)\s*=\s*(?:\d|"|\btrue\b|\bfalse\b)',
        re.MULTILINE,
    )

    def check(self, lines: List[str], content: str) -> List[Issue]:
        issues = []

        for match in self.CONSTANT_PATTERN.finditer(content):
            var_name = match.group(1)
            if not var_name.isupper():
                line_num = self._get_line_number(content, match.start())
                issues.append(
                    Issue(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        line=line_num,
                        column=1,
                        message=f"Constant '{var_name}' should be '{var_name.upper()}'",
                        suggestion=var_name.upper(),
                    )
                )

        return issues


class NAM002_FunctionPrefix(BaseRule):
    rule_id = "NAM002"
    severity = "info"
    message = "User-defined function should use f_ prefix"

    FUNCTION_PATTERN = re.compile(r"^(\w+)\s*\([^)]*\)\s*=>", re.MULTILINE)

    EXCLUDED_NAMES = {
        "if",
        "for",
        "while",
        "switch",
        "method",
        "type",
        "import",
        "export",
    }

    def check(self, lines: List[str], content: str) -> List[Issue]:
        issues = []

        for match in self.FUNCTION_PATTERN.finditer(content):
            func_name = match.group(1)

            if func_name in self.EXCLUDED_NAMES:
                continue
            if func_name.startswith("f_"):
                continue

            line_num = self._get_line_number(content, match.start())
            issues.append(
                Issue(
                    rule_id=self.rule_id,
                    severity=self.severity,
                    line=line_num,
                    column=1,
                    message=f"Function '{func_name}' should be renamed to 'f_{func_name}'",
                    suggestion=f"f_{func_name}",
                )
            )

        return issues


class NAM003_TypeCase(BaseRule):
    rule_id = "NAM003"
    severity = "info"
    message = "User-defined type should use PascalCase"

    TYPE_PATTERN = re.compile(r"^type\s+([a-z_][a-zA-Z0-9_]*)", re.MULTILINE)

    def check(self, lines: List[str], content: str) -> List[Issue]:
        issues = []

        for match in self.TYPE_PATTERN.finditer(content):
            type_name = match.group(1)

            if not type_name[0].isupper():
                line_num = self._get_line_number(content, match.start())
                pascal_name = "".join(
                    word.capitalize() for word in type_name.split("_")
                )
                issues.append(
                    Issue(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        line=line_num,
                        column=1,
                        message=f"Type '{type_name}' should use PascalCase: '{pascal_name}'",
                        suggestion=pascal_name,
                    )
                )

        return issues


class QUA001_BilingualTooltip(BaseRule):
    rule_id = "QUA001"
    severity = "info"
    message = "Input tooltip should contain bilingual text (EN/CN)"

    TOOLTIP_PATTERN = re.compile(r'tooltip\s*=\s*"([^"]*)"', re.MULTILINE | re.DOTALL)

    def check(self, lines: List[str], content: str) -> List[Issue]:
        issues = []

        for match in self.TOOLTIP_PATTERN.finditer(content):
            tooltip_text = match.group(1)

            has_chinese = bool(re.search(r"[\u4e00-\u9fff]", tooltip_text))
            has_english = bool(re.search(r"[a-zA-Z]{3,}", tooltip_text))

            if not (has_chinese and has_english):
                line_num = self._get_line_number(content, match.start())
                missing = "Chinese" if not has_chinese else "English"
                issues.append(
                    Issue(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        line=line_num,
                        column=self._get_column(content, match.start()),
                        message=f"Tooltip missing {missing} text",
                        suggestion="Add bilingual description: English\\n中文",
                    )
                )

        return issues


class QUA002_NaCheck(BaseRule):
    rule_id = "QUA002"
    severity = "warning"
    message = "request.security() result should be checked for na before use"

    SECURITY_ASSIGN_PATTERN = re.compile(
        r"\[?\s*(\w+).*\]?\s*=\s*request\.security\s*\(", re.MULTILINE
    )

    def check(self, lines: List[str], content: str) -> List[Issue]:
        issues = []
        security_vars = set()

        for match in self.SECURITY_ASSIGN_PATTERN.finditer(content):
            var_name = match.group(1)
            security_vars.add(var_name)

        for var_name in security_vars:
            na_check_pattern = re.compile(
                rf"(?:na\s*\(\s*{re.escape(var_name)}\s*\)|not\s+na\s*\(\s*{re.escape(var_name)}\s*\)|nz\s*\(\s*{re.escape(var_name)})",
                re.MULTILINE,
            )
            if not na_check_pattern.search(content):
                for match in re.finditer(rf"\b{re.escape(var_name)}\b", content):
                    line_num = self._get_line_number(content, match.start())
                    line_content = lines[line_num - 1] if line_num <= len(lines) else ""
                    if (
                        "request.security" not in line_content
                        and "=" not in line_content.split(var_name)[0]
                    ):
                        issues.append(
                            Issue(
                                rule_id=self.rule_id,
                                severity=self.severity,
                                line=line_num,
                                column=1,
                                message=f"Variable '{var_name}' from request.security() may be na",
                                suggestion=f"Use: not na({var_name}) or nz({var_name}, default)",
                            )
                        )
                        break

        return issues


ALL_RULES = [
    SEC001_SafeLookahead(),
    SEC002_SecurityInCondition(),
    SYN001_MultilineTernary(),
    SYN002_SwitchDefault(),
    SYN003_TableClearParams(),
    NAM001_ConstantCase(),
    NAM002_FunctionPrefix(),
    NAM003_TypeCase(),
    QUA001_BilingualTooltip(),
    QUA002_NaCheck(),
]

RULES_BY_ID = {rule.rule_id: rule for rule in ALL_RULES}
