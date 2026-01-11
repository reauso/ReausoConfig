"""Core multirun instantiation logic.

This module provides functions for generating run configurations from
sweep parameters and experiments, validating sweep values, and applying
_ref_ shorthand transformations to sweep values.
"""

import itertools
from pathlib import Path
from typing import Any, Iterator

from rconfig.loaders import supported_loader_extensions

from .errors import InvalidSweepValueError


def generate_sweep_combinations(
    sweep: dict[str, list[Any]],
) -> Iterator[dict[str, Any]]:
    """Generate cartesian product of sweep parameters.

    :param sweep: Dict mapping parameter paths to lists of values.
    :yields: Dicts with one value per parameter (all combinations).

    Example::

        sweep = {"lr": [0.01, 0.001], "layers": [4, 8]}
        # Yields:
        # {"lr": 0.01, "layers": 4}
        # {"lr": 0.01, "layers": 8}
        # {"lr": 0.001, "layers": 4}
        # {"lr": 0.001, "layers": 8}
    """
    if not sweep:
        yield {}
        return

    keys = list(sweep.keys())
    value_lists = [sweep[k] for k in keys]

    for combo in itertools.product(*value_lists):
        yield dict(zip(keys, combo))


def generate_run_configs(
    *,
    sweep: dict[str, list[Any]] | None = None,
    experiments: list[dict[str, Any]] | None = None,
    overrides: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Generate all run configurations from sweep and experiments.

    Combines experiments with sweep parameters (cartesian product) and
    applies constant overrides as base. Priority: experiment/sweep > overrides.

    :param sweep: Dict of parameter paths to lists of values.
    :param experiments: List of explicit experiment override dicts.
    :param overrides: Constant overrides applied to all runs (lowest priority).
    :return: List of override dicts, one per run.

    Example::

        # Sweep only (4 runs)
        generate_run_configs(sweep={"lr": [0.01, 0.001], "layers": [4, 8]})

        # Experiments only (2 runs)
        generate_run_configs(experiments=[{"model": "resnet"}, {"model": "vit"}])

        # Both (4 runs: 2 experiments x 2 sweep values)
        generate_run_configs(
            experiments=[{"model": "resnet"}, {"model": "vit"}],
            sweep={"lr": [0.01, 0.001]},
        )

        # With constant overrides
        generate_run_configs(
            sweep={"lr": [0.01, 0.001]},
            overrides={"epochs": 100},
        )
        # Each run has epochs=100 plus the sweep lr value
    """
    sweep = sweep or {}
    experiments = experiments or []
    overrides = overrides or {}

    run_configs: list[dict[str, Any]] = []

    if experiments:
        # Experiments provided - expand each with sweep combinations
        for experiment in experiments:
            for sweep_combo in generate_sweep_combinations(sweep):
                # Priority: sweep > experiment > overrides
                run_config = {**overrides, **experiment, **sweep_combo}
                run_configs.append(run_config)
    else:
        # No experiments - just sweep combinations
        for sweep_combo in generate_sweep_combinations(sweep):
            # Priority: sweep > overrides
            run_config = {**overrides, **sweep_combo}
            run_configs.append(run_config)

    return run_configs


def validate_sweep_values(sweep: dict[str, list[Any]]) -> None:
    """Validate that sweep values are lists.

    This performs basic syntax validation (values must be lists).
    Type validation for list-type parameters is done lazily during iteration.

    :param sweep: Dict of parameter paths to sweep values.
    :raises ValueError: If any sweep value is not a list.
    """
    for path, values in sweep.items():
        if not isinstance(values, list):
            raise ValueError(
                f"Sweep values for '{path}' must be a list, got {type(values).__name__}. "
                f"Use sweep={{'{path}': [value1, value2]}}."
            )


def validate_list_type_sweep_value(
    path: str,
    value: Any,
    index: int,
) -> None:
    """Validate a sweep value for a list-type parameter.

    When sweeping a parameter that expects a list type, each sweep value
    must itself be a list (so the sweep is list[list[...]]).

    :param path: The parameter path being swept.
    :param value: The sweep value to validate.
    :param index: Index in the sweep list (for error messages).
    :raises InvalidSweepValueError: If value is not a list.

    Example::

        # Parameter "callbacks" expects List[str]
        # WRONG - looks like sweep over 3 string values
        sweep={"callbacks": ["logger", "checkpoint", "early_stop"]}

        # CORRECT - sweep over 2 list values
        sweep={"callbacks": [["logger", "checkpoint"], ["logger", "early_stop"]]}
    """
    if not isinstance(value, list):
        raise InvalidSweepValueError(
            path=path,
            expected="list[list[...]]",
            actual=type(value).__name__,
            index=index,
        )


def apply_ref_shorthand_to_sweep(
    sweep_overrides: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Apply _ref_ shorthand to sweep values targeting dict fields.

    When a sweep targets a dict field, string values are treated as _ref_ paths
    and converted to `path._ref_=value`. Also applies extension-less resolution.

    :param sweep_overrides: Dict of path -> value from a single sweep combination.
    :param config: The base config dict (to check if target is a dict).
    :return: New dict with _ref_ shorthand applied where appropriate.

    Example::

        # Config has: {"model": {"_target_": "...", "layers": 10}}
        # Sweep: {"model": "models/resnet"}
        # Result: {"model._ref_": "models/resnet"}
    """
    result = {}

    for path, value in sweep_overrides.items():
        # Only apply shorthand if:
        # 1. Value is a string
        # 2. Target field exists and is a dict
        if isinstance(value, str) and _should_convert_to_ref(path, config):
            # Convert to _ref_ assignment
            result[f"{path}._ref_"] = value
        else:
            result[path] = value

    return result


def _should_convert_to_ref(path: str, config: dict[str, Any]) -> bool:
    """Check if a path points to a dict field in the config.

    :param path: Dot-notation path (e.g., "model" or "trainer.optimizer").
    :param config: The config dict to check.
    :return: True if the target field is a dict.
    """
    try:
        target = _get_value_at_path(config, path)
        return isinstance(target, dict)
    except (KeyError, TypeError, IndexError):
        return False


def _get_value_at_path(config: dict[str, Any], path: str) -> Any:
    """Get value at a dot-notation path.

    :param config: The config dict.
    :param path: Dot-notation path (e.g., "model.layers").
    :return: Value at the path.
    :raises KeyError: If path doesn't exist.
    """
    current = config
    for segment in path.split("."):
        if isinstance(current, dict):
            current = current[segment]
        elif isinstance(current, list):
            current = current[int(segment)]
        else:
            raise KeyError(f"Cannot navigate through {type(current).__name__}")
    return current


def resolve_extensionless_ref(
    ref_path: str,
    config_root: Path,
) -> str:
    """Resolve an extension-less ref path to include the extension.

    If the path already has a supported extension, returns it unchanged.
    Otherwise, searches for a matching file with supported extension.

    :param ref_path: The ref path (may or may not have extension).
    :param config_root: Root directory for resolving paths.
    :return: Path with extension (unchanged if already has one, or resolved).
    :raises ValueError: If no matching file found or multiple matches.

    Example::

        # ref_path="models/resnet", config_root="/project/configs"
        # If "/project/configs/models/resnet.yaml" exists:
        # Returns "models/resnet.yaml"
    """
    # Check if path already has a supported extension
    suffix = Path(ref_path).suffix.lower()
    supported_exts = supported_loader_extensions()
    if suffix in supported_exts:
        return ref_path

    # No extension - try to resolve
    if ref_path.startswith("/"):
        base_path = config_root / ref_path[1:]
    else:
        base_path = config_root / ref_path

    parent = base_path.parent
    stem = base_path.name

    if not parent.exists():
        # Directory doesn't exist - return original path
        # (error will be raised later during actual composition)
        return ref_path

    # Find matching files
    pattern = f"{stem}.*"
    matches = [
        f for f in parent.glob(pattern)
        if f.is_file() and f.suffix.lower() in supported_exts
    ]

    if len(matches) == 0:
        # No match found - return original path
        # (error will be raised later during actual composition)
        return ref_path

    if len(matches) > 1:
        # Multiple matches - return original path
        # (error will be raised later during actual composition)
        return ref_path

    # Single match - return path with extension
    resolved_suffix = matches[0].suffix
    return f"{ref_path}{resolved_suffix}"
