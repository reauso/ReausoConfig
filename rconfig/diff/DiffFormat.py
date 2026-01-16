"""Fluent builder for diff formatting.

This module provides DiffFormat and DiffPreset for
configuring diff output format with method chaining.
"""

from __future__ import annotations

from copy import deepcopy
from enum import Enum
from typing import TYPE_CHECKING, Self

from .DiffFlatLayout import DiffFlatLayout
from .DiffLayout import DiffFormatContext, DiffLayout
from .DiffMarkdownLayout import DiffMarkdownLayout
from .DiffTreeLayout import DiffTreeLayout

if TYPE_CHECKING:
    from .Diff import ConfigDiff


class DiffPreset(Enum):
    """Preset configurations for common diff output scenarios.

    :cvar CHANGES_ONLY: Only added/removed/changed entries (default).
    :cvar WITH_CONTEXT: Changes plus nearby unchanged entries.
    :cvar FULL: All entries including unchanged.
    :cvar SUMMARY: Only statistics, no individual entries.
    """

    CHANGES_ONLY = "changes_only"
    WITH_CONTEXT = "with_context"
    FULL = "full"
    SUMMARY = "summary"


class DiffFormat:
    """Fluent builder for configuring diff output format.

    Use method chaining to configure what to show/hide and the output format.
    Each method returns self for chaining.

    Usage::

        # Basic usage
        diff.format().terminal()

        # With options
        diff.format().show_provenance().hide_unchanged().markdown()

        # With preset
        diff.format().full().tree()

        # With custom layout
        diff.format().layout(MyCustomLayout()).terminal()

    Available output methods:
        - terminal() -> str: Default flat layout
        - tree() -> str: Grouped tree layout
        - markdown() -> str: Markdown table
        - json() -> dict: Dictionary format
    """

    __slots__ = ("_diff", "_ctx", "_layout")

    def __init__(self, diff: ConfigDiff) -> None:
        """Initialize DiffFormat with a ConfigDiff.

        :param diff: The ConfigDiff to format.
        """
        self._diff = diff
        self._layout: DiffLayout = DiffFlatLayout()
        self._ctx: DiffFormatContext = self._layout.get_default_context()

    # Show/Hide toggles

    def show_paths(self) -> Self:
        """Show config paths in output.

        :return: Self for chaining.
        """
        self._ctx.show_paths = True
        return self

    def hide_paths(self) -> Self:
        """Hide config paths from output.

        :return: Self for chaining.
        """
        self._ctx.show_paths = False
        return self

    def show_values(self) -> Self:
        """Show values in output.

        :return: Self for chaining.
        """
        self._ctx.show_values = True
        return self

    def hide_values(self) -> Self:
        """Hide values from output.

        :return: Self for chaining.
        """
        self._ctx.show_values = False
        return self

    def show_files(self) -> Self:
        """Show source file names from provenance.

        :return: Self for chaining.
        """
        self._ctx.show_files = True
        return self

    def hide_files(self) -> Self:
        """Hide source file names from output.

        :return: Self for chaining.
        """
        self._ctx.show_files = False
        return self

    def show_lines(self) -> Self:
        """Show line numbers from provenance.

        :return: Self for chaining.
        """
        self._ctx.show_lines = True
        return self

    def hide_lines(self) -> Self:
        """Hide line numbers from output.

        :return: Self for chaining.
        """
        self._ctx.show_lines = False
        return self

    def show_provenance(self) -> Self:
        """Show provenance information (file:line).

        :return: Self for chaining.
        """
        self._ctx.show_provenance = True
        return self

    def hide_provenance(self) -> Self:
        """Hide provenance information.

        :return: Self for chaining.
        """
        self._ctx.show_provenance = False
        return self

    def show_unchanged(self) -> Self:
        """Include unchanged entries in output.

        :return: Self for chaining.
        """
        self._ctx.show_unchanged = True
        return self

    def hide_unchanged(self) -> Self:
        """Exclude unchanged entries from output.

        :return: Self for chaining.
        """
        self._ctx.show_unchanged = False
        return self

    def show_added(self) -> Self:
        """Include added entries in output.

        :return: Self for chaining.
        """
        self._ctx.show_added = True
        return self

    def hide_added(self) -> Self:
        """Exclude added entries from output.

        :return: Self for chaining.
        """
        self._ctx.show_added = False
        return self

    def show_removed(self) -> Self:
        """Include removed entries in output.

        :return: Self for chaining.
        """
        self._ctx.show_removed = True
        return self

    def hide_removed(self) -> Self:
        """Exclude removed entries from output.

        :return: Self for chaining.
        """
        self._ctx.show_removed = False
        return self

    def show_changed(self) -> Self:
        """Include changed entries in output.

        :return: Self for chaining.
        """
        self._ctx.show_changed = True
        return self

    def hide_changed(self) -> Self:
        """Exclude changed entries from output.

        :return: Self for chaining.
        """
        self._ctx.show_changed = False
        return self

    def show_counts(self) -> Self:
        """Show summary statistics (Added: X, Removed: Y, ...).

        :return: Self for chaining.
        """
        self._ctx.show_counts = True
        return self

    def hide_counts(self) -> Self:
        """Hide summary statistics.

        :return: Self for chaining.
        """
        self._ctx.show_counts = False
        return self

    # Presets

    def changes_only(self) -> Self:
        """Apply CHANGES_ONLY preset: only added/removed/changed entries.

        :return: Self for chaining.
        """
        self._ctx.show_added = True
        self._ctx.show_removed = True
        self._ctx.show_changed = True
        self._ctx.show_unchanged = False
        self._ctx.show_counts = True
        return self

    def with_context(self) -> Self:
        """Apply WITH_CONTEXT preset: changes plus unchanged entries.

        :return: Self for chaining.
        """
        self._ctx.show_added = True
        self._ctx.show_removed = True
        self._ctx.show_changed = True
        self._ctx.show_unchanged = True
        self._ctx.show_counts = True
        return self

    def full(self) -> Self:
        """Apply FULL preset: all entries including unchanged.

        :return: Self for chaining.
        """
        self._ctx.show_added = True
        self._ctx.show_removed = True
        self._ctx.show_changed = True
        self._ctx.show_unchanged = True
        self._ctx.show_provenance = True
        self._ctx.show_counts = True
        return self

    def summary(self) -> Self:
        """Apply SUMMARY preset: only statistics, no individual entries.

        :return: Self for chaining.
        """
        self._ctx.show_added = False
        self._ctx.show_removed = False
        self._ctx.show_changed = False
        self._ctx.show_unchanged = False
        self._ctx.show_counts = True
        return self

    def preset(self, preset: DiffPreset) -> Self:
        """Apply a preset configuration.

        :param preset: The preset to apply.
        :return: Self for chaining.
        """
        if preset == DiffPreset.CHANGES_ONLY:
            return self.changes_only()
        elif preset == DiffPreset.WITH_CONTEXT:
            return self.with_context()
        elif preset == DiffPreset.FULL:
            return self.full()
        elif preset == DiffPreset.SUMMARY:
            return self.summary()
        return self

    # Filtering

    def for_path(self, pattern: str) -> Self:
        """Filter entries by path pattern.

        Uses glob-style patterns (e.g., "model.*", "/training/*").
        Multiple calls add additional patterns (OR logic).

        :param pattern: Glob pattern to match paths.
        :return: Self for chaining.
        """
        self._ctx.path_filters.append(pattern)
        return self

    def from_file(self, pattern: str) -> Self:
        """Filter entries by source file pattern.

        Uses glob-style patterns (e.g., "*.yaml", "configs/*").
        Multiple calls add additional patterns (OR logic).

        :param pattern: Glob pattern to match source files.
        :return: Self for chaining.
        """
        self._ctx.file_filters.append(pattern)
        return self

    # Layout

    def layout(self, layout: DiffLayout) -> Self:
        """Set a custom layout for formatting.

        :param layout: The layout instance to use.
        :return: Self for chaining.
        """
        self._layout = layout
        # Merge layout defaults with current context
        # Keep user's explicit settings, fill in from layout defaults
        layout_ctx = layout.get_default_context()
        # Copy any list fields that might have been modified
        if not self._ctx.path_filters:
            self._ctx.path_filters = deepcopy(layout_ctx.path_filters)
        if not self._ctx.file_filters:
            self._ctx.file_filters = deepcopy(layout_ctx.file_filters)
        return self

    # Output methods

    def terminal(self) -> str:
        """Format as terminal text using flat layout.

        :return: Formatted string for terminal display.
        """
        if not isinstance(self._layout, DiffFlatLayout):
            self._layout = DiffFlatLayout()
        return self._layout.format_diff(self._diff, self._ctx)

    def tree(self) -> str:
        """Format as grouped tree structure.

        :return: Formatted string with tree layout.
        """
        self._layout = DiffTreeLayout()
        return self._layout.format_diff(self._diff, self._ctx)

    def markdown(self) -> str:
        """Format as markdown table.

        :return: Markdown-formatted string.
        """
        self._layout = DiffMarkdownLayout()
        return self._layout.format_diff(self._diff, self._ctx)

    def json(self) -> dict:
        """Format as dictionary (for JSON serialization).

        :return: Dictionary representation of the diff.
        """
        return self._diff.to_dict()

    def __str__(self) -> str:
        """Return formatted string using current layout.

        :return: Formatted diff string.
        """
        return self._layout.format_diff(self._diff, self._ctx)
