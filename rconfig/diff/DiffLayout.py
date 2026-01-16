"""Diff layout system for customizable formatting.

This module provides the base class for diff layouts and the
DiffFormatContext dataclass that holds runtime formatting settings.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .Diff import ConfigDiff, DiffEntry


@dataclass
class DiffFormatContext:
    """Runtime settings passed from the builder to the layout.

    These settings control what information is displayed. The layout
    uses these flags to conditionally include/exclude components.

    :param show_paths: Show the config paths (e.g., /model.lr).
    :param show_values: Show the values that changed.
    :param show_files: Show source file names from provenance.
    :param show_lines: Show line numbers from provenance.
    :param show_provenance: Show provenance information (file:line).
    :param show_unchanged: Include unchanged entries in output.
    :param show_added: Include added entries in output.
    :param show_removed: Include removed entries in output.
    :param show_changed: Include changed entries in output.
    :param show_counts: Show summary statistics (Added: X, Removed: Y, ...).
    :param indent_size: Number of spaces per indentation level.
    :param path_filters: Glob patterns to filter by config path.
    :param file_filters: Glob patterns to filter by source file.
    """

    show_paths: bool = True
    show_values: bool = True
    show_files: bool = True
    show_lines: bool = True
    show_provenance: bool = False
    show_unchanged: bool = False
    show_added: bool = True
    show_removed: bool = True
    show_changed: bool = True
    show_counts: bool = True
    indent_size: int = 2
    path_filters: list[str] = field(default_factory=list)
    file_filters: list[str] = field(default_factory=list)


class DiffLayout(ABC):
    """Base class for diff formatting layouts.

    A layout defines HOW to format diff information, not WHAT to show.
    The WHAT is controlled by DiffFormatContext flags set via the builder.

    Subclass this to create custom layouts (tree, markdown, HTML, etc.).
    Override the methods you want to customize; the base implementations
    provide sensible defaults.

    Example::

        class HtmlLayout(DiffLayout):
            def format_diff(self, diff, ctx):
                lines = ["<table>"]
                for path, entry in diff.items():
                    lines.append(self.format_entry(entry, ctx))
                lines.append("</table>")
                return "\\n".join(lines)

            def format_entry(self, entry, ctx):
                return f"<tr><td>{entry.path}</td><td>{entry.diff_type}</td></tr>"
    """

    def get_default_context(self) -> DiffFormatContext:
        """Return default show/hide settings for this layout.

        Override this to change what's shown by default for this layout.
        Builder methods will override these settings.

        :return: DiffFormatContext with default settings.
        """
        return DiffFormatContext()

    @abstractmethod
    def format_diff(self, diff: ConfigDiff, ctx: DiffFormatContext) -> str:
        """Format the entire diff object.

        This is the main entry point called by DiffFormat.__str__().

        :param diff: The ConfigDiff object to format.
        :param ctx: Format context with show/hide settings.
        :return: Formatted string representation.
        """
        ...

    @abstractmethod
    def format_entry(self, entry: DiffEntry, ctx: DiffFormatContext) -> str:
        """Format a single diff entry.

        :param entry: The diff entry to format.
        :param ctx: Format context with show/hide settings.
        :return: Formatted string for this entry.
        """
        ...

    def format_value(self, value: Any, ctx: DiffFormatContext) -> str:
        """Format a value for display.

        Override this to customize value display (truncation, colors, etc.).

        :param value: The value to format.
        :param ctx: Format context.
        :return: Formatted value string.
        """
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, str):
            return repr(value)
        elif isinstance(value, (list, dict)):
            # Truncate complex values
            s = str(value)
            if len(s) > 50:
                return s[:47] + "..."
            return s
        else:
            return str(value)

    def format_location(self, file: str | None, line: int | None, ctx: DiffFormatContext) -> str:
        """Format file:line location from provenance.

        :param file: Source file name (may be None).
        :param line: Line number (may be None).
        :param ctx: Format context.
        :return: Formatted location string.
        """
        if not file:
            return ""

        parts = []
        if ctx.show_files:
            parts.append(file)
        if ctx.show_lines and line is not None:
            if parts:
                parts.append(f":{line}")
            else:
                parts.append(str(line))
        return "".join(parts)

    def format_summary(self, diff: ConfigDiff, ctx: DiffFormatContext) -> str:
        """Format the summary statistics line.

        Shows counts for all change types regardless of show_* flags.
        The show_* flags control entry visibility, not count visibility.

        :param diff: The ConfigDiff object.
        :param ctx: Format context.
        :return: Formatted summary string like "Added: 3, Removed: 1, Changed: 5".
        """
        parts: list[str] = []

        if len(diff.added) > 0:
            parts.append(f"Added: {len(diff.added)}")
        if len(diff.removed) > 0:
            parts.append(f"Removed: {len(diff.removed)}")
        if len(diff.changed) > 0:
            parts.append(f"Changed: {len(diff.changed)}")
        if ctx.show_unchanged and len(diff.unchanged) > 0:
            parts.append(f"Unchanged: {len(diff.unchanged)}")

        return ", ".join(parts)

    def format_added(self, entry: DiffEntry, ctx: DiffFormatContext) -> str:
        """Format an added entry.

        :param entry: The diff entry (must be ADDED type).
        :param ctx: Format context.
        :return: Formatted string for added entry.
        """
        parts: list[str] = []
        if ctx.show_paths:
            parts.append(f"+ {entry.path}")
        if ctx.show_values:
            value_str = self.format_value(entry.right_value, ctx)
            if parts:
                parts.append(f": {value_str}")
            else:
                parts.append(value_str)
        return "".join(parts)

    def format_removed(self, entry: DiffEntry, ctx: DiffFormatContext) -> str:
        """Format a removed entry.

        :param entry: The diff entry (must be REMOVED type).
        :param ctx: Format context.
        :return: Formatted string for removed entry.
        """
        parts: list[str] = []
        if ctx.show_paths:
            parts.append(f"- {entry.path}")
        if ctx.show_values:
            value_str = self.format_value(entry.left_value, ctx)
            if parts:
                parts.append(f": {value_str}")
            else:
                parts.append(value_str)
        return "".join(parts)

    def format_changed(self, entry: DiffEntry, ctx: DiffFormatContext) -> str:
        """Format a changed entry.

        :param entry: The diff entry (must be CHANGED type).
        :param ctx: Format context.
        :return: Formatted string for changed entry.
        """
        parts: list[str] = []
        if ctx.show_paths:
            parts.append(f"~ {entry.path}")
        if ctx.show_values:
            left_str = self.format_value(entry.left_value, ctx)
            right_str = self.format_value(entry.right_value, ctx)
            if parts:
                parts.append(f": {left_str} -> {right_str}")
            else:
                parts.append(f"{left_str} -> {right_str}")
        return "".join(parts)

    def format_unchanged(self, entry: DiffEntry, ctx: DiffFormatContext) -> str:
        """Format an unchanged entry.

        :param entry: The diff entry (must be UNCHANGED type).
        :param ctx: Format context.
        :return: Formatted string for unchanged entry.
        """
        parts: list[str] = []
        if ctx.show_paths:
            parts.append(f"  {entry.path}")
        if ctx.show_values:
            value_str = self.format_value(entry.left_value, ctx)
            if parts:
                parts.append(f": {value_str}")
            else:
                parts.append(value_str)
        return "".join(parts)

    def join_entries(self, entries: list[str], ctx: DiffFormatContext) -> str:
        """Join all formatted entries into final output.

        :param entries: List of formatted entry strings.
        :param ctx: Format context.
        :return: Combined output string.
        """
        return "\n".join(entries)

    def indent(self, text: str, depth: int, ctx: DiffFormatContext) -> str:
        """Apply indentation to text.

        :param text: Text to indent.
        :param depth: Indentation depth.
        :param ctx: Format context with indent_size.
        :return: Indented text.
        """
        prefix = " " * (depth * ctx.indent_size)
        return prefix + text
