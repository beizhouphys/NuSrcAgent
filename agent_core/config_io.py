from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_core.schemas import AnalysisConfig, ConfigError
from agent_core.simple_yaml import SimpleYamlError, load_simple_yaml


def load_config_file(config_path: str | Path) -> AnalysisConfig:
    payload = load_mapping_file(Path(config_path))
    return AnalysisConfig.from_dict(payload)


def load_mapping_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"config file does not exist: {path}")
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        with path.open("r", encoding="utf-8") as handle:
            try:
                payload = load_simple_yaml(handle.read())
            except SimpleYamlError as exc:
                raise ConfigError(f"invalid YAML config: {exc}") from exc
    elif suffix == ".json":
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    else:
        raise ConfigError("config must be .yaml/.yml; .json is also accepted for later API use")
    if not isinstance(payload, dict):
        raise ConfigError("config top level must be a mapping/object")
    return payload
