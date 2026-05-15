"""Configuration loading and repository-relative path resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

try:  # Python 3.11+
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


@dataclass(frozen=True)
class PipelineConfig:
    root: Path
    values: Mapping[str, Any]

    def get(self, dotted: str, default: Any = None) -> Any:
        current: Any = self.values
        for part in dotted.split("."):
            if not isinstance(current, Mapping) or part not in current:
                return default
            current = current[part]
        return current

    def path(self, dotted: str, default: str | None = None) -> Path:
        value = self.get(dotted, default)
        if value is None:
            raise KeyError(f"missing config path: {dotted}")
        path = Path(str(value)).expanduser()
        return path if path.is_absolute() else self.root / path


def discover_repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() or (candidate / ".git").exists():
            return candidate
    return current


def load_config(path: Path | str = "config/default.toml") -> PipelineConfig:
    config_path = Path(path).expanduser()
    if not config_path.is_absolute():
        config_path = discover_repo_root() / config_path
    with config_path.open("rb") as handle:
        values = tomllib.load(handle)
    return PipelineConfig(root=discover_repo_root(config_path.parent), values=values)
