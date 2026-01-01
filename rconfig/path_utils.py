"""Path parsing utilities for config paths.

This module provides utilities for parsing and navigating config paths
that support dot notation and list indexing.
"""

import re
from typing import Any


# Regex for parsing instance paths with list indices
PATH_SEGMENT_RE = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def parse_path_segments(path: str) -> list[str | int]:
    """Parse a config path into segments.

    Supports dot notation and list indexing:
    - "model.layers" -> ["model", "layers"]
    - "callbacks[0]" -> ["callbacks", 0]
    - "callbacks[0].name" -> ["callbacks", 0, "name"]

    :param path: The path string.
    :return: List of path segments (strings for dict keys, ints for list indices).
    """
    segments: list[str | int] = []

    for match in PATH_SEGMENT_RE.finditer(path):
        key, index = match.groups()
        if key:
            segments.append(key)
        elif index:
            segments.append(int(index))

    return segments


def get_value_at_path(config: dict[str, Any], path: str) -> Any:
    """Get a value from the config at the given path.

    Supports dot notation and list indexing:
    - "model.layers" -> config["model"]["layers"]
    - "callbacks[0]" -> config["callbacks"][0]
    - "callbacks[0].name" -> config["callbacks"][0]["name"]

    :param config: The config dictionary.
    :param path: The path to the value.
    :return: The value at the path.
    :raises KeyError: If a dict key is not found.
    :raises IndexError: If a list index is out of range.
    :raises TypeError: If trying to index a non-indexable value.
    """
    if not path:
        return config

    current = config
    segments = parse_path_segments(path)

    for segment in segments:
        if isinstance(segment, int):
            # List index
            if not isinstance(current, list):
                raise TypeError(f"Cannot index into non-list at '{path}'")
            current = current[segment]
        else:
            # Dict key
            if not isinstance(current, dict):
                raise TypeError(f"Cannot access key on non-dict at '{path}'")
            current = current[segment]

    return current
