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
import threading
from functools import singledispatch
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Callable, TypeVar, overload

from .store import ConfigStore, ConfigReference
from .help import (
    HelpIntegration,
    FunctionHelpIntegration,
    FlatHelpIntegration,
    GroupedHelpIntegration,
    ArgparseHelpIntegration,
)

if TYPE_CHECKING:
    from .composition import Provenance
    from .composition.ProvenanceBuilder import ProvenanceBuilder
from .validation import ConfigValidator, ValidationResult
from .instantiation import ConfigInstantiator, is_lazy_proxy, force_initialize
from .composition import (
    ConfigComposer,
    set_cache_size,
    clear_cache,
    Provenance,
    ProvenanceEntry,
    InstanceRef,
    EntrySourceType,
    NodeSourceType,
)
from .override import (
    Override,
    apply_overrides,
    extract_cli_overrides,
    parse_dict_overrides,
    parse_override_value,
)
from .export import (
    Exporter,
    DictExporter,
    YamlExporter,
    JsonExporter,
    TomlExporter,
    FileExporter,
    SingleFileExporter,
    MultiFileExporter,
    register_exporter,
    unregister_exporter,
    get_exporter,
    supported_exporter_extensions,
)
from .loaders import (
    ConfigFileLoader,
    YamlConfigLoader,
    JsonConfigLoader,
    TomlConfigLoader,
    register_loader,
    unregister_loader,
    get_loader,
    supported_loader_extensions,
)
from .errors import (
    AmbiguousRefError,
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
    InvalidInnerPathError,
    InvalidOverridePathError,
    InvalidOverrideSyntaxError,
    MergeError,
    MissingFieldError,
    OverrideError,
    RefAtRootError,
    RefInstanceConflictError,
    RefResolutionError,
    ResolverError,
    ResolverExecutionError,
    RequiredValueError,
    TargetNotFoundError,
    TargetTypeMismatchError,
    TypeInferenceError,
    TypeMismatchError,
    UnknownResolverError,
    ValidationError,
)
from .interpolation.registry import ResolverRegistry
from .deprecation import (
    DeprecationInfo,
    DeprecationHandler,
    RconfigDeprecationWarning,
    get_deprecation_registry,
)
from .errors import DeprecatedKeyError

T = TypeVar("T")


# Internal singleton instances
_store = ConfigStore()
_resolver_registry = ResolverRegistry()
_validator = ConfigValidator(_store)
_instantiator = ConfigInstantiator(_store, _validator)

# Help integration storage (thread-safe)
_help_integration: HelpIntegration = FlatHelpIntegration()
_help_integration_lock = threading.RLock()


def set_help_integration(integration: HelpIntegration) -> None:
    """Set a custom help integration.

    Thread-safe: protected by internal lock.

    :param integration: A HelpIntegration instance. Cannot be None.
    :raises ValueError: If integration is None.

    Example::

        from rconfig.help import GroupedHelpIntegration

        rc.set_help_integration(GroupedHelpIntegration())

        # Or a custom integration
        class CustomIntegration(HelpIntegration):
            def integrate(self, provenance, config_path):
                # Custom integration logic
                ...

        rc.set_help_integration(CustomIntegration())
    """
    if integration is None:
        raise ValueError("integration cannot be None")

    global _help_integration
    with _help_integration_lock:
        _help_integration = integration


def current_help_integration() -> HelpIntegration:
    """Return the current help integration.

    Thread-safe: protected by internal lock.
    Returns the default FlatHelpIntegration if none was explicitly set.

    :return: The current HelpIntegration (never None).

    Example::

        integration = rc.current_help_integration()
        print(f"Using: {integration.__class__.__name__}")
    """
    with _help_integration_lock:
        return _help_integration


