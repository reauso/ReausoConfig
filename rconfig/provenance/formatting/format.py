"""Fluent builder for provenance formatting.

This module provides the ProvenanceFormat builder class, ProvenancePreset
enum, and ProvenanceFormatContext for configuring how provenance is displayed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fnmatch import fnmatch
from typing import Any, Self

from rconfig.provenance.models import EntrySourceType, ProvenanceEntry
from rconfig.provenance.provenance import Provenance

from .layout import ProvenanceLayout
from .model import (
    InterpolationKind,
    InterpolationNodeDisplayModel,
    ProvenanceDisplayModel,
    ProvenanceDisplayModelBuilder,
)


@dataclass
class ProvenanceFormatContext:
    """Settings that control what information is displayed.

    These settings are used by ProvenanceRenderModelBuilder to determine
    what data to include in the render model.

    :param show_paths: Show the config paths (e.g., /model.lr).
    :param show_values: Show resolved values.
    :param show_files: Show source file names.
    :param show_lines: Show line numbers.
    :param show_source_type: Show source type markers (CLI/env/file).
    :param show_chain: Show full provenance chain (refs, instances, interpolations).
    :param show_overrides: Show what was overridden.
    :param show_targets: Show target class information.
    :param show_deprecations: Show deprecation information.
    :param show_types: Show type hint information.
    :param show_descriptions: Show description information.
    :param deprecations_only: Filter to show only deprecated keys.
    :param indent_size: Number of spaces per indentation level.
    :param path_filters: Glob patterns to filter by config path.
    :param file_filters: Glob patterns to filter by source file.
    """

    show_paths: bool = True
    show_values: bool = True
    show_files: bool = True
    show_lines: bool = True
    show_source_type: bool = True
    show_chain: bool = True
    show_overrides: bool = True
    show_targets: bool = True
    show_deprecations: bool = True
    show_types: bool = False
    show_descriptions: bool = False
    deprecations_only: bool = False
    indent_size: int = 2
    path_filters: list[str] = field(default_factory=list)
    file_filters: list[str] = field(default_factory=list)


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
        :param layout: Optional custom layout. Uses ProvenanceTreeLayout if None.
        """
        self._provenance = provenance
        self._layout = layout
        self._ctx = ProvenanceFormatContext()

    def _get_layout(self) -> ProvenanceLayout:
        """Get the layout, creating default ProvenanceTreeLayout if needed.

        :return: The layout instance.
        """
        if self._layout is None:
            from .tree import ProvenanceTreeLayout

            return ProvenanceTreeLayout(indent_size=self._ctx.indent_size)
        return self._layout

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
        # Build the display model (WHAT to show)
        model = self._build_model()

        # Render using the layout (HOW to show)
        layout = self._get_layout()
        return layout.render(model)

    def __repr__(self) -> str:
        """Return a representation of this format builder.

        :return: String representation.
        """
        layout = self._get_layout()
        return f"ProvenanceFormat(layout={layout.__class__.__name__})"

    # --- Model Building ---

    def _build_model(self) -> ProvenanceDisplayModel:
        """Build the display model from provenance data.

        This method handles all WHAT decisions: filtering entries,
        determining visibility, and populating the display model.

        :return: The display model ready for layout rendering.
        """
        builder = ProvenanceDisplayModelBuilder()

        for path, entry in self._provenance.items():
            # Apply filters
            if not self._matches_filters(path, entry):
                continue

            # Filter for deprecations_only mode
            if self._ctx.deprecations_only and entry.deprecation is None:
                continue

            # Build entry with visible fields only
            builder.add_entry(
                path=path if self._ctx.show_paths else None,
                value=entry.value if self._ctx.show_values else None,
                file=entry.file if self._ctx.show_files else None,
                line=entry.line if self._ctx.show_lines else None,
                source_type=entry.source_type if self._ctx.show_source_type else None,
                cli_arg=entry.cli_arg if self._ctx.show_source_type else None,
                env_var=entry.env_var if self._ctx.show_source_type else None,
                target_name=entry.target_name if self._ctx.show_targets else None,
                target_class=entry.target_class if self._ctx.show_targets else None,
                target_module=entry.target_module if self._ctx.show_targets else None,
                target_auto_registered=entry.target_auto_registered
                if self._ctx.show_targets
                else False,
                interpolation_expression=entry.interpolation.expression
                if self._ctx.show_chain and entry.interpolation
                else None,
                interpolation_tree=self._build_interpolation_tree(entry)
                if self._ctx.show_chain and entry.interpolation
                else None,
                instances=tuple(entry.instance)
                if self._ctx.show_chain and entry.instance
                else None,
                overrode=entry.overrode if self._ctx.show_overrides else None,
                deprecation=entry.deprecation
                if self._ctx.show_deprecations
                else None,
                type_hint=entry.type_hint if self._ctx.show_types else None,
                description=entry.description if self._ctx.show_descriptions else None,
            )

        # Set header/empty message for deprecations_only mode
        if self._ctx.deprecations_only:
            if builder._entries:  # Check if any entries were added
                builder.set_header("Deprecated Keys:\n" + "-" * 16)
            else:
                builder.set_empty_message("No deprecated keys found.")

        return builder.build()

    def _build_interpolation_tree(
        self, entry: ProvenanceEntry
    ) -> tuple[InterpolationNodeDisplayModel, ...] | None:
        """Build the interpolation tree nodes for an entry.

        :param entry: The provenance entry.
        :return: Tuple of interpolation node display models, or None.
        """
        if not entry.interpolation:
            return None

        return self._build_interpolation_nodes(
            entry.interpolation, is_root=True, is_last=True
        )

    def _build_interpolation_nodes(
        self,
        source: Any,  # InterpolationSource
        is_root: bool = False,
        is_last: bool = True,
    ) -> tuple[InterpolationNodeDisplayModel, ...]:
        """Build interpolation tree nodes recursively.

        :param source: The interpolation source.
        :param is_root: Whether this is the root node.
        :param is_last: Whether this is the last child.
        :return: Tuple of node display models.
        """
        match source.kind:
            case "expression" if source.operator:
                return self._build_expression_node(source, is_last)
            case "config":
                return self._build_config_node(source, is_last)
            case "env":
                return self._build_env_node(source, is_last)
            case "literal":
                return self._build_literal_node(source, is_last)
            case _:
                return ()

    def _build_expression_node(
        self, source: Any, is_last: bool
    ) -> tuple[InterpolationNodeDisplayModel, ...]:
        """Build an expression node with children.

        :param source: The interpolation source.
        :param is_last: Whether this is the last child.
        :return: Tuple containing the expression node.
        """
        children: list[InterpolationNodeDisplayModel] = []
        for i, child in enumerate(source.sources):
            child_is_last = i == len(source.sources) - 1
            child_nodes = self._build_interpolation_nodes(
                child, is_root=False, is_last=child_is_last
            )
            children.extend(child_nodes)

        return (
            InterpolationNodeDisplayModel(
                kind=InterpolationKind.EXPRESSION,
                is_last=is_last,
                text=source.operator,
                value=source.value if self._ctx.show_values else None,
                file=source.file if self._ctx.show_files else None,
                line=source.line if self._ctx.show_lines else None,
                children=tuple(children),
            ),
        )

    def _build_config_node(
        self, source: Any, is_last: bool
    ) -> tuple[InterpolationNodeDisplayModel, ...]:
        """Build a config reference node.

        :param source: The interpolation source.
        :param is_last: Whether this is the last child.
        :return: Tuple containing the config node.
        """
        return (
            InterpolationNodeDisplayModel(
                kind=InterpolationKind.CONFIG,
                is_last=is_last,
                text=source.path or "",
                value=source.value if self._ctx.show_values else None,
                file=source.file if self._ctx.show_files else None,
                line=source.line if self._ctx.show_lines else None,
                children=(),
            ),
        )

    def _build_env_node(
        self, source: Any, is_last: bool
    ) -> tuple[InterpolationNodeDisplayModel, ...]:
        """Build an environment variable node.

        :param source: The interpolation source.
        :param is_last: Whether this is the last child.
        :return: Tuple containing the env node.
        """
        return (
            InterpolationNodeDisplayModel(
                kind=InterpolationKind.ENV,
                is_last=is_last,
                text=source.env_var or "",
                value=source.value if self._ctx.show_values else None,
                file=None,
                line=None,
                children=(),
            ),
        )

    def _build_literal_node(
        self, source: Any, is_last: bool
    ) -> tuple[InterpolationNodeDisplayModel, ...]:
        """Build a literal value node.

        :param source: The interpolation source.
        :param is_last: Whether this is the last child.
        :return: Tuple containing the literal node.
        """
        return (
            InterpolationNodeDisplayModel(
                kind=InterpolationKind.LITERAL,
                is_last=is_last,
                text=str(source.value) if source.value is not None else "",
                value=None,  # Value is in text for literals
                file=None,
                line=None,
                children=(),
            ),
        )

    def _matches_filters(self, path: str, entry: ProvenanceEntry) -> bool:
        """Check if an entry matches the configured filters.

        :param path: The config path.
        :param entry: The provenance entry.
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

        # Check file filters (OR logic)
        if self._ctx.file_filters:
            file_match = any(
                fnmatch(entry.file, pattern) for pattern in self._ctx.file_filters
            )
            if not file_match:
                return False

        return True
