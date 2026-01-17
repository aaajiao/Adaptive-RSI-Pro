#!/usr/bin/env python3
from pathlib import Path
from typing import Dict, Optional


def _load_yaml_file(path):
    try:
        import yaml

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        return None
    except Exception:
        return {}


DEFAULT_CONFIG = {
    "rules": {
        "SEC001": "error",
        "SEC002": "warning",
        "SYN001": "warning",
        "SYN002": "info",
        "SYN003": "warning",
        "NAM001": "info",
        "NAM002": "info",
        "NAM003": "info",
        "QUA001": "info",
        "QUA002": "warning",
    },
    "ignore": [],
    "project": {
        "version": 6,
        "require_bilingual": True,
    },
}


def load_config(config_path: Optional[Path] = None) -> Dict:
    config = DEFAULT_CONFIG.copy()

    if config_path is None:
        for default_name in [".pine-lint.yml", ".pine-lint.yaml", "pine-lint.yml"]:
            potential_path = Path(default_name)
            if potential_path.exists():
                config_path = potential_path
                break

    if config_path and config_path.exists():
        user_config = _load_yaml_file(config_path)

        if user_config is None:
            import json

            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content.strip().startswith("{"):
                        user_config = json.loads(content)
            except Exception:
                user_config = {}

        if user_config:
            if "rules" in user_config:
                config["rules"].update(user_config["rules"])
            if "ignore" in user_config:
                config["ignore"] = user_config["ignore"]
            if "project" in user_config:
                config["project"].update(user_config["project"])

    return config


def should_ignore_file(file_path: Path, ignore_patterns: list) -> bool:
    import fnmatch

    file_str = str(file_path)
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(file_str, pattern):
            return True
        if fnmatch.fnmatch(file_path.name, pattern):
            return True

    return False