def help_integration(func: Callable[["Provenance", str], None]) -> Callable[["Provenance", str], None]:
    """Decorator to register a function as the help integration.

    The decorated function is responsible for all behavior including
    calling sys.exit() if needed. The framework only calls the function
    when --help/-h is detected.

    :param func: Integration function with signature (provenance, config_path) -> None.
    :return: The same function (for use as decorator).

    Example::

        @rc.help_integration
        def my_integration(provenance, config_path):
            for path, entry in provenance.items():
                print(f"{path}: {entry.type_hint}")
            sys.exit(0)
    """
    set_help_integration(FunctionHelpIntegration(func))
    return func


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

    # Handle --help/-h when cli_overrides is enabled
    if cli_overrides and ("--help" in sys.argv or "-h" in sys.argv):
        integration = current_help_integration()

        # Consume --help/-h from sys.argv if integration requests it
        if integration.consume_help_flag:
            sys.argv = [arg for arg in sys.argv if arg not in ("--help", "-h")]

        # Get provenance with type hints and descriptions
        provenance = get_provenance(path)

        # Call the integration (it's responsible for sys.exit() if needed)
        integration.integrate(provenance, str(path))

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
def instantiate(path: Path, *, cli_overrides: bool = ..., lazy: bool = ...) -> Any: ...
@overload
def instantiate(path: Path, expected_type: type[T], *, cli_overrides: bool = ..., lazy: bool = ...) -> T: ...
@overload
def instantiate(
    path: Path, *, overrides: dict[str, Any], cli_overrides: bool = ..., lazy: bool = ...
) -> Any: ...
@overload
def instantiate(
    path: Path,
    expected_type: type[T],
    *,
    overrides: dict[str, Any],
    cli_overrides: bool = ...,
    lazy: bool = ...,
) -> T: ...
@overload
def instantiate(
    path: Path, *, inner_path: str, cli_overrides: bool = ..., lazy: bool = ...
) -> Any: ...
@overload
def instantiate(
    path: Path,
    expected_type: type[T],
    *,
    inner_path: str,
    cli_overrides: bool = ...,
    lazy: bool = ...,
) -> T: ...
@overload
def instantiate(
    path: Path,
    *,
    inner_path: str,
    overrides: dict[str, Any],
    cli_overrides: bool = ...,
    lazy: bool = ...,
) -> Any: ...
@overload
def instantiate(
    path: Path,
    expected_type: type[T],
    *,
    inner_path: str,
    overrides: dict[str, Any],
    cli_overrides: bool = ...,
    lazy: bool = ...,
) -> T: ...


def instantiate(
    path: Path,
    expected_type: type[T] | None = None,
    *,
    inner_path: str | None = None,
    overrides: dict[str, Any] | None = None,
    cli_overrides: bool = True,
    lazy: bool = False,
) -> T | Any:
    """Load, compose, validate, and instantiate a config file.

    Composes the config (resolving _ref_ and _instance_ references), applies
    any overrides, validates against registered targets, and instantiates
    the final object tree.

    :param path: Path to config file.
    :param expected_type: Optional type for type-safe returns.
    :param inner_path: Optional path to instantiate only a section of the config.
                       Interpolations are resolved from the full config before
                       extraction. External _instance_ refs are auto-instantiated.
    :param overrides: Dictionary of config overrides using dot notation keys.
    :param cli_overrides: Whether to parse CLI overrides from sys.argv (default True).
    :param lazy: If True, all nested configs are lazily instantiated.
                 Lazy objects delay __init__ until first attribute access.
    :return: Instantiated object (typed if expected_type provided).
    :raises ConfigFileError: If file cannot be loaded.
    :raises CircularRefError: If circular _ref_ references are detected.
    :raises CircularInstanceError: If circular _instance_ references are detected.
    :raises RefResolutionError: If a _ref_ cannot be resolved.
    :raises InstanceResolutionError: If an _instance_ path cannot be resolved.
    :raises InvalidInnerPathError: If inner_path doesn't exist or is invalid.
    :raises ValidationError: If config is invalid.
    :raises InvalidOverridePathError: If an override path doesn't exist.
    :raises InvalidOverrideSyntaxError: If an override string is malformed.
    :raises InstantiationError: If instantiation fails.

    Example::

        # From file (CLI overrides enabled by default)
        model = rc.instantiate(Path("config.yaml"))

        # Type-safe version
        model = rc.instantiate(Path("config.yaml"), ModelConfig)

        # Partial instantiation - only instantiate a section
        model = rc.instantiate(Path("trainer.yaml"), inner_path="model")
        encoder = rc.instantiate(Path("trainer.yaml"), inner_path="model.encoder")

        # With programmatic overrides
        model = rc.instantiate(Path("config.yaml"), overrides={"model.lr": 0.01})

        # Disable CLI overrides (for tests)
        model = rc.instantiate(Path("config.yaml"), cli_overrides=False)

        # With lazy instantiation (all nested configs are lazy)
        model = rc.instantiate(Path("config.yaml"), lazy=True)

        # CLI help (--help or -h) shows config entries and exits
        # python main.py --help
    """
    # Handle --help/-h when cli_overrides is enabled
    if cli_overrides and ("--help" in sys.argv or "-h" in sys.argv):
        integration = current_help_integration()

        # Consume --help/-h from sys.argv if integration requests it
        if integration.consume_help_flag:
            sys.argv = [arg for arg in sys.argv if arg not in ("--help", "-h")]

        # Get provenance with type hints and descriptions
        provenance = get_provenance(path)

        # Call the integration (it's responsible for sys.exit() if needed)
        integration.integrate(provenance, str(path))

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

    # Handle partial instantiation
    if inner_path is not None:
        from rconfig._internal.partial import extract_partial_config
        from rconfig._internal.path_utils import get_value_at_path

        # Extract sub-config (interpolations already resolved from full config)
        sub_config, processed_targets, external_targets = extract_partial_config(
            config=config,
            inner_path=inner_path,
            instance_targets=instance_targets,
        )

        # Pre-instantiate external targets
        external_instances: dict[str, Any] = {}
        for ext_path in external_targets:
            ext_config = get_value_at_path(config, ext_path)
            if isinstance(ext_config, dict) and "_target_" in ext_config:
                external_instances[f"__external__:{ext_path}"] = (
                    _instantiator.instantiate(
                        ext_config, instance_targets={}, config_path=ext_path
                    )
                )

        return _instantiator.instantiate(
            sub_config,
            instance_targets=processed_targets,
            external_instances=external_instances,
            lazy=lazy,
        )

    return _instantiator.instantiate(config, instance_targets=instance_targets, lazy=lazy)


