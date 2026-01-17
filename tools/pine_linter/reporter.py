#!/usr/bin/env python3
import json
from pathlib import Path
from typing import List, Tuple
from .rules import Issue


SEVERITY_EMOJI = {"error": "🔴", "warning": "🟡", "info": "🔵"}

SEVERITY_ICON = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}


def format_text(results: List[Tuple[Path, List[Issue]]]) -> str:
    lines = []

    for file_path, issues in results:
        for issue in issues:
            icon = SEVERITY_ICON.get(issue.severity, "?")
            lines.append(
                f"{file_path}:{issue.line}:{issue.column}: "
                f"{icon} [{issue.rule_id}] {issue.message}"
            )
            if issue.suggestion:
                lines.append(f"  💡 {issue.suggestion}")

    errors = sum(1 for _, issues in results for i in issues if i.severity == "error")
    warnings = sum(
        1 for _, issues in results for i in issues if i.severity == "warning"
    )
    infos = sum(1 for _, issues in results for i in issues if i.severity == "info")

    lines.append("")
    lines.append("━" * 50)

    if errors > 0:
        lines.append(f"❌ Found {errors} error(s), {warnings} warning(s), {infos} info")
    else:
        lines.append(f"✅ Found {errors} error(s), {warnings} warning(s), {infos} info")

    return "\n".join(lines)


def format_github(results: List[Tuple[Path, List[Issue]]]) -> str:
    lines = []

    for file_path, issues in results:
        for issue in issues:
            level = "error" if issue.severity == "error" else "warning"
            msg = f"[{issue.rule_id}] {issue.message}"
            if issue.suggestion:
                msg += f" | Suggestion: {issue.suggestion}"

            lines.append(
                f"::{level} file={file_path},line={issue.line},col={issue.column}::{msg}"
            )

    return "\n".join(lines)


def format_markdown(results: List[Tuple[Path, List[Issue]]]) -> str:
    lines = [
        "## 🔍 Pine Script Lint Report",
        "",
        "| File | Line | Severity | Rule | Message |",
        "|------|------|----------|------|---------|",
    ]

    total_issues = sum(len(issues) for _, issues in results)

    if total_issues == 0:
        lines.append("| - | - | ✅ | - | No issues found! |")
    else:
        for file_path, issues in results:
            for issue in issues:
                emoji = SEVERITY_EMOJI.get(issue.severity, "⚪")
                msg = issue.message
                if issue.suggestion:
                    msg += f" *({issue.suggestion})*"
                lines.append(
                    f"| `{file_path.name}` | {issue.line} | {emoji} {issue.severity} | "
                    f"`{issue.rule_id}` | {msg} |"
                )

    lines.append("")

    errors = sum(1 for _, issues in results for i in issues if i.severity == "error")
    warnings = sum(
        1 for _, issues in results for i in issues if i.severity == "warning"
    )
    infos = sum(1 for _, issues in results for i in issues if i.severity == "info")

    if errors > 0:
        lines.append(
            f"**Summary**: 🔴 {errors} error(s), 🟡 {warnings} warning(s), 🔵 {infos} info"
        )
        lines.append("")
        lines.append("❌ **CI check failed** - please fix errors before merging")
    else:
        lines.append(f"**Summary**: 🟡 {warnings} warning(s), 🔵 {infos} info")
        lines.append("")
        lines.append("✅ **All checks passed!**")

    return "\n".join(lines)


def format_json(results: List[Tuple[Path, List[Issue]]]) -> str:
    output = {
        "files": [],
        "summary": {"total": 0, "errors": 0, "warnings": 0, "info": 0},
    }

    for file_path, issues in results:
        file_data = {"path": str(file_path), "issues": []}

        for issue in issues:
            file_data["issues"].append(
                {
                    "rule": issue.rule_id,
                    "severity": issue.severity,
                    "line": issue.line,
                    "column": issue.column,
                    "message": issue.message,
                    "suggestion": issue.suggestion,
                }
            )

            output["summary"]["total"] += 1
            output["summary"][issue.severity] += (
                1 if issue.severity in output["summary"] else 0
            )

        output["files"].append(file_data)

    output["summary"]["errors"] = sum(
        1 for _, issues in results for i in issues if i.severity == "error"
    )
    output["summary"]["warnings"] = sum(
        1 for _, issues in results for i in issues if i.severity == "warning"
    )
    output["summary"]["info"] = sum(
        1 for _, issues in results for i in issues if i.severity == "info"
    )
    output["summary"]["total"] = (
        output["summary"]["errors"]
        + output["summary"]["warnings"]
        + output["summary"]["info"]
    )

    return json.dumps(output, indent=2)


def generate_report(results: List[Tuple[Path, List[Issue]]], format_type: str) -> str:
    formatters = {
        "text": format_text,
        "github": format_github,
        "markdown": format_markdown,
        "json": format_json,
    }

    formatter = formatters.get(format_type, format_text)
    return formatter(results)
