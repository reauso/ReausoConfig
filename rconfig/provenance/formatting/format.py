"""Fluent builder for provenance formatting.

This module provides the ProvenanceFormat builder class and the
ProvenancePreset enum for configuring how provenance is displayed.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Self

from .layout import ProvenanceFormatContext

if TYPE_CHECKING:
    from rconfig.provenance.provenance import Provenance
    from .layout import ProvenanceLayout


class ProvenancePreset(Enum):
    """Preset configurations for provenance formatting.

    :cvar MINIMAL: Show only paths, files, and lines.
    :cvar COMPACT: Show paths, values, files, lines, source type, and types.
    :cvar FULL: Show everything including chains, overrides, types, and descriptions.
    :cvar HELP: Show paths, types, values, and descriptions for CLI help.
    """

    MINIMAL = "minimal"
    COMPACT = "compact"
    FULL = "full"
    HELP = "help"


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
            from .tree import TreeLayout

            layout = TreeLayout()

        self._layout = layout
        self._ctx = layout.get_default_context()

    # --- Show/Hide Toggles ---

    def show_paths(self) -> Self:
        """Show config paths in the output.

        :return: Self for method chaining.
        """
        self._ctx.show_paths = True
        return self

    def hide_paths(self) -> Self:
        """Hide config paths from the output.

        :return: Self for method chaining.
        """
        self._ctx.show_paths = False
        return self

    def show_values(self) -> Self:
        """Show resolved values in the output.

        :return: Self for method chaining.
        """
        self._ctx.show_values = True
        return self

    def hide_values(self) -> Self:
        """Hide resolved values from the output.

        :return: Self for method chaining.
        """
        self._ctx.show_values = False
        return self

    def show_files(self) -> Self:
        """Show source file names in the output.

        :return: Self for method chaining.
        """
        self._ctx.show_files = True
        return self

    def hide_files(self) -> Self:
        """Hide source file names from the output.

        :return: Self for method chaining.
        """
        self._ctx.show_files = False
        return self

    def show_lines(self) -> Self:
        """Show line numbers in the output.

        :return: Self for method chaining.
        """
        self._ctx.show_lines = True
        return self

    def hide_lines(self) -> Self:
        """Hide line numbers from the output.

        :return: Self for method chaining.
        """
        self._ctx.show_lines = False
        return self

    def show_source_type(self) -> Self:
        """Show source type markers (CLI/env/file) in the output.

        :return: Self for method chaining.
        """
        self._ctx.show_source_type = True
        return self

    def hide_source_type(self) -> Self:
        """Hide source type markers from the output.

        :return: Self for method chaining.
        """
        self._ctx.show_source_type = False
        return self

    def show_chain(self) -> Self:
        """Show full provenance chain (interpolations, refs, instances).

        :return: Self for method chaining.
        """
        self._ctx.show_chain = True
        return self

    def hide_chain(self) -> Self:
        """Hide provenance chain from the output.

        :return: Self for method chaining.
        """
        self._ctx.show_chain = False
        return self

    def show_overrides(self) -> Self:
        """Show override information in the output.

        :return: Self for method chaining.
        """
        self._ctx.show_overrides = True
        return self

    def hide_overrides(self) -> Self:
        """Hide override information from the output.

        :return: Self for method chaining.
        """
        self._ctx.show_overrides = False
        return self

    def show_targets(self) -> Self:
        """Show target class information in the output.

        :return: Self for method chaining.
        """
        self._ctx.show_targets = True
        return self

    def hide_targets(self) -> Self:
        """Hide target class information from the output.

        :return: Self for method chaining.
        """
        self._ctx.show_targets = False
        return self

    def show_deprecations(self) -> Self:
        """Show deprecation information in the output.

        :return: Self for method chaining.
        """
        self._ctx.show_deprecations = True
        return self

    def hide_deprecations(self) -> Self:
        """Hide deprecation information from the output.

        :return: Self for method chaining.
        """
        self._ctx.show_deprecations = False
        return self

    def show_types(self) -> Self:
        """Show type hint information in the output.

        :return: Self for method chaining.
        """
        self._ctx.show_types = True
        return self

    def hide_types(self) -> Self:
        """Hide type hint information from the output.

        :return: Self for method chaining.
        """
        self._ctx.show_types = False
        return self

    def show_descriptions(self) -> Self:
        """Show description information in the output.

        :return: Self for method chaining.
        """
        self._ctx.show_descriptions = True
        return self

    def hide_descriptions(self) -> Self:
        """Hide description information from the output.

        :return: Self for method chaining.
        """
        self._ctx.show_descriptions = False
        return self

    # --- Presets ---

    def minimal(self) -> Self:
        """Apply minimal preset: paths, files, and lines only.

        :return: Self for method chaining.
        """
        self._ctx.show_paths = True
        self._ctx.show_values = False
        self._ctx.show_files = True
        self._ctx.show_lines = True
        self._ctx.show_source_type = False
        self._ctx.show_chain = False
        self._ctx.show_overrides = False
        self._ctx.show_targets = False
        return self

    def compact(self) -> Self:
        """Apply compact preset: paths, values, files, lines, source type, targets, types.

        :return: Self for method chaining.
        """
        self._ctx.show_paths = True
        self._ctx.show_values = True
        self._ctx.show_files = True
        self._ctx.show_lines = True
        self._ctx.show_source_type = True
        self._ctx.show_chain = False
        self._ctx.show_overrides = False
        self._ctx.show_targets = True
        self._ctx.show_types = True
        self._ctx.show_descriptions = False
        return self

    def full(self) -> Self:
        """Apply full preset: show everything including types and descriptions.

        :return: Self for method chaining.
        """
        self._ctx.show_paths = True
        self._ctx.show_values = True
        self._ctx.show_files = True
        self._ctx.show_lines = True
        self._ctx.show_source_type = True
        self._ctx.show_chain = True
        self._ctx.show_overrides = True
        self._ctx.show_targets = True
        self._ctx.show_types = True
        self._ctx.show_descriptions = True
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
        elif preset == ProvenancePreset.HELP:
            return self.help()
        else:
            return self

    def help(self) -> Self:
        """Apply help preset: paths, types, values, and descriptions for CLI help.

        Shows: paths, types, values, descriptions
        Hides: files, lines, source_type, chain, overrides, targets, deprecations

        :return: Self for method chaining.

        Example::

            # Format provenance for CLI help display
            print(prov.format().help())
            # model.lr              float       0.001      Learning rate
            # model.hidden_size     int         256        Hidden layer size
        """
        self._ctx.show_paths = True
        self._ctx.show_types = True
        self._ctx.show_values = True
        self._ctx.show_descriptions = True
        self._ctx.show_files = False
        self._ctx.show_lines = False
        self._ctx.show_source_type = False
        self._ctx.show_chain = False
        self._ctx.show_overrides = False
        self._ctx.show_targets = False
        self._ctx.show_deprecations = False
        return self

    def deprecations(self) -> Self:
        """Apply deprecations preset: show only deprecated keys.

        This filters the output to only show entries that have deprecation
        information, displaying the deprecation details prominently.

        :return: Self for method chaining.

        Example::

            # Show only deprecated keys
            print(prov.format().deprecations())
            # Deprecated Keys:
            # ----------------
            # /learning_rate
            #   config.yaml:1
            #   DEPRECATED -> model.optimizer.lr (remove in 2.0.0)
            #   Message: Use 'model.optimizer.lr' instead
        """
        self._ctx.show_paths = True
        self._ctx.show_values = True
        self._ctx.show_files = True
        self._ctx.show_lines = True
        self._ctx.show_source_type = False
        self._ctx.show_chain = False
        self._ctx.show_overrides = False
        self._ctx.show_targets = False
        self._ctx.show_deprecations = True
        self._ctx.deprecations_only = True
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

    def __str__(self) -> str:
        """Format the provenance using the configured layout and options.

        :return: Formatted provenance string.
        """
        return self._layout.format_provenance(self._provenance, self._ctx)

    def __repr__(self) -> str:
        """Return a representation of this format builder.

        :return: String representation.
        """
        return f"ProvenanceFormat(layout={self._layout.__class__.__name__})"
