"""Flat layout for diff formatting.

This module provides a simple flat list layout for diffs,
similar to git diff output style.
"""

from __future__ import annotations

from rconfig._internal.format_utils import indent

from ..models import DiffEntryType
from .model import DiffDisplayModel, DiffEntryDisplayModel
from .layout import DiffLayout


class DiffFlatLayout(DiffLayout):
    """Simple flat list layout for diffs.

    Displays diffs in a flat list format with type indicators:
    - + for added entries
    - - for removed entries
    - ~ for changed entries
    - (space) for unchanged entries

    Example output::

        + model.dropout: 0.1
        + training.early_stopping: true
        - model.legacy_param: "old_value"
        ~ model.lr: 0.001 -> 0.0001
        ~ data.batch_size: 32 -> 64

        Added: 2, Removed: 1, Changed: 2

    :param indent_size: Number of spaces per indentation level.
    """

    def __init__(self, indent_size: int = 2) -> None:
        """Initialize the flat layout.

        :param indent_size: Number of spaces per indentation level.
        """
        self._indent_size = indent_size

    def render(self, model: DiffDisplayModel) -> str:
        """Render the diff model to string output.

        :param model: The display model.
        :return: Formatted string representation.
        """
        if model.empty_message:
            return model.empty_message

        entries = [self._render_entry(e) for e in model.entries]
        result = "\n".join(entries)

        if model.summary:
            result = f"{result}\n\n{model.summary}"

        return result

    def _render_entry(self, entry: DiffEntryDisplayModel) -> str:
        """Render a single diff entry.

        :param entry: The entry display model.
        :return: Formatted entry string.
        """
        parts: list[str] = []

        # Entry line (path, type, values)
        entry_line = self._format_entry_line(entry)
        if entry_line:
            parts.append(entry_line)

        # Provenance
        if entry.left_provenance or entry.right_provenance:
            prov = self._format_provenance(entry)
            if prov:
                parts.append(prov)

        return "\n".join(parts)

    def _format_entry_line(self, entry: DiffEntryDisplayModel) -> str:
        """Format the main line for an entry.

        :param entry: The entry display model.
        :return: Formatted entry line string.
        """
        indicator = entry.diff_type.indicator

        match entry.diff_type:
            case DiffEntryType.ADDED:
                # + path: new_value
                parts = [f"{indicator} {entry.path}"]
                if entry.right_value is not None:
                    parts.append(f": {entry.right_value}")
                return "".join(parts)

            case DiffEntryType.REMOVED:
                # - path: old_value
                parts = [f"{indicator} {entry.path}"]
                if entry.left_value is not None:
                    parts.append(f": {entry.left_value}")
                return "".join(parts)

            case DiffEntryType.CHANGED:
                # ~ path: old_value -> new_value
                parts = [f"{indicator} {entry.path}"]
                if entry.left_value is not None and entry.right_value is not None:
                    parts.append(f": {entry.left_value} -> {entry.right_value}")
                return "".join(parts)

            case DiffEntryType.UNCHANGED:
                # space path: value
                parts = [f"{indicator} {entry.path}"]
                if entry.left_value is not None:
                    parts.append(f": {entry.left_value}")
                return "".join(parts)

    def _format_provenance(self, entry: DiffEntryDisplayModel) -> str | None:
        """Format provenance information for an entry.

        :param entry: The entry display model.
        :return: Formatted provenance string or None.
        """
        parts: list[str] = []

        if entry.left_provenance:
            loc = f"{entry.left_provenance.file}:{entry.left_provenance.line}"
            parts.append(f"left: {loc}")

        if entry.right_provenance:
            loc = f"{entry.right_provenance.file}:{entry.right_provenance.line}"
            parts.append(f"right: {loc}")

        if not parts:
            return None

        return indent(", ".join(parts), 1, self._indent_size)
