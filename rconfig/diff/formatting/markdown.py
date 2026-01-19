"""Markdown table layout for diff formatting.

This module provides a markdown table layout for diffs,
suitable for documentation and export.
"""

from __future__ import annotations

from .model import DiffDisplayModel, DiffEntryDisplayModel
from .layout import DiffLayout
from ..models import DiffEntryType


class DiffMarkdownLayout(DiffLayout):
    """Markdown table layout for diffs.

    Formats diffs as a markdown table for documentation or export.

    Example output::

        | Type | Path | Old Value | New Value |
        |------|------|-----------|-----------|
        | + | model.dropout | - | 0.1 |
        | + | training.early_stopping | - | true |
        | - | model.legacy_param | "old_value" | - |
        | ~ | model.lr | 0.001 | 0.0001 |
        | ~ | data.batch_size | 32 | 64 |

        **Summary:** Added: 2, Removed: 1, Changed: 2
    """

    def render(self, model: DiffDisplayModel) -> str:
        """Render the diff model as a markdown table.

        :param model: The display model.
        :return: Formatted markdown string.
        """
        # Handle empty case
        if model.empty_message:
            return "_No differences found._"

        lines: list[str] = []

        # Determine which columns to show based on what data is present
        show_values = any(
            entry.left_value is not None or entry.right_value is not None
            for entry in model.entries
        )
        show_provenance = any(
            entry.left_provenance is not None or entry.right_provenance is not None
            for entry in model.entries
        )

        # Build header based on available data
        header_parts: list[str] = ["Type", "Path"]
        if show_values:
            header_parts.extend(["Old Value", "New Value"])
        if show_provenance:
            header_parts.append("Source")

        lines.append("| " + " | ".join(header_parts) + " |")
        lines.append("|" + "|".join(["------"] * len(header_parts)) + "|")

        # Table rows
        for entry in model.entries:
            row = self._render_row(entry, show_values, show_provenance)
            if row:
                lines.append(row)

        result = "\n".join(lines)

        # Add summary if present
        if model.summary:
            result = result + "\n\n**Summary:** " + model.summary

        return result

    def _render_row(
        self,
        entry: DiffEntryDisplayModel,
        show_values: bool,
        show_provenance: bool,
    ) -> str:
        """Render a single diff entry as a table row.

        :param entry: The entry display model.
        :param show_values: Whether to show value columns.
        :param show_provenance: Whether to show provenance column.
        :return: Formatted markdown table row.
        """
        parts: list[str] = []

        # Type indicator - get from diff_type enum
        parts.append(entry.diff_type.indicator)

        # Path
        parts.append(self._escape_markdown(entry.path))

        # Values
        if show_values:
            match entry.diff_type:
                case DiffEntryType.ADDED:
                    parts.append("-")
                    parts.append(
                        self._escape_markdown(entry.right_value)
                        if entry.right_value
                        else "-"
                    )
                case DiffEntryType.REMOVED:
                    parts.append(
                        self._escape_markdown(entry.left_value)
                        if entry.left_value
                        else "-"
                    )
                    parts.append("-")
                case DiffEntryType.CHANGED:
                    parts.append(
                        self._escape_markdown(entry.left_value)
                        if entry.left_value
                        else "-"
                    )
                    parts.append(
                        self._escape_markdown(entry.right_value)
                        if entry.right_value
                        else "-"
                    )
                case DiffEntryType.UNCHANGED:
                    value = (
                        self._escape_markdown(entry.left_value)
                        if entry.left_value
                        else "-"
                    )
                    parts.append(value)
                    parts.append(value)

        # Provenance
        if show_provenance:
            provenance_info = self._format_provenance(entry)
            parts.append(provenance_info if provenance_info else "-")

        return "| " + " | ".join(parts) + " |"

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

        return self._escape_markdown(", ".join(parts)) if parts else None

    def _escape_markdown(self, text: str) -> str:
        """Escape markdown special characters in table cells.

        :param text: Text to escape.
        :return: Escaped text safe for markdown tables.
        """
        # Escape pipe characters which break table structure
        text = text.replace("|", "\\|")
        # Escape newlines
        text = text.replace("\n", " ")
        return text
