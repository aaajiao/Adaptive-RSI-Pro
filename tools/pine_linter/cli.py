#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.pine_linter.linter import PineLinter
from tools.pine_linter.config import load_config, should_ignore_file
from tools.pine_linter.reporter import generate_report


def main():
    parser = argparse.ArgumentParser(
        description="Pine Script Static Analyzer - Lint your TradingView Pine Script v6 code"
    )
    parser.add_argument("files", nargs="+", help="Pine Script files to lint")
    parser.add_argument(
        "--config", "-c", type=Path, help="Path to configuration file (.pine-lint.yml)"
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["text", "github", "json", "markdown"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--output", "-o", type=Path, help="Output file (default: stdout)"
    )
    parser.add_argument(
        "--severity",
        "-s",
        choices=["error", "warning", "info", "all"],
        default="all",
        help="Minimum severity to report (default: all)",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Only output errors, no summary"
    )

    args = parser.parse_args()

    config = load_config(args.config)
    linter = PineLinter(config)

    file_paths = []
    for file_arg in args.files:
        path = Path(file_arg)
        if path.is_dir():
            file_paths.extend(path.glob("**/*.pine"))
        elif path.suffix == ".pine":
            file_paths.append(path)
        elif path.exists():
            file_paths.append(path)

    file_paths = [
        p for p in file_paths if not should_ignore_file(p, config.get("ignore", []))
    ]

    if not file_paths:
        print("No Pine Script files found to lint", file=sys.stderr)
        sys.exit(0)

    results = linter.lint_files(file_paths)

    if args.severity != "all":
        severity_order = {"error": 0, "warning": 1, "info": 2}
        min_level = severity_order[args.severity]
        results = [
            (
                path,
                [i for i in issues if severity_order.get(i.severity, 2) <= min_level],
            )
            for path, issues in results
        ]

    report = generate_report(results, args.format)

    if args.output:
        args.output.write_text(report, encoding="utf-8")
        if not args.quiet:
            total = sum(len(issues) for _, issues in results)
            print(f"Report written to {args.output} ({total} issue(s) found)")
    else:
        print(report)

    has_errors = any(
        issue.severity == "error" for _, issues in results for issue in issues
    )

    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
