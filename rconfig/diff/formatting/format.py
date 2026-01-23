"""Fluent builder for diff formatting.

This module provides DiffFormat and DiffFormatContext for configuring
diff output format with method chaining. Presets are managed via
the DiffRegistry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from functools import singledispatchmethod
from typing import Self, overload

from rconfig._internal.format_utils import format_value

from ..diff import ConfigDiff
from ..models import DiffEntry, DiffEntryType
from .layout import DiffLayout
from .model import DiffDisplayModelBuilder


@dataclass
class DiffFormatContext:
    """Settings that control what information is displayed.

    These settings are used by DiffRenderModelBuilder to determine
    what data to include in the render model.

    :param show_paths: Show the config paths.
    :param show_values: Show values.
    :param show_files: Show source file names from provenance.
    :param show_lines: Show line numbers from provenance.
    :param show_provenance: Show provenance information.
    :param show_unchanged: Include unchanged entries.
    :param show_added: Include added entries.
    :param show_removed: Include removed entries.
    :param show_changed: Include changed entries.
    :param show_counts: Show summary statistics.
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
        self._layout: DiffLayout | None = None
        self._ctx: DiffFormatContext = DiffFormatContext()

    def _get_layout(self) -> DiffLayout:
        """Get the layout, creating default FlatLayout if needed.

        :return: The layout instance.
        """
        if self._layout is None:
            from .flat import DiffFlatLayout

            return DiffFlatLayout()
        return self._layout

    def _build_model(self):
        """Build the display model from current context.

        This method implements all WHAT logic: filtering entries,
        checking visibility flags, and formatting values.

        :return: The display model.
        """
        builder = DiffDisplayModelBuilder()

        # Compute summary from original diff data if enabled
        if self._ctx.show_counts:
            summary = self._build_summary()
            builder.set_summary(summary)

        # Handle empty diff
        if self._diff.is_empty() and not self._ctx.show_unchanged:
            builder.set_empty_message("No differences found.")
            return builder.build()

        # Process entries in sorted order
        for path in sorted(self._diff.keys()):
            entry = self._diff[path]

            # Apply filters
            if not self._matches_filters(path, entry):
                continue

            # Check visibility flags
            if not self._should_show_type(entry.diff_type):
                continue

            # Add entry with only visible data
            builder.add_entry(
                path=path,
                diff_type=entry.diff_type,
                left_value=format_value(entry.left_value)
                if self._ctx.show_values and entry.left_value is not None
                else None,
                right_value=format_value(entry.right_value)
                if self._ctx.show_values and entry.right_value is not None
                else None,
                left_provenance=entry.left_provenance
                if self._ctx.show_provenance
                else None,
                right_provenance=entry.right_provenance
                if self._ctx.show_provenance
                else None,
            )

        # Set empty message if diff has no differences
        model = builder.build()
        if not model.entries and self._diff.is_empty():
            builder.set_empty_message("No differences found.")
            return builder.build()

        return model

    def _build_summary(self) -> str | None:
        """Build summary string from original diff data.

        :return: Summary string or None if no changes.
        """
        added = sum(
            1 for e in self._diff.values() if e.diff_type == DiffEntryType.ADDED
        )
        removed = sum(
            1 for e in self._diff.values() if e.diff_type == DiffEntryType.REMOVED
        )
        changed = sum(
            1 for e in self._diff.values() if e.diff_type == DiffEntryType.CHANGED
        )
        unchanged = sum(
            1 for e in self._diff.values() if e.diff_type == DiffEntryType.UNCHANGED
        )

        parts: list[str] = []
        if added > 0:
            parts.append(f"Added: {added}")
        if removed > 0:
            parts.append(f"Removed: {removed}")
        if changed > 0:
            parts.append(f"Changed: {changed}")
        if unchanged > 0 and self._ctx.show_unchanged:
            parts.append(f"Unchanged: {unchanged}")

        return ", ".join(parts) if parts else None

    def _should_show_type(self, diff_type: DiffEntryType) -> bool:
        """Check if a diff type should be shown.

        :param diff_type: The diff type to check.
        :return: True if the type should be shown.
        """
        match diff_type:
            case DiffEntryType.ADDED:
                return self._ctx.show_added
            case DiffEntryType.REMOVED:
                return self._ctx.show_removed
            case DiffEntryType.CHANGED:
                return self._ctx.show_changed
            case DiffEntryType.UNCHANGED:
                return self._ctx.show_unchanged

    def _matches_filters(self, path: str, entry: DiffEntry) -> bool:
        """Check if an entry matches the configured filters.

        :param path: The config path.
        :param entry: The diff entry.
        :return: True if entry matches all filters.
        """
        # If no filters, everything matches
        if not self._ctx.path_filters and not self._ctx.file_filters:
            return True

        # Check path filters (OR logic)
        if self._ctx.path_filters:
            path_match = any(
                fnmatch(f"/{path}", pattern) or fnmatch(path, pattern)
                for pattern in self._ctx.path_filters
            )
            if not path_match:
                return False

        # Check file filters (OR logic on either provenance)
        if self._ctx.file_filters:
            files_to_check: list[str] = []
            if entry.left_provenance:
                files_to_check.append(entry.left_provenance.file)
            if entry.right_provenance:
                files_to_check.append(entry.right_provenance.file)

            if files_to_check:
                file_match = any(
                    fnmatch(f, pattern)
                    for f in files_to_check
                    for pattern in self._ctx.file_filters
                )
                if not file_match:
                    return False
            else:
                # No provenance to check against file filters
                return False

        return True

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

    def preset(self, name: str) -> Self:
        """Apply a preset by name.

        :param name: The preset name (e.g., "changes_only", "full", "summary").
        :return: Self for chaining.
        :raises ValueError: If preset name is not registered.

        Example::

            # Apply a built-in preset
            print(diff.format().preset("changes_only"))

            # Apply a custom preset
            print(diff.format().preset("my_custom_preset"))
        """
        from .registry import get_diff_registry

        entry = get_diff_registry().get_preset(name)

        if entry is None:
            raise ValueError(f"Unknown preset '{name}' for diff formatting")

        preset_ctx = entry.factory()
        self._apply_context(preset_ctx)
        return self

    def _apply_context(self, preset_ctx: DiffFormatContext) -> None:
        """Apply preset context values to current context.

        :param preset_ctx: The preset context to apply.
        """
        for field_name in [
            "show_paths",
            "show_values",
            "show_files",
            "show_lines",
            "show_provenance",
            "show_unchanged",
            "show_added",
            "show_removed",
            "show_changed",
            "show_counts",
            "indent_size",
        ]:
            if hasattr(preset_ctx, field_name):
                setattr(self._ctx, field_name, getattr(preset_ctx, field_name))

    def default(self) -> Self:
        """Apply default preset: reset to default settings.

        :return: Self for chaining.
        """
        return self.preset("default")

    def changes_only(self) -> Self:
        """Apply changes_only preset: only added/removed/changed entries.

        :return: Self for chaining.
        """
        return self.preset("changes_only")

    def with_context(self) -> Self:
        """Apply with_context preset: changes plus unchanged entries.

        :return: Self for chaining.
        """
        return self.preset("with_context")

    def full(self) -> Self:
        """Apply full preset: all entries including unchanged.

        :return: Self for chaining.
        """
        return self.preset("full")

    def summary(self) -> Self:
        """Apply summary preset: only statistics, no individual entries.

        :return: Self for chaining.
        """
        return self.preset("summary")

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

    @overload
    def layout(self, layout: DiffLayout) -> Self: ...

    @overload
    def layout(self, layout: str) -> Self: ...

    @singledispatchmethod
    def layout(self, layout: DiffLayout | str) -> Self:
        """Set a custom layout for formatting.

        :param layout: The layout instance to use.
        :return: Self for chaining.
        """
        self._layout = layout  # type: ignore[assignment]
        return self

    @layout.register
    def _(self, layout: str) -> Self:
        """Set a layout by registered name.

        :param layout: The registered layout name (e.g., "flat", "tree", "markdown").
        :return: Self for chaining.
        :raises ValueError: If layout name is not registered.
        """
        from .registry import get_diff_registry

        entry = get_diff_registry().get_layout(layout)
        if entry is None:
            raise ValueError(f"Unknown layout '{layout}' for diff formatting")
        self._layout = entry.factory()
        return self

    # Output methods

    def terminal(self) -> str:
        """Format as terminal text using flat layout.

        :return: Formatted string for terminal display.
        """
        return self.layout("flat").__str__()

    def tree(self) -> str:
        """Format as grouped tree structure.

        :return: Formatted string with tree layout.
        """
        return self.layout("tree").__str__()

    def markdown(self) -> str:
        """Format as markdown table.

        :return: Markdown-formatted string.
        """
        return self.layout("markdown").__str__()

    def json(self) -> dict:
        """Format as dictionary (for JSON serialization).

        :return: Dictionary representation of the diff.
        """
        return self._diff.to_dict()

    def __str__(self) -> str:
        """Return formatted string using current layout.

        :return: Formatted diff string.
        """
        model = self._build_model()
        layout = self._get_layout()
        return layout.render(model)
