"""Display models for diff formatting.

This module provides data structures that represent diff data
ready for display by layouts. The display models contain only
the data that should be displayed - layouts render what's present.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..models import DiffEntryType

if TYPE_CHECKING:
    from rconfig.provenance.models import ProvenanceEntry


@dataclass(frozen=True)
class DiffEntryDisplayModel:
    """Single diff entry to display.

    Contains only the data that will be displayed. Layouts render
    what's present without checking visibility flags.

    :param path: The config path.
    :param diff_type: The type of difference (layout uses diff_type.indicator).
    :param left_value: Formatted left/old value, or None if hidden.
    :param right_value: Formatted right/new value, or None if hidden.
    :param left_provenance: Left provenance entry, or None if hidden.
    :param right_provenance: Right provenance entry, or None if hidden.
    """

    path: str
    diff_type: DiffEntryType
    left_value: str | None
    right_value: str | None
    left_provenance: ProvenanceEntry | None
    right_provenance: ProvenanceEntry | None


@dataclass(frozen=True)
class DiffDisplayModel:
    """Complete display model for diff output.

    Contains all entries to display and optional empty message.
    Layouts can derive counts from entries, or use pre-computed summary.

    :param entries: Tuple of entry display models to render.
    :param empty_message: Message to show when no differences.
    :param summary: Pre-computed summary string, or None if not shown.
    """

    entries: tuple[DiffEntryDisplayModel, ...]
    empty_message: str | None
    summary: str | None = None


class DiffDisplayModelBuilder:
    """Builds DiffDisplayModel via add calls.

    The builder collects entries via add_entry() calls and builds
    the final model. It has no filtering logic - the Format class
    decides what to add.
    """

    def __init__(self) -> None:
        """Initialize the builder."""
        self._entries: list[DiffEntryDisplayModel] = []
        self._empty_message: str | None = None
        self._summary: str | None = None

    def add_entry(
        self,
        path: str,
        diff_type: DiffEntryType,
        left_value: str | None = None,
        right_value: str | None = None,
        left_provenance: ProvenanceEntry | None = None,
        right_provenance: ProvenanceEntry | None = None,
    ) -> None:
        """Add an entry to display.

        :param path: The config path.
        :param diff_type: The type of difference.
        :param left_value: Formatted left value, or None if hidden.
        :param right_value: Formatted right value, or None if hidden.
        :param left_provenance: Left provenance, or None if hidden.
        :param right_provenance: Right provenance, or None if hidden.
        """
        self._entries.append(
            DiffEntryDisplayModel(
                path=path,
                diff_type=diff_type,
                left_value=left_value,
                right_value=right_value,
                left_provenance=left_provenance,
                right_provenance=right_provenance,
            )
        )

    def set_empty_message(self, message: str) -> None:
        """Set message for empty diff.

        :param message: The empty message to display.
        """
        self._empty_message = message

    def set_summary(self, summary: str | None) -> None:
        """Set the pre-computed summary string.

        :param summary: The summary string, or None to hide it.
        """
        self._summary = summary

    def build(self) -> DiffDisplayModel:
        """Build the final display model.

        :return: The display model ready for layout rendering.
        """
        return DiffDisplayModel(
            entries=tuple(self._entries),
            empty_message=self._empty_message,
            summary=self._summary,
        )
