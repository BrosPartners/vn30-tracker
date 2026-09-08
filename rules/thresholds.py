"""Doc bang nguong tu thresholds.yaml. Nguon: Ground Rules v4.0."""
from functools import lru_cache
from pathlib import Path

import yaml

THRESHOLDS_FILE = Path(__file__).with_name("thresholds.yaml")


@lru_cache(maxsize=1)
def load_thresholds() -> dict:
    with THRESHOLDS_FILE.open(encoding="utf-8") as f:
        return yaml.safe_load(f)
