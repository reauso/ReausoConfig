"""Data models for the hooks system.

This module provides the core data structures for lifecycle hooks:
- HookPhase: Enum of lifecycle stages where hooks can be registered
- HookEntry: Immutable entry representing a registered hook
- HookContext: Immutable context passed to hook functions
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from types import MappingProxyType
from typing import Any, Callable


class HookPhase(Enum):
    """Configuration lifecycle phases where hooks can be injected.

    Phases are invoked in the following order during instantiation:

    1. CONFIG_LOADED - After config composition, before interpolation
    2. BEFORE_INSTANTIATE - Before each object's constructor is called
    3. AFTER_INSTANTIATE - After each object's constructor returns
    4. ON_ERROR - When an error occurs during instantiation (instead of normal flow)
    """

    CONFIG_LOADED = auto()
    """Called after config file is loaded and composed (refs resolved)."""

    BEFORE_INSTANTIATE = auto()
    """Called before each object instantiation (per nested config with _target_)."""

    AFTER_INSTANTIATE = auto()
    """Called after each object instantiation with the created instance."""

    ON_ERROR = auto()
    """Called when an error occurs during instantiation."""


@dataclass(frozen=True, kw_only=True)
class HookEntry:
    """Immutable entry representing a registered hook.

    :param name: Unique identifier for the hook.
    :param phase: Lifecycle phase when this hook is invoked.
    :param func: The hook function to call.
    :param pattern: Optional glob pattern for conditional execution.
                   If set, hook only runs when config_path matches pattern.
    :param priority: Execution order (lower values run first, default 50).
    """

    name: str
    phase: HookPhase
    func: Callable[[HookContext], None]
    pattern: str | None = None
    priority: int = 50


@dataclass(frozen=True, kw_only=True)
class HookContext:
    """Immutable context passed to hook functions.

    Contains information about the current lifecycle stage and relevant data.
    Different fields are populated depending on the phase:

    - CONFIG_LOADED: config_path, config
    - BEFORE_INSTANTIATE: config_path, config, inner_path, target_name
    - AFTER_INSTANTIATE: config_path, config, inner_path, target_name, instance
    - ON_ERROR: config_path, config, error (and optionally inner_path, target_name)

    :param phase: The lifecycle phase that triggered this hook.
    :param config_path: Path to the config file being processed.
    :param config: Read-only view of the configuration dictionary.
    :param inner_path: Path within config to the current object (for nested configs).
    :param instance: The instantiated object (AFTER_INSTANTIATE only).
    :param target_name: The _target_ name being instantiated.
    :param error: The exception that occurred (ON_ERROR only).
    """

    phase: HookPhase
    config_path: str
    config: MappingProxyType[str, Any] | None = None
    inner_path: str | None = None
    instance: Any | None = None
    target_name: str | None = None
    error: Exception | None = None
