#!/usr/bin/env python3
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from .rules import Issue, ALL_RULES, RULES_BY_ID, BaseRule


class PineLinter:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.rules = self._load_enabled_rules()

    def _load_enabled_rules(self) -> List[BaseRule]:
        rules_config = self.config.get("rules", {})
        enabled_rules = []

        for rule in ALL_RULES:
            rule_setting = rules_config.get(rule.rule_id, rule.severity)

            if rule_setting == "off":
                continue

            if rule_setting in ("error", "warning", "info"):
                rule.severity = rule_setting

            enabled_rules.append(rule)

        return enabled_rules

    def lint_file(self, file_path: Path) -> List[Issue]:
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="latin-1")

        lines = content.split("\n")
        all_issues = []

        disabled_lines = self._get_disabled_lines(lines)

        for rule in self.rules:
            issues = rule.check(lines, content)

            for issue in issues:
                if not self._is_disabled(issue, disabled_lines):
                    all_issues.append(issue)

        return sorted(all_issues, key=lambda x: (x.line, x.column))

    def _get_disabled_lines(self, lines: List[str]) -> Dict[int, set]:
        disabled = {}

        for i, line in enumerate(lines):
            line_num = i + 1

            if "pine-lint-disable-next-line" in line:
                rules = self._extract_disabled_rules(
                    line, "pine-lint-disable-next-line"
                )
                disabled[line_num + 1] = rules

            if "pine-lint-disable-line" in line:
                rules = self._extract_disabled_rules(line, "pine-lint-disable-line")
                disabled[line_num] = rules

        return disabled

    def _extract_disabled_rules(self, line: str, directive: str) -> set:
        import re

        match = re.search(rf"{directive}\s+([\w,\s]+)", line)
        if match:
            return set(r.strip() for r in match.group(1).split(","))
        return {"*"}

    def _is_disabled(self, issue: Issue, disabled_lines: Dict[int, set]) -> bool:
        if issue.line not in disabled_lines:
            return False

        disabled_rules = disabled_lines[issue.line]
        return "*" in disabled_rules or issue.rule_id in disabled_rules

    def lint_files(self, file_paths: List[Path]) -> List[Tuple[Path, List[Issue]]]:
        results = []
        for file_path in file_paths:
            if file_path.suffix == ".pine" and file_path.exists():
                issues = self.lint_file(file_path)
                results.append((file_path, issues))
        return results
