from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config(path: Path | None = None) -> dict:
    config_path = path or DEFAULT_CONFIG_PATH
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
    # Resolve relative output path against the project root, not CWD
    out = cfg.get("paths", {}).get("output", "./output")
    if not Path(out).is_absolute():
        cfg["paths"]["output"] = str(PROJECT_ROOT / out)
    return cfg
