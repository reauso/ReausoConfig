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
"""

from pathlib import Path
from types import MappingProxyType
from typing import Any, TypeVar, overload

from .ConfigStore import ConfigStore, ConfigReference
from .ConfigValidator import ConfigValidator, ValidationResult
from .ConfigInstantiator import ConfigInstantiator
from .loaders import load_config as _load_config
from .errors import (
    AmbiguousTargetError,
    ConfigError,
    ConfigFileError,
    InstantiationError,
    MissingFieldError,
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
def instantiate(path: Path) -> Any: ...
@overload
def instantiate(path: Path, expected_type: type[T]) -> T: ...


def instantiate(path: Path, expected_type: type[T] | None = None) -> T | Any:
    """Load, validate, and instantiate a config file.

    :param path: Path to config file.
    :param expected_type: Optional type for type-safe returns.
    :return: Instantiated object (typed if expected_type provided).
    :raises ConfigFileError: If file cannot be loaded.
    :raises ValidationError: If config is invalid.
    :raises InstantiationError: If instantiation fails.

    Example::

        # From file
        model = rc.instantiate(Path("config.yaml"))

        # Type-safe version
        model = rc.instantiate(Path("config.yaml"), ModelConfig)
    """
    config = _load_config(path)
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
    # Exceptions
    "AmbiguousTargetError",
    "ConfigError",
    "ConfigFileError",
    "InstantiationError",
    "MissingFieldError",
    "TargetNotFoundError",
    "TargetTypeMismatchError",
    "TypeInferenceError",
    "TypeMismatchError",
    "ValidationError",
]
