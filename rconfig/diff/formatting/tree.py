"""Tree-style layout for diff formatting.

This module provides a grouped tree layout for diffs
that organizes entries by their diff type.
"""

from __future__ import annotations

from rconfig._internal.format_utils import indent

from .model import DiffDisplayModel, DiffEntryDisplayModel
from .layout import DiffLayout
from ..models import DiffEntryType


class DiffTreeLayout(DiffLayout):
    """Grouped tree-style layout for diffs.

    Organizes diff entries by type (Added, Removed, Changed, Unchanged)
    for easier scanning of changes.

    Example output::

        ConfigDiff:
          Added:
            + model.dropout: 0.1
            + training.early_stopping: true

          Removed:
            - model.legacy_param: "old_value"

          Changed:
            ~ model.lr: 0.001 -> 0.0001
            ~ data.batch_size: 32 -> 64

        Added: 2, Removed: 1, Changed: 2

    :param indent_size: Number of spaces per indentation level.
    """

    def __init__(self, indent_size: int = 2) -> None:
        """Initialize the tree layout.

        :param indent_size: Number of spaces per indentation level.
        """
        self._indent_size = indent_size

    def render(self, model: DiffDisplayModel) -> str:
        """Render the diff model to string output.

        :param model: The display model.
        :return: Formatted string representation.
        """
        # Handle empty case
        if model.empty_message:
            return model.empty_message

        # Group entries by type
        added = [e for e in model.entries if e.diff_type == DiffEntryType.ADDED]
        removed = [e for e in model.entries if e.diff_type == DiffEntryType.REMOVED]
        changed = [e for e in model.entries if e.diff_type == DiffEntryType.CHANGED]
        unchanged = [e for e in model.entries if e.diff_type == DiffEntryType.UNCHANGED]

        sections: list[str] = []
        sections.append("ConfigDiff:")

        # Added section
        if added:
            added_section = self._render_section("Added", added)
            if added_section:
                sections.append(added_section)

        # Removed section
        if removed:
            removed_section = self._render_section("Removed", removed)
            if removed_section:
                sections.append(removed_section)

        # Changed section
        if changed:
            changed_section = self._render_section("Changed", changed)
            if changed_section:
                sections.append(changed_section)

        # Unchanged section
        if unchanged:
            unchanged_section = self._render_section("Unchanged", unchanged)
            if unchanged_section:
                sections.append(unchanged_section)

        result = "\n".join(sections)

        # Add summary if present
        if model.summary:
            result = result + "\n\n" + model.summary

        return result

    def _render_section(
        self,
        title: str,
        entries: list[DiffEntryDisplayModel],
    ) -> str:
        """Render a section of entries.

        :param title: Section title (e.g., "Added").
        :param entries: List of entry display models.
        :return: Formatted section string.
        """
        lines: list[str] = []
        lines.append(indent(f"{title}:", 1, self._indent_size))

        for entry in entries:
            formatted = self._render_entry(entry)
            if formatted:
                # Indent entry lines
                for line in formatted.split("\n"):
                    lines.append(indent(line, 2, self._indent_size))

        # Return empty if only header
        if len(lines) == 1:
            return ""

        return "\n".join(lines)

    def _render_entry(self, entry: DiffEntryDisplayModel) -> str:
        """Render a single diff entry.

        :param entry: The entry display model.
        :return: Formatted string for this entry.
        """
        line = self._format_entry_line(entry)

        # Add provenance info if present
        provenance = self._format_provenance(entry)
        if provenance:
            line = line + "\n" + indent(provenance, 1, self._indent_size)

        return line

    def _format_entry_line(self, entry: DiffEntryDisplayModel) -> str:
        """Format the main line for an entry.

        :param entry: The entry display model.
        :return: Formatted main line.
        """
        indicator = entry.diff_type.indicator

        match entry.diff_type:
            case DiffEntryType.ADDED:
                parts = [f"{indicator} {entry.path}"]
                if entry.right_value is not None:
                    parts.append(f": {entry.right_value}")
                return "".join(parts)

            case DiffEntryType.REMOVED:
                parts = [f"{indicator} {entry.path}"]
                if entry.left_value is not None:
                    parts.append(f": {entry.left_value}")
                return "".join(parts)

            case DiffEntryType.CHANGED:
                parts = [f"{indicator} {entry.path}"]
                if entry.left_value is not None and entry.right_value is not None:
                    parts.append(f": {entry.left_value} -> {entry.right_value}")
                return "".join(parts)

            case DiffEntryType.UNCHANGED:
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

        return ", ".join(parts) if parts else None