def known_references() -> MappingProxyType[str, ConfigReference]:
    """Get a read-only view of all registered configuration references.

    :return: Immutable mapping of name to ConfigReference.
    """
    return _store.known_references


# Type variable for the resolver decorator
F = TypeVar("F", bound=Callable[..., Any])


def register_resolver(*path: str, func: Callable[..., Any]) -> None:
    """Register a custom resolver function.

    Resolvers can be invoked in interpolation expressions using the syntax:
    ``${app:resolver_name}`` or ``${app:namespace:resolver_name(args)}``.

    :param path: One or more path components (e.g., "uuid" or "db", "lookup").
    :param func: The resolver function to register.
    :raises ValueError: If path is empty or func is not callable.

    Example::

        def gen_uuid() -> str:
            import uuid
            return str(uuid.uuid4())

        rc.register_resolver("uuid", func=gen_uuid)

        # Namespaced resolver
        def db_lookup(table: str, id: int) -> dict:
            return database.get(table, id)

        rc.register_resolver("db", "lookup", func=db_lookup)
    """
    _resolver_registry.register(*path, func=func)


def unregister_resolver(*path: str) -> None:
    """Unregister a previously registered resolver.

    :param path: One or more path components (e.g., "uuid" or "db", "lookup").
    :raises KeyError: If no resolver with that path exists.

    Example::

        rc.unregister_resolver("uuid")
        rc.unregister_resolver("db", "lookup")
    """
    _resolver_registry.unregister(*path)


def resolver(*path: str) -> Callable[[F], F]:
    """Decorator to register a resolver function.

    Resolvers can be invoked in interpolation expressions using the syntax:
    ``${app:resolver_name}`` or ``${app:namespace:resolver_name(args)}``.

    If the resolver function has a parameter named ``_config_``, it will receive
    the current config dictionary (read-only) when invoked.

    :param path: One or more path components (e.g., "uuid" or "db", "lookup").
    :return: Decorator function.

    Example::

        @rc.resolver("uuid")
        def gen_uuid() -> str:
            import uuid
            return str(uuid.uuid4())

        @rc.resolver("db", "lookup")
        def db_lookup(table: str, id: int) -> dict:
            return database.get(table, id)

        @rc.resolver("derive")
        def derive(path: str, *, _config_: dict) -> Any:
            # Access config values
            return get_nested_value(_config_, path)
    """

    def decorator(func: F) -> F:
        register_resolver(*path, func=func)
        return func

    return decorator


