"""Immutable diff container for config comparison.

This module provides ConfigDiff: an immutable mapping of paths to diff entries.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Iterator

from .models import DiffEntry, DiffEntryType


class ConfigDiff:
    """Immutable mapping of paths to diff entries.

    Implements the Mapping protocol for accessing diff entries by path.
    Provides filtered views for added, removed, and changed entries.

    Usage::

        diff = ConfigDiff(entries)
        print(diff["model.lr"])  # Access single entry
        for path, entry in diff.items():
            print(f"{path}: {entry.diff_type}")

        # Filtered views
        for path, entry in diff.added.items():
            print(f"Added: {path}")

        # Format output
        print(diff.format().terminal())
    """

    __slots__ = ("_entries", "_added", "_removed", "_changed", "_unchanged")

    def __init__(self, entries: dict[str, DiffEntry]) -> None:
        """Initialize ConfigDiff with entries.

        :param entries: Dictionary mapping paths to DiffEntry objects.
        """
        self._entries: MappingProxyType[str, DiffEntry] = MappingProxyType(entries)

        # Pre-compute filtered views for efficient access
        added: dict[str, DiffEntry] = {}
        removed: dict[str, DiffEntry] = {}
        changed: dict[str, DiffEntry] = {}
        unchanged: dict[str, DiffEntry] = {}

        for path, entry in entries.items():
            if entry.diff_type == DiffEntryType.ADDED:
                added[path] = entry
            elif entry.diff_type == DiffEntryType.REMOVED:
                removed[path] = entry
            elif entry.diff_type == DiffEntryType.CHANGED:
                changed[path] = entry
            elif entry.diff_type == DiffEntryType.UNCHANGED:
                unchanged[path] = entry

        self._added: MappingProxyType[str, DiffEntry] = MappingProxyType(added)
        self._removed: MappingProxyType[str, DiffEntry] = MappingProxyType(removed)
        self._changed: MappingProxyType[str, DiffEntry] = MappingProxyType(changed)
        self._unchanged: MappingProxyType[str, DiffEntry] = MappingProxyType(unchanged)

    # Mapping protocol

    def __getitem__(self, path: str) -> DiffEntry:
        """Get a diff entry by path.

        :param path: The config path.
        :return: The DiffEntry for that path.
        :raises KeyError: If path not in diff.
        """
        return self._entries[path]

    def __iter__(self) -> Iterator[str]:
        """Iterate over paths.

        :return: Iterator of paths.
        """
        return iter(self._entries)

    def __len__(self) -> int:
        """Get number of entries.

        :return: Number of diff entries.
        """
        return len(self._entries)

    def __contains__(self, path: object) -> bool:
        """Check if path is in diff.

        :param path: The path to check.
        :return: True if path exists in diff.
        """
        return path in self._entries

    def keys(self) -> Iterator[str]:
        """Get all paths.

        :return: Iterator of paths.
        """
        return iter(self._entries.keys())

    def values(self) -> Iterator[DiffEntry]:
        """Get all entries.

        :return: Iterator of DiffEntry objects.
        """
        return iter(self._entries.values())

    def items(self) -> Iterator[tuple[str, DiffEntry]]:
        """Get all path-entry pairs.

        :return: Iterator of (path, DiffEntry) tuples.
        """
        return iter(self._entries.items())

    def get(self, path: str, default: DiffEntry | None = None) -> DiffEntry | None:
        """Get entry by path with default.

        :param path: The config path.
        :param default: Default value if path not found.
        :return: The DiffEntry or default.
        """
        return self._entries.get(path, default)

    # Filtered views

    @property
    def added(self) -> MappingProxyType[str, DiffEntry]:
        """Get mapping of added entries only.

        :return: MappingProxyType of paths to added entries.
        """
        return self._added

    @property
    def removed(self) -> MappingProxyType[str, DiffEntry]:
        """Get mapping of removed entries only.

        :return: MappingProxyType of paths to removed entries.
        """
        return self._removed

    @property
    def changed(self) -> MappingProxyType[str, DiffEntry]:
        """Get mapping of changed entries only.

        :return: MappingProxyType of paths to changed entries.
        """
        return self._changed

    @property
    def unchanged(self) -> MappingProxyType[str, DiffEntry]:
        """Get mapping of unchanged entries only.

        :return: MappingProxyType of paths to unchanged entries.
        """
        return self._unchanged

    # Utility methods

    def is_empty(self) -> bool:
        """Check if there are no differences (only unchanged entries).

        :return: True if no added, removed, or changed entries.
        """
        return len(self._added) == 0 and len(self._removed) == 0 and len(self._changed) == 0

    def to_dict(self) -> dict[str, dict[str, Any]]:
        """Convert diff to a plain dictionary.

        Useful for serialization or programmatic access.

        :return: Dictionary with structure:
            {path: {"diff_type": str, "left_value": Any, "right_value": Any}}
        """
        result: dict[str, dict[str, Any]] = {}
        for path, entry in self._entries.items():
            result[path] = {
                "diff_type": entry.diff_type.value,
                "left_value": entry.left_value,
                "right_value": entry.right_value,
            }
        return result

    def __repr__(self) -> str:
        """Return repr string.

        :return: Repr string showing counts.
        """
        return (
            f"ConfigDiff(added={len(self._added)}, "
            f"removed={len(self._removed)}, "
            f"changed={len(self._changed)}, "
            f"unchanged={len(self._unchanged)})"
        )

    def __str__(self) -> str:
        """Return formatted string using default layout.

        :return: Formatted diff string.
        """
        from .formatting import DiffFormat

        return str(DiffFormat(self))
