from __future__ import annotations # Codex

import json # Codex
from pathlib import Path # Codex
from typing import Any # Codex

from agent_core_cdx.schemas_cdx import AnalysisConfig, ConfigError # cdx
from agent_core_cdx.simple_yaml_cdx import SimpleYamlError, load_simple_yaml # cdx


def load_config_file(config_path: str | Path) -> AnalysisConfig: # Codex
    payload = load_mapping_file(Path(config_path)) # Codex
    return AnalysisConfig.from_dict(payload) # Codex


def load_mapping_file(path: Path) -> dict[str, Any]: # Codex
    if not path.exists(): # Codex
        raise ConfigError(f"config file does not exist: {path}") # Codex
    suffix = path.suffix.lower() # Codex
    if suffix in {".yaml", ".yml"}: # Codex
        with path.open("r", encoding="utf-8") as handle: # Codex
            try: # Codex
                payload = load_simple_yaml(handle.read()) # Codex
            except SimpleYamlError as exc: # Codex
                raise ConfigError(f"invalid YAML config: {exc}") from exc # Codex
    elif suffix == ".json": # Codex
        with path.open("r", encoding="utf-8") as handle: # Codex
            payload = json.load(handle) # Codex
    else: # Codex
        raise ConfigError("config must be .yaml/.yml; .json is also accepted for later API use") # Codex
    if not isinstance(payload, dict): # Codex
        raise ConfigError("config top level must be a mapping/object") # Codex
    return payload # Codex
