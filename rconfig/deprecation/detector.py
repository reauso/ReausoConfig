"""Deprecation detection during config composition.

This module provides functions to detect deprecated keys during the
config composition process and record them in provenance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .info import DeprecationInfo
from .registry import get_deprecation_registry
from rconfig.errors import DeprecatedKeyError

if TYPE_CHECKING:
    from rconfig.provenance import ProvenanceBuilder

# Marker key for in-config deprecation
_DEPRECATED_KEY = "_deprecated_"
_VALUE_KEY = "_value_"


def check_deprecation(
    config_path: str,
    file: str,
    line: int,
    provenance: "ProvenanceBuilder",
) -> DeprecationInfo | None:
    """Check if a config path is deprecated via registry.

    Looks up the path against registered deprecations using pattern matching.
    If found, records the deprecation in provenance and handles policy.

    :param config_path: The config path to check (e.g., "model.lr").
    :param file: Source file path.
    :param line: Line number in source file.
    :param provenance: Provenance tracker to record deprecation.
    :return: DeprecationInfo if deprecated, None otherwise.
    :raises DeprecatedKeyError: If policy is "error".
    """
    registry = get_deprecation_registry()
    info = registry.find_match(config_path)

    if info is None:
        return None

    # Create a copy with matched_path set
    matched_info = info.with_matched_path(config_path)

    # Record in provenance
    entry = provenance.get(config_path)
    if entry is not None:
        entry.deprecation = matched_info

    # Handle policy
    policy = registry.effective_policy(info)
    if policy == "error":
        raise DeprecatedKeyError(
            key=config_path,
            pattern=info.pattern,
            new_key=info.new_key,
            message=info.message,
            remove_in=info.remove_in,
            config_path=file,
        )
    elif policy == "warn":
        registry.handler.handle(matched_info, config_path, file, line)

    return matched_info


def handle_deprecated_marker(
    value: dict[str, Any],
    config_path: str,
    file: str,
    line: int,
    provenance: "ProvenanceBuilder",
) -> tuple[Any, DeprecationInfo | None]:
    """Process _deprecated_ marker in a config dict.

    Handles both short form (_deprecated_: "message") and long form
    (_deprecated_: {message: ..., new_key: ...}).

    :param value: Dict potentially containing _deprecated_ marker.
    :param config_path: Current config path.
    :param file: Source file path.
    :param line: Line number in source file.
    :param provenance: Provenance tracker to record deprecation.
    :return: Tuple of (actual_value, deprecation_info).
             actual_value is the value without _deprecated_ marker.
             deprecation_info is the parsed deprecation or None.
    """
    deprecated = value.get(_DEPRECATED_KEY)
    if deprecated is None:
        return value, None

    # Parse deprecation info
    if isinstance(deprecated, str):
        # Short form: _deprecated_: "message"
        info = DeprecationInfo(
            pattern=config_path,
            matched_path=config_path,
            message=deprecated,
        )
    elif isinstance(deprecated, dict):
        # Long form: _deprecated_: {message: ..., new_key: ..., remove_in: ...}
        info = DeprecationInfo(
            pattern=config_path,
            matched_path=config_path,
            message=deprecated.get("message"),
            new_key=deprecated.get("new_key"),
            remove_in=deprecated.get("remove_in"),
            policy=deprecated.get("policy"),
        )
    else:
        # Invalid format - treat as no deprecation
        return value, None

    # Record in provenance
    entry = provenance.get(config_path)
    if entry is not None:
        entry.deprecation = info

    # Handle policy
    registry = get_deprecation_registry()
    policy = registry.effective_policy(info)
    if policy == "error":
        raise DeprecatedKeyError(
            key=config_path,
            pattern=info.pattern,
            new_key=info.new_key,
            message=info.message,
            remove_in=info.remove_in,
            config_path=file,
        )
    elif policy == "warn":
        registry.handler.handle(info, config_path, file, line)

    # Extract actual value
    if _VALUE_KEY in value:
        # Scalar with _value_ key
        actual_value = value[_VALUE_KEY]
    else:
        # Dict value - return without _deprecated_ key
        actual_value = {k: v for k, v in value.items() if k != _DEPRECATED_KEY}

    return actual_value, info


def has_deprecated_marker(value: dict[str, Any]) -> bool:
    """Check if a dict has a _deprecated_ marker.

    :param value: Dict to check.
    :return: True if _deprecated_ key exists.
    """
    return _DEPRECATED_KEY in value


def auto_map_deprecated_values(
    config: dict[str, Any],
    provenance: "ProvenanceBuilder",
) -> dict[str, Any]:
    """Map deprecated key values to new key locations.

    For each deprecated key with a new_key mapping, copies the value
    to the new location if it doesn't already exist. Creates intermediate
    dict structures as needed.

    :param config: The config dict to process.
    :param provenance: Provenance with deprecation info.
    :return: Config with values mapped to new locations.
    """
    from rconfig._internal.path_utils import (
        get_value_at_path,
        path_exists,
        set_value_at_path,
    )

    for path, entry in provenance.items():
        if entry.deprecation is None or entry.deprecation.new_key is None:
            continue

        info = entry.deprecation
        try:
            value = get_value_at_path(config, path)
        except (KeyError, IndexError, TypeError):
            continue

        # Don't override if new key already has a value
        if path_exists(config, info.new_key):
            continue

        # Set value at new location (creates intermediate dicts as needed)
        set_value_at_path(config, info.new_key, value, create_parents=True)

    return config