def get_provenance(path: Path) -> "Provenance":
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
    from rconfig.composition.ProvenanceBuilder import ProvenanceBuilder
    from rconfig.composition.Walker import CompositionWalker
    from rconfig.composition.InstanceResolver import InstanceResolver

    # Create builder for accumulating provenance during composition
    builder = ProvenanceBuilder()

    # Compose the config tree, resolving _ref_ and collecting _instance_ markers
    walker = CompositionWalker(None, builder)
    result = walker.compose(path)

    # Resolve all _instance_ references
    instance_resolver = InstanceResolver(builder)
    config = instance_resolver.resolve(result.instances, result.config)

    # Set initial config
    builder.set_config(config)

    # Resolve interpolations and update builder with interpolation sources
    resolved = resolve_interpolations(config, builder)
    builder.set_config(resolved)

    # Resolve target class information from registered targets
    builder.resolve_targets(_store.known_references)

    # Build the final immutable provenance
    return builder.build()


# === Deprecation API ===


def deprecate(
    old_key: str,
    *,
    new_key: str | None = None,
    message: str | None = None,
    remove_in: str | None = None,
    policy: str | None = None,
) -> None:
    """Register a deprecated configuration key.

    Supports exact paths and glob-style patterns:
    - Exact: "model.lr" matches only "model.lr"
    - Single wildcard (*): "*.lr" matches "model.lr", "encoder.lr" (one level)
    - Double wildcard (**): "**.lr" matches "a.b.c.lr" (any depth)

    :param old_key: The deprecated key pattern (exact path or glob).
    :param new_key: Optional new key location for auto-mapping.
    :param message: Optional custom deprecation message.
    :param remove_in: Optional version when the key will be removed.
    :param policy: Per-deprecation policy override ("warn", "error", "ignore").

    Example::

        # Register a simple deprecation
        rc.deprecate("learning_rate", new_key="model.optimizer.lr")

        # With version and message
        rc.deprecate(
            "n_epochs",
            new_key="training.epochs",
            message="Use 'training.epochs' instead",
            remove_in="2.0.0",
        )

        # Glob patterns
        rc.deprecate("**.dropout", message="Dropout configured elsewhere")
        rc.deprecate("*.lr", message="Use full path 'optimizer.learning_rate'")

        # Per-deprecation policy (always error for this key)
        rc.deprecate("critical_key", policy="error")
    """
    registry = get_deprecation_registry()
    registry.register(
        old_key,
        new_key=new_key,
        message=message,
        remove_in=remove_in,
        policy=policy,
    )


def undeprecate(old_key: str) -> None:
    """Remove a deprecation registration.

    :param old_key: The deprecated key pattern to remove.
    :raises KeyError: If no deprecation with that pattern exists.

    Example::

        rc.undeprecate("learning_rate")
    """
    registry = get_deprecation_registry()
    registry.unregister(old_key)


def set_deprecation_policy(policy: str) -> None:
    """Set the global deprecation policy.

    Controls how deprecated keys are handled by default:
    - "warn": Emit a warning (default)
    - "error": Raise DeprecatedKeyError
    - "ignore": Silently ignore

    Per-deprecation policies override this global setting.

    :param policy: One of "warn", "error", "ignore".

    Example::

        rc.set_deprecation_policy("warn")   # Emit warnings (default)
        rc.set_deprecation_policy("error")  # Raise errors
        rc.set_deprecation_policy("ignore") # Silent
    """
    registry = get_deprecation_registry()
    registry.set_policy(policy)  # type: ignore


def set_deprecation_handler(handler: DeprecationHandler) -> None:
    """Set a custom deprecation warning handler.

    The handler is called when a deprecated key is accessed and policy is "warn".

    :param handler: A DeprecationHandler instance.

    Example::

        from rconfig.deprecation import DeprecationHandler, DeprecationInfo

        class LoggingHandler(DeprecationHandler):
            def handle(self, info: DeprecationInfo, path: str, file: str, line: int) -> None:
                import logging
                logging.warning(f"Deprecated key '{path}' at {file}:{line}")

        rc.set_deprecation_handler(LoggingHandler())
    """
    registry = get_deprecation_registry()
    registry.set_handler(handler)


# Type for deprecation handler decorator
H = TypeVar("H", bound=Callable[..., Any])


def deprecation_handler(func: H) -> H:
    """Decorator to register a function as the deprecation handler.

    The function should accept: (info: DeprecationInfo, path: str, file: str, line: int)

    :param func: Handler function.
    :return: The same function (for use as decorator).

    Example::

        @rc.deprecation_handler
        def my_handler(info, path, file, line):
            print(f"DEPRECATED: {path} -> {info.new_key}")
    """
    registry = get_deprecation_registry()
    registry.set_handler_func(func)
    return func


