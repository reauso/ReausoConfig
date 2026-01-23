"""Path parsing utilities for config paths.

This module provides utilities for parsing and navigating config paths
that support dot notation and list indexing, as well as path type utilities
for the public API.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

# Type alias for public API - accepts strings and any PathLike
StrOrPath = str | os.PathLike[str]

__all__ = [
    "StrOrPath",
    "ensure_path",
    "parse_path_segments",
    "PathNavigationError",
    "navigate_path",
    "get_value_at_path",
    "path_exists",
    "set_value_at_path",
    "build_child_path",
]


def ensure_path(path: StrOrPath) -> Path:
    """Convert str or PathLike to Path for internal use.

    :param path: A string, Path, or any os.PathLike object.
    :return: A pathlib.Path object.
    """
    if isinstance(path, Path):
        return path
    return Path(path)

# Regex for parsing instance paths with list indices and dict keys
PATH_SEGMENT_RE = re.compile(
    r'([^.\[\]]+)'       # Group 1: bare key (model, layers, etc.)
    r'|\[(\d+)\]'        # Group 2: integer index [0], [1], etc.
    r'|\["([^"]+)"\]'    # Group 3: double-quoted string key ["key"]
    r"|\['([^']+)'\]"    # Group 4: single-quoted string key ['key']
)


def build_child_path(parent: str, key: str | int) -> str:
    """Build a child config path from a parent path and a key or index.

    Examples:
        - build_child_path("", "model") -> "model"
        - build_child_path("model", "layers") -> "model.layers"
        - build_child_path("model.layers", 0) -> "model.layers[0]"
        - build_child_path("callbacks", 0) -> "callbacks[0]"

    :param parent: The parent path (may be empty string for root level).
    :param key: The child key (str for dict key, int for list index).
    :return: The combined child path.
    """
    if isinstance(key, int):
        return f"{parent}[{key}]"
    return f"{parent}.{key}" if parent else key


def parse_path_segments(path: str) -> list[str | int]:
    """Parse a config path into segments.

    Supports dot notation, list indexing, and dict key access:
    - "model.layers" -> ["model", "layers"]
    - "callbacks[0]" -> ["callbacks", 0]
    - "callbacks[0].name" -> ["callbacks", 0, "name"]
    - 'models["resnet"]' -> ["models", "resnet"]
    - "models['resnet']" -> ["models", "resnet"]

    :param path: The path string.
    :return: List of path segments (strings for dict keys, ints for list indices).
    """
    segments: list[str | int] = []

    for match in PATH_SEGMENT_RE.finditer(path):
        key, index, dq_key, sq_key = match.groups()
        if key:
            segments.append(key)
        elif index:
            segments.append(int(index))
        elif dq_key:
            segments.append(dq_key)
        elif sq_key:
            segments.append(sq_key)

    return segments


class PathNavigationError(Exception):
    """Error during path navigation with context about the failure location."""

    def __init__(self, message: str, segment_index: int, path: list[str | int]) -> None:
        self.message = message
        self.segment_index = segment_index
        self.path = path
        super().__init__(message)


def navigate_path(
    config: Any,
    path: list[str | int],
    stop_before_last: bool = False,
) -> Any:
    """Navigate a config structure following a path of segments.

    :param config: The starting dict/list.
    :param path: List of keys (str) and indices (int).
    :param stop_before_last: If True, stop before the final segment (for parent access).
    :return: The value at the path (or parent if stop_before_last).
    :raises PathNavigationError: If navigation fails, with context about failure location.
    """
    if not path:
        return config

    current = config
    end_index = len(path) - 1 if stop_before_last else len(path)

    for i, segment in enumerate(path[:end_index]):
        if isinstance(segment, int):
            if not isinstance(current, list):
                raise PathNavigationError(
                    f"Cannot index into non-list at position {i}",
                    segment_index=i,
                    path=path,
                )
            if segment < 0 or segment >= len(current):
                raise PathNavigationError(
                    f"List index {segment} out of range (list has {len(current)} elements)",
                    segment_index=i,
                    path=path,
                )
            current = current[segment]
        else:
            if not isinstance(current, dict):
                raise PathNavigationError(
                    f"Cannot access key '{segment}' on non-dict at position {i}",
                    segment_index=i,
                    path=path,
                )
            if segment not in current:
                raise PathNavigationError(
                    f"Key '{segment}' not found",
                    segment_index=i,
                    path=path,
                )
            current = current[segment]

    return current


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

    segments = parse_path_segments(path)
    try:
        return navigate_path(config, segments)
    except PathNavigationError as e:
        # Convert to original error types for backwards compatibility
        if "non-list" in e.message or "non-dict" in e.message:
            raise TypeError(f"{e.message.split(' at position')[0]} at '{path}'") from e
        elif "not found" in e.message:
            raise KeyError(e.message) from e
        elif "out of range" in e.message:
            raise IndexError(e.message) from e
        raise


def path_exists(config: dict[str, Any], path: str) -> bool:
    """Check if a path exists in the config.

    :param config: The config dictionary.
    :param path: The path to check.
    :return: True if the path exists, False otherwise.
    """
    if not path:
        return True

    segments = parse_path_segments(path)
    try:
        navigate_path(config, segments)
        return True
    except PathNavigationError:
        return False


def set_value_at_path(
    config: dict[str, Any],
    path: str,
    value: Any,
    create_parents: bool = False,
) -> None:
    """Set a value in the config at the given path.

    :param config: The config dictionary to modify.
    :param path: The path where to set the value.
    :param value: The value to set.
    :param create_parents: If True, create intermediate dicts as needed.
    :raises KeyError: If a parent path doesn't exist and create_parents is False.
    :raises TypeError: If trying to navigate through a non-dict.
    """
    if not path:
        raise ValueError("Cannot set value at empty path")

    segments = parse_path_segments(path)
    if not segments:
        raise ValueError("Cannot set value at empty path")

    # Navigate to parent, creating dicts if needed
    current = config
    for i, segment in enumerate(segments[:-1]):
        if isinstance(segment, int):
            raise TypeError(f"Cannot create list indices in path at segment {i}")

        if segment not in current:
            if create_parents:
                current[segment] = {}
            else:
                raise KeyError(f"Key '{segment}' not found in path")

        next_val = current[segment]
        if not isinstance(next_val, dict):
            raise TypeError(f"Cannot navigate through non-dict at '{segment}'")
        current = next_val

    # Set the final value
    final_segment = segments[-1]
    if isinstance(final_segment, int):
        raise TypeError("Cannot set value at list index")
    current[final_segment] = value
