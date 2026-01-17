#!/usr/bin/env python3
import re
from dataclasses import dataclass, field
from typing import List, Optional
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


class SEC001_LookaheadOff(BaseRule):
    rule_id = "SEC001"
    severity = "error"
    message = "request.security() should have lookahead=barmerge.lookahead_off to prevent future data leak"

    SECURITY_START_PATTERN = re.compile(r"request\.security\s*\(", re.DOTALL)

    def _find_matching_paren(self, content: str, start: int) -> int:
        depth = 1
        i = start
        while i < len(content) and depth > 0:
            if content[i] == "(":
                depth += 1
            elif content[i] == ")":
                depth -= 1
            i += 1
        return i

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
                        message=self.message,
                        suggestion="Add: lookahead=barmerge.lookahead_off",
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
    SEC001_LookaheadOff(),
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
