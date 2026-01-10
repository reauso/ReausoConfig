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
from typing import Any, Callable, TypeVar, overload

from .store import ConfigStore, ConfigReference
from .validation import ConfigValidator, ValidationResult
from .instantiation import ConfigInstantiator, is_lazy_proxy, force_initialize
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

T = TypeVar("T")


# Internal singleton instances
_store = ConfigStore()
_resolver_registry = ResolverRegistry()
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

    # Resolve target class information from registered targets
    provenance.resolve_targets(_store.known_references)

    return provenance


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


@overload
def to_file(
    source: Path,
    output_path: Path,
    *,
    overrides: dict[str, Any] | None = None,
    cli_overrides: bool = True,
    exclude_markers: bool = False,
) -> None: ...


@overload
def to_file(
    source: dict[str, Any],
    output_path: Path,
    *,
    exclude_markers: bool = False,
) -> None: ...


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
    if isinstance(source, dict):
        config = source
    else:
        config, _ = _resolved_config(
            source, overrides=overrides, cli_overrides=cli_overrides
        )
    file_exporter = SingleFileExporter(exclude_markers=exclude_markers)
    file_exporter.export_to_file(config, output_path)


@overload
def to_files(
    source: Path,
    config_root_file: Path,
    *,
    overrides: dict[str, Any] | None = None,
    cli_overrides: bool = True,
    exclude_markers: bool = False,
) -> None: ...


@overload
def to_files(
    source: dict[str, Any],
    config_root_file: Path,
    *,
    exclude_markers: bool = False,
) -> None: ...


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
    if isinstance(source, dict):
        config = source
        ref_graph = None
        source_path = None
    else:
        config, composer = _resolved_config(
            source, overrides=overrides, cli_overrides=cli_overrides
        )
        ref_graph = composer.ref_graph()
        source_path = source

    file_exporter = MultiFileExporter(exclude_markers=exclude_markers)
    file_exporter.export_to_file(
        config,
        config_root_file,
        source_path=source_path,
        ref_graph=ref_graph,
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
