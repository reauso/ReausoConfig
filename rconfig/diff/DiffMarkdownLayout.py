"""Markdown table layout for diff formatting.

This module provides a markdown table layout for diffs,
suitable for documentation and export.
"""

from __future__ import annotations

from fnmatch import fnmatch
from typing import TYPE_CHECKING

from .Diff import DiffEntryType
from .DiffLayout import DiffFormatContext, DiffLayout

if TYPE_CHECKING:
    from .Diff import ConfigDiff, DiffEntry


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

    def format_diff(self, diff: ConfigDiff, ctx: DiffFormatContext) -> str:
        """Format the entire diff object as a markdown table.

        :param diff: The ConfigDiff object to format.
        :param ctx: Format context with show/hide settings.
        :return: Formatted markdown string.
        """
        if diff.is_empty() and not ctx.show_unchanged:
            return "_No differences found._"

        lines: list[str] = []

        # Table header
        header_parts: list[str] = ["Type"]
        if ctx.show_paths:
            header_parts.append("Path")
        if ctx.show_values:
            header_parts.append("Old Value")
            header_parts.append("New Value")
        if ctx.show_provenance:
            header_parts.append("Source")

        lines.append("| " + " | ".join(header_parts) + " |")
        lines.append("|" + "|".join(["------"] * len(header_parts)) + "|")

        # Table rows
        for path in sorted(diff.keys()):
            entry = diff[path]

            # Apply filters
            if not self._matches_filters(path, entry, ctx):
                continue

            # Check visibility flags
            if entry.diff_type == DiffEntryType.ADDED and not ctx.show_added:
                continue
            if entry.diff_type == DiffEntryType.REMOVED and not ctx.show_removed:
                continue
            if entry.diff_type == DiffEntryType.CHANGED and not ctx.show_changed:
                continue
            if entry.diff_type == DiffEntryType.UNCHANGED and not ctx.show_unchanged:
                continue

            row = self.format_entry(entry, ctx)
            if row:
                lines.append(row)

        result = "\n".join(lines)

        # Add summary if enabled
        if ctx.show_counts:
            summary = self.format_summary(diff, ctx)
            if summary:
                result = result + "\n\n**Summary:** " + summary

        return result

    def format_entry(self, entry: DiffEntry, ctx: DiffFormatContext) -> str:
        """Format a single diff entry as a table row.

        :param entry: The diff entry to format.
        :param ctx: Format context with show/hide settings.
        :return: Formatted markdown table row.
        """
        parts: list[str] = []

        # Type indicator
        type_char = self._get_type_char(entry.diff_type)
        parts.append(type_char)

        # Path
        if ctx.show_paths:
            parts.append(self._escape_markdown(entry.path))

        # Values
        if ctx.show_values:
            if entry.diff_type == DiffEntryType.ADDED:
                parts.append("-")
                parts.append(self._escape_markdown(self.format_value(entry.right_value, ctx)))
            elif entry.diff_type == DiffEntryType.REMOVED:
                parts.append(self._escape_markdown(self.format_value(entry.left_value, ctx)))
                parts.append("-")
            elif entry.diff_type == DiffEntryType.CHANGED:
                parts.append(self._escape_markdown(self.format_value(entry.left_value, ctx)))
                parts.append(self._escape_markdown(self.format_value(entry.right_value, ctx)))
            else:  # UNCHANGED
                value_str = self._escape_markdown(self.format_value(entry.left_value, ctx))
                parts.append(value_str)
                parts.append(value_str)

        # Provenance
        if ctx.show_provenance:
            prov_str = self._format_provenance(entry, ctx)
            parts.append(self._escape_markdown(prov_str) if prov_str else "-")

        return "| " + " | ".join(parts) + " |"

    def _get_type_char(self, diff_type: DiffEntryType) -> str:
        """Get the single-character type indicator.

        :param diff_type: The diff entry type.
        :return: Single character (+, -, ~, or space).
        """
        if diff_type == DiffEntryType.ADDED:
            return "+"
        elif diff_type == DiffEntryType.REMOVED:
            return "-"
        elif diff_type == DiffEntryType.CHANGED:
            return "~"
        else:
            return " "

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

    def _format_provenance(self, entry: DiffEntry, ctx: DiffFormatContext) -> str:
        """Format provenance information for an entry.

        :param entry: The diff entry.
        :param ctx: Format context.
        :return: Formatted provenance string.
        """
        parts: list[str] = []

        if entry.left_provenance:
            loc = self.format_location(
                entry.left_provenance.file,
                entry.left_provenance.line,
                ctx,
            )
            if loc:
                parts.append(f"L: {loc}")

        if entry.right_provenance:
            loc = self.format_location(
                entry.right_provenance.file,
                entry.right_provenance.line,
                ctx,
            )
            if loc:
                parts.append(f"R: {loc}")

        return ", ".join(parts)

    def _matches_filters(
        self, path: str, entry: DiffEntry, ctx: DiffFormatContext
    ) -> bool:
        """Check if an entry matches the configured filters.

        :param path: The config path.
        :param entry: The diff entry.
        :param ctx: Format context with filters.
        :return: True if entry matches all filters.
        """
        # If no filters, everything matches
        if not ctx.path_filters and not ctx.file_filters:
            return True

        # Check path filters (OR logic)
        if ctx.path_filters:
            path_match = any(
                fnmatch(f"/{path}", pattern) or fnmatch(path, pattern)
                for pattern in ctx.path_filters
            )
            if not path_match:
                return False

        # Check file filters (OR logic on either provenance)
        if ctx.file_filters:
            files_to_check = []
            if entry.left_provenance:
                files_to_check.append(entry.left_provenance.file)
            if entry.right_provenance:
                files_to_check.append(entry.right_provenance.file)

            if files_to_check:
                file_match = any(
                    fnmatch(f, pattern)
                    for f in files_to_check
                    for pattern in ctx.file_filters
                )
                if not file_match:
                    return False
            else:
                # No provenance to check against file filters
                return False

        return True
