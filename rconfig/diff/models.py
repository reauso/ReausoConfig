"""Core data models for config diffing.

This module provides:
- DiffEntryType: Enum for categorizing differences
- DiffEntry: Immutable entry representing a single difference
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rconfig.provenance import ProvenanceEntry


class DiffEntryType(StrEnum):
    """Type of difference for a config entry.

    :cvar ADDED: Key exists only in the right config.
    :cvar REMOVED: Key exists only in the left config.
    :cvar CHANGED: Key exists in both but has different values.
    :cvar UNCHANGED: Key exists in both with the same value.
    """

    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"
    UNCHANGED = "unchanged"

    @property
    def indicator(self) -> str:
        """Return the visual indicator for this diff type.

        :return: Single character indicator (+, -, ~, or space).
        """
        match self:
            case DiffEntryType.ADDED:
                return "+"
            case DiffEntryType.REMOVED:
                return "-"
            case DiffEntryType.CHANGED:
                return "~"
            case DiffEntryType.UNCHANGED:
                return " "


@dataclass(frozen=True, slots=True)
class DiffEntry:
    """A single difference between two configs.

    This is an immutable dataclass representing one path's difference.

    :param path: The config path (e.g., "model.lr").
    :param diff_type: The type of difference (added/removed/changed/unchanged).
    :param left_value: Value in the left config (None if added).
    :param right_value: Value in the right config (None if removed).
    :param left_provenance: Provenance entry from left config.
    :param right_provenance: Provenance entry from right config.
    """

    path: str
    diff_type: DiffEntryType
    left_value: Any = None
    right_value: Any = None
    left_provenance: ProvenanceEntry | None = None
    right_provenance: ProvenanceEntry | None = None
