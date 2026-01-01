"""ReausoConfig - A lightweight configuration library.

This module provides a simple, pandas-like API for loading YAML config files
and instantiating Python objects from them.

Example::

    import rconfig as rc
    from dataclasses import dataclass

    @dataclass
    class ModelConfig:
        hidden_size: int
        dropout: float = 0.1

    # Register target class
    rc.register("model", ModelConfig)

    # Instantiate from config file
    model = rc.instantiate(Path("config.yaml"))

    # Type-safe version
    model = rc.instantiate(Path("config.yaml"), ModelConfig)

    # With CLI overrides (enabled by default)
    # python main.py hidden_size=512
    model = rc.instantiate(Path("config.yaml"))

    # With programmatic overrides
    model = rc.instantiate(Path("config.yaml"), overrides={"hidden_size": 512})
"""

import sys
from pathlib import Path
from types import MappingProxyType
from typing import Any, TypeVar, overload

from .ConfigStore import ConfigStore, ConfigReference
from .ConfigValidator import ConfigValidator, ValidationResult
from .ConfigInstantiator import ConfigInstantiator
from .loaders import load_config as _load_config
from .override import (
    Override,
    apply_overrides,
    extract_cli_overrides,
    parse_dict_overrides,
    parse_override_value,
)
from .errors import (
    AmbiguousTargetError,
    ConfigError,
    ConfigFileError,
    InstantiationError,
    InvalidOverridePathError,
    InvalidOverrideSyntaxError,
    MergeError,
    MissingFieldError,
    OverrideError,
    TargetNotFoundError,
    TargetTypeMismatchError,
    TypeInferenceError,
    TypeMismatchError,
    ValidationError,
)

T = TypeVar("T")


# Internal singleton instances
_store = ConfigStore()
_validator = ConfigValidator(_store)
_instantiator = ConfigInstantiator(_store, _validator)


def register(name: str, target: type) -> None:
    """Register a target class under a unique name.

    :param name: Unique identifier for the target class.
    :param target: Class to register.

    Example::

        @dataclass
        class ModelConfig:
            hidden_size: int

        rc.register("model", ModelConfig)
    """
    _store.register(name, target)


def unregister(name: str) -> None:
    """Unregister a previously registered configuration reference.

    :param name: Identifier of the reference to unregister.
    :raises KeyError: If no reference with that name exists.
    """
    _store.unregister(name)


def validate(path: Path) -> ValidationResult:
    """Validate a config file without instantiating (dry-run).

    :param path: Path to config file.
    :return: ValidationResult with any errors found.

    Example::

        result = rc.validate(Path("config.yaml"))
        if not result.valid:
            for error in result.errors:
                print(error)
    """
    config = _load_config(path)
    return _validator.validate(config)


@overload
def instantiate(path: Path, *, cli_overrides: bool = ...) -> Any: ...
@overload
def instantiate(path: Path, expected_type: type[T], *, cli_overrides: bool = ...) -> T: ...
@overload
def instantiate(
    path: Path, *, overrides: dict[str, Any], cli_overrides: bool = ...
) -> Any: ...
@overload
def instantiate(
    path: Path,
    expected_type: type[T],
    *,
    overrides: dict[str, Any],
    cli_overrides: bool = ...,
) -> T: ...


def instantiate(
    path: Path,
    expected_type: type[T] | None = None,
    *,
    overrides: dict[str, Any] | None = None,
    cli_overrides: bool = True,
) -> T | Any:
    """Load, validate, and instantiate a config file.

    :param path: Path to config file.
    :param expected_type: Optional type for type-safe returns.
    :param overrides: Dictionary of config overrides using dot notation keys.
    :param cli_overrides: Whether to parse CLI overrides from sys.argv (default True).
    :return: Instantiated object (typed if expected_type provided).
    :raises ConfigFileError: If file cannot be loaded.
    :raises ValidationError: If config is invalid.
    :raises InvalidOverridePathError: If an override path doesn't exist.
    :raises InvalidOverrideSyntaxError: If an override string is malformed.
    :raises InstantiationError: If instantiation fails.

    Example::

        # From file (CLI overrides enabled by default)
        model = rc.instantiate(Path("config.yaml"))

        # Type-safe version
        model = rc.instantiate(Path("config.yaml"), ModelConfig)

        # With programmatic overrides
        model = rc.instantiate(Path("config.yaml"), overrides={"model.lr": 0.01})

        # Disable CLI overrides (for tests)
        model = rc.instantiate(Path("config.yaml"), cli_overrides=False)
    """
    config = _load_config(path)

    # Collect all overrides
    all_overrides: list[Override] = []

    # Programmatic overrides first
    if overrides:
        all_overrides.extend(parse_dict_overrides(overrides))

    # CLI overrides second (wins on conflict)
    if cli_overrides:
        all_overrides.extend(extract_cli_overrides(sys.argv[1:]))

    # Validate paths and coerce values
    for override in all_overrides:
        expected_type_hint = _validator.validate_override_path(override.path, config)
        if override.operation == "set" and isinstance(override.value, str):
            override.value = parse_override_value(override.value, expected_type_hint)

    # Apply overrides
    if all_overrides:
        config = apply_overrides(config, all_overrides)

    return _instantiator.instantiate(config)


def known_references() -> MappingProxyType[str, ConfigReference]:
    """Get a read-only view of all registered configuration references.

    :return: Immutable mapping of name to ConfigReference.
    """
    return _store.known_references


# Public API
__all__ = [
    # Module-level API (primary)
    "register",
    "unregister",
    "validate",
    "instantiate",
    "known_references",
    # Classes for advanced usage
    "ConfigStore",
    "ConfigReference",
    "ConfigValidator",
    "ValidationResult",
    "ConfigInstantiator",
    "Override",
    # Exceptions
    "AmbiguousTargetError",
    "ConfigError",
    "ConfigFileError",
    "InstantiationError",
    "InvalidOverridePathError",
    "InvalidOverrideSyntaxError",
    "MergeError",
    "MissingFieldError",
    "OverrideError",
    "TargetNotFoundError",
    "TargetTypeMismatchError",
    "TypeInferenceError",
    "TypeMismatchError",
    "ValidationError",
]
