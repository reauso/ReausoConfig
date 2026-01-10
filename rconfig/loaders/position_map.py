"""Position tracking for config file loaders.

This module provides data types for tracking line and column positions
of keys in config files, without depending on external libraries.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Position:
    """Line and column position (1-indexed).

    :param line: Line number (1-indexed).
    :param column: Column number (1-indexed).
    """

    line: int
    column: int


class PositionMap(dict[str, Any]):
    """Dict subclass that tracks key positions (line and column).

    A dependency-free alternative to ruamel.yaml's CommentedMap.
    Behaves like a regular dict but provides position lookup via get_position().

    Example::

        pmap = PositionMap({"key": "value"})
        pmap.set_position("key", line=1, column=1)
        pos = pmap.get_position("key")  # Position(line=1, column=1)
    """

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        """Initialize PositionMap with optional data.

        :param data: Initial dictionary data.
        """
        super().__init__(data or {})
        self._positions: dict[str, Position] = {}

    def set_position(self, key: str, line: int, column: int) -> None:
        """Set position for a key.

        :param key: The key to set position for.
        :param line: Line number (1-indexed).
        :param column: Column number (1-indexed).
        """
        self._positions[key] = Position(line, column)

    def get_position(self, key: str) -> Position | None:
        """Get position (line, column) for a key.

        :param key: The key to get position for.
        :return: Position if found, None otherwise.
        """
        return self._positions.get(key)

    def get_line(self, key: str) -> int | None:
        """Get line number for a key.

        :param key: The key to get line for.
        :return: Line number if found, None otherwise.
        """
        pos = self._positions.get(key)
        return pos.line if pos else None

    def get_column(self, key: str) -> int | None:
        """Get column number for a key.

        :param key: The key to get column for.
        :return: Column number if found, None otherwise.
        """
        pos = self._positions.get(key)
        return pos.column if pos else None

    def has_position(self, key: str) -> bool:
        """Check if position exists for a key.

        :param key: The key to check.
        :return: True if position exists.
        """
        return key in self._positions
