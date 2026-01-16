"""Tree-style layout for diff formatting.

This module provides a grouped tree layout for diffs
that organizes entries by their diff type.
"""

from __future__ import annotations

from fnmatch import fnmatch
from typing import TYPE_CHECKING

from .Diff import DiffEntryType
from .DiffLayout import DiffFormatContext, DiffLayout

if TYPE_CHECKING:
    from .Diff import ConfigDiff, DiffEntry


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
    """

    def format_diff(self, diff: ConfigDiff, ctx: DiffFormatContext) -> str:
        """Format the entire diff object.

        :param diff: The ConfigDiff object to format.
        :param ctx: Format context with show/hide settings.
        :return: Formatted string representation.
        """
        if diff.is_empty() and not ctx.show_unchanged:
            return "No differences found."

        sections: list[str] = []
        sections.append("ConfigDiff:")

        # Added section
        if ctx.show_added and len(diff.added) > 0:
            added_section = self._format_section("Added", diff.added, ctx)
            if added_section:
                sections.append(added_section)

        # Removed section
        if ctx.show_removed and len(diff.removed) > 0:
            removed_section = self._format_section("Removed", diff.removed, ctx)
            if removed_section:
                sections.append(removed_section)

        # Changed section
        if ctx.show_changed and len(diff.changed) > 0:
            changed_section = self._format_section("Changed", diff.changed, ctx)
            if changed_section:
                sections.append(changed_section)

        # Unchanged section
        if ctx.show_unchanged and len(diff.unchanged) > 0:
            unchanged_section = self._format_section("Unchanged", diff.unchanged, ctx)
            if unchanged_section:
                sections.append(unchanged_section)

        result = "\n".join(sections)

        # Add summary if enabled
        if ctx.show_counts:
            summary = self.format_summary(diff, ctx)
            if summary:
                result = result + "\n\n" + summary

        return result

    def _format_section(
        self,
        title: str,
        entries: dict[str, DiffEntry],
        ctx: DiffFormatContext,
    ) -> str:
        """Format a section of entries.

        :param title: Section title (e.g., "Added").
        :param entries: Dictionary of path -> DiffEntry.
        :param ctx: Format context.
        :return: Formatted section string.
        """
        lines: list[str] = []
        lines.append(self.indent(f"{title}:", 1, ctx))

        for path in sorted(entries.keys()):
            entry = entries[path]

            # Apply filters
            if not self._matches_filters(path, entry, ctx):
                continue

            formatted = self.format_entry(entry, ctx)
            if formatted:
                # Indent entry lines
                for line in formatted.split("\n"):
                    lines.append(self.indent(line, 2, ctx))

        # Return empty if only header (all filtered out)
        if len(lines) == 1:
            return ""

        return "\n".join(lines)

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