# === Config Export / Serialization API ===


def _resolved_config(
    path: Path,
    *,
    overrides: dict[str, Any] | None = None,
    cli_overrides: bool = True,
) -> tuple[dict[str, Any], ConfigComposer]:
    """Internal helper: run resolution pipeline without instantiation.

    :param path: Path to config file.
    :param overrides: Dictionary of config overrides using dot notation keys.
    :param cli_overrides: Whether to parse CLI overrides from sys.argv.
    :return: Tuple of (resolved config dict, composer instance).
    """
    from rconfig.interpolation import resolve_interpolations
    from rconfig.validation.required import find_required_markers

    # Handle --help/-h when cli_overrides is enabled
    if cli_overrides and ("--help" in sys.argv or "-h" in sys.argv):
        integration = current_help_integration()

        # Consume --help/-h from sys.argv if integration requests it
        if integration.consume_help_flag:
            sys.argv = [arg for arg in sys.argv if arg not in ("--help", "-h")]

        # Get provenance with type hints and descriptions
        provenance = get_provenance(path)

        # Call the integration (it's responsible for sys.exit() if needed)
        integration.integrate(provenance, str(path))

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
    if required_markers:
        missing = [(m.path, m.expected_type) for m in required_markers]
        raise RequiredValueError(missing)

    # Resolve interpolations
    config = resolve_interpolations(config)

    return config, composer


def export(
    path: Path,
    exporter: Exporter,
    *,
    overrides: dict[str, Any] | None = None,
    cli_overrides: bool = True,
) -> Any:
    """Export resolved config using a custom exporter.

    :param path: Path to config file.
    :param exporter: Exporter instance to use.
    :param overrides: Dictionary of config overrides using dot notation keys.
    :param cli_overrides: Whether to parse CLI overrides from sys.argv.
    :return: The exported data in the exporter's target format.

    Example::

        class TomlExporter(rc.Exporter):
            def export(self, config: dict) -> str:
                import tomli_w
                return tomli_w.dumps(config)

        toml_str = rc.export(Path("config.yaml"), exporter=TomlExporter())
    """
    config, _ = _resolved_config(path, overrides=overrides, cli_overrides=cli_overrides)
    return exporter.export(config)


def to_dict(
    path: Path,
    *,
    overrides: dict[str, Any] | None = None,
    cli_overrides: bool = True,
    exclude_markers: bool = False,
) -> dict[str, Any]:
    """Export resolved config as a Python dictionary.

    :param path: Path to config file.
    :param overrides: Dictionary of config overrides using dot notation keys.
    :param cli_overrides: Whether to parse CLI overrides from sys.argv.
    :param exclude_markers: If True, remove internal markers (_target_, etc.).
    :return: Resolved config as a dictionary.

    Example::

        config = rc.to_dict(Path("config.yaml"))
        print(config["model"]["hidden_size"])

        # With overrides
        config = rc.to_dict(
            Path("config.yaml"),
            overrides={"model.lr": 0.01},
        )

        # Without internal markers
        clean = rc.to_dict(Path("config.yaml"), exclude_markers=True)
    """
    exporter = DictExporter(exclude_markers=exclude_markers)
    return export(path, exporter, overrides=overrides, cli_overrides=cli_overrides)


def to_yaml(
    path: Path,
    *,
    overrides: dict[str, Any] | None = None,
    cli_overrides: bool = True,
    exclude_markers: bool = False,
) -> str:
    """Export resolved config as a YAML string.

    :param path: Path to config file.
    :param overrides: Dictionary of config overrides using dot notation keys.
    :param cli_overrides: Whether to parse CLI overrides from sys.argv.
    :param exclude_markers: If True, remove internal markers (_target_, etc.).
    :return: Resolved config as a YAML string.

    Example::

        yaml_str = rc.to_yaml(Path("config.yaml"))
        print(yaml_str)

        # With overrides
        yaml_str = rc.to_yaml(
            Path("config.yaml"),
            overrides={"model.lr": 0.01},
        )
    """
    exporter = YamlExporter(exclude_markers=exclude_markers)
    return export(path, exporter, overrides=overrides, cli_overrides=cli_overrides)


