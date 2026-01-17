"""Flat layout for diff formatting.

This module provides a simple flat list layout for diffs,
similar to git diff output style.
"""

from __future__ import annotations

from fnmatch import fnmatch
from typing import TYPE_CHECKING

from ..models import DiffEntryType
from .layout import DiffFormatContext, DiffLayout

if TYPE_CHECKING:
    from ..diff import ConfigDiff
    from ..models import DiffEntry


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
    """

    def format_diff(self, diff: ConfigDiff, ctx: DiffFormatContext) -> str:
        """Format the entire diff object.

        :param diff: The ConfigDiff object to format.
        :param ctx: Format context with show/hide settings.
        :return: Formatted string representation.
        """
        if diff.is_empty() and not ctx.show_unchanged:
            return "No differences found."

        entries: list[str] = []

        # Sort paths for consistent output
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

            formatted = self.format_entry(entry, ctx)
            if formatted:
                entries.append(formatted)

        result = self.join_entries(entries, ctx)

        # Add summary if enabled
        if ctx.show_counts:
            summary = self.format_summary(diff, ctx)
            if summary:
                if result:
                    result = result + "\n\n" + summary
                else:
                    result = summary

        return result

    def format_entry(self, entry: DiffEntry, ctx: DiffFormatContext) -> str:
        """Format a single diff entry.

        :param entry: The diff entry to format.
        :param ctx: Format context with show/hide settings.
        :return: Formatted string for this entry.
        """
        if entry.diff_type == DiffEntryType.ADDED:
            line = self.format_added(entry, ctx)
        elif entry.diff_type == DiffEntryType.REMOVED:
            line = self.format_removed(entry, ctx)
        elif entry.diff_type == DiffEntryType.CHANGED:
            line = self.format_changed(entry, ctx)
        else:
            line = self.format_unchanged(entry, ctx)

        # Add provenance info if enabled
        if ctx.show_provenance:
            provenance_info = self._format_provenance(entry, ctx)
            if provenance_info:
                line = line + "\n" + self.indent(provenance_info, 1, ctx)

        return line

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
                parts.append(f"left: {loc}")

        if entry.right_provenance:
            loc = self.format_location(
                entry.right_provenance.file,
                entry.right_provenance.line,
                ctx,
            )
            if loc:
                parts.append(f"right: {loc}")

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
