"""Tree-style layout for provenance formatting.

This module provides a tree layout that displays provenance
in a multiline format with tree connectors (+-- and |--).
"""

from __future__ import annotations

from typing import Any

from rconfig._internal.format_utils import format_type_hint, format_value, indent
from rconfig.deprecation.info import DeprecationInfo
from rconfig.provenance.models import EntrySourceType, InstanceRef

from .model import (
    InterpolationKind,
    InterpolationNodeDisplayModel,
    ProvenanceDisplayModel,
    ProvenanceEntryDisplayModel,
)
from .layout import ProvenanceLayout


class ProvenanceTreeLayout(ProvenanceLayout):
    """Tree-style text layout for provenance.

    Displays provenance in a multiline format with tree structures
    for interpolation chains, using +-- and |-- connectors.

    Example output::

        /model.lr = 0.01
          config.yaml:5
          Interpolation: ${/defaults.lr * 2}
            +-- * (multiply)
                 |-- /defaults.lr = 0.005
                 |     defaults.yaml:3
                 +-- 2 (literal)
          Overrode: base.yaml:10

    :param indent_size: Number of spaces per indentation level.
    """

    def __init__(self, indent_size: int = 2) -> None:
        """Initialize the tree layout.

        :param indent_size: Number of spaces per indentation level.
        """
        self._indent_size = indent_size

    def render(self, model: ProvenanceDisplayModel) -> str:
        """Render the provenance model to string output.

        :param model: The display model.
        :return: Formatted string representation.
        """
        # Handle empty/message cases
        if model.empty_message:
            return model.empty_message

        entries: list[str] = []
        for entry in model.entries:
            formatted = self._render_entry(entry)
            if formatted:
                entries.append(formatted)

        result = "\n\n".join(entries)

        # Add header if present (e.g., for deprecations mode)
        if model.header:
            result = model.header + "\n\n" + result

        return result

    def _render_entry(self, entry: ProvenanceEntryDisplayModel) -> str:
        """Render a single provenance entry.

        :param entry: The entry display model.
        :return: Formatted entry string.
        """
        lines: list[str] = []

        # First line: path = value
        first_line_parts: list[str] = []
        if entry.path is not None:
            first_line_parts.append(f"/{entry.path}")
        if entry.value is not None:
            if first_line_parts:
                first_line_parts.append(f" = {format_value(entry.value)}")
            else:
                first_line_parts.append(format_value(entry.value))

        if first_line_parts:
            lines.append("".join(first_line_parts))

        # Location line
        location = self._format_location(entry)
        if location:
            lines.append(indent(location, 1, self._indent_size))

        # Target info
        target_info = self._format_target_info(entry)
        if target_info:
            lines.append(indent(target_info, 1, self._indent_size))

        # Interpolation section
        if entry.interpolation_expression:
            lines.append(
                indent(f"Interpolation: ${{{entry.interpolation_expression}}}", 1, self._indent_size)
            )

        if entry.interpolation_tree:
            tree_lines = self._render_interpolation_tree(entry.interpolation_tree, 2)
            lines.extend(tree_lines)

        # Instance chain
        if entry.instances:
            for ref in entry.instances:
                instance_line = self._format_instance(ref)
                lines.append(indent(instance_line, 1, self._indent_size))

        # Override info
        if entry.overrode:
            lines.append(indent(f"Overrode: {entry.overrode}", 1, self._indent_size))

        # Deprecation lines
        if entry.deprecation:
            for line in self._format_deprecation(entry.deprecation):
                lines.append(indent(line, 1, self._indent_size))

        # Type hint
        if entry.type_hint is not None:
            lines.append(indent(self._format_type_hint(entry.type_hint), 1, self._indent_size))

        # Description
        if entry.description:
            lines.append(indent(f"Description: {entry.description}", 1, self._indent_size))

        return "\n".join(lines)

    def _format_location(self, entry: ProvenanceEntryDisplayModel) -> str | None:
        """Format location string for an entry.

        :param entry: The entry display model.
        :return: Formatted location string or None.
        """
        # Handle non-file source types specially
        if entry.source_type and entry.source_type != EntrySourceType.FILE:
            return self._format_source_type_location(entry)

        # Standard file:line format
        if entry.file and entry.line is not None:
            return f"{entry.file}:{entry.line}"
        if entry.file:
            return entry.file
        if entry.line is not None:
            return str(entry.line)
        return None

    def _format_source_type_location(
        self, entry: ProvenanceEntryDisplayModel
    ) -> str:
        """Format location for non-file source types.

        :param entry: The entry display model.
        :return: Formatted source type location.
        """
        source_marker = self._format_source_type(entry.source_type)
        match entry.source_type:
            case EntrySourceType.CLI if entry.cli_arg:
                return f"{source_marker}: {entry.cli_arg}"
            case EntrySourceType.ENV if entry.env_var:
                return f"{source_marker}: {entry.env_var}"
            case _:
                return source_marker

    def _format_source_type(self, source_type: EntrySourceType | None) -> str:
        """Format source type marker.

        :param source_type: The source type.
        :return: Formatted source type string.
        """
        match source_type:
            case EntrySourceType.CLI:
                return "CLI"
            case EntrySourceType.ENV:
                return "env"
            case EntrySourceType.PROGRAMMATIC:
                return "programmatic"
            case _:
                return ""

    def _format_target_info(
        self, entry: ProvenanceEntryDisplayModel
    ) -> str | None:
        """Format target class information.

        :param entry: The entry display model.
        :return: Formatted target string or None.
        """
        if entry.target_name is None:
            return None

        target_ref = self._format_target_reference(entry)
        suffix = " (auto-registered)" if entry.target_auto_registered else ""
        return f"Target: {entry.target_name}{target_ref}{suffix}"

    def _format_target_reference(
        self, entry: ProvenanceEntryDisplayModel
    ) -> str:
        """Format the target class reference.

        :param entry: The entry display model.
        :return: Formatted target reference.
        """
        if entry.target_class is None:
            return " (not registered)"
        if entry.target_module is not None:
            return f" -> {entry.target_module}.{entry.target_class}"
        return f" -> {entry.target_class}"

    def _format_instance(self, ref: InstanceRef) -> str:
        """Format an instance reference.

        :param ref: The instance reference.
        :return: Formatted instance line.
        """
        instance_line = f"Instance: {ref.path}"
        if ref.file and ref.line:
            instance_line += f" <- {ref.file}:{ref.line}"
        elif ref.file:
            instance_line += f" <- {ref.file}"
        return instance_line

    def _format_deprecation(self, deprecation: DeprecationInfo) -> list[str]:
        """Format deprecation information.

        :param deprecation: The deprecation info.
        :return: List of deprecation lines.
        """
        lines: list[str] = []

        # Main line: DEPRECATED -> new_key (remove in X.X.X)
        main_parts = ["DEPRECATED"]
        if deprecation.new_key:
            main_parts.append(f"-> {deprecation.new_key}")
        if deprecation.remove_in:
            main_parts.append(f"(remove in {deprecation.remove_in})")
        lines.append(" ".join(main_parts))

        # Message on separate line if present
        if deprecation.message:
            lines.append(f"Message: {deprecation.message}")

        return lines

    def _format_type_hint(self, type_hint: Any) -> str:
        """Format a type hint.

        :param type_hint: The type hint.
        :return: Formatted type hint string.
        """
        return format_type_hint(type_hint, prefix="Type")

    def _render_interpolation_tree(
        self,
        nodes: tuple[InterpolationNodeDisplayModel, ...],
        depth: int,
    ) -> list[str]:
        """Render interpolation tree nodes.

        :param nodes: Tuple of tree nodes.
        :param depth: Current depth for indentation.
        :return: List of formatted lines.
        """
        lines: list[str] = []

        for node in nodes:
            lines.extend(self._render_interpolation_node(node, depth))

        return lines

    def _render_interpolation_node(
        self,
        node: InterpolationNodeDisplayModel,
        depth: int,
    ) -> list[str]:
        """Render a single interpolation node.

        :param node: The node display model.
        :param depth: Current depth for indentation.
        :return: List of formatted lines.
        """
        lines: list[str] = []
        indent_str = " " * (depth * self._indent_size)

        # Build connector based on is_last
        connector = "+--" if node.is_last else "|--"

        # Build main line with display text
        main_line = f"{connector} {self._format_node_text(node)}"
        if node.value is not None:
            main_line += f" = {format_value(node.value)}"
        lines.append(indent_str + main_line)

        # Add location on next line if present
        if node.file is not None:
            location = f"{node.file}:{node.line}" if node.line else node.file
            continuation = "|" if connector == "|--" else " "
            lines.append(indent_str + f"{continuation}     {location}")

        # Render children
        if node.children:
            for child in node.children:
                child_lines = self._render_interpolation_node(child, depth + 1)
                lines.extend(child_lines)

        return lines

    def _format_node_text(self, node: InterpolationNodeDisplayModel) -> str:
        """Format the display text for an interpolation node.

        :param node: The node display model.
        :return: Formatted text for the node.
        """
        match node.kind:
            case InterpolationKind.ENV:
                return f"env:{node.text}"
            case _:
                return node.text