def to_json(
    path: Path,
    *,
    overrides: dict[str, Any] | None = None,
    cli_overrides: bool = True,
    exclude_markers: bool = False,
    indent: int | None = 2,
) -> str:
    """Export resolved config as a JSON string.

    :param path: Path to config file.
    :param overrides: Dictionary of config overrides using dot notation keys.
    :param cli_overrides: Whether to parse CLI overrides from sys.argv.
    :param exclude_markers: If True, remove internal markers (_target_, etc.).
    :param indent: Number of spaces for indentation, None for compact output.
    :return: Resolved config as a JSON string.

    Example::

        json_str = rc.to_json(Path("config.yaml"))
        print(json_str)

        # Compact output
        json_str = rc.to_json(Path("config.yaml"), indent=None)

        # With overrides
        json_str = rc.to_json(
            Path("config.yaml"),
            overrides={"model.lr": 0.01},
        )
    """
    exporter = JsonExporter(exclude_markers=exclude_markers, indent=indent)
    return export(path, exporter, overrides=overrides, cli_overrides=cli_overrides)


def to_toml(
    path: Path,
    *,
    overrides: dict[str, Any] | None = None,
    cli_overrides: bool = True,
    exclude_markers: bool = False,
) -> str:
    """Export resolved config as a TOML string.

    :param path: Path to config file.
    :param overrides: Dictionary of config overrides using dot notation keys.
    :param cli_overrides: Whether to parse CLI overrides from sys.argv.
    :param exclude_markers: If True, remove internal markers (_target_, etc.).
    :return: Resolved config as a TOML string.

    Example::

        toml_str = rc.to_toml(Path("config.yaml"))
        print(toml_str)

        # With overrides
        toml_str = rc.to_toml(
            Path("config.yaml"),
            overrides={"model.lr": 0.01},
        )
    """
    exporter = TomlExporter(exclude_markers=exclude_markers)
    return export(path, exporter, overrides=overrides, cli_overrides=cli_overrides)


@singledispatch
def to_file(
    source: Path | dict[str, Any],
    output_path: Path,
    *,
    overrides: dict[str, Any] | None = None,
    cli_overrides: bool = True,
    exclude_markers: bool = False,
) -> None:
    """Export config to a single file with format auto-detection.

    All references are flattened into a single standalone file.
    Format is determined by the output file extension.

    :param source: Source config (Path to file, or dict).
    :param output_path: Output file path (extension determines format).
    :param overrides: Config overrides (only used with Path input).
    :param cli_overrides: Parse CLI overrides (only used with Path input).
    :param exclude_markers: If True, remove internal markers (_target_, etc.).
    :raises ConfigFileError: If the output file extension is not supported.

    Example::

        # Export from file to different formats
        rc.to_file(Path("config.yaml"), Path("output.json"))   # YAML -> JSON
        rc.to_file(Path("config.yaml"), Path("output.toml"))   # YAML -> TOML

        # Export from dict
        config = {"model": {"lr": 0.01}, "epochs": 10}
        rc.to_file(config, Path("output.yaml"))

        # Post-processing workflow
        config = rc.to_dict(Path("config.yaml"))
        config["extra"] = "value"
        rc.to_file(config, Path("output.json"))
    """
    raise TypeError(f"Unsupported source type: {type(source)}")


@to_file.register
def _to_file_from_path(
    source: Path,
    output_path: Path,
    *,
    overrides: dict[str, Any] | None = None,
    cli_overrides: bool = True,
    exclude_markers: bool = False,
) -> None:
    config, _ = _resolved_config(
        source, overrides=overrides, cli_overrides=cli_overrides
    )
    file_exporter = SingleFileExporter(exclude_markers=exclude_markers)
    file_exporter.export_to_file(config, output_path)


@to_file.register
def _to_file_from_dict(
    source: dict,
    output_path: Path,
    *,
    exclude_markers: bool = False,
) -> None:
    file_exporter = SingleFileExporter(exclude_markers=exclude_markers)
    file_exporter.export_to_file(source, output_path)


