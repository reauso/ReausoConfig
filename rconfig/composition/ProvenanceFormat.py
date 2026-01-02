"""Fluent builder for provenance formatting.

This module provides the ProvenanceFormat builder class and the
ProvenancePreset enum for configuring how provenance is displayed.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Self

from .ProvenanceLayout import FormatContext

if TYPE_CHECKING:
    from .Provenance import Provenance
    from .ProvenanceLayout import ProvenanceLayout


class ProvenancePreset(Enum):
    """Preset configurations for provenance formatting.

    :cvar MINIMAL: Show only paths, files, and lines.
    :cvar COMPACT: Show paths, values, files, lines, and source type.
    :cvar FULL: Show everything including chains and overrides.
    """

    MINIMAL = "minimal"
    COMPACT = "compact"
    FULL = "full"


class ProvenanceFormat:
    """Fluent builder for formatting provenance output.

    This class provides a chainable API for configuring how provenance
    information is displayed. It supports show/hide toggles, presets,
    filtering, and custom layouts.

    Example::

        # Default full format
        print(prov.format())

        # Use minimal preset
        print(prov.format().minimal())

        # Chain multiple options
        print(prov.format()
            .hide_chain()
            .hide_overrides()
            .for_path("/model.*")
        )

        # Use custom layout
        print(prov.format().layout(TableLayout()))
    """

    def __init__(
        self,
        provenance: Provenance,
        layout: ProvenanceLayout | None = None,
    ) -> None:
        """Initialize the format builder.

        :param provenance: The provenance object to format.
        :param layout: Optional custom layout. Uses TreeLayout if None.
        """
        self._provenance = provenance

        # Import here to avoid circular imports
        if layout is None:
            from .TreeLayout import TreeLayout

            layout = TreeLayout()

        self._layout = layout
        self._ctx = layout.get_default_context()

        # Track explicit overrides (None = use default from context)
        self._overrides: dict[str, bool | None] = {
            "show_paths": None,
            "show_values": None,
            "show_files": None,
            "show_lines": None,
            "show_source_type": None,
            "show_chain": None,
            "show_overrides": None,
        }

    # --- Show/Hide Toggles ---

    def show_paths(self) -> Self:
        """Show config paths in the output.

        :return: Self for method chaining.
        """
        self._overrides["show_paths"] = True
        return self

    def hide_paths(self) -> Self:
        """Hide config paths from the output.

        :return: Self for method chaining.
        """
        self._overrides["show_paths"] = False
        return self

    def show_values(self) -> Self:
        """Show resolved values in the output.

        :return: Self for method chaining.
        """
        self._overrides["show_values"] = True
        return self

    def hide_values(self) -> Self:
        """Hide resolved values from the output.

        :return: Self for method chaining.
        """
        self._overrides["show_values"] = False
        return self

    def show_files(self) -> Self:
        """Show source file names in the output.

        :return: Self for method chaining.
        """
        self._overrides["show_files"] = True
        return self

    def hide_files(self) -> Self:
        """Hide source file names from the output.

        :return: Self for method chaining.
        """
        self._overrides["show_files"] = False
        return self

    def show_lines(self) -> Self:
        """Show line numbers in the output.

        :return: Self for method chaining.
        """
        self._overrides["show_lines"] = True
        return self

    def hide_lines(self) -> Self:
        """Hide line numbers from the output.

        :return: Self for method chaining.
        """
        self._overrides["show_lines"] = False
        return self

    def show_source_type(self) -> Self:
        """Show source type markers (CLI/env/file) in the output.

        :return: Self for method chaining.
        """
        self._overrides["show_source_type"] = True
        return self

    def hide_source_type(self) -> Self:
        """Hide source type markers from the output.

        :return: Self for method chaining.
        """
        self._overrides["show_source_type"] = False
        return self

    def show_chain(self) -> Self:
        """Show full provenance chain (interpolations, refs, instances).

        :return: Self for method chaining.
        """
        self._overrides["show_chain"] = True
        return self

    def hide_chain(self) -> Self:
        """Hide provenance chain from the output.

        :return: Self for method chaining.
        """
        self._overrides["show_chain"] = False
        return self

    def show_overrides(self) -> Self:
        """Show override information in the output.

        :return: Self for method chaining.
        """
        self._overrides["show_overrides"] = True
        return self

    def hide_overrides(self) -> Self:
        """Hide override information from the output.

        :return: Self for method chaining.
        """
        self._overrides["show_overrides"] = False
        return self

    # --- Presets ---

    def minimal(self) -> Self:
        """Apply minimal preset: paths, files, and lines only.

        :return: Self for method chaining.
        """
        self._overrides["show_paths"] = True
        self._overrides["show_values"] = False
        self._overrides["show_files"] = True
        self._overrides["show_lines"] = True
        self._overrides["show_source_type"] = False
        self._overrides["show_chain"] = False
        self._overrides["show_overrides"] = False
        return self

    def compact(self) -> Self:
        """Apply compact preset: paths, values, files, lines, source type.

        :return: Self for method chaining.
        """
        self._overrides["show_paths"] = True
        self._overrides["show_values"] = True
        self._overrides["show_files"] = True
        self._overrides["show_lines"] = True
        self._overrides["show_source_type"] = True
        self._overrides["show_chain"] = False
        self._overrides["show_overrides"] = False
        return self

    def full(self) -> Self:
        """Apply full preset: show everything.

        :return: Self for method chaining.
        """
        self._overrides["show_paths"] = True
        self._overrides["show_values"] = True
        self._overrides["show_files"] = True
        self._overrides["show_lines"] = True
        self._overrides["show_source_type"] = True
        self._overrides["show_chain"] = True
        self._overrides["show_overrides"] = True
        return self

    def preset(self, preset: ProvenancePreset) -> Self:
        """Apply a preset by enum value.

        :param preset: The preset to apply.
        :return: Self for method chaining.
        """
        if preset == ProvenancePreset.MINIMAL:
            return self.minimal()
        elif preset == ProvenancePreset.COMPACT:
            return self.compact()
        elif preset == ProvenancePreset.FULL:
            return self.full()
        else:
            return self

    # --- Layout ---

    def layout(self, layout: ProvenanceLayout) -> Self:
        """Set a custom layout for formatting.

        :param layout: The layout to use.
        :return: Self for method chaining.
        """
        self._layout = layout
        # Get new defaults from the layout, but preserve explicit overrides
        new_ctx = layout.get_default_context()
        self._ctx = new_ctx
        return self

    # --- Filtering ---

    def for_path(self, pattern: str) -> Self:
        """Filter output to only show paths matching the pattern.

        Multiple calls are additive (OR logic).

        :param pattern: Glob pattern for config paths (e.g., "/model.*").
        :return: Self for method chaining.
        """
        self._ctx.path_filters.append(pattern)
        return self

    def from_file(self, pattern: str) -> Self:
        """Filter output to only show entries from matching files.

        Multiple calls are additive (OR logic).

        :param pattern: Glob pattern for file names (e.g., "*.yaml").
        :return: Self for method chaining.
        """
        self._ctx.file_filters.append(pattern)
        return self

    # --- Formatting ---

    def indent(self, spaces: int) -> Self:
        """Set the indentation size.

        :param spaces: Number of spaces per indentation level.
        :return: Self for method chaining.
        """
        self._ctx.indent_size = spaces
        return self

    # --- Output ---

    def _build_context(self) -> FormatContext:
        """Build the final FormatContext with overrides applied.

        :return: FormatContext with all settings resolved.
        """
        # Start with a copy of the base context
        ctx = FormatContext(
            show_paths=self._ctx.show_paths,
            show_values=self._ctx.show_values,
            show_files=self._ctx.show_files,
            show_lines=self._ctx.show_lines,
            show_source_type=self._ctx.show_source_type,
            show_chain=self._ctx.show_chain,
            show_overrides=self._ctx.show_overrides,
            indent_size=self._ctx.indent_size,
            path_filters=list(self._ctx.path_filters),
            file_filters=list(self._ctx.file_filters),
        )

        # Apply explicit overrides
        for key, value in self._overrides.items():
            if value is not None:
                setattr(ctx, key, value)

        return ctx

    def __str__(self) -> str:
        """Format the provenance using the configured layout and options.

        :return: Formatted provenance string.
        """
        ctx = self._build_context()
        return self._layout.format_provenance(self._provenance, ctx)

    def __repr__(self) -> str:
        """Return a representation of this format builder.

        :return: String representation.
        """
        return f"ProvenanceFormat(layout={self._layout.__class__.__name__})"
