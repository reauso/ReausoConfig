"""Mutable builder for accumulating diff entries.

This module provides DiffBuilder for constructing ConfigDiff objects
by comparing two Provenance objects or manually adding entries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .diff import ConfigDiff
from .models import DiffEntry, DiffEntryType

if TYPE_CHECKING:
    from rconfig.provenance import Provenance, ProvenanceEntry


class DiffBuilder:
    """Mutable builder for constructing ConfigDiff objects.

    Use this class to build a ConfigDiff either by:
    1. Manually adding entries with add_* methods
    2. Computing diff from two Provenance objects

    Usage::

        # Manual construction
        builder = DiffBuilder()
        builder.add_added("model.dropout", 0.1)
        builder.add_changed("model.lr", 0.001, 0.0001)
        diff = builder.build()

        # From provenance
        builder = DiffBuilder()
        diff = builder.compute_diff(left_provenance, right_provenance)
    """

    __slots__ = ("_entries",)

    def __init__(self) -> None:
        """Initialize an empty DiffBuilder."""
        self._entries: dict[str, DiffEntry] = {}

    def add_added(
        self,
        path: str,
        value: Any,
        provenance: ProvenanceEntry | None = None,
    ) -> DiffBuilder:
        """Add an entry that exists only in the right config.

        :param path: The config path.
        :param value: The value in the right config.
        :param provenance: Optional provenance entry from right config.
        :return: Self for chaining.
        """
        self._entries[path] = DiffEntry(
            path=path,
            diff_type=DiffEntryType.ADDED,
            left_value=None,
            right_value=value,
            left_provenance=None,
            right_provenance=provenance,
        )
        return self

    def add_removed(
        self,
        path: str,
        value: Any,
        provenance: ProvenanceEntry | None = None,
    ) -> DiffBuilder:
        """Add an entry that exists only in the left config.

        :param path: The config path.
        :param value: The value in the left config.
        :param provenance: Optional provenance entry from left config.
        :return: Self for chaining.
        """
        self._entries[path] = DiffEntry(
            path=path,
            diff_type=DiffEntryType.REMOVED,
            left_value=value,
            right_value=None,
            left_provenance=provenance,
            right_provenance=None,
        )
        return self

    def add_changed(
        self,
        path: str,
        left_value: Any,
        right_value: Any,
        left_provenance: ProvenanceEntry | None = None,
        right_provenance: ProvenanceEntry | None = None,
    ) -> DiffBuilder:
        """Add an entry that has different values in both configs.

        :param path: The config path.
        :param left_value: The value in the left config.
        :param right_value: The value in the right config.
        :param left_provenance: Optional provenance entry from left config.
        :param right_provenance: Optional provenance entry from right config.
        :return: Self for chaining.
        """
        self._entries[path] = DiffEntry(
            path=path,
            diff_type=DiffEntryType.CHANGED,
            left_value=left_value,
            right_value=right_value,
            left_provenance=left_provenance,
            right_provenance=right_provenance,
        )
        return self

    def add_unchanged(
        self,
        path: str,
        value: Any,
        left_provenance: ProvenanceEntry | None = None,
        right_provenance: ProvenanceEntry | None = None,
    ) -> DiffBuilder:
        """Add an entry that has the same value in both configs.

        :param path: The config path.
        :param value: The value (same in both configs).
        :param left_provenance: Optional provenance entry from left config.
        :param right_provenance: Optional provenance entry from right config.
        :return: Self for chaining.
        """
        self._entries[path] = DiffEntry(
            path=path,
            diff_type=DiffEntryType.UNCHANGED,
            left_value=value,
            right_value=value,
            left_provenance=left_provenance,
            right_provenance=right_provenance,
        )
        return self

    def compute_diff(
        self,
        left: Provenance,
        right: Provenance,
    ) -> ConfigDiff:
        """Compute diff between two Provenance objects.

        Compares all paths in both provenance objects and categorizes
        each as added, removed, changed, or unchanged.

        :param left: The left (original/base) provenance.
        :param right: The right (new/updated) provenance.
        :return: Immutable ConfigDiff with all differences.
        """
        left_paths = set(left.keys())
        right_paths = set(right.keys())

        # Paths only in left (removed)
        for path in left_paths - right_paths:
            entry = left[path]
            self.add_removed(path, entry.value, entry)

        # Paths only in right (added)
        for path in right_paths - left_paths:
            entry = right[path]
            self.add_added(path, entry.value, entry)

        # Paths in both (changed or unchanged)
        for path in left_paths & right_paths:
            left_entry = left[path]
            right_entry = right[path]

            if self._values_equal(left_entry.value, right_entry.value):
                self.add_unchanged(
                    path,
                    left_entry.value,
                    left_entry,
                    right_entry,
                )
            else:
                self.add_changed(
                    path,
                    left_entry.value,
                    right_entry.value,
                    left_entry,
                    right_entry,
                )

        return self.build()

    def _values_equal(self, left: Any, right: Any) -> bool:
        """Check if two values are equal.

        Handles special cases like NaN and complex objects.

        :param left: Left value.
        :param right: Right value.
        :return: True if values are considered equal.
        """
        # Handle NaN (NaN != NaN)
        if isinstance(left, float) and isinstance(right, float):
            import math

            if math.isnan(left) and math.isnan(right):
                return True

        # Standard equality
        try:
            return left == right
        except (TypeError, ValueError):
            # Fallback for objects that don't support ==
            return left is right

    def build(self) -> ConfigDiff:
        """Build the immutable ConfigDiff.

        :return: Immutable ConfigDiff containing all added entries.
        """
        return ConfigDiff(dict(self._entries))

    def clear(self) -> DiffBuilder:
        """Clear all entries from the builder.

        :return: Self for chaining.
        """
        self._entries.clear()
        return self

    def __len__(self) -> int:
        """Get number of entries in builder.

        :return: Number of entries.
        """
        return len(self._entries)
