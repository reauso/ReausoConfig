"""Provenance layout system for customizable formatting.

This module provides the base class for provenance layouts and the
FormatContext dataclass that holds runtime formatting settings.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .Provenance import Provenance, ProvenanceEntry, ProvenanceNode


@dataclass
class FormatContext:
    """Runtime settings passed from the builder to the layout.

    These settings control what information is displayed. The layout
    uses these flags to conditionally include/exclude components.

    :param show_paths: Show the config paths (e.g., /model.lr).
    :param show_values: Show resolved values.
    :param show_files: Show source file names.
    :param show_lines: Show line numbers.
    :param show_source_type: Show source type markers (CLI/env/file).
    :param show_chain: Show full provenance chain (refs, instances, interpolations).
    :param show_overrides: Show what was overridden.
    :param show_targets: Show target class information.
    :param show_deprecations: Show deprecation information.
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
    deprecations_only: bool = False
    indent_size: int = 2
    path_filters: list[str] = field(default_factory=list)
    file_filters: list[str] = field(default_factory=list)


class ProvenanceLayout(ABC):
    """Base class for provenance formatting layouts.

    A layout defines HOW to format provenance information, not WHAT to show.
    The WHAT is controlled by FormatContext flags set via the builder.

    Subclass this to create custom layouts (table, HTML, etc.).
    Override the methods you want to customize; the base implementations
    provide sensible defaults.

    Example::

        class TableLayout(ProvenanceLayout):
            def format_provenance(self, provenance, ctx):
                # Return table representation
                lines = [f"{p}: {e.file}:{e.line}" for p, e in provenance.items()]
                return "\\n".join(lines)

            def format_entry(self, entry, path, ctx):
                # Return table row format
                return f"| {path} | {entry.file}:{entry.line} |"
    """

    def get_default_context(self) -> FormatContext:
        """Return default show/hide settings for this layout.

        Override this to change what's shown by default for this layout.
        Builder methods will override these settings.

        :return: FormatContext with default settings.
        """
        return FormatContext()

    @abstractmethod
    def format_provenance(self, provenance: Provenance, ctx: FormatContext) -> str:
        """Format the entire provenance object.

        This is the main entry point called by ProvenanceFormat.__str__().

        :param provenance: The provenance object to format.
        :param ctx: Format context with show/hide settings.
        :return: Formatted string representation.
        """
        ...

    @abstractmethod
    def format_entry(
        self, entry: ProvenanceEntry, path: str, ctx: FormatContext
    ) -> str:
        """Format a single provenance entry.

        :param entry: The provenance entry to format.
        :param path: The config path for this entry.
        :param ctx: Format context with show/hide settings.
        :return: Formatted string for this entry.
        """
        ...

    def format_path(self, path: str, ctx: FormatContext) -> str:
        """Format a config path.

        :param path: The config path (e.g., "/model.lr").
        :param ctx: Format context.
        :return: Formatted path string.
        """
        return path

    def format_value(self, value: Any, ctx: FormatContext) -> str:
        """Format a resolved value.

        Override this to customize value display (truncation, colors, etc.).

        :param value: The resolved value.
        :param ctx: Format context.
        :return: Formatted value string.
        """
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, str):
            return repr(value)
        else:
            return str(value)

    def format_location(self, file: str, line: int, ctx: FormatContext) -> str:
        """Format file:line location.

        :param file: Source file name.
        :param line: Line number.
        :param ctx: Format context.
        :return: Formatted location string.
        """
        parts = []
        if ctx.show_files:
            parts.append(file)
        if ctx.show_lines:
            if parts:
                parts.append(f":{line}")
            else:
                parts.append(str(line))
        return "".join(parts)

    def format_source_type(self, source_type: str, ctx: FormatContext) -> str:
        """Format source type marker (CLI/env/file/programmatic).

        :param source_type: The source type.
        :param ctx: Format context.
        :return: Formatted source type string.
        """
        if source_type == "cli":
            return "CLI"
        elif source_type == "env":
            return "env"
        elif source_type == "programmatic":
            return "programmatic"
        else:
            return ""

    def format_chain(
        self, node: ProvenanceNode, depth: int, ctx: FormatContext
    ) -> str:
        """Format a single node in the provenance chain/tree.

        :param node: The provenance node to format.
        :param depth: Current depth in the tree (for indentation).
        :param ctx: Format context.
        :return: Formatted node string.
        """
        return str(node)

    def format_tree(self, root: ProvenanceNode, ctx: FormatContext) -> str:
        """Format the full provenance tree structure.

        :param root: Root node of the provenance tree.
        :param ctx: Format context.
        :return: Formatted tree string.
        """
        lines: list[str] = []
        self._format_tree_recursive(root, 0, lines, ctx)
        return "\n".join(lines)

    def _format_tree_recursive(
        self,
        node: ProvenanceNode,
        depth: int,
        lines: list[str],
        ctx: FormatContext,
    ) -> None:
        """Recursively format tree nodes.

        :param node: Current node.
        :param depth: Current depth.
        :param lines: List to append lines to.
        :param ctx: Format context.
        """
        lines.append(self.format_chain(node, depth, ctx))
        for child in node.children:
            self._format_tree_recursive(child, depth + 1, lines, ctx)

    def format_override(
        self, overrode: str, ctx: FormatContext
    ) -> str:
        """Format override information.

        :param overrode: The override info string (e.g., "file.yaml:10").
        :param ctx: Format context.
        :return: Formatted override string.
        """
        return f"Overrode: {overrode}"

    def join_entries(self, entries: list[str], ctx: FormatContext) -> str:
        """Join all formatted entries into final output.

        :param entries: List of formatted entry strings.
        :param ctx: Format context.
        :return: Combined output string.
        """
        return "\n".join(entries)

    def indent(self, text: str, depth: int, ctx: FormatContext) -> str:
        """Apply indentation to text.

        :param text: Text to indent.
        :param depth: Indentation depth.
        :param ctx: Format context with indent_size.
        :return: Indented text.
        """
        prefix = " " * (depth * ctx.indent_size)
        return prefix + text
