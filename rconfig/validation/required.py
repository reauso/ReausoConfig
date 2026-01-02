"""Required value detection and validation.

This module provides utilities for detecting _required_ markers in configs
and validating that all required values have been satisfied.
"""

from dataclasses import dataclass
from typing import Any

from rconfig._internal.path_utils import build_child_path
from rconfig._internal.type_utils import REQUIRED_KEY


# Builtin type name mappings
_BUILTIN_TYPES: dict[str, type] = {
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "list": list,
    "dict": dict,
}


@dataclass
class RequiredMarker:
    """A required value marker in the config.

    :param path: Config path where the marker was found.
    :param expected_type: Optional type hint if provided.
    """

    path: str
    expected_type: type | None = None


def is_required_marker(value: Any) -> bool:
    """Check if a value is a _required_ marker.

    Supports two forms:
    - Simple: "_required_"
    - With type hint: {"_required_": "int"}

    :param value: Value to check.
    :return: True if value is a required marker.
    """
    if value == REQUIRED_KEY:
        return True
    if isinstance(value, dict) and REQUIRED_KEY in value and len(value) == 1:
        return True
    return False


def extract_required_type(value: Any) -> type | None:
    """Extract the expected type from a _required_ marker.

    :param value: The required marker value.
    :return: Expected type if specified, None otherwise.
    """
    if value == REQUIRED_KEY:
        return None
    if isinstance(value, dict) and REQUIRED_KEY in value:
        type_name = value[REQUIRED_KEY]
        return _resolve_type_name(type_name)
    return None


def _resolve_type_name(type_name: Any) -> type | None:
    """Resolve a type name string to a type object.

    :param type_name: Type name (str like "int", "str") or type object.
    :return: Resolved type or None if resolution fails.
    """
    if isinstance(type_name, type):
        return type_name
    if isinstance(type_name, str):
        return _BUILTIN_TYPES.get(type_name)
    return None


def find_required_markers(
    config: dict[str, Any],
    path: str = "",
) -> list[RequiredMarker]:
    """Find all _required_ markers in a config tree.

    :param config: Config dictionary to search.
    :param path: Current path prefix.
    :return: List of RequiredMarker objects.
    """
    markers: list[RequiredMarker] = []

    for key, value in config.items():
        current_path = build_child_path(path, key)

        if is_required_marker(value):
            expected_type = extract_required_type(value)
            markers.append(RequiredMarker(current_path, expected_type))
        elif isinstance(value, dict):
            markers.extend(find_required_markers(value, current_path))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                item_path = build_child_path(current_path, i)
                if is_required_marker(item):
                    markers.append(
                        RequiredMarker(item_path, extract_required_type(item))
                    )
                elif isinstance(item, dict):
                    markers.extend(find_required_markers(item, item_path))

    return markers
