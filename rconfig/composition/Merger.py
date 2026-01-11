"""Deep merge utilities for config composition.

This module provides functions for merging configuration dictionaries
with support for deep merging and list operations like extend and prepend.
"""

from typing import Any

from rconfig.errors import MergeError


# Special keys for list operations
_EXTEND_KEY = "_extend_"
_PREPEND_KEY = "_prepend_"


def deep_merge(base: dict[str, Any], override: dict[str, Any], path: str = "") -> dict[str, Any]:
    """Deep merge two configuration dictionaries.

    This function recursively merges `override` into `base`, following these rules:
    - Dictionaries are merged recursively (keys are combined, nested dicts merge)
    - Lists are replaced by default (override list replaces base list)
    - Scalar values in override replace values in base
    - Special keys `_extend_` and `_prepend_` modify list behavior

    :param base: The base configuration dictionary.
    :param override: The override configuration dictionary.
    :param path: Current path in the config tree (for error messages).
    :return: A new dictionary with merged values.
    :raises MergeError: If a merge operation is invalid (e.g., extending a non-list).

    Example::

        base = {"a": 1, "b": {"c": 2, "d": 3}}
        override = {"b": {"c": 10}}
        result = deep_merge(base, override)
        # result = {"a": 1, "b": {"c": 10, "d": 3}}
    """
    result = dict(base)

    for key, override_value in override.items():
        current_path = f"{path}.{key}" if path else key

        if key not in result:
            # Key only in override - add it
            result[key] = _copy_value(override_value)
        else:
            base_value = result[key]

            if isinstance(override_value, dict) and isinstance(base_value, dict):
                # Both are dicts - merge recursively
                result[key] = deep_merge(base_value, override_value, current_path)
            elif isinstance(override_value, dict) and not isinstance(base_value, dict):
                # Override is dict, base is not - check for list operations
                result[key] = _list_operation_result(base_value, override_value, current_path)
            else:
                # Scalar or list replacement - override wins
                result[key] = _copy_value(override_value)

    return result


def _list_operation_result(
    base_value: Any, override_dict: dict[str, Any], path: str
) -> Any:
    """Return result of list operation (_extend_ or _prepend_) if present.

    :param base_value: The base value (must be a list for list operations).
    :param override_dict: The override dictionary that may contain list operations.
    :param path: Current path in the config tree (for error messages).
    :return: The result of the list operation, or the override dict if no operation.
    :raises MergeError: If a list operation is invalid.
    """
    has_extend = _EXTEND_KEY in override_dict
    has_prepend = _PREPEND_KEY in override_dict

    if not has_extend and not has_prepend:
        # No list operations - just return the override dict as-is
        return _copy_value(override_dict)

    # Validate: can't have both
    if has_extend and has_prepend:
        raise MergeError(
            f"Cannot use both '{_EXTEND_KEY}' and '{_PREPEND_KEY}' in the same block",
            path,
            hint="Use _extend_ to add items at the end or _prepend_ to add at the beginning, not both.",
        )

    # Validate: can't have other keys alongside list operations
    operation_key = _EXTEND_KEY if has_extend else _PREPEND_KEY
    if len(override_dict) > 1:
        other_keys = [k for k in override_dict.keys() if k != operation_key]
        raise MergeError(
            f"'{operation_key}' cannot be combined with other keys: {other_keys}",
            path,
            hint="Use _extend_/_prepend_ alone to modify a list, or use regular keys to replace it.",
        )

    # Validate: base must be a list
    if not isinstance(base_value, list):
        raise MergeError(
            f"Cannot apply '{operation_key}' to non-list value of type '{type(base_value).__name__}'",
            path,
            hint="The target field must be a list to use _extend_/_prepend_.",
        )

    # Validate: operation value must be a list
    operation_value = override_dict[operation_key]
    if not isinstance(operation_value, list):
        raise MergeError(
            f"'{operation_key}' value must be a list, got '{type(operation_value).__name__}'",
            path,
            hint="Provide a list of items to extend/prepend.",
        )

    # Apply the operation
    if has_extend:
        return list(base_value) + list(operation_value)
    else:  # has_prepend
        return list(operation_value) + list(base_value)


def _copy_value(value: Any) -> Any:
    """Create a shallow copy of a value to avoid mutation.

    :param value: The value to copy.
    :return: A copy of the value (shallow copy for dicts and lists).
    """
    if isinstance(value, dict):
        return dict(value)
    elif isinstance(value, list):
        return list(value)
    else:
        return value