@singledispatch
def to_files(
    source: Path | dict[str, Any],
    config_root_file: Path,
    *,
    overrides: dict[str, Any] | None = None,
    cli_overrides: bool = True,
    exclude_markers: bool = False,
) -> None:
    """Export config preserving file structure with format auto-detection.

    When source is a Path, each referenced file is exported separately with
    interpolations resolved. The _ref_ paths are preserved.

    When source is a dict, only the root file is written (no ref_graph available).

    Format is determined by file extensions:
    - Root file: format from config_root_file extension
    - Referenced files: preserve original extension from source files

    :param source: Source config (Path to file, or dict).
    :param config_root_file: Output root file path (extension determines root format).
    :param overrides: Config overrides (only used with Path input).
    :param cli_overrides: Parse CLI overrides (only used with Path input).
    :param exclude_markers: If True, remove internal markers (_target_, etc.).
    :raises ConfigFileError: If an output file extension is not supported.

    Example::

        # Export from file with preserved structure
        rc.to_files(Path("trainer.yaml"), Path("output/trainer.json"))
        # Creates:
        #   output/trainer.json (root file in JSON)
        #   output/models/resnet.yaml (preserves original YAML format)

        # Export from dict (root file only)
        config = {"model": {"lr": 0.01}, "epochs": 10}
        rc.to_files(config, Path("output/config.yaml"))
    """
    raise TypeError(f"Unsupported source type: {type(source)}")


@to_files.register
def _to_files_from_path(
    source: Path,
    config_root_file: Path,
    *,
    overrides: dict[str, Any] | None = None,
    cli_overrides: bool = True,
    exclude_markers: bool = False,
) -> None:
    config, composer = _resolved_config(
        source, overrides=overrides, cli_overrides=cli_overrides
    )
    ref_graph = composer.ref_graph()
    file_exporter = MultiFileExporter(exclude_markers=exclude_markers)
    file_exporter.export_to_file(
        config,
        config_root_file,
        source_path=source,
        ref_graph=ref_graph,
    )


@to_files.register
def _to_files_from_dict(
    source: dict,
    config_root_file: Path,
    *,
    exclude_markers: bool = False,
) -> None:
    file_exporter = MultiFileExporter(exclude_markers=exclude_markers)
    file_exporter.export_to_file(
        source,
        config_root_file,
        source_path=None,
        ref_graph=None,
    )


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
    # Resolver API
    "register_resolver",
    "unregister_resolver",
    "resolver",
    # Lazy instantiation utilities
    "is_lazy_proxy",
    "force_initialize",
    # Help integration API
    "set_help_integration",
    "current_help_integration",
    "help_integration",
    "HelpIntegration",
    "FlatHelpIntegration",
    "GroupedHelpIntegration",
    "ArgparseHelpIntegration",
    # Deprecation API
    "deprecate",
    "undeprecate",
    "set_deprecation_policy",
    "set_deprecation_handler",
    "deprecation_handler",
    "DeprecationInfo",
    "DeprecationHandler",
    "DeprecatedKeyError",
    "RconfigDeprecationWarning",
    # Export API (string output)
    "export",
    "to_dict",
    "to_yaml",
    "to_json",
    "to_toml",
    # Export API (file output with format auto-detection)
    "to_file",
    "to_files",
    # Export classes (for custom exporters)
    "Exporter",
    "DictExporter",
    "YamlExporter",
    "JsonExporter",
    "TomlExporter",
    "FileExporter",
    "SingleFileExporter",
    "MultiFileExporter",
    # Exporter registry
    "register_exporter",
    "unregister_exporter",
    "get_exporter",
    "supported_exporter_extensions",
    # Loader classes (for custom loaders)
    "ConfigFileLoader",
    "YamlConfigLoader",
    "JsonConfigLoader",
    "TomlConfigLoader",
    # Loader registry
    "register_loader",
    "unregister_loader",
    "get_loader",
    "supported_loader_extensions",
    # Exceptions (available at root for convenience)
    "AmbiguousRefError",
    "AmbiguousTargetError",
    "CircularInstanceError",
    "CircularRefError",
    "CompositionError",
    "ConfigError",
    "ConfigFileError",
    "InstanceResolutionError",
    "InstantiationError",
    "InvalidInnerPathError",
    "InvalidOverridePathError",
    "InvalidOverrideSyntaxError",
    "MergeError",
    "MissingFieldError",
    "OverrideError",
    "RefAtRootError",
    "RefInstanceConflictError",
    "RefResolutionError",
    "ResolverError",
    "ResolverExecutionError",
    "RequiredValueError",
    "TargetNotFoundError",
    "TargetTypeMismatchError",
    "TypeInferenceError",
    "TypeMismatchError",
    "UnknownResolverError",
    "ValidationError",
]
