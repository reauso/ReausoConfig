"""Multirun module for generating and instantiating multiple config combinations.

This module provides functionality for hyperparameter sweeps and experiment runs:
- `MultirunResult`: Result of a single run with config, overrides, and instance
- `MultirunIterator`: Lazy iterator with length, slicing, and reversal support
- Error classes for multirun-specific failures

Example::

    import rconfig as rc

    for result in rc.instantiate_multirun(
        path=Path("config.yaml"),
        sweep={"model.lr": [0.01, 0.001]},
    ):
        train(result.instance)
"""

from .errors import (
    InvalidSweepValueError,
    MultirunError,
    NoRunConfigurationError,
)
from .iterator import MultirunIterator
from .result import MultirunResult
from .instantiator import (
    generate_run_configs,
    generate_sweep_combinations,
    validate_sweep_values,
    validate_list_type_sweep_value,
    apply_ref_shorthand_to_sweep,
    resolve_extensionless_ref,
)
from .cli import (
    parse_cli_sweep_value,
    extract_cli_multirun_overrides,
)

__all__ = [
    # Main types
    "MultirunResult",
    "MultirunIterator",
    # Error classes
    "MultirunError",
    "InvalidSweepValueError",
    "NoRunConfigurationError",
    # Core functions
    "generate_run_configs",
    "generate_sweep_combinations",
    "validate_sweep_values",
    "validate_list_type_sweep_value",
    "apply_ref_shorthand_to_sweep",
    "resolve_extensionless_ref",
    # CLI functions
    "parse_cli_sweep_value",
    "extract_cli_multirun_overrides",
]
