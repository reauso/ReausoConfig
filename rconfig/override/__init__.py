"""CLI and programmatic override subsystem.

Parses and applies configuration overrides.
"""

from .override import (
    Override,
    apply_cli_overrides_with_ref_shorthand,
    apply_overrides,
    extract_cli_overrides,
    parse_cli_arg,
    parse_dict_overrides,
    parse_override_key,
    parse_override_value,
)

__all__ = [
    "Override",
    "apply_cli_overrides_with_ref_shorthand",
    "apply_overrides",
    "extract_cli_overrides",
    "parse_cli_arg",
    "parse_dict_overrides",
    "parse_override_key",
    "parse_override_value",
]
