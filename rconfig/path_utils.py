"""Path parsing utilities for config paths.

This module provides utilities for parsing and navigating config paths
that support dot notation and list indexing.
"""

import re
from typing import Any

__all__ = [
    "parse_path_segments",
    "PathNavigationError",
    "navigate_path",
    "get_value_at_path",
    "build_child_path",
]

# Regex for parsing instance paths with list indices
PATH_SEGMENT_RE = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


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
