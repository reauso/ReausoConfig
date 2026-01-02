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

from .store import ConfigStore, ConfigReference
from .validation import ConfigValidator, ValidationResult
from .instantiation import ConfigInstantiator
from .composition import (
    ConfigComposer,
    set_cache_size,
    clear_cache,
    Provenance,
    ProvenanceEntry,
    InstanceRef,
)
from .override import (
    Override,
    apply_overrides,
    extract_cli_overrides,
    parse_dict_overrides,
    parse_override_value,
)
from .errors import (
    AmbiguousTargetError,
    CircularInstanceError,
    CircularInterpolationError,
    CircularRefError,
    CompositionError,
    ConfigError,
    ConfigFileError,
    EnvironmentVariableError,
    InstanceResolutionError,
    InstantiationError,
    InterpolationError,
    InterpolationResolutionError,
    InterpolationSyntaxError,
    InvalidOverridePathError,
    InvalidOverrideSyntaxError,
    MergeError,
    MissingFieldError,
    OverrideError,
    RefAtRootError,
    RefInstanceConflictError,
    RefResolutionError,
    RequiredValueError,
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


def validate(
    path: Path,
    *,
    overrides: dict[str, Any] | None = None,
    cli_overrides: bool = True,
) -> ValidationResult:
    """Validate a config file without instantiating (dry-run).

    Composes the config (resolving _ref_ and _instance_ references), applies
    any overrides, and validates against registered targets. Also checks that
    all _required_ values have been satisfied.

    :param path: Path to config file.
    :param overrides: Dictionary of config overrides using dot notation keys.
    :param cli_overrides: Whether to parse CLI overrides from sys.argv (default True).
    :return: ValidationResult with any errors found.

    Example::

        result = rc.validate(Path("config.yaml"))
        if not result.valid:
            for error in result.errors:
                print(error)

        # With overrides to satisfy _required_ values
        result = rc.validate(
            Path("config.yaml"),
            overrides={"api_key": "secret123"},
        )
    """
    from rconfig.validation.required import find_required_markers
    from rconfig.errors import RequiredValueError

    composer = ConfigComposer()
    config = composer.compose(path)

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

    # Check for unsatisfied _required_ values
    required_markers = find_required_markers(config)
    required_errors: list[ValidationError] = []
    if required_markers:
        missing = [(m.path, m.expected_type) for m in required_markers]
        required_errors.append(RequiredValueError(missing))

    # Run regular validation
    result = _validator.validate(config)

    # Combine required value errors with validation errors
    all_errors = required_errors + result.errors
    return ValidationResult(valid=len(all_errors) == 0, errors=all_errors)


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
    """Load, compose, validate, and instantiate a config file.

    Composes the config (resolving _ref_ and _instance_ references), applies
    any overrides, validates against registered targets, and instantiates
    the final object tree.

    :param path: Path to config file.
    :param expected_type: Optional type for type-safe returns.
    :param overrides: Dictionary of config overrides using dot notation keys.
    :param cli_overrides: Whether to parse CLI overrides from sys.argv (default True).
    :return: Instantiated object (typed if expected_type provided).
    :raises ConfigFileError: If file cannot be loaded.
    :raises CircularRefError: If circular _ref_ references are detected.
    :raises CircularInstanceError: If circular _instance_ references are detected.
    :raises RefResolutionError: If a _ref_ cannot be resolved.
    :raises InstanceResolutionError: If an _instance_ path cannot be resolved.
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
    # Compose config (resolve _ref_ and _instance_)
    composer = ConfigComposer()
    config = composer.compose(path)
    instance_targets = composer.instance_targets

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

    # Check for unsatisfied _required_ values (after overrides, before interpolation)
    from rconfig.validation.required import find_required_markers
    from rconfig.errors import RequiredValueError

    required_markers = find_required_markers(config)
    if required_markers:
        missing = [(m.path, m.expected_type) for m in required_markers]
        raise RequiredValueError(missing)

    # Resolve interpolations (${...} expressions)
    from rconfig.interpolation import resolve_interpolations

    config = resolve_interpolations(config)

    return _instantiator.instantiate(config, instance_targets=instance_targets)


def known_references() -> MappingProxyType[str, ConfigReference]:
    """Get a read-only view of all registered configuration references.

    :return: Immutable mapping of name to ConfigReference.
    """
    return _store.known_references


def get_provenance(path: Path) -> Provenance:
    """Compose a config file and track the origin of each value.

    :param path: Path to the entry-point config file.
    :return: Provenance object with origin information for each config value.

    Example::

        prov = rc.get_provenance(Path("trainer.yaml"))
        print(prov)  # Shows config with file:line annotations
        entry = prov.get("model.layers")  # Get specific origin info
        for path, entry in prov.items():
            print(f"{path}: {entry.file}:{entry.line}")
    """
    from rconfig.interpolation import resolve_interpolations

    composer = ConfigComposer()
    provenance = composer.compose_with_provenance(path)

    # Resolve interpolations and update provenance with interpolation sources
    config = provenance._config
    resolved = resolve_interpolations(config, provenance)
    provenance.set_config(resolved)

    return provenance


# Public API - Minimal root exports
# For classes like ConfigStore, ConfigValidator, etc., import from submodules:
#   from rconfig.store import ConfigStore
#   from rconfig.validation import ConfigValidator
#   from rconfig.composition import ConfigComposer, Provenance
#   from rconfig.override import Override
__all__ = [
    # Module-level API functions (primary interface)
    "register",
    "unregister",
    "validate",
    "instantiate",
    "known_references",
    "get_provenance",
    "set_cache_size",
    "clear_cache",
    # Exceptions (available at root for convenience)
    "AmbiguousTargetError",
    "CircularInstanceError",
    "CircularRefError",
    "CompositionError",
    "ConfigError",
    "ConfigFileError",
    "InstanceResolutionError",
    "InstantiationError",
    "InvalidOverridePathError",
    "InvalidOverrideSyntaxError",
    "MergeError",
    "MissingFieldError",
    "OverrideError",
    "RefAtRootError",
    "RefInstanceConflictError",
    "RefResolutionError",
    "RequiredValueError",
    "TargetNotFoundError",
    "TargetTypeMismatchError",
    "TypeInferenceError",
    "TypeMismatchError",
    "ValidationError",
]
